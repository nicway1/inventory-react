-- Create feature_test_cases table for test case management
-- MySQL version

CREATE TABLE IF NOT EXISTS feature_test_cases (
    id INT AUTO_INCREMENT PRIMARY KEY,
    feature_id INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    preconditions TEXT,
    test_steps TEXT NOT NULL,
    expected_result TEXT NOT NULL,
    actual_result TEXT,
    status VARCHAR(20) DEFAULT 'Pending',
    priority VARCHAR(20) DEFAULT 'Medium',
    test_data TEXT,
    created_by_id INT NOT NULL,
    tested_by_id INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME ON UPDATE CURRENT_TIMESTAMP,
    tested_at DATETIME,
    FOREIGN KEY (feature_id) REFERENCES feature_requests(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by_id) REFERENCES users(id),
    FOREIGN KEY (tested_by_id) REFERENCES users(id),
    INDEX idx_feature_id (feature_id),
    INDEX idx_status (status),
    INDEX idx_priority (priority)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
