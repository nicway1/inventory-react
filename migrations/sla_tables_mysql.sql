-- Migration: Create SLA and Holiday tables (MySQL)
--
-- Run this script on MySQL to create the sla_configs and queue_holidays tables.
-- Usage: mysql -u user -p database < migrations/sla_tables_mysql.sql
-- Or run directly in MySQL Workbench / phpMyAdmin

-- Create sla_configs table
CREATE TABLE IF NOT EXISTS sla_configs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    queue_id INT NOT NULL,
    ticket_category VARCHAR(50) NOT NULL,
    working_days INT NOT NULL DEFAULT 3,
    description VARCHAR(500),
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME ON UPDATE CURRENT_TIMESTAMP,
    created_by_id INT,
    FOREIGN KEY (queue_id) REFERENCES queues(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by_id) REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE KEY uq_queue_category_sla (queue_id, ticket_category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create queue_holidays table
CREATE TABLE IF NOT EXISTS queue_holidays (
    id INT AUTO_INCREMENT PRIMARY KEY,
    queue_id INT NOT NULL,
    holiday_date DATE NOT NULL,
    name VARCHAR(200) NOT NULL,
    country VARCHAR(100),
    is_recurring BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by_id INT,
    FOREIGN KEY (queue_id) REFERENCES queues(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by_id) REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE KEY uq_queue_holiday_date (queue_id, holiday_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Add indexes for better query performance
CREATE INDEX idx_sla_configs_queue ON sla_configs(queue_id);
CREATE INDEX idx_sla_configs_category ON sla_configs(ticket_category);
CREATE INDEX idx_sla_configs_active ON sla_configs(is_active);
CREATE INDEX idx_queue_holidays_queue ON queue_holidays(queue_id);
CREATE INDEX idx_queue_holidays_date ON queue_holidays(holiday_date);

-- Verify tables were created
SELECT 'SLA tables created successfully!' AS status;
SHOW TABLES LIKE 'sla_%';
SHOW TABLES LIKE 'queue_holidays';
