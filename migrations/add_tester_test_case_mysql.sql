-- MySQL Migration: Add test_case field and tester tables
-- Run this with: mysql -u root -p inventory < migrations/add_tester_test_case_mysql.sql

-- 1. Add test_case column to bug_reports
ALTER TABLE bug_reports
ADD COLUMN test_case TEXT NULL;

-- 2. Create testers table
CREATE TABLE IF NOT EXISTS testers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    specialization VARCHAR(100) NULL,
    is_active VARCHAR(10) DEFAULT 'Yes',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. Create bug_tester_assignments table
CREATE TABLE IF NOT EXISTS bug_tester_assignments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    bug_id INT NOT NULL,
    tester_id INT NOT NULL,
    assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    notified VARCHAR(10) DEFAULT 'No',
    notified_at DATETIME NULL,
    test_status VARCHAR(20) DEFAULT 'Pending',
    test_notes TEXT NULL,
    tested_at DATETIME NULL,
    FOREIGN KEY (bug_id) REFERENCES bug_reports(id) ON DELETE CASCADE,
    FOREIGN KEY (tester_id) REFERENCES testers(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Done!
SELECT 'Migration completed successfully!' as status;
