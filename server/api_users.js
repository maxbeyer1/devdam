//
// app.get('/users', async (req, res) => {...});
//
// Return all the users from the database:
//
const photoapp_db = require("./photoapp_db.js");
const { query_database } = require("./utility.js");

exports.get_users = async (req, res) => {
  console.log("**Call to get /users...");

  try {
    // query database for all users
    let sql = `
        Select userid, email, lastname, firstname, bucketfolder From users;
        `;

    console.log("/users: calling DB to get users...");

    let results = await query_database(photoapp_db, sql);

    console.log("/users: got results from DB");

    res.json({
      message: "success",
      data: results,
    });
  } catch (err) {
    //try
    console.log("**Error in /users");
    console.log(err.message);

    res.status(500).json({
      message: err.message,
      data: [],
    });
  } //catch
}; //get
