//
// Helper functions
//

// getContentType:
//   Returns the content type for a given file extension
// Helper function to determine content type from file extension
function getContentType(extension) {
  const contentTypes = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
    ".ico": "image/x-icon",
  };

  return contentTypes[extension] || "image/jpeg"; // Default to JPEG if unknown
}

//
// query_database:
//
// Queries database, returning a PROMISE that you can await on.
// When the PROMISE resolves, you'll have the results of your
// query (or you'll get an error thrown).
//
// Parameters:
//   db: database connection object
//   sql: query string to execute
//   params: optional array of parameters to inject into query string
//
function query_database(db, sql, params = []) {
  let response = new Promise((resolve, reject) => {
    try {
      //
      // execute the query, and when we get the callback from
      // the database server, either resolve with the results
      // or error with the error object
      //
      db.query(sql, params, (err, results, _) => {
        if (err) {
          reject(err);
        } else {
          resolve(results);
        }
      });
    } catch (err) {
      reject(err);
    }
  });

  //
  // return the PROMISE back to the caller, which will
  // eventually resolve to results or an error:
  //
  return response;
}

//
// list the functions we are exporting:
//
module.exports = { query_database, getContentType };
