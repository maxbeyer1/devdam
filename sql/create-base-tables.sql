USE damdb;

DROP TABLE IF EXISTS assets;
DROP TABLE IF EXISTS projects;
DROP TABLE IF EXISTS clients;
DROP TABLE IF EXISTS users;

-- Users table
CREATE TABLE users (
  userid int NOT NULL AUTO_INCREMENT,
  email varchar(128) NOT NULL,
  lastname varchar(64) NOT NULL,
  firstname varchar(64) NOT NULL,
  bucketfolder varchar(48) NOT NULL,
  PRIMARY KEY (userid),
  UNIQUE KEY email (email),
  UNIQUE KEY bucketfolder (bucketfolder)
) AUTO_INCREMENT=80001;

-- Clients table
CREATE TABLE clients (
  clientid int NOT NULL AUTO_INCREMENT,
  userid int NOT NULL,
  clientname varchar(128) NOT NULL,
  description varchar(255),
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (clientid),
  KEY userid (userid),
  CONSTRAINT clients_ibfk_1 FOREIGN KEY (userid) REFERENCES users (userid)
) AUTO_INCREMENT=1001;

-- Projects table
CREATE TABLE projects (
  projectid int NOT NULL AUTO_INCREMENT,
  clientid int NOT NULL,
  projectname varchar(128) NOT NULL,
  description varchar(255),
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (projectid),
  KEY clientid (clientid),
  CONSTRAINT projects_ibfk_1 FOREIGN KEY (clientid) REFERENCES clients (clientid)
) AUTO_INCREMENT=2001;

-- Assets table
CREATE TABLE assets (
  assetid int NOT NULL AUTO_INCREMENT,
  userid int NOT NULL,
  projectid int NOT NULL,
  assetname varchar(128) NOT NULL,
  description varchar(255),
  bucketkey varchar(128) NOT NULL,
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (assetid),
  UNIQUE KEY bucketkey (bucketkey),
  KEY userid (userid),
  KEY projectid (projectid),
  CONSTRAINT assets_ibfk_1 FOREIGN KEY (userid) REFERENCES users (userid),
  CONSTRAINT assets_ibfk_2 FOREIGN KEY (projectid) REFERENCES projects (projectid)
) AUTO_INCREMENT=5001;