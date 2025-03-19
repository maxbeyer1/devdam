// api_asset_post.js
//
// Endpoint for uploading a new asset to a project
//
const photoapp_db = require("./photoapp_db.js");
const { PutObjectCommand } = require("@aws-sdk/client-s3");
const { photoapp_s3, s3_bucket_name } = require("./photoapp_s3.js");
const { query_database, getContentType } = require("./utility.js");
const uuid = require("uuid");
const path = require("path");

//
// POST /asset/:projectid - Upload a new asset to a project
//
exports.post_asset = async (req, res) => {
  console.log("**Call to post /asset/:projectid...");

  try {
    let projectid = req.params.projectid;

    if (isNaN(projectid)) {
      res.status(400).json({
        message: "Invalid project ID format",
        asset_id: -1,
      });
      return;
    }

    let data = req.body;
    let assetname = data.assetname;
    let image_data = data.data; // Base64 encoded image data
    let description = data.description || "";

    // Processing options for images
    // Ex: {
    //   variants: [
    //     {
    //      "type": "thumbnail",
    //      "width": 200,
    //      "height": 200,
    //      "format": "webp",
    //      "quality": 80
    //     },
    //   ]
    // }
    // TODO: Remove default processing options used for testing
    let processing_options = data.processing_options || {
      variants: [
        {
          type: "thumbnail",
          width: 200,
          height: 200,
          format: "webp",
          quality: 80,
        },
      ],
    };

    // Check if project exists and get user ID
    let projectSql = `
      SELECT p.projectid, c.userid
      FROM projects p
      JOIN clients c ON p.clientid = c.clientid
      WHERE p.projectid = ${projectid};
    `;

    console.log("/asset: calling DB to get project...");

    let projectResult = await query_database(photoapp_db, projectSql);

    console.log("/asset: got results from DB");

    if (projectResult.length === 0) {
      res.status(404).json({
        message: "Project not found",
        asset_id: -1,
      });
      return;
    }

    let userid = projectResult[0].userid;

    // Get user's bucket folder
    let userSql = `SELECT bucketfolder FROM users WHERE userid = ${userid}`;

    console.log("/asset: calling DB to get user...");

    let userResult = await query_database(photoapp_db, userSql);

    console.log("/asset: got results from DB");

    if (userResult.length === 0) {
      res.status(500).json({
        message: "User not found",
        asset_id: -1,
      });
      return;
    }

    let bucketfolder = userResult[0].bucketfolder;

    // Extract file extension from assetname
    let extension = path.extname(assetname).toLowerCase();
    if (!extension) {
      extension = ".jpg"; // Default to .jpg if no extension provided
    }

    let contentType = getContentType(extension);

    // Generate unique ID and S3 key
    let asset_id = uuid.v4();
    let asset_key = `${bucketfolder}/p${projectid}/${asset_id}${extension}`;

    // Convert base64 to binary
    let bytes = Buffer.from(image_data, "base64");

    // Upload file to S3
    let upload_params = {
      Bucket: s3_bucket_name,
      Key: asset_key,
      Body: bytes,
      ContentType: contentType,
      ACL: "public-read",
      Metadata: {
        assetid: asset_id,
        projectid: projectid.toString(),
        userid: userid.toString(),
        processing_options: JSON.stringify(processing_options),
      },
    };

    console.log("/asset: calling S3 to upload image...");

    let upload_res = await photoapp_s3.send(
      new PutObjectCommand(upload_params)
    );

    console.log("/asset: got results from S3");

    if (upload_res.$metadata.httpStatusCode != 200) {
      res.status(500).json({
        message: "Failed to upload to S3",
        asset_id: -1,
      });
      return;
    }

    // Store asset in database
    let insertSql = `
      INSERT INTO assets (userid, projectid, assetname, description, bucketkey)
      VALUES (${userid}, ${projectid}, '${assetname}', '${description}', '${asset_key}');
    `;

    console.log("/asset: calling DB to insert asset...");

    let insertResult = await query_database(photoapp_db, insertSql);

    console.log("/asset: got results from DB");

    // if (insertResult.affectedRows === 1) {
    //   res.json({
    //     message: "success",
    //     asset_id: insertResult.insertId,
    //   });
    // } else {
    //   res.status(500).json({
    //     message: "Failed to insert asset record",
    //     asset_id: -1,
    //   });
    // }

    if (insertResult.affectedRows !== 1) {
      console.log("/asset: failed to insert asset in DB");

      res.status(500).json({
        message: "Failed to insert asset record",
        asset_id: -1,
      });
      return;
    }

    let assetid = insertResult.insertId;

    // Create processing job
    let jobSql = `
      INSERT INTO processing_jobs (
        assetid,
        status,
        processing_options
      ) VALUES (
        ${assetid},
        'pending',
        '${JSON.stringify(processing_options)}'
      );
    `;

    console.log("/asset: calling DB to insert processing job...");

    let jobResult = await query_database(photoapp_db, jobSql);

    if (jobResult.affectedRows !== 1) {
      console.log("/asset: failed to insert processing job in DB");

      res.status(500).json({
        message: "Failed to create processing job",
        asset_id: assetid,
      });
      return;
    }

    console.log("/asset: inserted processing job in DB");

    let jobid = jobResult.insertId;
    let variants_total = processing_options.variants
      ? processing_options.variants.length
      : 0;

    res.json({
      message: "success",
      asset_id: assetid,
      processing_job: {
        jobid: jobid,
        status: "pending",
        variants_total: variants_total,
        variants_completed: 0,
      },
    });
  } catch (err) {
    console.log("**Error in POST /asset/:projectid");
    console.log(err.message);

    res.status(500).json({
      message: err.message,
      asset_id: -1,
    });
  }
};
