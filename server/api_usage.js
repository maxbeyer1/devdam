// api_usage.js
//
// Endpoints for usage statistics
//
const photoapp_db = require("./photoapp_db.js");
const { query_database } = require("./utility.js");

//
// GET /asset/:assetid/usage - Get usage statistics for a specific asset
//
exports.get_asset_usage = async (req, res) => {
  console.log("**Call to get /asset/:assetid/usage...");

  try {
    let assetid = req.params.assetid;

    if (isNaN(assetid)) {
      res.status(400).json({
        message: "Invalid asset ID format",
        data: null,
      });
      return;
    }

    // Check if asset exists
    let assetSql = `
      SELECT assetid, assetname 
      FROM assets 
      WHERE assetid = ${assetid};
    `;

    let assetResult = await query_database(photoapp_db, assetSql);

    if (assetResult.length === 0) {
      res.status(404).json({
        message: "Asset not found",
        data: null,
      });
      return;
    }

    // Get usage data
    let usageSql = `
      SELECT last_accessed, access_count, last_referer, unique_referers
      FROM asset_usage
      WHERE assetid = ${assetid};
    `;

    let usageResult = await query_database(photoapp_db, usageSql);

    // Format response
    let response = {
      assetid: assetid,
      assetname: assetResult[0].assetname,
      usage:
        usageResult.length > 0
          ? {
              last_accessed: usageResult[0].last_accessed,
              access_count: usageResult[0].access_count,
              last_referer: usageResult[0].last_referer,
              unique_referers: usageResult[0].unique_referers,
            }
          : {
              last_accessed: null,
              access_count: 0,
              last_referer: null,
              unique_referers: 0,
            },
    };

    res.json({
      message: "success",
      data: response,
    });
  } catch (err) {
    console.log("**Error in /asset/:assetid/usage");
    console.log(err.message);

    res.status(500).json({
      message: err.message,
      data: null,
    });
  }
};

//
// GET /project/:projectid/usage - Get usage statistics for all assets in a project
//
exports.get_project_usage = async (req, res) => {
  console.log("**Call to get /project/:projectid/usage...");

  try {
    let projectid = req.params.projectid;

    if (isNaN(projectid)) {
      res.status(400).json({
        message: "Invalid project ID format",
        data: null,
      });
      return;
    }

    // Check if project exists
    let projectSql = `
      SELECT projectid, projectname 
      FROM projects 
      WHERE projectid = ${projectid};
    `;

    let projectResult = await query_database(photoapp_db, projectSql);

    if (projectResult.length === 0) {
      res.status(404).json({
        message: "Project not found",
        data: null,
      });
      return;
    }

    // Get usage summary for all assets in the project
    let usageSql = `
      SELECT 
        a.assetid,
        a.assetname,
        u.last_accessed,
        u.access_count,
        u.unique_referers
      FROM 
        assets a
      LEFT JOIN 
        asset_usage u ON a.assetid = u.assetid
      WHERE 
        a.projectid = ${projectid}
      ORDER BY 
        COALESCE(u.access_count, 0) DESC;
    `;

    let usageResults = await query_database(photoapp_db, usageSql);

    // Get project-level summary
    let summarySql = `
      SELECT 
        COUNT(a.assetid) AS total_assets,
        SUM(COALESCE(u.access_count, 0)) AS total_accesses,
        MAX(u.last_accessed) AS last_accessed,
        COUNT(DISTINCT CASE WHEN u.access_count > 0 THEN a.assetid END) AS assets_accessed
      FROM 
        assets a
      LEFT JOIN 
        asset_usage u ON a.assetid = u.assetid
      WHERE 
        a.projectid = ${projectid};
    `;

    let summaryResult = await query_database(photoapp_db, summarySql);

    // Format response
    let response = {
      projectid: projectid,
      projectname: projectResult[0].projectname,
      summary: {
        total_assets: summaryResult[0].total_assets,
        total_accesses: summaryResult[0].total_accesses || 0,
        last_accessed: summaryResult[0].last_accessed,
        assets_accessed: summaryResult[0].assets_accessed || 0,
        access_percentage:
          summaryResult[0].total_assets > 0
            ? Math.round(
                ((summaryResult[0].assets_accessed || 0) /
                  summaryResult[0].total_assets) *
                  100
              )
            : 0,
      },
      assets: usageResults.map((asset) => ({
        assetid: asset.assetid,
        assetname: asset.assetname,
        last_accessed: asset.last_accessed,
        access_count: asset.access_count || 0,
        unique_referers: asset.unique_referers || 0,
      })),
    };

    res.json({
      message: "success",
      data: response,
    });
  } catch (err) {
    console.log("**Error in /project/:projectid/usage");
    console.log(err.message);

    res.status(500).json({
      message: err.message,
      data: null,
    });
  }
};

//
// GET /client/:clientid/usage - Get usage statistics for all projects of a client
//
exports.get_client_usage = async (req, res) => {
  console.log("**Call to get /client/:clientid/usage...");

  try {
    let clientid = req.params.clientid;

    if (isNaN(clientid)) {
      res.status(400).json({
        message: "Invalid client ID format",
        data: null,
      });
      return;
    }

    // Check if client exists
    let clientSql = `
      SELECT clientid, clientname 
      FROM clients 
      WHERE clientid = ${clientid};
    `;

    let clientResult = await query_database(photoapp_db, clientSql);

    if (clientResult.length === 0) {
      res.status(404).json({
        message: "Client not found",
        data: null,
      });
      return;
    }

    // Get project usage summary
    let projectsSql = `
      SELECT 
        p.projectid,
        p.projectname,
        COUNT(a.assetid) AS asset_count,
        SUM(COALESCE(u.access_count, 0)) AS total_accesses,
        MAX(u.last_accessed) AS last_accessed
      FROM 
        projects p
      LEFT JOIN 
        assets a ON p.projectid = a.projectid
      LEFT JOIN 
        asset_usage u ON a.assetid = u.assetid
      WHERE 
        p.clientid = ${clientid}
      GROUP BY 
        p.projectid, p.projectname
      ORDER BY 
        total_accesses DESC;
    `;

    let projectResults = await query_database(photoapp_db, projectsSql);

    // Get client-level summary
    let summarySql = `
      SELECT 
        COUNT(DISTINCT p.projectid) AS total_projects,
        COUNT(a.assetid) AS total_assets,
        SUM(COALESCE(u.access_count, 0)) AS total_accesses,
        MAX(u.last_accessed) AS last_accessed,
        COUNT(DISTINCT CASE WHEN u.access_count > 0 THEN a.assetid END) AS assets_accessed
      FROM 
        clients c
      LEFT JOIN 
        projects p ON c.clientid = p.clientid
      LEFT JOIN 
        assets a ON p.projectid = a.projectid
      LEFT JOIN 
        asset_usage u ON a.assetid = u.assetid
      WHERE 
        c.clientid = ${clientid};
    `;

    let summaryResult = await query_database(photoapp_db, summarySql);

    // Format response
    let response = {
      clientid: clientid,
      clientname: clientResult[0].clientname,
      summary: {
        total_projects: summaryResult[0].total_projects,
        total_assets: summaryResult[0].total_assets || 0,
        total_accesses: summaryResult[0].total_accesses || 0,
        last_accessed: summaryResult[0].last_accessed,
        assets_accessed: summaryResult[0].assets_accessed || 0,
        access_percentage:
          summaryResult[0].total_assets > 0
            ? Math.round(
                ((summaryResult[0].assets_accessed || 0) /
                  summaryResult[0].total_assets) *
                  100
              )
            : 0,
      },
      projects: projectResults.map((project) => ({
        projectid: project.projectid,
        projectname: project.projectname,
        asset_count: project.asset_count || 0,
        total_accesses: project.total_accesses || 0,
        last_accessed: project.last_accessed,
      })),
    };

    res.json({
      message: "success",
      data: response,
    });
  } catch (err) {
    console.log("**Error in /client/:clientid/usage");
    console.log(err.message);

    res.status(500).json({
      message: err.message,
      data: null,
    });
  }
};

//
// GET /usage/top-assets - Get top accessed assets across the whole system
//
exports.get_top_assets = async (req, res) => {
  console.log("**Call to get /usage/top-assets...");

  try {
    // Get limit parameter or default to 10
    let limit = req.query.limit || 10;

    if (isNaN(limit) || limit < 1 || limit > 100) {
      limit = 10;
    }

    // Get top assets
    let sql = `
      SELECT 
        a.assetid,
        a.assetname,
        p.projectid,
        p.projectname,
        c.clientid,
        c.clientname,
        u.access_count,
        u.last_accessed,
        u.unique_referers
      FROM 
        asset_usage u
      JOIN 
        assets a ON u.assetid = a.assetid
      JOIN 
        projects p ON a.projectid = p.projectid
      JOIN 
        clients c ON p.clientid = c.clientid
      ORDER BY 
        u.access_count DESC
      LIMIT ${limit};
    `;

    let results = await query_database(photoapp_db, sql);

    // Format response
    let response = results.map((asset) => ({
      assetid: asset.assetid,
      assetname: asset.assetname,
      projectid: asset.projectid,
      projectname: asset.projectname,
      clientid: asset.clientid,
      clientname: asset.clientname,
      access_count: asset.access_count,
      last_accessed: asset.last_accessed,
      unique_referers: asset.unique_referers,
    }));

    res.json({
      message: "success",
      data: response,
    });
  } catch (err) {
    console.log("**Error in /usage/top-assets");
    console.log(err.message);

    res.status(500).json({
      message: err.message,
      data: [],
    });
  }
};
