-- Add case_progress field to feature_requests table
-- MySQL version

ALTER TABLE feature_requests
ADD COLUMN case_progress INT DEFAULT 0
COMMENT 'Progress percentage 0-100';
