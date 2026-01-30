"""
Migration: Create SLA and Holiday tables (MySQL - PythonAnywhere)

Run this script on PythonAnywhere to create the sla_configs and queue_holidays tables.
Usage: python3 migrations/run_sla_mysql.py
"""

import mysql.connector

# PythonAnywhere MySQL connection settings
DB_CONFIG = {
    'host': 'nicway2.mysql.pythonanywhere-services.com',
    'user': 'nicway2',
    'password': 'Truelog123@',
    'database': 'nicway2$default'
}

# SQL statements to create tables
CREATE_SLA_CONFIGS = """
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
"""

CREATE_QUEUE_HOLIDAYS = """
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
"""

# Index statements
CREATE_INDEXES = [
    "CREATE INDEX idx_sla_configs_queue ON sla_configs(queue_id);",
    "CREATE INDEX idx_sla_configs_category ON sla_configs(ticket_category);",
    "CREATE INDEX idx_sla_configs_active ON sla_configs(is_active);",
    "CREATE INDEX idx_queue_holidays_queue ON queue_holidays(queue_id);",
    "CREATE INDEX idx_queue_holidays_date ON queue_holidays(holiday_date);"
]


def run_migration():
    print("Connecting to MySQL database...")

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        print("Creating sla_configs table...")
        cursor.execute(CREATE_SLA_CONFIGS)

        print("Creating queue_holidays table...")
        cursor.execute(CREATE_QUEUE_HOLIDAYS)

        print("Creating indexes...")
        for index_sql in CREATE_INDEXES:
            try:
                cursor.execute(index_sql)
            except mysql.connector.Error as e:
                # Ignore "index already exists" errors
                if e.errno != 1061:
                    print(f"  Warning: {e.msg}")

        conn.commit()

        # Verify tables exist
        cursor.execute("SHOW TABLES LIKE 'sla_%'")
        sla_tables = cursor.fetchall()
        cursor.execute("SHOW TABLES LIKE 'queue_holidays'")
        holiday_tables = cursor.fetchall()

        print("\n✓ Migration completed successfully!")
        print("Tables created:")
        for table in sla_tables:
            print(f"  - {table[0]}")
        for table in holiday_tables:
            print(f"  - {table[0]}")

        cursor.close()
        conn.close()

        print("\nNext steps:")
        print("1. Reload your web app from the PythonAnywhere Web tab")
        print("2. Add 'Case Manager SLA' widget to your dashboard")
        print("3. Configure SLA rules at /sla/manage")

    except mysql.connector.Error as e:
        print(f"Error: {e}")
        return False

    return True


if __name__ == '__main__':
    run_migration()
