-- 修复 admin 密码哈希（原 init.sql 中哈希被截断会导致「malformed bcrypt hash」）
-- 密码仍为: admin123
-- 在 MySQL 中执行: mysql -u root -p pump_station < sql/fix_admin_password.sql

UPDATE users
SET password_hash = '$2b$12$oSup02NPjzn2LRCp/BiAF.lnKDK9ae7RO5l/5RTd.mCQsdJcdMk7y'
WHERE username = 'admin';
