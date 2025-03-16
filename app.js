//
// Express js (and node.js) web service that interacts with 
// AWS S3 and RDS to provide clients data for building a 
// simple photo application for photo storage and viewing.
//
// Authors:
//  Max Beyer
//  Prof. Joe Hummel (initial template)
//  Northwestern University
//
// References:
// Node.js: 
//   https://nodejs.org/
// Express: 
//   https://expressjs.com/
// MySQL: 
//   https://expressjs.com/en/guide/database-integration.html#mysql
//   https://github.com/mysqljs/mysql
// AWS SDK with JS:
//   https://docs.aws.amazon.com/AWSJavaScriptSDK/v3/latest/index.html
//   https://docs.aws.amazon.com/sdk-for-javascript/v3/developer-guide/getting-started-nodejs.html
//   https://docs.aws.amazon.com/AWSJavaScriptSDK/v3/latest/clients/client-s3/
//   https://docs.aws.amazon.com/sdk-for-javascript/v3/developer-guide/javascript_s3_code_examples.html
//

const express = require('express');
const app = express();
const config = require('./config.js');

const photoapp_db = require('./photoapp_db.js')
const { HeadBucketCommand, ListObjectsV2Command } = require('@aws-sdk/client-s3');
const { photoapp_s3, s3_bucket_name, s3_region_name } = require('./photoapp_s3.js');

// support larger image uploads/downloads:
app.use(express.json({ strict: false, limit: "50mb" }));

var startTime;

//
// main():
//
app.listen(config.service_port, () => {
  startTime = Date.now();
  console.log('**Web service running, listening on port', config.service_port);
  //
  // Configure AWS to use our config file:
  //
  process.env.AWS_SHARED_CREDENTIALS_FILE = config.photoapp_config;
});

//
// request for default page /
//
app.get('/', (req, res) => {
  try {
    console.log("**Call to /...");
    
    let uptime = Math.round((Date.now() - startTime) / 1000);

    res.json({
      "status": "running",
      "uptime-in-secs": uptime,
      "dbConnection": photoapp_db.state
    });
  }
  catch(err) {
    console.log("**Error in /");
    console.log(err.message);

    res.status(500).json(err.message);
  }
});

//
// web service functions (API):
//
let stats = require('./api_stats.js');
let users = require('./api_users.js');
let assets = require('./api_assets.js');
let bucket = require('./api_bucket.js');
let download = require('./api_image_get.js');
let user = require('./api_user.js');
let upload = require('./api_image_post.js');

app.get('/stats', stats.get_stats);  
app.get('/users', users.get_users);  
app.get('/assets', assets.get_assets);  
app.get('/bucket', bucket.get_bucket);  
app.get('/image/:assetid', download.get_image);

app.put('/user', user.put_user);

app.post('/image/:userid', upload.post_image);
