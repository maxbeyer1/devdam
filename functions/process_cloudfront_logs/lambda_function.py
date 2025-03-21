import json
import gzip
import os
import re
import logging
import urllib.parse
import configparser
from datetime import datetime
import boto3

import datatier

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')

# Asset path pattern
# /userfolder/p1234/asset-uuid.jpg or /userfolder/p1234/variants/asset-uuid_thumbnail.webp
ASSET_PATTERN = r'/([^/]+)/p(\d+)/(?:variants/)?([^_/]+)(?:_[^.]+)?\.([^.]+)'

# Path to config file in Lambda
CONFIG_PATH = 'devdam-functions-config.ini'


def load_config():
    """Load configuration from INI file"""
    try:
        # Check if config file exists
        if not os.path.exists(CONFIG_PATH):
            logger.warning(
                f"Config file {CONFIG_PATH} not found, using environment variables")
            return {
                'endpoint': os.environ.get('DB_HOST'),
                'port_number': int(os.environ.get('DB_PORT', 3306)),
                'user_name': os.environ.get('DB_USER'),
                'user_pwd': os.environ.get('DB_PASSWORD'),
                'db_name': os.environ.get('DB_NAME')
            }

        # Read config file
        config = configparser.ConfigParser()
        config.read(CONFIG_PATH)

        # Return database configuration
        return {
            'endpoint': config['rds']['endpoint'],
            'port_number': int(config['rds']['port_number']),
            'user_name': config['rds']['user_name'],
            'user_pwd': config['rds']['user_pwd'],
            'db_name': config['rds']['db_name']
        }
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        raise


def get_db_connection():
    """Create a connection to the MySQL database using datatier"""
    try:
        # Load configuration
        config = load_config()

        # Create database connection
        conn = datatier.get_dbConn(
            endpoint=config['endpoint'],
            portnum=config['port_number'],
            username=config['user_name'],
            pwd=config['user_pwd'],
            dbname=config['db_name']
        )
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        raise


def parse_log_line(line):
    """Parse a single CloudFront log line"""
    # CloudFront log format:
    # https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/standard-logs-reference.html

    try:
        parts = line.strip().split('\t')

        # Check if line has enough parts to be valid
        if len(parts) < 15:
            return None

        # Extract timestamp, URI, and referer
        date_str = parts[0]
        time_str = parts[1]
        uri = parts[7]
        referer = parts[9] if parts[9] != '-' else None

        timestamp_str = f"{date_str} {time_str}"
        timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")

        # Decode the URI path
        uri_decoded = urllib.parse.unquote(uri)

        # Extract asset info from URI
        match = re.search(ASSET_PATTERN, uri_decoded)
        if not match:
            return None

        user_folder, project_id, asset_uuid, extension = match.groups()

        return {
            'timestamp': timestamp,
            'uri': uri_decoded,
            'referer': referer,
            'user_folder': user_folder,
            'project_id': project_id,
            'asset_uuid': asset_uuid,
            'extension': extension
        }
    except Exception as e:
        logger.warning(f"Error parsing log line: {e}")
        return None


def extract_asset_id_from_uri(dbConn, uri):
    """Map the URI path to an asset ID in the database"""
    try:
        # Extract the path pattern
        match = re.search(ASSET_PATTERN, uri)
        if not match:
            return None

        user_folder, project_id, asset_uuid_part, extension = match.groups()

        # Either direct match or contains the asset_uuid
        sql = """
        SELECT assetid 
        FROM assets 
        WHERE bucketkey = %s OR bucketkey LIKE %s
        """

        # Try an exact match first
        exact_key = f"{user_folder}/p{project_id}/{asset_uuid_part}.{extension}"
        # Then try a pattern match for variants
        pattern_key = f"{user_folder}/p{project_id}/%{asset_uuid_part}%"

        # Use datatier to execute query
        result = datatier.retrieve_one_row(
            dbConn, sql, [exact_key, pattern_key])

        if result and len(result) > 0:
            return result[0]

        # Try looking in variants
        sql_variant = """
        SELECT assetid 
        FROM asset_variants 
        WHERE bucketkey = %s OR bucketkey LIKE %s
        """

        # Use datatier to execute query
        result = datatier.retrieve_one_row(
            dbConn, sql_variant, [exact_key, pattern_key])

        return result[0] if result and len(result) > 0 else None

    except Exception as e:
        logger.warning(f"Error extracting asset ID from URI: {e}, URI: {uri}")
        return None


def update_asset_usage(dbConn, asset_id, timestamp, referer):
    """Update the asset_usage table with access information"""
    try:
        # Format timestamp for MySQL
        timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')

        # Check if the asset already has a usage record
        sql_check = "SELECT access_count, unique_referers, last_referer FROM asset_usage WHERE assetid = %s"
        existing = datatier.retrieve_one_row(dbConn, sql_check, [asset_id])

        if existing and len(existing) > 0:
            # Update existing record
            access_count, unique_referers, last_known_referer = existing

            # Increment referer count if this is a new one
            if referer and referer != last_known_referer:
                unique_referers += 1

            sql_update = """
            UPDATE asset_usage 
            SET access_count = access_count + 1, 
                last_accessed = %s,
                last_referer = CASE WHEN %s IS NOT NULL THEN %s ELSE last_referer END,
                unique_referers = %s
            WHERE assetid = %s
            """
            datatier.perform_action(dbConn, sql_update, [
                timestamp_str,
                referer,
                referer,
                unique_referers,
                asset_id
            ])
        else:
            # Create new record
            sql_insert = """
            INSERT INTO asset_usage 
            (assetid, last_accessed, access_count, last_referer, unique_referers) 
            VALUES (%s, %s, 1, %s, %s)
            """
            datatier.perform_action(dbConn, sql_insert, [
                asset_id,
                timestamp_str,
                referer,
                1 if referer else 0
            ])
    except Exception as e:
        logger.error(f"Error updating asset usage: {e}")
        raise


def process_log_file(bucket, key):
    """Process a single CloudFront log file from S3"""
    try:
        # Get the log file from S3
        response = s3.get_object(Bucket=bucket, Key=key)

        # CloudFront logs are gzipped
        if key.endswith('.gz'):
            content = gzip.decompress(response['Body'].read()).decode('utf-8')
        else:
            content = response['Body'].read().decode('utf-8')

        # Skip header lines (CloudFront logs have comments starting with #)
        lines = [line for line in content.splitlines()
                 if not line.startswith('#')]

        # Parse log entries
        log_entries = []
        for line in lines:
            entry = parse_log_line(line)
            if entry:
                log_entries.append(entry)

        # Connect to database
        dbConn = get_db_connection()

        # Process log entries
        asset_access_count = 0
        for entry in log_entries:
            # Try to map the URI to an asset ID
            asset_id = extract_asset_id_from_uri(dbConn, entry['uri'])

            if asset_id:
                # Update usage statistics
                update_asset_usage(
                    dbConn, asset_id, entry['timestamp'], entry['referer'])
                asset_access_count += 1

        # Close database connection
        dbConn.close()

        logger.info(
            f"Processed {len(log_entries)} log entries, updated {asset_access_count} asset usage records")
        return asset_access_count

    except Exception as e:
        logger.error(f"Error processing log file {key}: {e}")
        raise


def lambda_handler(event, context):
    """Lambda function entry point"""
    try:
        # Process each record in the event
        for record in event['Records']:
            # Get the S3 bucket and key
            bucket = record['s3']['bucket']['name']
            key = record['s3']['object']['key']

            logger.info(f"Processing log file: {bucket}/{key}")

            # Skip non-log files
            if not key.endswith('.gz') and not key.endswith('.log'):
                logger.info(f"Skipping non-log file: {key}")
                continue

            # Process the log file
            assets_updated = process_log_file(bucket, key)

            logger.info(
                f"Successfully processed {key}, updated {assets_updated} assets")

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f"Successfully processed {len(event['Records'])} log files"
            })
        }
    except Exception as e:
        logger.error(f"Error processing event: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': f"Error: {str(e)}"
            })
        }
