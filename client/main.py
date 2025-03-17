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
    userid: int  # these must match columns from DB table
    email: str
    lastname: str
    firstname: str
    bucketfolder: str


class Client:
    clientid: int
    userid: int
    clientname: str
    description: str
    created_at: str


class Project:
    projectid: int
    clientid: int
    projectname: str
    description: str
    created_at: str


class Asset:
    assetid: int  # these must match columns from DB table
    userid: int
    projectid: int
    assetname: str
    description: str
    bucketkey: str
    created_at: str


class BucketItem:
    Key: str
    LastModified: str
    ETag: str
    Size: int
    StorageClass: str


class Image:
    user_id: int
    asset_name: str
    bucket_key: str
    data: str  # base64 encoded


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
        #
        # Now we can think OOP:
        #
        for asset in assets:
            print(f"Asset id: {asset.assetid}")
            print(f" User id: {asset.userid}")
            print(f" Asset name: {asset.assetname}")
            print(f" Bucket key: {asset.bucketkey}")

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
        api = '/image'
        url = baseurl + api + '/' + assetid

        # res = requests.get(url)
        res = web_service_get(url)

        #
        # let's look at what we got back:
        #
        if handle_asset_error(res, url) != 0:
            return

        #
        # deserialize and extract image:
        #
        body = res.json()

        # map result to Image object
        image = jsons.load(body, Image)

        print("userid:", image.user_id)
        print("asset name:", image.asset_name)
        print("bucket key:", image.bucket_key)

        # decode the base64 string into bytes
        bytes = base64.b64decode(image.data)

        #
        # write the binary data to a file (as a
        # binary file, not a text file):
        #
        outfile = open(image.asset_name, "wb")
        outfile.write(bytes)

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

        print("Enter user id>")
        userid = input()

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

        data = {"assetname": local_filename, "data": datastr}

        #
        # call the web service:
        #
        api = '/image'
        url = baseurl + api + "/" + userid

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
        # success, extract userid:
        #
        body = res.json()

        asset_id = body["asset_id"]

        print(f"Image uploaded, asset id = {asset_id}")

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


#########################################################################
# main
#
try:
    print('** Welcome to Multi-tier PhotoApp **')
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
