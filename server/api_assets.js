//
// app.get('/assets', async (req, res) => {...});
//
// Return all the assets from the database:
//
const photoapp_db = require("./photoapp_db.js");
const { query_database } = require("./utility.js");

exports.get_assets = async (req, res) => {
  console.log("**Call to get /assets...");

  try {
    // query database for all assets with project and client info
    let sql = `
      SELECT a.assetid, a.assetname, a.description, a.bucketkey, a.created_at,
             p.projectid, p.projectname,
             c.clientid, c.clientname
      FROM assets a
      JOIN projects p ON a.projectid = p.projectid
      JOIN clients c ON p.clientid = c.clientid;
    `;

    console.log("/assets: calling DB to get assets...");

    let results = await query_database(photoapp_db, sql);

    console.log("/assets: got results from DB");

    // Check if results are empty
    if (results.length === 0) {
      res.status(404).json({
        message: "No assets found",
        data: [],
      });
      return;
    }

    // Format response
    let assets = results.map((asset) => {
      return {
        assetid: asset.assetid,
        assetname: asset.assetname,
        description: asset.description || "",
        created_at: asset.created_at,
        bucketkey: asset.bucketkey,
        project: {
          projectid: asset.projectid,
          projectname: asset.projectname,
        },
        client: {
          clientid: asset.clientid,
          clientname: asset.clientname,
        },
      };
    });

    res.json({
      message: "success",
      data: assets,
    });
  } catch (err) {
    //try
    console.log("**Error in /assets");
    console.log(err.message);

    res.status(500).json({
      message: err.message,
      data: [],
    });
  } //catch
}; //get
