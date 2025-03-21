CREATE USER 'dam-read-write'@'%' IDENTIFIED BY 'dam123!!';
GRANT SELECT, INSERT, UPDATE, DELETE ON damdb.* TO 'dam-read-write'@'%';
FLUSH PRIVILEGES;