// api_asset_variant.js
//
// Endpoints for managing asset variants
//
const photoapp_db = require("./photoapp_db.js");
const { GetObjectCommand } = require("@aws-sdk/client-s3");
const { photoapp_s3, s3_bucket_name } = require("./photoapp_s3.js");
const { query_database } = require("./utility.js");

//
// GET /asset/:assetid/variants - Get all variants for an asset
//
exports.get_asset_variants = async (req, res) => {
  console.log("**Call to get /asset/:assetid/variants...");

  try {
    let assetid = req.params.assetid;

    if (isNaN(assetid)) {
      res.status(400).json({
        message: "Invalid asset ID format",
        data: [],
      });
      return;
    }

    // Get variants
    let sql = `
      SELECT variantid, variant_type, width, height, format, quality, filesize, bucketkey, cdn_url
      FROM asset_variants
      WHERE assetid = ${assetid};
    `;

    let results = await query_database(photoapp_db, sql);

    res.json({
      message: "success",
      data: results,
    });
  } catch (err) {
    console.log("**Error in /asset/:assetid/variants");
    console.log(err.message);

    res.status(500).json({
      message: err.message,
      data: [],
    });
  }
};

//
// GET /asset/:assetid/variant/:variantid/download - Download a specific variant
//
exports.download_variant = async (req, res) => {
  console.log("**Call to get /asset/:assetid/variant/:variantid/download...");

  try {
    let assetid = req.params.assetid;
    let variantid = req.params.variantid;

    if (isNaN(assetid) || isNaN(variantid)) {
      res.status(400).json({
        message: "Invalid ID format",
        variant_type: "?",
        asset_name: "?",
        bucket_key: "?",
        data: [],
      });
      return;
    }

    // Get variant details
    let sql = `
      SELECT v.variant_type, v.bucketkey, a.assetname
      FROM asset_variants v
      JOIN assets a ON v.assetid = a.assetid
      WHERE v.assetid = ${assetid} AND v.variantid = ${variantid};
    `;

    let result = await query_database(photoapp_db, sql);

    // Check if variant exists
    if (result.length === 0) {
      res.status(404).json({
        message: "Variant not found",
        variant_type: "?",
        asset_name: "?",
        bucket_key: "?",
        data: [],
      });
      return;
    }

    let variant = result[0];
    let variant_type = variant.variant_type;
    let assetname = variant.assetname;
    let bucketkey = variant.bucketkey;

    // Get file from S3
    let input = {
      Bucket: s3_bucket_name,
      Key: bucketkey,
    };

    console.log("/variant/download: calling S3...");
    let command = new GetObjectCommand(input);
    let s3_result = await photoapp_s3.send(command);
    console.log("/variant/download: got results from S3");

    // Convert to base64 string
    let s3_body = s3_result.Body;
    let datastr = await s3_body.transformToString("base64");

    // Return base64 data in response
    res.json({
      message: "success",
      variant_type: variant_type,
      asset_name: assetname,
      bucket_key: bucketkey,
      data: datastr,
    });
  } catch (err) {
    console.log("**Error in /asset/:assetid/variant/:variantid/download");
    console.log(err.message);

    res.status(500).json({
      message: err.message,
      variant_type: "?",
      asset_name: "?",
      bucket_key: "?",
      data: [],
    });
  }
};
