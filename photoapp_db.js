//
// photoapp_db.js
//
// Exports 
// photoapp_db: connection object to our MySQL database in AWS RDS
//

const mysql = require('mysql');
const fs = require('fs');
const ini = require('ini');

const config = require('./config.js');

const photoapp_config = ini.parse(fs.readFileSync(config.photoapp_config, 'utf-8'));
const endpoint = photoapp_config.rds.endpoint;
const port_number = photoapp_config.rds.port_number;
const user_name = photoapp_config.rds.user_name;
const user_pwd = photoapp_config.rds.user_pwd;
const db_name = photoapp_config.rds.db_name;

//
// creates connection object, but doesn't open connnection:
//
let photoapp_db = mysql.createConnection(
  {
    host: endpoint,
    port: port_number,
    user: user_name,
    password: user_pwd,
    database: db_name,
    multipleStatements: true  // allow multiple queries in one call
  }
);

module.exports = photoapp_db;
