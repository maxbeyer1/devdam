//
// app.get('/bucket?startafter=bucketkey', async (req, res) => {...});
//
// Retrieves the contents of the S3 bucket and returns the 
// information about each asset to the client. Note that it
// returns 12 at a time, use startafter query parameter to pass
// the last bucketkey and get the next set of 12, and so on.
//
const { ListObjectsV2Command } = require('@aws-sdk/client-s3');
const { photoapp_s3, s3_bucket_name, s3_region_name } = require('./photoapp_s3.js');
const { query_database } = require('./utility.js');

exports.get_bucket = async (req, res) => {

  console.log("**Call to get /bucket...");

  try {
    // get the startafter query parameter, if any
    let startafter = req.query.startafter;
    console.log("startafter: " + startafter);

    // build input object for S3 with request parameters
    let input = {
      Bucket: s3_bucket_name,
      MaxKeys: 12
    };

    if (startafter) {
      input.StartAfter = startafter;
    }

    console.log("/bucket: calling S3...");

    let command = new ListObjectsV2Command(input);
    let results = await photoapp_s3.send(command);

    console.log("/bucket: got results from S3");
    
    // extract results
    if (results.KeyCount > 0) {
      let assets = results.Contents;

      res.json({
        "message": "success",
        "data": assets
      });
    } else {
      res.json({
        "message": "success",
        "data": []
      });
    }

    //
    // TODO: remember, 12 at a time...  Do not try to cache them here, instead 
    // request them 12 at a time from S3. We don't cache data on the server 
    // because we want the web service to be stateless --- the client needs to 
    // keep track of which 12 they want. Stateless designs are more scalable.
    //
    // AWS:
    //   https://docs.aws.amazon.com/sdk-for-javascript/v3/developer-guide/javascript_s3_code_examples.html
    //   https://docs.aws.amazon.com/AWSJavaScriptSDK/v3/latest/clients/client-s3/classes/listobjectsv2command.html
    //   https://docs.aws.amazon.com/AWSJavaScriptSDK/v3/latest/clients/client-s3/
    //
    

  }//try
  catch (err) {
    console.log("**Error in /bucket");
    console.log(err.message);
    
    res.status(500).json({
      "message": err.message,
      "data": []
    });
  }//catch

}//get
