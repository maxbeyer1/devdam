//
// app.get('/stats', async (req, res) => {...});
//
// return some stats about our bucket and database:
//
const photoapp_db = require("./photoapp_db.js");
const { HeadBucketCommand } = require("@aws-sdk/client-s3");
const {
  photoapp_s3,
  s3_bucket_name,
  s3_region_name,
} = require("./photoapp_s3.js");
const { query_database } = require("./utility.js");

//
// get /stats:
//
exports.get_stats = async (req, res) => {
  console.log("**Call to get /stats...");

  try {
    //
    // calling S3 to get bucket status, returning a PROMISE
    // we have to wait on eventually:
    //
    // build input object for S3 with request parameters:
    let input = {
      Bucket: s3_bucket_name,
    };

    console.log("/stats: calling S3...");

    let command = new HeadBucketCommand(input);
    let s3_promise = photoapp_s3.send(command);

    // Get user count
    let sql1 = `SELECT count(*) As NumUsers FROM users;`;
    let mysql_promise1 = query_database(photoapp_db, sql1);

    // Add client count
    let sql2 = `SELECT count(*) As NumClients FROM clients;`;
    let mysql_promise2 = query_database(photoapp_db, sql2);

    // Add project count
    let sql3 = `SELECT count(*) As NumProjects FROM projects;`;
    let mysql_promise3 = query_database(photoapp_db, sql3);

    // Get asset count
    let sql4 = `SELECT count(*) As NumAssets FROM assets;`;
    let mysql_promise4 = query_database(photoapp_db, sql4);

    // Get storage used
    // let sql5 = `
    //   SELECT SUM(filesize) AS StorageBytes
    //   FROM assets
    // `;
    // let mysql_promise5 = query_database(photoapp_db, sql5);

    let results = await Promise.all([
      s3_promise,
      mysql_promise1,
      mysql_promise2,
      mysql_promise3,
      mysql_promise4,
    ]);

    console.log("/stats done, sending response...");

    res.json({
      message: "success",
      bucket_status: results[0].$metadata.httpStatusCode,
      users: results[1][0].NumUsers,
      clients: results[2][0].NumClients,
      projects: results[3][0].NumProjects,
      assets: results[4][0].NumAssets,
      // FOR FUTURE USE:
      // processing_jobs: {
      //   pending: 0,
      //   processing: 0,
      //   completed: results[4][0].NumAssets,
      //   failed: 0,
      // },
    });
  } catch (err) {
    //try
    //
    // generally we end up here if we made a
    // programming error, like undefined variable
    // or function, or bad SQL:
    //
    console.log("**Error in /stats");
    console.log(err.message);

    res.status(500).json({
      message: err.message,
      users: -1,
      clients: -1,
      projects: -1,
      assets: -1,
      // processing_jobs: null,
    });
  } //catch
}; //get
