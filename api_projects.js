// api_projects.js
//
// Project management API endpoints
//
const photoapp_db = require('./photoapp_db.js');
const { query_database } = require('./utility.js');

//
// GET /projects - Get list of projects
//
exports.get_projects = async (req, res) => {
  console.log("**Call to get /projects...");

  try {
    let clientid = req.query.clientid;
    let limit = req.query.limit || 20;
    let offset = req.query.offset || 0;

    let sql = `
      SELECT p.projectid, p.projectname, p.description, p.created_at, 
             c.clientid, c.clientname
      FROM projects p
      JOIN clients c ON p.clientid = c.clientid
    `;
    
    // Add client filter if provided
    if (clientid) {
      sql += ` WHERE p.clientid = ${clientid}`;
    }
    
    // Add pagination
    sql += ` LIMIT ${limit} OFFSET ${offset}`;

    console.log("/projects: calling DB to get projects...");
    let results = await query_database(photoapp_db, sql);
    console.log("/projects: got results from DB");

    // Format response
    res.json({
      "message": "success",
      "data": results
    });
  }
  catch (err) {
    console.log("**Error in /projects");
    console.log(err.message);
    
    res.status(500).json({
      "message": err.message,
      "data": []
    });
  }
};

//
// GET /project/:projectid - Get a specific project's details
//
exports.get_project = async (req, res) => {
  console.log("**Call to get /project/:projectid...");

  try {
    let projectid = req.params.projectid;
    
    // Validate projectid
    if (isNaN(projectid)) {
      res.status(400).json({
        "message": "Invalid project ID format",
        "data": null
      });
      return;
    }

    // Get project details
    let sql = `
      SELECT p.projectid, p.projectname, p.description, p.created_at, 
             c.clientid, c.clientname
      FROM projects p
      JOIN clients c ON p.clientid = c.clientid
      WHERE p.projectid = ${projectid};
    `;

    // Get asset count and storage used
    // let sql2 = `
    //   SELECT COUNT(*) AS asset_count, SUM(filesize) AS storage_used
    //   FROM assets
    //   WHERE projectid = ${projectid};
    // `;

    // Execute both queries concurrently
    let [projectResult, statsResult] = await Promise.all([
      query_database(photoapp_db, sql),
    //   query_database(photoapp_db, sql2)
    ]);

    // Check if project exists
    if (projectResult.length === 0) {
      res.status(404).json({
        "message": "Project not found",
        "data": null
      });
      return;
    }

    // Combine results
    let project = projectResult[0];
    // project.asset_count = statsResult[0].asset_count;
    // project.storage_used = statsResult[0].storage_used || 0;

    // Return project details with statistics
    res.json({
      "message": "success",
      "data": project
    });
  }
  catch (err) {
    console.log("**Error in /project/:projectid");
    console.log(err.message);
    
    res.status(500).json({
      "message": err.message,
      "data": null
    });
  }
};

//
// PUT /project - Add or update a project
//
exports.put_project = async (req, res) => {
  console.log("**Call to put /project...");

  try {
    let data = req.body;
    let projectid = data.projectid;
    let clientid = data.clientid;
    let projectname = data.projectname;
    let description = data.description || '';

    // Required fields
    if (!clientid || !projectname) {
      res.status(400).json({
        "message": "Missing required fields: clientid and projectname are required",
        "projectid": null
      });
      return;
    }

    // Check if client exists
    let clientSql = `SELECT clientid FROM clients WHERE clientid = ${clientid}`;
    let clientResult = await query_database(photoapp_db, clientSql);
    
    if (clientResult.length === 0) {
      res.status(404).json({
        "message": "Client not found",
        "projectid": null
      });
      return;
    }

    let result;
    
    // If projectid is provided update existing project
    if (projectid) {
      // Check if project exists
      let checkSql = `SELECT projectid FROM projects WHERE projectid = ${projectid}`;
      let checkResult = await query_database(photoapp_db, checkSql);
      
      if (checkResult.length === 0) {
        res.status(404).json({
          "message": "Project not found",
          "projectid": null
        });
        return;
      }
      
      // Update project
      let updateSql = `
        UPDATE projects
        SET clientid = ${clientid},
            projectname = '${projectname}',
            description = '${description}'
        WHERE projectid = ${projectid};
      `;
      
      result = await query_database(photoapp_db, updateSql);
      
      res.json({
        "message": "Project updated successfully",
        "projectid": projectid
      });
    } 
    // If not create new project
    else {
      let insertSql = `
        INSERT INTO projects (clientid, projectname, description)
        VALUES (${clientid}, '${projectname}', '${description}');
      `;
      
      result = await query_database(photoapp_db, insertSql);
      
      res.json({
        "message": "Project created successfully",
        "projectid": result.insertId
      });
    }
  }
  catch (err) {
    console.log("**Error in /project");
    console.log(err.message);
    
    res.status(500).json({
      "message": err.message,
      "projectid": null
    });
  }
};

//
// DELETE /project/:projectid - Delete a project
//
exports.delete_project = async (req, res) => {
  console.log("**Call to delete /project/:projectid...");

  try {
    let projectid = req.params.projectid;
    
    if (isNaN(projectid)) {
      res.status(400).json({
        "message": "Invalid project ID format"
      });
      return;
    }

    // Check if project has assets
    let checkSql = `
      SELECT COUNT(*) AS asset_count
      FROM assets
      WHERE projectid = ${projectid};
    `;
    
    let checkResult = await query_database(photoapp_db, checkSql);
    
    if (checkResult[0].asset_count > 0) {
      res.status(400).json({
        "message": "Cannot delete project with existing assets"
      });
      return;
    }

    // Delete project
    let deleteSql = `
      DELETE FROM projects
      WHERE projectid = ${projectid};
    `;
    
    let result = await query_database(photoapp_db, deleteSql);
    
    if (result.affectedRows === 0) {
      res.status(404).json({
        "message": "Project not found"
      });
      return;
    }
    
    res.json({
      "message": "Project deleted successfully"
    });
  }
  catch (err) {
    console.log("**Error in DELETE /project/:projectid");
    console.log(err.message);
    
    res.status(500).json({
      "message": err.message
    });
  }
};