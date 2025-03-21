USE damdb;

DROP TABLE IF EXISTS asset_variants;
DROP TABLE IF EXISTS processing_jobs;

CREATE TABLE asset_variants (
  variantid int NOT NULL AUTO_INCREMENT,
  assetid int NOT NULL,
  variant_type varchar(32) NOT NULL,
  width int,
  height int,
  format varchar(16) NOT NULL,
  quality int,
  filesize int,
  bucketkey varchar(128) NOT NULL,
  cdn_url varchar(255) NOT NULL,
  PRIMARY KEY (variantid),
  UNIQUE KEY bucketkey (bucketkey),
  KEY assetid (assetid),
  CONSTRAINT asset_variants_ibfk_1 FOREIGN KEY (assetid) REFERENCES assets (assetid) ON DELETE CASCADE
) AUTO_INCREMENT=6001;

CREATE TABLE processing_jobs (
  jobid int NOT NULL AUTO_INCREMENT,
  assetid int NOT NULL,
  status enum('pending', 'processing', 'completed', 'failed') NOT NULL,
  processing_options JSON,
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  completed_at timestamp NULL DEFAULT NULL,
  error_message varchar(255),
  PRIMARY KEY (jobid),
  KEY assetid (assetid),
  CONSTRAINT processing_jobs_ibfk_1 FOREIGN KEY (assetid) REFERENCES assets (assetid) ON DELETE CASCADE
) AUTO_INCREMENT=3001;