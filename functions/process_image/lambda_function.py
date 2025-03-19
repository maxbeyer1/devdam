import json
import os
import configparser
from io import BytesIO
import logging
import boto3
from PIL import Image
import datatier

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')

# Constants
CONFIG_FILE = 'devdam-functions-config.ini'
# Default to S3 domain if not specified
CDN_DOMAIN = os.environ.get(
    'CDN_DOMAIN', 'dam-assets-beyer-cs310.s3.us-east-2.amazonaws.com')


def get_db_connection():
    try:
        # Parse config file
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE)

        # Extract database connection parameters
        endpoint = config['rds']['endpoint']
        port_number = int(config['rds']['port_number'])
        user_name = config['rds']['user_name']
        user_pwd = config['rds']['user_pwd']
        db_name = config['rds']['db_name']

        # Get database connection using datatier
        conn = datatier.get_dbConn(
            endpoint, port_number, user_name, user_pwd, db_name)
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        return None


# Update job status
def update_job_status(conn, job_id, status, error_message=None):
    try:
        if status == 'completed' or status == 'failed':
            if error_message:
                sql = """
                    UPDATE processing_jobs 
                    SET status = %s, completed_at = NOW(), error_message = %s 
                    WHERE jobid = %s
                """
                datatier.perform_action(
                    conn, sql, [status, error_message, job_id])
            else:
                sql = """
                    UPDATE processing_jobs 
                    SET status = %s, completed_at = NOW() 
                    WHERE jobid = %s
                """
                datatier.perform_action(conn, sql, [status, job_id])
        else:
            sql = """
                UPDATE processing_jobs 
                SET status = %s 
                WHERE jobid = %s
            """
            datatier.perform_action(conn, sql, [status, job_id])

        logger.info(f"Updated job {job_id} status to {status}")
    except Exception as e:
        logger.error(f"Error updating job status: {e}")
        raise


# Create a variant record in the database
def create_variant_record(conn, asset_id, variant_type, width, height, format, quality, filesize, bucket_key):
    try:
        cdn_url = f"https://{CDN_DOMAIN}/{bucket_key}"
        sql = """
            INSERT INTO asset_variants 
            (assetid, variant_type, width, height, format, quality, filesize, bucketkey, cdn_url) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        parameters = [
            asset_id, variant_type, width, height, format, quality,
            filesize, bucket_key, cdn_url
        ]

        rows_affected = datatier.perform_action(conn, sql, parameters)

        if rows_affected > 0:
            # Get the last inserted ID (variant ID)
            id_sql = "SELECT LAST_INSERT_ID()"
            variant_id = datatier.retrieve_one_row(conn, id_sql)[0]
            return variant_id
        else:
            return None
    except Exception as e:
        logger.error(f"Error creating variant record: {e}")
        raise


# Process an image to create a variant
def create_image_variant(image, variant_config):
    try:
        # Extract variant parameters
        variant_type = variant_config.get('type', 'custom')
        width = variant_config.get('width')
        height = variant_config.get('height')
        format = variant_config.get('format', 'webp').lower()
        quality = variant_config.get('quality', 85)

        # Make a copy of the image to avoid modifying the original
        img = image.copy()

        # Image resizing
        if width or height:
            # Calculate new dimensions maintaining aspect ratio
            orig_width, orig_height = img.size
            if width and height:
                # Both dimensions specified: resize exactly
                new_size = (width, height)
            elif width:
                # Only width specified: maintain aspect ratio
                ratio = width / orig_width
                new_size = (width, int(orig_height * ratio))
            else:
                # Only height specified: maintain aspect ratio
                ratio = height / orig_height
                new_size = (int(orig_width * ratio), height)

            # Resize image
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        output = BytesIO()

        # Save with correct format and quality
        if format == 'jpeg' or format == 'jpg':
            # Convert to RGB if needed for JPEG
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            img.save(output, format='JPEG', quality=quality, optimize=True)
        elif format == 'png':
            img.save(output, format='PNG', optimize=True)
        elif format == 'webp':
            img.save(output, format='WEBP', quality=quality)
        elif format == 'gif':
            img.save(output, format='GIF')
        else:
            # Default to WebP
            img.save(output, format='WEBP', quality=quality)

        output.seek(0)
        return {
            'data': output.getvalue(),
            'width': img.width,
            'height': img.height,
            'format': format,
            'quality': quality,
            'filesize': len(output.getvalue())
        }
    except Exception as e:
        logger.error(f"Error creating image variant: {e}")
        raise


def lambda_handler(event, context):
    # Get S3 bucket and key
    try:
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = event['Records'][0]['s3']['object']['key']
        logger.info(f"Processing new image: {bucket}/{key}")
    except Exception as e:
        logger.error(f"Error extracting bucket and key from event: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

    # Check if this is an original asset
    if '/variants/' in key:
        logger.info(f"Skipping variant file: {key}")
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Skipped variant file'})
        }

    # Connect to database
    conn = get_db_connection()
    if not conn:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Could not connect to database'})
        }

    try:
        # Get the asset metadata from S3
        response = s3.head_object(Bucket=bucket, Key=key)
        metadata = response.get('Metadata', {})

        # Extract metadata
        asset_id_from_metadata = metadata.get('assetid')

        # Get asset information from database
        sql = """
            SELECT a.assetid, a.projectid, a.userid, a.bucketkey 
            FROM assets a 
            WHERE a.bucketkey = %s
        """
        asset_row = datatier.retrieve_one_row(conn, sql, [key])

        if not asset_row:
            logger.error(f"Asset not found for key: {key}")
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Asset not found'})
            }

        asset = {
            'assetid': asset_row[0],
            'projectid': asset_row[1],
            'userid': asset_row[2],
            'bucketkey': asset_row[3]
        }

        # Get processing job and options
        job_sql = """
            SELECT j.jobid, j.processing_options 
            FROM processing_jobs j 
            WHERE j.assetid = %s AND j.status = 'pending'
            ORDER BY j.created_at DESC 
            LIMIT 1
        """
        job_row = datatier.retrieve_one_row(conn, job_sql, [asset['assetid']])

        if not job_row:
            logger.error(
                f"No pending processing job found for asset: {asset['assetid']}")
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'No pending processing job found'})
            }

        job_id = job_row[0]
        processing_options_str = job_row[1]

        # Parse processing options
        if processing_options_str:
            processing_options = json.loads(processing_options_str)
        else:
            # TODO: Remove default, this is just for testing
            # Default processing options if none specified
            processing_options = {
                'variants': [
                    {'type': 'thumbnail', 'width': 200, 'height': 200,
                        'format': 'webp', 'quality': 80}
                ]
            }

        # Update job status to processing
        update_job_status(conn, job_id, 'processing')

        # Download the original image
        response = s3.get_object(Bucket=bucket, Key=key)
        image_data = response['Body'].read()

        # Open image with PIL
        image = Image.open(BytesIO(image_data))
        logger.info(
            f"Original image size: {image.size}, format: {image.format}")

        # Get file extension for variants
        original_ext = os.path.splitext(key)[1].lower()

        # Process variants
        variants_created = 0
        variants_failed = 0
        error_messages = []

        # Create variants folder path
        base_path = os.path.dirname(key)
        variants_base_path = f"{base_path}/variants"

        for variant_config in processing_options.get('variants', []):
            try:
                # Generate variant
                variant = create_image_variant(image, variant_config)

                variant_type = variant_config.get('type', 'custom')
                variant_format = variant_config.get('format', 'webp').lower()
                variant_ext = f".{variant_format}"
                variant_filename = f"{os.path.basename(key).split('.')[0]}_{variant_type}{variant_ext}"
                variant_key = f"{variants_base_path}/{variant_filename}"

                # Upload variant to S3
                content_type = f"image/{variant_format}"
                if variant_format == 'jpg':
                    content_type = 'image/jpeg'

                s3.put_object(
                    Bucket=bucket,
                    Key=variant_key,
                    Body=variant['data'],
                    ContentType=content_type,
                    ACL='public-read',
                    Metadata={
                        'assetid': str(asset['assetid']),
                        'varianttype': variant_type
                    }
                )

                # Create variant record in database
                variant_id = create_variant_record(
                    conn,
                    asset['assetid'],
                    variant_type,
                    variant['width'],
                    variant['height'],
                    variant_format,
                    variant['quality'],
                    variant['filesize'],
                    variant_key
                )

                if variant_id:
                    variants_created += 1
                    logger.info(
                        f"Created variant: {variant_type}, id: {variant_id}")
                else:
                    variants_failed += 1
                    error_messages.append(
                        f"Failed to create database record for variant: {variant_type}")

            except Exception as e:
                variants_failed += 1
                error_msg = f"Error processing variant {variant_config.get('type', 'unknown')}: {str(e)}"
                error_messages.append(error_msg)
                logger.error(error_msg)

        # Update job status based on results
        if variants_failed > 0 and variants_created == 0:
            update_job_status(conn, job_id, 'failed',
                              "; ".join(error_messages[:3]))
        elif variants_failed > 0:
            update_job_status(conn, job_id, 'completed',
                              f"Partial success: {variants_created} created, {variants_failed} failed")
        else:
            update_job_status(conn, job_id, 'completed')

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Processing complete',
                'asset_id': asset['assetid'],
                'job_id': job_id,
                'variants_created': variants_created,
                'variants_failed': variants_failed
            })
        }

    except Exception as e:
        logger.error(f"Unhandled error: {str(e)}")
        if 'job_id' in locals():
            update_job_status(conn, job_id, 'failed', str(e)[:250])

        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

    finally:
        if conn:
            conn.close()
