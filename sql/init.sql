CREATE DATABASE IF NOT EXISTS pump_station DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE pump_station;

-- 1. 用户表
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin','operator','viewer') DEFAULT 'operator',
    avatar VARCHAR(255) DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. 对话会话表
CREATE TABLE IF NOT EXISTS conversations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(200) DEFAULT '新对话',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. 消息记录表
CREATE TABLE IF NOT EXISTS messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    conversation_id INT NOT NULL,
    role ENUM('user','assistant','system') NOT NULL,
    content TEXT,
    msg_type ENUM('text','voice','docx') DEFAULT 'text',
    file_url VARCHAR(500) DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. 泵站表
CREATE TABLE IF NOT EXISTS pump_stations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    location VARCHAR(200),
    meta_json JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. 机组表
CREATE TABLE IF NOT EXISTS pump_units (
    id INT AUTO_INCREMENT PRIMARY KEY,
    station_id INT NOT NULL,
    unit_name VARCHAR(50),
    rated_power_kw DECIMAL(10,2),
    rated_flow DECIMAL(10,2),
    meta_json JSON COMMENT '效率曲线/功率-流量关系参数',
    FOREIGN KEY (station_id) REFERENCES pump_stations(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. 实时工况表
CREATE TABLE IF NOT EXISTS operating_points (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    station_id INT NOT NULL,
    flow DECIMAL(10,2),
    head DECIMAL(10,2),
    power DECIMAL(10,2),
    voltage DECIMAL(10,2),
    current_amp DECIMAL(10,2),
    energy_wh DECIMAL(12,2),
    ts DATETIME NOT NULL,
    FOREIGN KEY (station_id) REFERENCES pump_stations(id) ON DELETE CASCADE,
    INDEX idx_station_ts (station_id, ts)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 7. 调度任务表
CREATE TABLE IF NOT EXISTS schedule_tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    conversation_id INT,
    objective_text TEXT,
    constraints_json JSON,
    status ENUM('created','parsing','optimizing','validating','done','failed') DEFAULT 'created',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 8. 调度方案表
CREATE TABLE IF NOT EXISTS schedule_plans (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_id INT NOT NULL,
    plan_json JSON COMMENT '机组开停与负荷分配方案',
    energy_kwh DECIMAL(10,2),
    explanation TEXT COMMENT '大模型生成的自然语言解释',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES schedule_tasks(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 9. 审计日志
CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    action VARCHAR(100),
    payload_json JSON,
    ts DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 插入默认管理员账号 (密码: admin123，bcrypt hash，须为 60 字符)
INSERT IGNORE INTO users (username, password_hash, role) VALUES
('admin', '$2b$12$oSup02NPjzn2LRCp/BiAF.lnKDK9ae7RO5l/5RTd.mCQsdJcdMk7y', 'admin');
