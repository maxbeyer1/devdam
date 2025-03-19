// api_asset.js
//
// Asset management API endpoints for single asset operations
//
const photoapp_db = require("./photoapp_db.js");
const { GetObjectCommand, DeleteObjectCommand } = require("@aws-sdk/client-s3");
const { photoapp_s3, s3_bucket_name } = require("./photoapp_s3.js");
const { query_database } = require("./utility.js");

//
// GET /asset/:assetid - Get full details of a specific asset
//
exports.get_asset = async (req, res) => {
  console.log("**Call to get /asset/:assetid...");

  try {
    let assetid = req.params.assetid;

    if (isNaN(assetid)) {
      res.status(400).json({
        message: "Invalid asset ID format",
        data: null,
      });
      return;
    }

    // Get asset details with project and client info
    let sql = `
      SELECT a.assetid, a.assetname, a.description, a.bucketkey, a.created_at,
             p.projectid, p.projectname,
             c.clientid, c.clientname
      FROM assets a
      JOIN projects p ON a.projectid = p.projectid
      JOIN clients c ON p.clientid = c.clientid
      WHERE a.assetid = ${assetid};
    `;

    let result = await query_database(photoapp_db, sql);

    // Check if asset exists
    if (result.length === 0) {
      res.status(404).json({
        message: "Asset not found",
        data: null,
      });
      return;
    }

    let asset = result[0];

    let response = {
      assetid: asset.assetid,
      assetname: asset.assetname,
      description: asset.description || "",
      created_at: asset.created_at,
      project: {
        projectid: asset.projectid,
        projectname: asset.projectname,
      },
      client: {
        clientid: asset.clientid,
        clientname: asset.clientname,
      },
      // FOR FUTURE USE
      //   "variants": [],
      //   "usage": {
      //     "last_accessed": null,
      //     "access_count": 0,
      //     "last_referer": null,
      //     "unique_referers": 0
      //   }
    };

    res.json({
      message: "success",
      data: response,
    });
  } catch (err) {
    console.log("**Error in /asset/:assetid");
    console.log(err.message);

    res.status(500).json({
      message: err.message,
      data: null,
    });
  }
};

//
// PUT /asset/:assetid - Update asset metadata
//
exports.put_asset = async (req, res) => {
  console.log("**Call to put /asset/:assetid...");

  try {
    let assetid = req.params.assetid;

    if (isNaN(assetid)) {
      res.status(400).json({
        message: "Invalid asset ID format",
        data: null,
      });
      return;
    }

    let data = req.body;
    let assetname = data.assetname;
    let description = data.description;

    // Check if asset exists
    let checkSql = `SELECT assetid FROM assets WHERE assetid = ${assetid}`;
    let checkResult = await query_database(photoapp_db, checkSql);

    if (checkResult.length === 0) {
      res.status(404).json({
        message: "Asset not found",
        data: null,
      });
      return;
    }

    // Build update SQL
    let updates = [];
    let params = [];

    if (assetname !== undefined) {
      updates.push("assetname = ?");
      params.push(assetname);
    }

    if (description !== undefined) {
      updates.push("description = ?");
      params.push(description);
    }

    // If no updates, return
    if (updates.length === 0) {
      res.status(400).json({
        message: "No update parameters provided",
        data: null,
      });
      return;
    }

    // Add assetid parameter
    params.push(assetid);

    // Update asset
    let updateSql = `
      UPDATE assets
      SET ${updates.join(", ")}
      WHERE assetid = ?;
    `;

    let result = await query_database(photoapp_db, updateSql, params);

    if (result.affectedRows === 0) {
      res.status(500).json({
        message: "Failed to update asset",
        data: null,
      });
      return;
    }

    // Get updated asset
    let getUpdatedSql = `
      SELECT a.assetid, a.assetname, a.description, a.bucketkey, a.created_at,
             p.projectid, p.projectname,
             c.clientid, c.clientname
      FROM assets a
      JOIN projects p ON a.projectid = p.projectid
      JOIN clients c ON p.clientid = c.clientid
      WHERE a.assetid = ${assetid};
    `;

    let updatedResult = await query_database(photoapp_db, getUpdatedSql);
    let updatedAsset = updatedResult[0];

    res.json({
      message: "Asset updated successfully",
      data: updatedAsset,
    });
  } catch (err) {
    console.log("**Error in PUT /asset/:assetid");
    console.log(err.message);

    res.status(500).json({
      message: err.message,
      data: null,
    });
  }
};

//
// DELETE /asset/:assetid - Delete an asset
//
exports.delete_asset = async (req, res) => {
  console.log("**Call to delete /asset/:assetid...");

  try {
    let assetid = req.params.assetid;

    if (isNaN(assetid)) {
      res.status(400).json({
        message: "Invalid asset ID format",
      });
      return;
    }

    // Check if asset exists and get bucket key
    let checkSql = `SELECT assetid, bucketkey FROM assets WHERE assetid = ${assetid}`;
    let checkResult = await query_database(photoapp_db, checkSql);

    if (checkResult.length === 0) {
      res.status(404).json({
        message: "Asset not found",
      });
      return;
    }

    // Get bucket key for S3 deletion
    let bucketkey = checkResult[0].bucketkey;

    // Delete from database
    let deleteSql = `DELETE FROM assets WHERE assetid = ${assetid}`;
    let result = await query_database(photoapp_db, deleteSql);

    if (result.affectedRows === 0) {
      res.status(500).json({
        message: "Failed to delete asset",
      });
      return;
    }

    // Delete from S3
    let deleteParams = {
      Bucket: s3_bucket_name,
      Key: bucketkey,
    };

    console.log("/asset/:assetid: calling S3...");

    let deleteCommand = new DeleteObjectCommand(deleteParams);
    let deleteResult = await photoapp_s3.send(deleteCommand);

    console.log("/asset/:assetid: got S3 result");

    if (deleteResult.$metadata.httpStatusCode !== 204) {
      res.status(500).json({
        message: "Failed to delete asset from S3",
      });
      return;
    }

    res.json({
      message: "Asset deleted successfully",
    });
  } catch (err) {
    console.log("**Error in DELETE /asset/:assetid");
    console.log(err.message);

    res.status(500).json({
      message: err.message,
    });
  }
};

//
// GET /asset/:assetid/download - Download the original asset file
//
exports.download_asset = async (req, res) => {
  console.log("**Call to get /asset/:assetid/download...");

  try {
    // Get assetid from request
    let assetid = req.params.assetid;

    // Validate assetid
    if (isNaN(assetid)) {
      res.status(400).json({
        message: "Invalid asset ID format",
        project_id: -1,
        asset_name: "?",
        bucket_key: "?",
        data: [],
      });
      return;
    }

    // Get asset details
    let sql = `
      SELECT projectid, assetname, bucketkey
      FROM assets
      WHERE assetid = ${assetid};
    `;

    let result = await query_database(photoapp_db, sql);

    // Check if asset exists
    if (result.length === 0) {
      res.status(404).json({
        message: "Asset not found",
        project_id: -1,
        asset_name: "?",
        bucket_key: "?",
        data: [],
      });
      return;
    }

    let asset = result[0];
    let project_id = asset.projectid;
    let asset_name = asset.assetname;
    let bucket_key = asset.bucketkey;

    // Get file from S3
    let input = {
      Bucket: s3_bucket_name,
      Key: asset.bucketkey,
    };

    console.log("/asset/:assetid/download: calling S3...");

    let command = new GetObjectCommand(input);
    let s3_result = await photoapp_s3.send(command);

    console.log("/asset/:assetid/download: got S3 result");

    // Convert to base64
    var datastr = await s3_result.Body.transformToString("base64");

    res.json({
      message: "success",
      project_id: project_id,
      asset_name: asset_name,
      bucket_key: bucket_key,
      data: datastr,
    });
  } catch (err) {
    console.log("**Error in /asset/:assetid/download");
    console.log(err.message);

    res.status(500).json({
      message: err.message,
      project_id: -1,
      asset_name: "?",
      bucket_key: "?",
      data: [],
    });
  }
};
