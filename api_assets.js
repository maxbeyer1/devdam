//
// app.get('/assets', async (req, res) => {...});
//
// Return all the assets from the database:
//
const photoapp_db = require('./photoapp_db.js')
const { query_database } = require('./utility.js');

exports.get_assets = async (req, res) => {

  console.log("**Call to get /assets...");

  try {
    // query database for all assets
    let sql = `
        Select assetid, userid, assetname, bucketkey From assets;
        `;

    console.log("/assets: calling DB to get assets...");

    let results = await query_database(photoapp_db, sql);

    console.log("/assets: got results from DB");

    res.json({
      "message": "success",
      "data": results
    });
    

  }//try
  catch (err) {
    console.log("**Error in /assets");
    console.log(err.message);
    
    res.status(500).json({
      "message": err.message,
      "data": []
    });
  }//catch

}//get
