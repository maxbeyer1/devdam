//
// app.post('/image/:userid', async (req, res) => {...});
//
// Uploads an image to the bucket and updates the database,
// returning the asset id assigned to this image.
//
const photoapp_db = require('./photoapp_db.js')
const { PutObjectCommand } = require('@aws-sdk/client-s3');
const { photoapp_s3, s3_bucket_name, s3_region_name } = require('./photoapp_s3.js');
const { query_database } = require('./utility.js');

const uuid = require('uuid');

exports.post_image = async (req, res) => {

  console.log("**Call to post /image/:userid...");

  try {

    let data = req.body;  // data => JS object

    // extract data
    let assetname = data.assetname;
    let image_data = data.data;
    let userid = req.params.userid;

    // check for user in database
    let sql = `
        Select userid From users
        Where userid = ${userid};
        `;

    console.log("/image: calling DB to get user...");

    let query_res = query_database(photoapp_db, sql);

    // try to resolve promise and catch ER_BAD_FIELD_ERROR
    try {
      query_res = await query_res;
    } catch (err) {
      if (err.code == "ER_BAD_FIELD_ERROR") {
        res.status(400).json({
          "message": "No such user...",
          "asset_id": -1
        });
        return;
      }
      throw err;
    }

    console.log("/image: got results from DB");

    if (query_res.length == 0) {
      res.status(400).json({
        "message": "No such user...",
        "asset_id": -1
      });
      return;
    }

    // get bucket folder for user
    let bucketfolder = query_res[0].bucketfolder;

    // create asset id and key
    let asset_id = uuid.v4();
    let asset_key = `${bucketfolder}/${asset_id}.jpg`;

    // upload image to s3
    let bytes = Buffer.from(image_data, 'base64');

    const upload_params = {
      Bucket: s3_bucket_name,
      Key: asset_key,
      Body: bytes,
      ContentType: 'image/jpg',
      ACL: 'public-read'
    };

    console.log("/image: calling S3 to upload image...");

    const upload_res = await photoapp_s3.send(new PutObjectCommand(upload_params));

    console.log("/image: got results from S3");
    console.log(upload_res);

    // check for success
    if (upload_res.$metadata.httpStatusCode != 200) {
      res.status(500).json({
        "message": "failed to upload",
        "asset_id": -1
      });
      return;
    }

    // add image to database
    sql = `
        Insert Into assets (userid, assetname, bucketkey)
        Values (${userid}, '${assetname}', '${asset_key}');
        `;

    console.log("/image: calling DB to insert asset...");

    let db_res = await query_database(photoapp_db, sql);
	
    if (db_res.affectedRows == 1) {
      console.log("/image: inserted asset in DB");
      res.json({
        "message": "success",
        "asset_id": db_res.insertId
      });
    } else {
      console.log("/image: failed to insert asset in DB");
      res.status(500).json({
        "message": "failed to insert",
        "asset_id": -1
      });
    }
	
  }//try
  catch (err) {
    console.log("**Error in /image");
    console.log(err.message);
    
    res.status(500).json({
      "message": err.message,
      "asset_id": -1
    });
  }//catch

}//post
