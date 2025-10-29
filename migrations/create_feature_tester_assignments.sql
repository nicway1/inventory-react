-- Create feature_tester_assignments table
-- Links features to testers for testing assignments

CREATE TABLE IF NOT EXISTS feature_tester_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feature_id INTEGER NOT NULL,
    tester_id INTEGER NOT NULL,
    assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    notified VARCHAR(10) DEFAULT 'No',
    notified_at DATETIME,
    test_status VARCHAR(20) DEFAULT 'Pending',
    test_notes TEXT,
    tested_at DATETIME,
    FOREIGN KEY (feature_id) REFERENCES feature_requests(id) ON DELETE CASCADE,
    FOREIGN KEY (tester_id) REFERENCES testers(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_feature_tester_feature_id ON feature_tester_assignments(feature_id);
CREATE INDEX IF NOT EXISTS idx_feature_tester_tester_id ON feature_tester_assignments(tester_id);
CREATE INDEX IF NOT EXISTS idx_feature_tester_status ON feature_tester_assignments(test_status);
