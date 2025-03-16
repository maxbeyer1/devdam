//
// app.get('/image/:assetid', async (req, res) => {...});
//
// downloads an asset from S3 bucket and sends it back to the
// client as a base64-encoded string.
//
const photoapp_db = require('./photoapp_db.js')
const { GetObjectCommand } = require('@aws-sdk/client-s3');
const { photoapp_s3, s3_bucket_name, s3_region_name } = require('./photoapp_s3.js');
const { query_database } = require('./utility.js');

exports.get_image = async (req, res) => {

  console.log("**Call to get /image/:assetid...");

  try {
    // get the assetid from the request
    let assetid = req.params.assetid;

    // validate assetid
    if (isNaN(assetid)) {
      res.status(400).json({
        "message": "No such asset...",
        "user_id": -1,
        "asset_name": "?",
        "bucket_key": "?",
        "data": []
      });
      return;
    }

    // query database for asset
    let sql = `
        Select userid, assetname, bucketkey From assets
        Where assetid = ${assetid};
        `;
    
    console.log("/image: calling DB to get asset...");

    let db_results = await query_database(photoapp_db, sql);

    console.log("/image: got results from DB");

    let userid = -1;
    let assetname = "?";
    let bucketkey = "?";

    if (db_results.length == 1) {
      // extract results
      let asset = db_results[0];
      userid = asset.userid;
      assetname = asset.assetname;
      bucketkey = asset.bucketkey;
    } else {
      res.status(400).json({
        "message": "No such asset...",
        "user_id": userid,
        "asset_name": assetname,
        "bucket_key": bucketkey,
        "data": []
      });
      return;
    }

    // build input object for S3 with request parameters
    let input = {
      Bucket: s3_bucket_name,
      Key: bucketkey
    };

    console.log("/image: calling S3...");

    let command = new GetObjectCommand(input);
    let s3_results = await photoapp_s3.send(command);

    console.log("/image: got results from S3");

    // extract results
    let s3_body = s3_results.Body;

    // convert to base64 string
    var datastr = await s3_body.transformToString("base64");

    res.json({
      "message": "success",
      "user_id": userid,
      "asset_name": assetname,
      "bucket_key": bucketkey,
      "data": datastr
    });

    //
    // TODO
    //
    // MySQL in JS:
    //   https://expressjs.com/en/guide/database-integration.html#mysql
    //   https://github.com/mysqljs/mysql
    // AWS:
    //   https://docs.aws.amazon.com/sdk-for-javascript/v3/developer-guide/javascript_s3_code_examples.html
    //   https://docs.aws.amazon.com/AWSJavaScriptSDK/v3/latest/clients/client-s3/classes/getobjectcommand.html
    //   https://docs.aws.amazon.com/AWSJavaScriptSDK/v3/latest/clients/client-s3/
    //
    

  }//try
  catch (err) {
    console.log("**Error in /image");
    console.log(err.message);
    
    res.status(500).json({
      "message": err.message,
      "user_id": -1,
      "asset_name": "?",
      "bucket_key": "?",
      "data": []
    });
  }//catch

}//get