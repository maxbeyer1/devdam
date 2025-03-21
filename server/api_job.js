// api_job.js
//
// Endpoints for managing processing jobs
//
const photoapp_db = require("./photoapp_db.js");
const { query_database } = require("./utility.js");

//
// GET /job/:jobid - Get processing job status
//
exports.get_job = async (req, res) => {
  console.log("**Call to get /job/:jobid...");

  try {
    let jobid = req.params.jobid;

    if (isNaN(jobid)) {
      res.status(400).json({
        message: "Invalid job ID format",
        data: null,
      });
      return;
    }

    // Get job details
    let sql = `
      SELECT j.jobid, j.assetid, j.status, j.created_at, j.completed_at, j.error_message,
             a.assetname
      FROM processing_jobs j
      JOIN assets a ON j.assetid = a.assetid
      WHERE j.jobid = ${jobid};
    `;

    let result = await query_database(photoapp_db, sql);

    // Check if job exists
    if (result.length === 0) {
      res.status(404).json({
        message: "Job not found",
        data: null,
      });
      return;
    }

    let job = result[0];
    let assetid = job.assetid;

    // Get variant count
    let sql2 = `
      SELECT COUNT(*) AS variant_count
      FROM asset_variants
      WHERE assetid = ${assetid};
    `;

    let variantResult = await query_database(photoapp_db, sql2);
    let variantCount = variantResult[0].variant_count;

    // Format response
    let response = {
      jobid: job.jobid,
      assetid: job.assetid,
      assetname: job.assetname,
      status: job.status,
      created_at: job.created_at,
      completed_at: job.completed_at,
      error_message: job.error_message || "",
      variants_completed: job.status === "completed" ? variantCount : 0,
      variants_total: variantCount,
    };

    res.json({
      message: "success",
      data: response,
    });
  } catch (err) {
    console.log("**Error in /job/:jobid");
    console.log(err.message);

    res.status(500).json({
      message: err.message,
      data: null,
    });
  }
};
