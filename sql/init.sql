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
    is_deleted TINYINT(1) DEFAULT 0 COMMENT '软删除标记',
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

-- 演示泵站与机组（详设 §1.1 工况展示依赖种子数据）
INSERT IGNORE INTO pump_stations (id, name, location, meta_json) VALUES
(1, '东湖泵站', '浙江省杭州市', '{"design_flow": 500, "design_head": 12}');

INSERT IGNORE INTO pump_units (id, station_id, unit_name, rated_power_kw, rated_flow, meta_json) VALUES
(1, 1, '1号机组', 150.00, 100.00, '{"efficiency_curve": "standard"}'),
(2, 1, '2号机组', 180.00, 120.00, '{"efficiency_curve": "standard"}'),
(3, 1, '3号机组', 200.00, 150.00, '{"efficiency_curve": "standard"}'),
(4, 1, '4号机组', 220.00, 160.00, '{"efficiency_curve": "standard"}');

-- 演示工况数据（最近 24 小时采样）
INSERT IGNORE INTO operating_points (id, station_id, flow, head, power, voltage, current_amp, energy_wh, ts) VALUES
(1, 1, 280.00, 11.50, 320.00, 380.00, 520.00, 320000.00, DATE_SUB(NOW(), INTERVAL 6 HOUR)),
(2, 1, 295.00, 11.80, 335.00, 381.00, 540.00, 335000.00, DATE_SUB(NOW(), INTERVAL 5 HOUR)),
(3, 1, 310.00, 12.00, 350.00, 382.00, 560.00, 350000.00, DATE_SUB(NOW(), INTERVAL 4 HOUR)),
(4, 1, 305.00, 11.90, 345.00, 380.00, 550.00, 345000.00, DATE_SUB(NOW(), INTERVAL 3 HOUR)),
(5, 1, 290.00, 11.70, 330.00, 379.00, 530.00, 330000.00, DATE_SUB(NOW(), INTERVAL 2 HOUR)),
(6, 1, 300.00, 11.85, 340.00, 380.00, 545.00, 340000.00, DATE_SUB(NOW(), INTERVAL 1 HOUR)),
(7, 1, 315.00, 12.10, 355.00, 382.00, 565.00, 355000.00, NOW());
