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

const express = require("express");
const app = express();
const config = require("./config.js");

const photoapp_db = require("./photoapp_db.js");
const {
  HeadBucketCommand,
  ListObjectsV2Command,
} = require("@aws-sdk/client-s3");
const {
  photoapp_s3,
  s3_bucket_name,
  s3_region_name,
} = require("./photoapp_s3.js");

// support larger image uploads/downloads:
app.use(express.json({ strict: false, limit: "50mb" }));

var startTime;

//
// main():
//
app.listen(config.service_port, () => {
  startTime = Date.now();
  console.log("**Web service running, listening on port", config.service_port);
  //
  // Configure AWS to use our config file:
  //
  process.env.AWS_SHARED_CREDENTIALS_FILE = config.photoapp_config;
});

//
// request for default page /
//
app.get("/", (req, res) => {
  try {
    console.log("**Call to /...");

    let uptime = Math.round((Date.now() - startTime) / 1000);

    res.json({
      status: "running",
      "uptime-in-secs": uptime,
      dbConnection: photoapp_db.state,
    });
  } catch (err) {
    console.log("**Error in /");
    console.log(err.message);

    res.status(500).json(err.message);
  }
});

//
// web service functions (API):
//

// System operations
let stats = require("./api_stats.js");
let bucket = require("./api_bucket.js");

// User management
let users = require("./api_users.js");
let user = require("./api_user.js");

// Client management
let clients = require("./api_clients.js");

// Project management
let projects = require("./api_projects.js");

// Asset management
let assets = require("./api_assets.js");
let asset = require("./api_asset.js");
let asset_post = require("./api_asset_post.js");
let asset_variant = require("./api_asset_variant.js");

// Special operations
let job = require("./api_job.js");
let cdn = require("./api_cdn.js");
let usage = require("./api_usage.js");

app.get("/stats", stats.get_stats);
app.get("/bucket", bucket.get_bucket);

app.get("/users", users.get_users);
app.put("/user", user.put_user);

app.get("/clients", clients.get_clients);
app.get("/client/:clientid", clients.get_client);
app.put("/client", clients.put_client);
app.delete("/client/:clientid", clients.delete_client);

app.get("/projects", projects.get_projects);
app.get("/project/:projectid", projects.get_project);
app.put("/project", projects.put_project);
app.delete("/project/:projectid", projects.delete_project);

app.get("/assets", assets.get_assets);
app.get("/asset/:assetid", asset.get_asset);
app.put("/asset/:assetid", asset.put_asset);
app.delete("/asset/:assetid", asset.delete_asset);
app.get("/asset/:assetid/download", asset.download_asset);
app.post("/asset/:projectid", asset_post.post_asset);

app.get("/asset/:assetid/variants", asset_variant.get_asset_variants);
app.get(
  "/asset/:assetid/variant/:variantid/download",
  asset_variant.download_variant
);

app.get("/asset/:assetid/cdn-urls", cdn.get_cdn_urls);

app.get("/job/:jobid", job.get_job);

app.get("/asset/:assetid/usage", usage.get_asset_usage);
app.get("/project/:projectid/usage", usage.get_project_usage);
app.get("/client/:clientid/usage", usage.get_client_usage);
app.get("/usage/top-assets", usage.get_top_assets);
