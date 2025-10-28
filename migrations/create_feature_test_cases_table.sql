-- Create feature_test_cases table for test case management
-- SQLite version

CREATE TABLE IF NOT EXISTS feature_test_cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feature_id INTEGER NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    preconditions TEXT,
    test_steps TEXT NOT NULL,
    expected_result TEXT NOT NULL,
    actual_result TEXT,
    status VARCHAR(20) DEFAULT 'Pending',
    priority VARCHAR(20) DEFAULT 'Medium',
    test_data TEXT,
    created_by_id INTEGER NOT NULL,
    tested_by_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME,
    tested_at DATETIME,
    FOREIGN KEY (feature_id) REFERENCES feature_requests(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by_id) REFERENCES users(id),
    FOREIGN KEY (tested_by_id) REFERENCES users(id)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_feature_test_cases_feature_id ON feature_test_cases(feature_id);
CREATE INDEX IF NOT EXISTS idx_feature_test_cases_status ON feature_test_cases(status);
CREATE INDEX IF NOT EXISTS idx_feature_test_cases_priority ON feature_test_cases(priority);
