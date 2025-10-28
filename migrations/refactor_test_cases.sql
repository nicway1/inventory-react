-- Migration: Refactor test cases to separate table
-- This migration removes the test_case column from bug_reports and creates a separate test_cases table

-- MySQL Version

-- Drop test_case column from bug_reports (if it exists)
SET @dbname = DATABASE();
SET @tablename = 'bug_reports';
SET @columnname = 'test_case';
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE
      (table_name = @tablename)
      AND (table_schema = @dbname)
      AND (column_name = @columnname)
  ) > 0,
  CONCAT('ALTER TABLE ', @tablename, ' DROP COLUMN ', @columnname, ';'),
  'SELECT 1;'
));
PREPARE alterIfExists FROM @preparedStatement;
EXECUTE alterIfExists;
DEALLOCATE PREPARE alterIfExists;

-- Create test_cases table
CREATE TABLE IF NOT EXISTS test_cases (
    id INT AUTO_INCREMENT PRIMARY KEY,
    bug_id INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    preconditions TEXT COMMENT 'What needs to be set up before testing',
    test_steps TEXT NOT NULL COMMENT 'Step-by-step instructions',
    expected_result TEXT NOT NULL COMMENT 'What should happen',
    actual_result TEXT COMMENT 'What actually happened (filled by tester)',
    status VARCHAR(20) DEFAULT 'Pending' COMMENT 'Pending, Passed, Failed, Blocked, Skipped',
    priority VARCHAR(20) DEFAULT 'Medium' COMMENT 'Low, Medium, High',
    test_data TEXT COMMENT 'Any specific data needed for testing',
    created_by_id INT NOT NULL,
    tested_by_id INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME ON UPDATE CURRENT_TIMESTAMP,
    tested_at DATETIME,
    FOREIGN KEY (bug_id) REFERENCES bug_reports(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by_id) REFERENCES users(id),
    FOREIGN KEY (tested_by_id) REFERENCES users(id),
    INDEX idx_bug_id (bug_id),
    INDEX idx_status (status),
    INDEX idx_created_by (created_by_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
