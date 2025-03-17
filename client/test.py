#
# An example of a Python-based unit test for Project 02
# "search" functionality: GET /labels/:label
#
# Author:
#   Prof. Joe Hummel
#   Northwestern University
#   CS 310
#

import requests  
import jsons

import uuid
import pathlib
import sys
import os
import base64
import time

import unittest

from configparser import ConfigParser


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
        break;

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
    print("web_service_get() failed")
    print("url: '%s'", url)
    print("msg: %s", str(e))
    raise
  
  
############################################################
#
# Unit tests
#
class WebServiceTests(unittest.TestCase):
    #
    # NOTE: a unit test must start with "test" in order to be
    # discovered by Python's unit testing framework.
    #
    # unit test #1:
    #
    def test_search_1(self):
      print()
      print("** SEARCH TEST #1 (no images found) **")
      
      config_file = 'photoapp-client-config.ini'

      self.assertTrue(pathlib.Path(config_file).is_file())
      
      configur = ConfigParser()
      configur.read(config_file)
      baseurl = configur.get('client', 'webservice')

      #
      # call web service, confirm no images are returned...
      #
      print("calling web service to search...")
      
      label = "no-such-label-in-any-image"      
      
      api = '/images'
      url = baseurl + api + '/' + label

      response = web_service_get(url)
      
      #
      # should be a successful call with empty list:
      #
      status_code = response.status_code
      self.assertEqual(status_code, 200)
      
      body = response.json()
      
      message = body["message"]
      self.assertEqual(message, "success")
      
      returned_images = body["data"]      
      self.assertEqual(len(returned_images), 0)
      
      #
      # end of test
      #
      print("test passed!")        
      
      
    #
    # unit test #2:
    #
    def test_search_2(self):
      print()
      print("** SEARCH TEST #2 **")
      
      #
      # TODO
      #
             
      print("test passed!")  
      

    #
    # unit test #3:
    #
    def test_search_3(self):
      print()
      print("** SEARCH TEST #3 **")
      
      #
      # TODO
      #
             
      print("test passed!")  

      
############################################################
#
# main
#
unittest.main()
