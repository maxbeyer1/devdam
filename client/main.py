#
# Client-side python app for photoapp, this time working with
# web service, which in turn uses AWS S3, RDS, and Rekognition
# to implement a simple photo application for photo analysis,
# storage, and viewing.
#
# Authors:
#
#   Max Beyer
#
#   Starter code: Prof. Joe Hummel
#   Northwestern University
#

import requests  # calling web service
import jsons  # relational-object mapping

import uuid
import pathlib
import logging
import sys
import os
import base64
import time

from configparser import ConfigParser


###################################################################
#
# classes
#
class User:
    userid: int
    email: str
    lastname: str
    firstname: str
    bucketfolder: str


class Client:
    clientid: int
    user: User
    clientname: str
    description: str
    created_at: str
    project_count: int
    asset_count: int


class Project:
    projectid: int
    client: Client
    projectname: str
    description: str
    created_at: str
    asset_count: int


class Asset:
    assetid: int
    assetname: str
    description: str
    bucketkey: str
    created_at: str
    project: Project
    client: Client


class BucketItem:
    Key: str
    LastModified: str
    ETag: str
    Size: int
    StorageClass: str


class Image:
    project_id: int
    asset_name: str
    bucket_key: str
    data: str  # base64 encoded


class ProcessingJob:
    jobid: int
    assetid: int
    assetname: str
    status: str
    created_at: str
    completed_at: str
    error_message: str
    variants_completed: int
    variants_total: int


class AssetVariant:
    variantid: int
    variant_type: str
    width: int
    height: int
    format: str
    quality: int
    filesize: int
    bucketkey: str
    cdn_url: str


class CDNUrls:
    asset_id: int
    asset_name: str
    variants: list
    html_snippets: dict


class UsageStats:
    last_accessed: str
    access_count: int
    last_referer: str
    unique_referers: int


class AssetUsage:
    assetid: int
    assetname: str
    usage: UsageStats


class ProjectUsageSummary:
    total_assets: int
    total_accesses: int
    last_accessed: str
    assets_accessed: int
    access_percentage: int


class ProjectUsage:
    projectid: int
    projectname: str
    summary: ProjectUsageSummary
    assets: list


class ClientUsageSummary:
    total_projects: int
    total_assets: int
    total_accesses: int
    last_accessed: str
    assets_accessed: int
    access_percentage: int


class ClientUsage:
    clientid: int
    clientname: str
    summary: ClientUsageSummary
    projects: list


class TopAsset:
    assetid: int
    assetname: str
    projectid: int
    projectname: str
    clientid: int
    clientname: str
    access_count: int
    last_accessed: str
    unique_referers: int


###################################################################
#
# helper functions
def handle_asset_error(res, url):
    """
    Checks response from an asset call and outputs the approriate error message 
    if the asset call fails, based on the status code.

    Parameters
    ----------
    res: response from web service
    url: url for calling the web service

    Returns
    -------
    0 if successful
    -1 if failed
    """
    if res.status_code != 200:
        # check if asset exists
        if res.status_code == 400:
            if res.json()["message"].lower() == "no such asset...":
                print("No such asset...")
                return -1
        # failed:
        print("Failed with status code:", res.status_code)
        print("url: " + url)
        if res.status_code in [400, 500]:  # we'll have an error message
            body = res.json()
            print("Error message:", body["message"])
        #
        return -1
    else:
        return 0


###################################################################
#
# web_service_get
#
# When calling servers on a network, calls can randomly fail.
# The better approach is to repeat at least N times (typically
# N=3), and then give up after N tries.
#
def web_service_get(url):
    """
    Submits a GET request to a web service at most 3 times, since 
    web services can fail to respond e.g. to heavy user or internet 
    traffic. If the web service responds with status code 200, 400 
    or 500, we consider this a valid response and return the response.
    Otherwise we try again, at most 3 times. After 3 attempts the 
    function returns with the last response.

    Parameters
    ----------
    url: url for calling the web service

    Returns
    -------
    response received from web service
    """

    try:
        retries = 0

        while True:
            response = requests.get(url)

            if response.status_code in [200, 400, 500]:
                #
                # we consider this a successful call and response
                #
                break

            #
            # failed, try again?
            #
            retries = retries + 1
            if retries < 3:
                # try at most 3 times
                time.sleep(retries)
                continue

            #
            # if get here, we tried 3 times, we give up:
            #
            break

        return response

    except Exception as e:
        print("**ERROR**")
        logging.error("web_service_get() failed:")
        logging.error("url: " + url)
        logging.error(e)
        return None


###################################################################
#
# web_service_put
#
def web_service_put(url, data):
    """
    Submits a PUT request to web service at most 3 times. 

    Parameters
    ----------
    url: url for calling the web service

    Returns
    -------
    response received from web service
    """

    try:
        retries = 0

        while True:
            response = requests.put(url, json=data)

            if response.status_code in [200, 400, 500]:
                # call successful
                break

            # retry
            retries = retries + 1
            if retries < 3:
                time.sleep(retries)
                continue

            # retry failed
            break

        return response

    except Exception as e:
        print("**ERROR**")
        logging.error("web_service_put() failed:")
        logging.error("url: " + url)
        logging.error(e)
        return None


###################################################################
#
# prompt
#
def prompt():
    """
    Prompts the user and returns the command number

    Parameters
    ----------
    None

    Returns
    -------
    Command number entered by user (0, 1, 2, ...)
    """

    try:
        print()
        print(">> Enter a command:")
        print("   0 => end")
        print("   1 => stats")
        print("   2 => users")
        print("   3 => assets")
        print("   4 => download")
        print("   5 => bucket contents")
        print("   6 => upload")
        print("   7 => add/update user")
        print("   8 => clients")
        print("   9 => client details")
        print("   10 => add/update client")
        print("   11 => delete client")
        print("   12 => projects")
        print("   13 => project details")
        print("   14 => add/update project")
        print("   15 => delete project")
        print("   16 => check processing job")
        print("   17 => get asset variants and CDN urls")
        print("   18 => get asset usage stats")
        print("   19 => get project usage stats")
        print("   20 => get client usage stats")
        print("   21 => get top assets by usage")
        print("   22 => download variant")

        cmd = int(input())
        return cmd

    except Exception as e:
        print("ERROR")
        print("ERROR: invalid input")
        print("ERROR")
        return -1


###################################################################
#
# stats
#
def stats(baseurl):
    """
    Prints out S3 and RDS info: bucket status, # of users and 
    assets in the database

    Parameters
    ----------
    baseurl: baseurl for web service

    Returns
    -------
    nothing
    """

    try:
        #
        # call the web service:
        #
        api = '/stats'
        url = baseurl + api

        # res = requests.get(url)
        res = web_service_get(url)

        #
        # let's look at what we got back:
        #
        if res.status_code != 200:
            # failed:
            print("Failed with status code:", res.status_code)
            print("url: " + url)
            if res.status_code in [400, 500]:  # we'll have an error message
                body = res.json()
                print("Error message:", body["message"])
            #
            return

        #
        # deserialize and extract stats:
        #
        body = res.json()
        #
        msg = body["message"]

        if msg != "success":
            print("Failed with message:", msg)
            return

        bucket_status = body["bucket_status"]
        num_users = body["users"]
        num_clients = body["clients"]
        num_projects = body["projects"]
        num_assets = body["assets"]
        #
        print(f"bucket status: {bucket_status}")
        print(f"# of users in DevDAM DB: {num_users}")
        print(f"# of clients in DevDAM DB: {num_clients}")
        print(f"# of projects in DevDAM DB: {num_projects}")
        print(f"# of assets in DevDAM DB: {num_assets}")

    except Exception as e:
        logging.error("stats() failed:")
        logging.error("url: " + url)
        logging.error(e)
        return


###################################################################
#
# users
#
def users(baseurl):
    """
    Prints out all the users in the database

    Parameters
    ----------
    baseurl: baseurl for web service

    Returns
    -------
    nothing
    """

    try:
        #
        # call the web service:
        #
        api = '/users'
        url = baseurl + api

        # res = requests.get(url)
        res = web_service_get(url)

        #
        # let's look at what we got back:
        #
        if res.status_code != 200:
            # failed:
            print("Failed with status code:", res.status_code)
            print("url: " + url)
            if res.status_code in [400, 500]:  # we'll have an error message
                body = res.json()
                print("Error message:", body["message"])
            #
            return

        #
        # deserialize and extract users:
        #
        body = res.json()
        #
        # let's map each dictionary into a User object:
        #
        users = []
        for row in body["data"]:
            user = jsons.load(row, User)
            users.append(user)

        if len(users) == 0:
            print("No users found...")
            return

        for user in users:
            print(f"User id: {user.userid}")
            print(f" Email: {user.email}")
            print(f" Name: {user.lastname}, {user.firstname}")
            print(f" Folder: {user.bucketfolder}")

    except Exception as e:
        logging.error("users() failed:")
        logging.error("url: " + url)
        logging.error(e)
        return


###################################################################
#
# assets
#
def assets(baseurl):
    """
    Prints out all the assets in the database

    Parameters
    ----------
    baseurl: baseurl for web service

    Returns
    -------
    nothing
    """

    try:
        #
        # call the web service:
        #
        api = '/assets'
        url = baseurl + api

        # res = requests.get(url)
        res = web_service_get(url)

        #
        # let's look at what we got back:
        #
        if res.status_code != 200:
            # failed:
            print("Failed with status code:", res.status_code)
            print("url: " + url)
            if res.status_code == 404:
                print("No assets found...")
                return
            if res.status_code in [400, 500]:  # we'll have an error message
                body = res.json()
                print("Error message:", body["message"])
            #
            return

        #
        # deserialize and extract assets:
        #
        body = res.json()

        #
        # let's map each dictionary into an Asset object:
        #
        assets = []
        for row in body["data"]:
            asset = jsons.load(row, Asset)
            assets.append(asset)

        for asset in assets:
            print(f"Asset id: {asset.assetid}")
            print(f" Asset name: {asset.assetname}")
            print(f" Description: {asset.description}")
            print(f" Bucket key: {asset.bucketkey}")
            print(f" Created at: {asset.created_at}")
            print(
                f" Project: {asset.project.projectname} ({asset.project.projectid})")
            print(
                f" Client: {asset.client.clientname} ({asset.client.clientid})")
            print()

    except Exception as e:
        logging.error("assets() failed:")
        logging.error("url: " + url)
        logging.error(e)
        return


###################################################################
#
# download
#
def download(baseurl):
    """
    Prompts the user for an asset id, and downloads
    that asset (image) from the bucket.

    Parameters
    ----------
    baseurl: baseurl for web service

    Returns
    -------
    nothing
    """

    try:
        print("Enter asset id>")
        assetid = input()

        #
        # call the web service:
        #
        api = '/asset'
        url = baseurl + api + '/' + assetid + '/download'

        # res = requests.get(url)
        res = web_service_get(url)
        if handle_asset_error(res, url) != 0:
            return

        #
        # deserialize and extract image:
        #
        body = res.json()

        # map result to Image object
        image = jsons.load(body, Image)

        print("project id:", image.project_id)
        print("asset name:", image.asset_name)
        print("bucket key:", image.bucket_key)

        # decode the base64 string into bytes
        image_bytes = base64.b64decode(image.data)

        outfile = open(image.asset_name, "wb")
        outfile.write(image_bytes)

        print(f"Downloaded from S3 and saved as '{image.asset_name}'")

    except Exception as e:
        logging.error("download() failed:")
        logging.error("url: " + url)
        logging.error(e)
        return


###################################################################
#
# bucket_contents
#
def bucket_contents(baseurl):
    """
    Prints out the contents of the S3 bucket

    Parameters
    ----------
    baseurl: baseurl for web service

    Returns
    -------
    nothing
    """

    try:
        #
        # call the web service:
        #
        api = '/bucket'
        url = baseurl + api

        #
        # we have to loop since data is returned page
        # by page:
        #
        lastkey = ""

        while True:
            #
            # make a request...
            # check status code, if failed break out of loop
            # any data? if not, break out of loop
            # display data
            #
            res = web_service_get(url)

            if res.status_code != 200:
                print("Failed with status code:", res.status_code)
                print("url: " + url)
                if res.status_code in [400, 500]:
                    body = res.json()
                    print("Error message:", body["message"])

                return

            # deserialize and extract bucket items
            body = res.json()

            # map to BucketItem objects
            items = []
            for row in body["data"]:
                item = jsons.load(row, BucketItem)
                items.append(item)

                print(f"Bucket key: {item.Key}")
                print(f" Last modified: {item.LastModified}")
                print(f" Size: {item.Size}")

                lastkey = item.Key

            # check if <12 items
            if len(items) < 12:
                # no more pages
                break

            #
            # prompt...
            # if 'y' then continue, else break
            #
            print("another page? [y/n]")
            answer = input()
            #
            if answer == 'y':
                # add parameter to url
                url = baseurl + api
                url += "?startafter=" + lastkey
                #
                continue
            else:
                break

    except Exception as e:
        logging.error("bucket_contents() failed:")
        logging.error("url: " + url)
        logging.error(e)
        return


###################################################################
#
# upload
#
def upload(baseurl):
    """
    Prompts the user for a local filename and user id, 
    and uploads that asset (image) to the user's folder 
    in the bucket. The asset is given a random, unique 
    name. The database is also updated to record the 
    existence of this new asset in S3.

    Parameters
    ----------
    baseurl: baseurl for web service

    Returns
    -------
    nothing
    """

    try:
        print("Enter local filename>")
        local_filename = input()

        if not pathlib.Path(local_filename).is_file():
            print(f"Local file '{local_filename}' does not exist...")
            return

        print("Enter project id>")
        projectid = input()

        print("Enter asset description (optional)>")
        description = input()

        # Processing options selection
        print("\nSelect processing options:")
        print("1 => Minimal (thumbnail only)")
        print("2 => Standard (thumbnail, medium, large)")
        print("3 => Comprehensive (thumbnail, small, medium, large, xl)")
        print("4 => Custom")
        print("Enter your choice (default: 2)>")

        choice = input() or "2"

        # Define format options
        formats = {
            "1": "webp",
            "2": "jpg",
            "3": "png"
        }

        # Default processing options
        processing_options = {
            "variants": []
        }

        if choice == "1":
            # Minimal
            processing_options["variants"] = [
                {"type": "thumbnail", "width": 200, "height": 200,
                    "format": "webp", "quality": 80}
            ]
        elif choice == "3":
            # Comprehensive
            processing_options["variants"] = [
                {"type": "thumbnail", "width": 200, "height": 200,
                    "format": "webp", "quality": 80},
                {"type": "small", "width": 400, "height": None,
                    "format": "webp", "quality": 85},
                {"type": "medium", "width": 800, "height": None,
                    "format": "webp", "quality": 85},
                {"type": "large", "width": 1600, "height": None,
                    "format": "webp", "quality": 90},
                {"type": "xl", "width": 2400, "height": None,
                    "format": "webp", "quality": 90}
            ]
        elif choice == "4":
            # Custom
            print("\nHow many variants would you like to create? (1-5)>")
            num_variants = int(input() or "1")
            num_variants = max(1, min(5, num_variants))

            for i in range(num_variants):
                print(f"\nVariant {i+1}:")

                print("Enter variant type (e.g., thumbnail, medium, large)>")
                variant_type = input() or f"variant_{i+1}"

                print("Enter width in pixels (leave blank for auto)>")
                width_input = input()
                width = int(width_input) if width_input else None

                print("Enter height in pixels (leave blank for auto)>")
                height_input = input()
                height = int(height_input) if height_input else None

                print("Select format:")
                print("1 => WebP (recommended)")
                print("2 => JPEG")
                print("3 => PNG")
                format_choice = input() or "1"
                format = formats.get(format_choice, "webp")

                print("Enter quality (1-100, recommended: 80-90)>")
                quality_input = input() or "85"
                quality = min(100, max(1, int(quality_input)))

                variant = {
                    "type": variant_type,
                    "width": width,
                    "height": height,
                    "format": format,
                    "quality": quality
                }

                processing_options["variants"].append(variant)
        else:
            # Standard (default)
            processing_options["variants"] = [
                {"type": "thumbnail", "width": 200, "height": 200,
                    "format": "webp", "quality": 80},
                {"type": "medium", "width": 800, "height": None,
                    "format": "webp", "quality": 85},
                {"type": "large", "width": 1600, "height": None,
                    "format": "webp", "quality": 90}
            ]

        # Ask if user for format pref
        if choice != "4":  # Skip if already customized
            print("\nWould you like to adjust the format for all variants? (y/n)>")
            change_format = input().lower() == "y"

            if change_format:
                print("Select format:")
                print("1 => WebP (recommended)")
                print("2 => JPEG")
                print("3 => PNG")
                format_choice = input() or "1"
                selected_format = formats.get(format_choice, "webp")

                # Update format for all variants
                for variant in processing_options["variants"]:
                    variant["format"] = selected_format

        #
        # build the data packet:
        #
        infile = open(local_filename, "rb")
        bytes = infile.read()
        infile.close()

        #
        # now encode the image as base64. Note b64encode returns
        # a bytes object, not a string. So then we have to convert
        # (decode) the bytes -> string, and then we can serialize
        # the string as JSON for upload to server:
        #
        data = base64.b64encode(bytes)
        datastr = data.decode()

        data = {
            "assetname": local_filename,
            "description": description,
            "data": datastr,
            "processing_options": processing_options
        }

        # Show options summary
        print("\nUploading with the following processing options:")
        for i, variant in enumerate(processing_options["variants"], 1):
            width_display = variant["width"] if variant["width"] else "auto"
            height_display = variant["height"] if variant["height"] else "auto"
            print(
                f"{i}. {variant['type']}: {width_display}x{height_display} {variant['format']} (quality: {variant['quality']})")

        #
        # call the web service:
        #
        api = '/asset'
        url = baseurl + api + "/" + projectid

        res = requests.post(url, json=data)

        #
        # let's look at what we got back:
        #
        if res.status_code != 200:
            # failed:
            print("Failed with status code:", res.status_code)
            print("url: " + url)
            if res.status_code in [400, 500]:  # we'll have an error message
                body = res.json()
                print("Error message:", body["message"])
            #
            return

        #
        # success, extract asset id:
        #
        body = res.json()

        asset_id = body["asset_id"]

        # Get processing job info if available
        processing_job = body.get("processing_job", {})
        job_id = processing_job.get("jobid", None)
        job_status = processing_job.get("status", "unknown")
        variants_total = processing_job.get("variants_total", 0)

        print(f"Image uploaded, asset id = {asset_id}")

        if job_id:
            print(f"Processing job created (ID: {job_id})")
            print(f"Status: {job_status}")
            print(f"Processing {variants_total} variants...")
            print("Use 'cmd 16 - check processing job' to monitor the job status.")

    except Exception as e:
        logging.error("upload() failed:")
        logging.error("url: " + url)
        logging.error(e)
        return


###################################################################
#
# add_user
#
def add_user(baseurl):
    """
    Prompts the user for the new user's email,
    last name, and first name, and then inserts
    this user into the database. But if the user's
    email already exists in the database, then we
    update the user's info instead of inserting
    a new user.

    Parameters
    ----------
    baseurl: baseurl for web service

    Returns
    -------
    nothing
    """

    try:
        print("Enter user's email>")
        email = input()

        print("Enter user's last (family) name>")
        last_name = input()

        print("Enter user's first (given) name>")
        first_name = input()

        # generate unique folder name:
        folder = str(uuid.uuid4())

        #
        # build the data packet:
        #
        data = {
            "email": email,
            "lastname": last_name,
            "firstname": first_name,
            "bucketfolder": folder
        }

        #
        # call the web service:
        #
        api = '/user'
        url = baseurl + api

        res = web_service_put(url, data)

        #
        # let's look at what we got back:
        #
        if res.status_code != 200:
            # failed:
            print("Failed with status code:", res.status_code)
            print("url: " + url)
            if res.status_code in [400, 500]:  # we'll have an error message
                body = res.json()
                print("Error message:", body["message"])
            #
            return

        #
        # success, extract userid:
        #
        body = res.json()

        user_id = body["user_id"]
        message = body["message"]

        print(f"User {user_id} successfully {message}")

    except Exception as e:
        logging.error("add_user() failed:")
        logging.error("url: " + url)
        logging.error(e)
        return


###################################################################
#
# clients
#
def clients(baseurl):
    """
    Prints out all the clients in the database

    Parameters
    ----------
    baseurl: baseurl for web service

    Returns
    -------
    nothing
    """

    try:
        api = '/clients'
        url = baseurl + api

        res = web_service_get(url)

        if res.status_code != 200:
            # failed:
            print("Failed with status code:", res.status_code)
            print("url: " + url)
            if res.status_code in [400, 500]:  # we'll have an error message
                body = res.json()
                print("Error message:", body["message"])
            #
            return

        body = res.json()

        # map to Client objects
        clients = []
        for row in body["data"]:
            client = jsons.load(row, Client)
            clients.append(client)

        if len(clients) == 0:
            print("No clients found...")
            return

        for client in clients:
            print(f"Client id: {client.clientid}")
            print(f" Name: {client.clientname}")
            print(f" Description: {client.description}")
            print(f" Created at: {client.created_at}")
            print(
                f" User: {client.user.firstname} {client.user.lastname} ({client.user.userid})")
            print()

    except Exception as e:
        logging.error("clients() failed:")
        logging.error("url: " + url)
        logging.error(e)
        return


###################################################################
#
# client_details
#
def client_details(baseurl):
    """
    Gets details for a specific client

    Parameters
    ----------
    baseurl: baseurl for web service

    Returns
    -------
    nothing
    """

    try:
        print("Enter client id>")
        clientid = input()

        api = '/client'
        url = baseurl + api + '/' + clientid

        res = web_service_get(url)

        if res.status_code != 200:
            # failed:
            print("Failed with status code:", res.status_code)
            print("url: " + url)
            if res.status_code == 404:
                print("No such client...")
                return
            if res.status_code in [400, 500]:  # we'll have an error message
                body = res.json()
                print("Error message:", body["message"])
            #
            return

        body = res.json()

        # map to client object
        client = jsons.load(body["data"], Client)

        print(f"Client id: {client.clientid}")
        print(f" Name: {client.clientname}")
        print(f" Description: {client.description}")
        print(f" Created at: {client.created_at}")
        print(
            f" User: {client.user.firstname} {client.user.lastname} ({client.user.userid})")
        print(f" Project count: {client.project_count}")
        print(f" Asset count: {client.asset_count}")

    except Exception as e:
        logging.error("client_details() failed:")
        logging.error("url: " + url)
        logging.error(e)
        return


###################################################################
#
# add_client
#
def add_client(baseurl):
    """
    Adds or updates a client

    Parameters
    ----------
    baseurl: baseurl for web service

    Returns
    -------
    nothing
    """

    try:
        print("Enter client id (leave blank for new client)>")
        clientid = input()

        print("Enter user id for this client>")
        userid = input()

        print("Enter client name>")
        clientname = input()

        print("Enter client description (optional)>")
        description = input()

        # build the data packet
        data = {
            "clientname": clientname,
            "description": description,
            "userid": userid
        }

        # add clientid if provided
        if clientid:
            data["clientid"] = clientid

        api = '/client'
        url = baseurl + api

        res = web_service_put(url, data)

        if res.status_code != 200:
            # failed:
            print("Failed with status code:", res.status_code)
            print("url: " + url)
            if res.status_code in [400, 500]:  # we'll have an error message
                body = res.json()
                print("Error message:", body["message"])
            #
            return

        body = res.json()

        client_id = body["clientid"]
        message = body["message"]

        print(f"Client {client_id}\n{message}")

    except Exception as e:
        logging.error("add_client() failed:")
        logging.error("url: " + url)
        logging.error(e)
        return


###################################################################
#
# delete_client
#
def delete_client(baseurl):
    """
    Deletes a client from the database

    Parameters
    ----------
    baseurl: baseurl for web service

    Returns
    -------
    nothing
    """

    try:
        print("Enter client id to delete>")
        clientid = input()

        #
        # call the web service:
        #
        api = '/client'
        url = baseurl + api + '/' + clientid

        res = requests.delete(url, timeout=10)

        if res.status_code != 200:
            # failed:
            print("Failed with status code:", res.status_code)
            print("url: " + url)
            if res.status_code == 400:
                body = res.json()
                print("Error message:", body["message"])
                if "cannot delete client with existing projects" in body["message"].lower():
                    print("NOTE: you must delete all projects for this client first")
            elif res.status_code == 404:
                print("No such client...")
            elif res.status_code in [400, 500]:  # we'll have an error message
                body = res.json()
                print("Error message:", body["message"])
            #
            return

        body = res.json()
        message = body["message"]
        print(message)

    except Exception as e:
        logging.error("delete_client() failed:")
        logging.error("url: " + url)
        logging.error(e)
        return


###################################################################
#
# projects
#
def projects(baseurl):
    """
    Prints out all projects or projects for a specific client

    Parameters
    ----------
    baseurl: baseurl for web service

    Returns
    -------
    nothing
    """

    try:
        print("Enter client id (leave blank for all projects)>")
        clientid = input()

        #
        # call the web service:
        #
        api = '/projects'
        url = baseurl + api

        # Add client filter if provided
        if clientid:
            url += f"?clientid={clientid}"

        res = web_service_get(url)

        #
        # let's look at what we got back:
        #
        if res.status_code != 200:
            # failed:
            print("Failed with status code:", res.status_code)
            print("url: " + url)
            if res.status_code in [400, 500]:  # we'll have an error message
                body = res.json()
                print("Error message:", body["message"])
            #
            return

        #
        # deserialize and extract projects:
        #
        body = res.json()

        #
        # let's map each dictionary into a Project object:
        #
        projects = []
        for row in body["data"]:
            project = jsons.load(row, Project)
            projects.append(project)

        if len(projects) == 0:
            print("No projects found...")
            return

        for project in projects:
            print(f"Project id: {project.projectid}")
            print(f" Name: {project.projectname}")
            print(f" Description: {project.description}")
            print(f" Created at: {project.created_at}")
            print(
                f" Client: {project.client.clientname} ({project.client.clientid})")
            print()

    except Exception as e:
        logging.error("projects() failed:")
        logging.error("url: " + url)
        logging.error(e)
        return


###################################################################
#
# project_details
#
def project_details(baseurl):
    """
    Gets details for a specific project

    Parameters
    ----------
    baseurl: baseurl for web service

    Returns
    -------
    nothing
    """

    try:
        print("Enter project id>")
        projectid = input()

        #
        # call the web service:
        #
        api = '/project'
        url = baseurl + api + '/' + projectid

        res = web_service_get(url)

        #
        # let's look at what we got back:
        #
        if res.status_code != 200:
            # failed:
            print("Failed with status code:", res.status_code)
            print("url: " + url)
            if res.status_code == 404:
                print("No such project...")
                return
            if res.status_code in [400, 500]:  # we'll have an error message
                body = res.json()
                print("Error message:", body["message"])
            #
            return

        #
        # deserialize and extract project data:
        #
        body = res.json()

        # map to project object
        project = jsons.load(body["data"], Project)

        print(f"Project id: {project.projectid}")
        print(f" Name: {project.projectname}")
        print(f" Description: {project.description}")
        print(f" Created at: {project.created_at}")
        print(
            f" Client: {project.client.clientname} ({project.client.clientid})")
        print(f" Asset count: {project.asset_count}")
        if hasattr(project, 'storage_used'):
            print(f" Storage used: {project.storage_used} bytes")

    except Exception as e:
        logging.error("project_details() failed:")
        logging.error("url: " + url)
        logging.error(e)
        return


###################################################################
#
# add_project
#
def add_project(baseurl):
    """
    Adds or updates a project

    Parameters
    ----------
    baseurl: baseurl for web service

    Returns
    -------
    nothing
    """

    try:
        print("Enter project id (leave blank for new project)>")
        projectid = input()

        print("Enter client id for this project>")
        clientid = input()

        print("Enter project name>")
        projectname = input()

        print("Enter project description (optional)>")
        description = input()

        #
        # build the data packet:
        #
        data = {
            "clientid": clientid,
            "projectname": projectname,
            "description": description
        }

        # Add projectid if provided
        if projectid:
            data["projectid"] = projectid

        #
        # call the web service:
        #
        api = '/project'
        url = baseurl + api

        res = web_service_put(url, data)

        #
        # let's look at what we got back:
        #
        if res.status_code != 200:
            # failed:
            print("Failed with status code:", res.status_code)
            print("url: " + url)
            if res.status_code in [400, 500]:  # we'll have an error message
                body = res.json()
                print("Error message:", body["message"])
            #
            return

        #
        # success, extract projectid:
        #
        body = res.json()

        project_id = body["projectid"]
        message = body["message"]

        print(f"Project {project_id}\n{message}")

    except Exception as e:
        logging.error("add_project() failed:")
        logging.error("url: " + url)
        logging.error(e)
        return


###################################################################
#
# delete_project
#
def delete_project(baseurl):
    """
    Deletes a project from the database

    Parameters
    ----------
    baseurl: baseurl for web service

    Returns
    -------
    nothing
    """

    try:
        print("Enter project id to delete>")
        projectid = input()

        #
        # call the web service:
        #
        api = '/project'
        url = baseurl + api + '/' + projectid

        res = requests.delete(url)

        #
        # let's look at what we got back:
        #
        if res.status_code != 200:
            # failed:
            print("Failed with status code:", res.status_code)
            print("url: " + url)
            if res.status_code == 400:
                body = res.json()
                print("Error message:", body["message"])
                if "cannot delete project with existing assets" in body["message"].lower():
                    print("NOTE: you must delete all assets for this project first")
            elif res.status_code == 404:
                print("No such project...")
            elif res.status_code in [400, 500]:  # we'll have an error message
                body = res.json()
                print("Error message:", body["message"])
            #
            return

        #
        # success
        #
        body = res.json()
        message = body["message"]
        print(message)

    except Exception as e:
        logging.error("delete_project() failed:")
        logging.error("url: " + url)
        logging.error(e)
        return


###################################################################
#
# check_processing_job
#
def check_processing_job(baseurl):
    """
    Checks the status of an asset processing job

    Parameters
    ----------
    baseurl: baseurl for web service

    Returns
    -------
    nothing
    """

    try:
        print("Enter job id>")
        jobid = input()

        api = '/job'
        url = baseurl + api + '/' + jobid

        res = web_service_get(url)

        if res.status_code != 200:
            # failed:
            print("Failed with status code:", res.status_code)
            print("url: " + url)
            if res.status_code == 404:
                print("No such job...")
                return
            if res.status_code in [400, 500]:  # we'll have an error message
                body = res.json()
                print("Error message:", body["message"])
            return

        body = res.json()

        job = jsons.load(body["data"], ProcessingJob)

        print(f"Job ID: {job.jobid}")
        print(f"Asset: {job.assetname} (ID: {job.assetid})")
        print(f"Status: {job.status}")
        print(f"Created: {job.created_at}")
        if job.completed_at:
            print(f"Completed: {job.completed_at}")
        if job.error_message:
            print(f"Error: {job.error_message}")
        print(
            f"Variants: {job.variants_completed} of {job.variants_total} completed")

    except Exception as e:
        logging.error("check_processing_job() failed:")
        logging.error("url: " + url)
        logging.error(e)
        return


###################################################################
#
# get_cdn_urls
#
def get_cdn_urls(baseurl):
    """
    Gets CDN URLs for an asset

    Parameters
    ----------
    baseurl: baseurl for web service

    Returns
    -------
    nothing
    """

    try:
        print("Enter asset id>")
        assetid = input()

        api = '/asset'
        url = baseurl + api + '/' + assetid + '/cdn-urls'

        res = web_service_get(url)

        if res.status_code != 200:
            # failed:
            print("Failed with status code:", res.status_code)
            print("url: " + url)
            if res.status_code == 404:
                print("No variants found for this asset...")
                return
            if res.status_code in [400, 500]:  # we'll have an error message
                body = res.json()
                print("Error message:", body["message"])
            return

        body = res.json()

        cdn_data = jsons.load(body["data"], CDNUrls)

        print(
            f"CDN URLs for asset: {cdn_data.asset_name} (ID: {cdn_data.asset_id})")
        print("\nVariants:")
        for variant in cdn_data.variants:
            print(
                f"- {variant['variant_type']}: {variant['width']}x{variant['height']} {variant['format']} (quality: {variant['quality']})")
            print(f"  Variant ID: {variant['variantid']}")
            print(f"  URL: {variant['cdn_url']}")

        print("\nHTML Snippets:")
        print("\n<img> tag with srcset:")
        print(cdn_data.html_snippets["img_tag"])

        print("\n<picture> element:")
        print(cdn_data.html_snippets["picture_tag"])

    except Exception as e:
        logging.error("get_cdn_urls() failed:")
        logging.error("url: " + url)
        logging.error(e)
        return


###################################################################
#
# download_variant
#
def download_variant(baseurl):
    """
    Prompts the user for an asset id and variant id, and downloads
    that variant from the bucket.

    Parameters
    ----------
    baseurl: baseurl for web service

    Returns
    -------
    nothing
    """

    try:
        print("Enter asset id>")
        assetid = input()

        print("Enter variant id>")
        variantid = input()

        api = '/asset'
        url = baseurl + api + '/' + assetid + '/variant/' + variantid + '/download'

        res = web_service_get(url)

        if res.status_code != 200:
            # failed:
            print("Failed with status code:", res.status_code)
            print("url: " + url)
            if res.status_code == 404:
                print("Variant not found...")
                return
            if res.status_code in [400, 500]:  # we'll have an error message
                body = res.json()
                print("Error message:", body["message"])
            return

        body = res.json()

        variant_type = body["variant_type"]
        asset_name = body["asset_name"]
        bucket_key = body["bucket_key"]
        image_data = body["data"]

        print("variant type:", variant_type)
        print("asset name:", asset_name)
        print("bucket key:", bucket_key)

        # Generate a filename that includes the variant type
        base_name = os.path.splitext(asset_name)[0]
        ext = bucket_key.split('.')[-1].lower()
        variant_filename = f"{base_name}_{variant_type}.{ext}"

        # decode the base64 string into bytes
        image_bytes = base64.b64decode(image_data)

        outfile = open(variant_filename, "wb")
        outfile.write(image_bytes)

        print(f"Downloaded variant from S3 and saved as '{variant_filename}'")

    except Exception as e:
        logging.error("download_variant() failed:")
        logging.error("url: " + url)
        logging.error(e)
        return


###################################################################
#
# asset_usage
#
def asset_usage(baseurl):
    """
    Gets usage statistics for an asset

    Parameters
    ----------
    baseurl: baseurl for web service

    Returns
    -------
    nothing
    """

    try:
        print("Enter asset id>")
        assetid = input()

        api = '/asset'
        url = baseurl + api + '/' + assetid + '/usage'

        res = web_service_get(url)

        if res.status_code != 200:
            # failed:
            print("Failed with status code:", res.status_code)
            print("url: " + url)
            if res.status_code == 404:
                print("Asset not found...")
                return
            if res.status_code in [400, 500]:  # we'll have an error message
                body = res.json()
                print("Error message:", body["message"])
            return

        body = res.json()

        usage_data = jsons.load(body["data"], AssetUsage)

        print(
            f"Usage statistics for asset: {usage_data.assetname} (ID: {usage_data.assetid})")

        if usage_data.usage.access_count == 0:
            print("This asset has not been accessed yet.")
            return

        print(f"Total accesses: {usage_data.usage.access_count}")
        print(f"Last accessed: {usage_data.usage.last_accessed}")
        print(f"Unique referrers: {usage_data.usage.unique_referers}")
        if usage_data.usage.last_referer:
            print(f"Last referrer: {usage_data.usage.last_referer}")

    except Exception as e:
        logging.error("asset_usage() failed:")
        logging.error("url: " + url)
        logging.error(e)
        return


###################################################################
#
# project_usage
#
def project_usage(baseurl):
    """
    Gets usage statistics for a project

    Parameters
    ----------
    baseurl: baseurl for web service

    Returns
    -------
    nothing
    """

    try:
        print("Enter project id>")
        projectid = input()

        api = '/project'
        url = baseurl + api + '/' + projectid + '/usage'

        res = web_service_get(url)

        if res.status_code != 200:
            # failed:
            print("Failed with status code:", res.status_code)
            print("url: " + url)
            if res.status_code == 404:
                print("Project not found...")
                return
            if res.status_code in [400, 500]:  # we'll have an error message
                body = res.json()
                print("Error message:", body["message"])
            return

        body = res.json()

        usage_data = jsons.load(body["data"], ProjectUsage)

        # Print nicely
        print(
            f"Usage statistics for project: {usage_data.projectname} (ID: {usage_data.projectid})")
        print("\nSummary:")
        print(f"Total assets: {usage_data.summary.total_assets}")
        print(f"Total accesses: {usage_data.summary.total_accesses}")
        print(
            f"Assets accessed: {usage_data.summary.assets_accessed} ({usage_data.summary.access_percentage}%)")

        if usage_data.summary.last_accessed:
            print(f"Last accessed: {usage_data.summary.last_accessed}")
        else:
            print("No assets have been accessed yet.")
            return

        print("\nAsset Details:")
        for asset in usage_data.assets:
            print(f"- {asset['assetname']} (ID: {asset['assetid']})")
            print(f"  Accesses: {asset['access_count']}")
            if asset['last_accessed']:
                print(f"  Last accessed: {asset['last_accessed']}")
            print(f"  Unique referrers: {asset['unique_referers']}")
            print()

    except Exception as e:
        logging.error("project_usage() failed:")
        logging.error("url: " + url)
        logging.error(e)
        return


###################################################################
#
# client_usage
#
def client_usage(baseurl):
    """
    Gets usage statistics for a client

    Parameters
    ----------
    baseurl: baseurl for web service

    Returns
    -------
    nothing
    """

    try:
        print("Enter client id>")
        clientid = input()

        api = '/client'
        url = baseurl + api + '/' + clientid + '/usage'

        res = web_service_get(url)

        if res.status_code != 200:
            # failed:
            print("Failed with status code:", res.status_code)
            print("url: " + url)
            if res.status_code == 404:
                print("Client not found...")
                return
            if res.status_code in [400, 500]:  # we'll have an error message
                body = res.json()
                print("Error message:", body["message"])
            return

        body = res.json()

        usage_data = jsons.load(body["data"], ClientUsage)

        print(
            f"Usage statistics for client: {usage_data.clientname} (ID: {usage_data.clientid})")
        print("\nSummary:")
        print(f"Total projects: {usage_data.summary.total_projects}")
        print(f"Total assets: {usage_data.summary.total_assets}")
        print(f"Total accesses: {usage_data.summary.total_accesses}")
        print(
            f"Assets accessed: {usage_data.summary.assets_accessed} ({usage_data.summary.access_percentage}%)")

        if usage_data.summary.last_accessed:
            print(f"Last accessed: {usage_data.summary.last_accessed}")
        else:
            print("No assets have been accessed yet.")
            return

        print("\nProject Details:")
        for project in usage_data.projects:
            print(f"- {project['projectname']} (ID: {project['projectid']})")
            print(f"  Assets: {project['asset_count']}")
            print(f"  Total accesses: {project['total_accesses']}")
            if project['last_accessed']:
                print(f"  Last accessed: {project['last_accessed']}")
            print()

    except Exception as e:
        logging.error("client_usage() failed:")
        logging.error("url: " + url)
        logging.error(e)
        return


###################################################################
#
# top_assets
#
def top_assets(baseurl):
    """
    Gets the top accessed assets across the system

    Parameters
    ----------
    baseurl: baseurl for web service

    Returns
    -------
    nothing
    """

    try:
        print("How many top assets to display? (default: 10)>")
        limit = input() or "10"

        api = '/usage/top-assets'
        url = baseurl + api + '?limit=' + limit

        res = web_service_get(url)

        if res.status_code != 200:
            # failed:
            print("Failed with status code:", res.status_code)
            print("url: " + url)
            if res.status_code in [400, 500]:  # we'll have an error message
                body = res.json()
                print("Error message:", body["message"])
            return

        body = res.json()

        top_assets_data = []
        for asset in body["data"]:
            top_asset = jsons.load(asset, TopAsset)
            top_assets_data.append(top_asset)

        if len(top_assets_data) == 0:
            print("No asset usage data available yet.")
            return

        print(f"Top {len(top_assets_data)} assets by access count:")
        print()

        for i, asset in enumerate(top_assets_data, 1):
            print(f"{i}. {asset.assetname} (ID: {asset.assetid})")
            print(f"   Project: {asset.projectname} (ID: {asset.projectid})")
            print(f"   Client: {asset.clientname} (ID: {asset.clientid})")
            print(f"   Access count: {asset.access_count}")
            print(f"   Last accessed: {asset.last_accessed}")
            print(f"   Unique referrers: {asset.unique_referers}")
            print()

    except Exception as e:
        logging.error("top_assets() failed:")
        logging.error("url: " + url)
        logging.error(e)
        return


#########################################################################
# main
#
try:
    print('** Welcome to devDAM **')
    print()

    # eliminate traceback so we just get error message:
    sys.tracebacklimit = 0

    #
    # what config file should we use for this session?
    #
    config_file = 'photoapp-client-config.ini'

    print("What config file to use for this session?")
    print("Press ENTER to use default (photoapp-client-config.ini),")
    print("otherwise enter name of config file>")
    s = input()

    if s == "":  # use default
        pass  # already set
    else:
        config_file = s

    #
    # does config file exist?
    #
    if not pathlib.Path(config_file).is_file():
        print("**ERROR: config file '", config_file,
              "' does not exist, exiting")
        sys.exit(0)

    #
    # setup base URL to web service:
    #
    configur = ConfigParser()
    configur.read(config_file)
    baseurl = configur.get('client', 'webservice')

    #
    # make sure baseurl does not end with /, if so remove:
    #
    if len(baseurl) < 16:
        print("**ERROR**")
        print("**ERROR: baseurl '", baseurl,
              "' in .ini file is empty or not nearly long enough, please fix")
        sys.exit(0)

    if baseurl.startswith('https'):
        print("**ERROR**")
        print("**ERROR: baseurl '", baseurl,
              "' in .ini file starts with https, which is not supported (use http)")
        sys.exit(0)

    lastchar = baseurl[len(baseurl) - 1]
    if lastchar == "/":
        baseurl = baseurl[:-1]

    # print(baseurl)

    #
    # main processing loop:
    #
    cmd = prompt()

    while cmd != 0:
        #
        if cmd == 1:
            stats(baseurl)
        elif cmd == 2:
            users(baseurl)
        elif cmd == 3:
            assets(baseurl)
        elif cmd == 4:
            download(baseurl)
        elif cmd == 5:
            bucket_contents(baseurl)
        elif cmd == 6:
            upload(baseurl)
        elif cmd == 7:
            add_user(baseurl)
        elif cmd == 8:
            clients(baseurl)
        elif cmd == 9:
            client_details(baseurl)
        elif cmd == 10:
            add_client(baseurl)
        elif cmd == 11:
            delete_client(baseurl)
        elif cmd == 12:
            projects(baseurl)
        elif cmd == 13:
            project_details(baseurl)
        elif cmd == 14:
            add_project(baseurl)
        elif cmd == 15:
            delete_project(baseurl)
        elif cmd == 16:
            check_processing_job(baseurl)
        elif cmd == 17:
            get_cdn_urls(baseurl)
        elif cmd == 18:
            asset_usage(baseurl)
        elif cmd == 19:
            project_usage(baseurl)
        elif cmd == 20:
            client_usage(baseurl)
        elif cmd == 21:
            top_assets(baseurl)
        elif cmd == 22:
            download_variant(baseurl)
        else:
            print("** Unknown command, try again...")
        #
        cmd = prompt()

    #
    # done
    #
    print()
    print('** done **')

except Exception as e:
    print("ERROR")
    print("ERROR:", str(e))
    print("ERROR")
