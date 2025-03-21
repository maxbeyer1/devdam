#!/bin/bash
#

# Install dependencies
pip install pymysql -t . --platform=manylinux2014_x86_64 --only-binary=:all: --upgrade

# Zip the contents
zip -r lambda_deployment.zip . -x ".gitignore" -x "deploy.sh"