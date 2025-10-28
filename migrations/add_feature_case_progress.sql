-- Add case_progress field to feature_requests table
-- SQLite version (COMMENT not supported in SQLite)

ALTER TABLE feature_requests
ADD COLUMN case_progress INTEGER DEFAULT 0;
