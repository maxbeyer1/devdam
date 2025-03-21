USE damdb;

DROP TABLE IF EXISTS asset_usage;

CREATE TABLE asset_usage (
  assetid int NOT NULL,
  last_accessed timestamp NULL DEFAULT NULL,
  access_count int NOT NULL DEFAULT 0,
  last_referer varchar(255),
  unique_referers int NOT NULL DEFAULT 0,
  PRIMARY KEY (assetid),
  CONSTRAINT asset_usage_ibfk_1 FOREIGN KEY (assetid) REFERENCES assets (assetid) ON DELETE CASCADE
);