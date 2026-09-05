-- The read-only account pyfog is meant to use; docker-compose.yml points
-- pyfog at it instead of root.
CREATE USER IF NOT EXISTS 'fogread'@'%' IDENTIFIED BY 'fogread';
GRANT SELECT ON `fog`.* TO 'fogread'@'%';
FLUSH PRIVILEGES;
