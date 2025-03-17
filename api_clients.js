// api_clients.js
//
// Client management API endpoints
//
const photoapp_db = require("./photoapp_db.js");
const { query_database } = require("./utility.js");

//
// GET /clients - Get list of clients
//
exports.get_clients = async (req, res) => {
  console.log("**Call to get /clients...");

  try {
    let limit = req.query.limit || 20;
    let offset = req.query.offset || 0;

    // Query database for clients with pagination
    let sql = `
      SELECT c.clientid, c.clientname, c.description, c.created_at, 
             u.userid, u.firstname, u.lastname
      FROM clients c
      JOIN users u ON c.userid = u.userid
      LIMIT ${limit} OFFSET ${offset};
    `;

    console.log("/clients: calling DB to get clients...");

    let results = await query_database(photoapp_db, sql);

    console.log("/clients: got results from DB");

    res.json({
      message: "success",
      data: results,
    });
  } catch (err) {
    console.log("**Error in /clients");
    console.log(err.message);

    res.status(500).json({
      message: err.message,
      data: [],
    });
  }
};

//
// GET /client/:clientid - Get a specific client's details
//
exports.get_client = async (req, res) => {
  console.log("**Call to get /client/:clientid...");

  try {
    let clientid = req.params.clientid;

    // Validate clientid
    if (isNaN(clientid)) {
      res.status(400).json({
        message: "Invalid client ID format",
        data: null,
      });
      return;
    }

    // Get client details
    let sql = `
      SELECT c.clientid, c.clientname, c.description, c.created_at, 
             u.userid, u.firstname, u.lastname
      FROM clients c
      JOIN users u ON c.userid = u.userid
      WHERE c.clientid = ${clientid};
    `;

    // Get project count
    let sql2 = `
      SELECT COUNT(*) AS project_count
      FROM projects
      WHERE clientid = ${clientid};
    `;

    // Get asset count
    let sql3 = `
      SELECT COUNT(*) AS asset_count
      FROM assets a
      JOIN projects p ON a.projectid = p.projectid
      WHERE p.clientid = ${clientid};
    `;

    let [clientResult, projectCountResult, assetCountResult] =
      await Promise.all([
        query_database(photoapp_db, sql),
        query_database(photoapp_db, sql2),
        query_database(photoapp_db, sql3),
      ]);

    // Make sure client exists
    if (clientResult.length === 0) {
      res.status(404).json({
        message: "Client not found",
        data: null,
      });
      return;
    }

    // Combine results
    let client = clientResult[0];
    client.project_count = projectCountResult[0].project_count;
    client.asset_count = assetCountResult[0].asset_count;

    // Return client details
    res.json({
      message: "success",
      data: client,
    });
  } catch (err) {
    console.log("**Error in /client/:clientid");
    console.log(err.message);

    res.status(500).json({
      message: err.message,
      data: null,
    });
  }
};

//
// PUT /client - Add or update a client
//
exports.put_client = async (req, res) => {
  console.log("**Call to put /client...");

  try {
    let data = req.body;
    let clientid = data.clientid;
    let userid = data.userid;
    let clientname = data.clientname;
    let description = data.description || "";

    // Validate required fields
    if (!userid || !clientname) {
      res.status(400).json({
        message: "Missing required fields: userid and clientname are required",
        clientid: null,
      });
      return;
    }

    // Check if user exists
    let userSql = `SELECT userid FROM users WHERE userid = ${userid}`;
    let userResult = await query_database(photoapp_db, userSql);

    if (userResult.length === 0) {
      res.status(404).json({
        message: "User not found",
        clientid: null,
      });
      return;
    }

    let result;

    // If clientid is provided, update existing client
    if (clientid) {
      // Check if client exists
      let checkSql = `SELECT clientid FROM clients WHERE clientid = ${clientid}`;
      let checkResult = await query_database(photoapp_db, checkSql);

      if (checkResult.length === 0) {
        res.status(404).json({
          message: "Client not found",
          clientid: null,
        });
        return;
      }

      // Update client
      let updateSql = `
        UPDATE clients
        SET userid = ${userid},
            clientname = '${clientname}',
            description = '${description}'
        WHERE clientid = ${clientid};
      `;

      result = await query_database(photoapp_db, updateSql);

      res.json({
        message: "Client updated successfully",
        clientid: clientid,
      });
    }
    // Otherwise create new client
    else {
      let insertSql = `
        INSERT INTO clients (userid, clientname, description)
        VALUES (${userid}, '${clientname}', '${description}');
      `;

      result = await query_database(photoapp_db, insertSql);

      res.json({
        message: "Client created successfully",
        clientid: result.insertId,
      });
    }
  } catch (err) {
    console.log("**Error in /client");
    console.log(err.message);

    res.status(500).json({
      message: err.message,
      clientid: null,
    });
  }
};

//
// DELETE /client/:clientid - Delete a client
//
exports.delete_client = async (req, res) => {
  console.log("**Call to delete /client/:clientid...");

  try {
    let clientid = req.params.clientid;

    // Validate clientid
    if (isNaN(clientid)) {
      res.status(400).json({
        message: "Invalid client ID format",
      });
      return;
    }

    // Check if client has projects
    let checkSql = `
      SELECT COUNT(*) AS project_count
      FROM projects
      WHERE clientid = ${clientid};
    `;

    let checkResult = await query_database(photoapp_db, checkSql);

    if (checkResult[0].project_count > 0) {
      res.status(400).json({
        message: "Cannot delete client with existing projects",
      });
      return;
    }

    // Delete client
    let deleteSql = `
      DELETE FROM clients
      WHERE clientid = ${clientid};
    `;

    let result = await query_database(photoapp_db, deleteSql);

    if (result.affectedRows === 0) {
      res.status(404).json({
        message: "Client not found",
      });
      return;
    }

    res.json({
      message: "Client deleted successfully",
    });
  } catch (err) {
    console.log("**Error in DELETE /client/:clientid");
    console.log(err.message);

    res.status(500).json({
      message: err.message,
    });
  }
};
