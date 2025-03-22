# Digital Asset Manager (DAM)

A multi-tier application for managing digital assets with automated image processing, CDN integration, and usage tracking capabilities.

## Setup Guide

### AWS Infrastructure Setup

#### Database

- Create an RDS MySQL database instance
- Use the provided schema file to create tables
- Configure security group to allow access from Lambda and Elastic Beanstalk (also local for testing)

#### S3 Buckets

- Create primary bucket for storing assets
- Create second bucket for CloudFront logs
- Configure CORS to allow access from your domains
- Add lifecycle rules for logs (30-day expiration)

#### IAM Roles

- Create roles for Lambda with S3 and RDS access
- Create service role and EC2 role for Elastic Beanstalk

#### Lambda Functions

1. Image Processing Function

   - Runtime: Python 3.12+
   - Trigger: S3 upload events on the main bucket
   - Dependencies: PIL, pymysql

2. Log Processing Function
   - Runtime: Python 3.12+
   - Trigger: S3 upload events on the logs bucket
   - Dependencies: pymysql

#### CloudFront

- Create distribution with S3 origin
- Enable logging to the logs bucket (use prefix `cloudfront-logs/`)

### Backend Deployment (Elastic Beanstalk)

1. Make a `web-service` folder with all .js files and `package.json` in it (rename `package.web-service.json` to `package.json`).

2. Create Elastic Beanstalk application

   - Platform: Node.js
   - Place in same VPC as RDS

3. Upload `web-service` folder as a zip file.

### Client Setup

Read the `readme.txt` in the `client` folder for platform-specific instructions.
