//
// app.put('/user', async (req, res) => {...});
//
// Inserts a new user into the database, or if the
// user already exists (based on email) then the
// user's data is updated (name and bucket folder).
// Returns the user's userid in the database.
//
const photoapp_db = require("./photoapp_db.js");
const { query_database } = require("./utility.js");

exports.put_user = async (req, res) => {
  console.log("**Call to put /user...");

  try {
    let data = req.body; // data => JS object

    console.log(data);

    // extract request data
    let email = data.email;
    let lastname = data.lastname;
    let firstname = data.firstname;
    let bucketfolder = data.bucketfolder;

    // query database for user
    let sql = `
        Select userid From users
        Where email = '${email}';
        `;

    console.log("/user: calling DB to get user...");

    let query_res = await query_database(photoapp_db, sql);

    console.log("/user: got results from DB");

    // if user exists, update
    if (query_res.length > 0) {
      let userid = query_res[0].userid;

      sql = `
          Update users
          Set lastname = '${lastname}',
              firstname = '${firstname}',
              bucketfolder = '${bucketfolder}'
          Where userid = ${userid};
          `;

      console.log("/user: calling DB to update user...");

      let update_res = await query_database(photoapp_db, sql);

      if (update_res.affectedRows == 1) {
        console.log("/user: updated user in DB");
        res.json({
          message: "updated",
          user_id: userid,
        });
      } else {
        console.log("/user: failed to update user in DB");
        res.status(500).json({
          message: "failed to update",
          user_id: userid,
        });
      }
    } else {
      // if user does not exist, insert
      sql = `
          Insert Into users (email, lastname, firstname, bucketfolder)
          Values ('${email}', '${lastname}', '${firstname}', '${bucketfolder}');
          `;

      console.log("/user: calling DB to insert user...");

      let insert_res = await query_database(photoapp_db, sql);

      if (insert_res.affectedRows == 1) {
        console.log("/user: inserted user in DB");
        res.json({
          message: "inserted",
          user_id: insert_res.insertId,
        });
      } else {
        console.log("/user: failed to insert user in DB");
        res.status(500).json({
          message: "failed to insert",
          user_id: -1,
        });
      }
    }
  } catch (err) {
    //try
    console.log("**Error in /user");
    console.log(err.message);

    res.status(500).json({
      message: err.message,
      user_id: -1,
    });
  } //catch
}; //put
