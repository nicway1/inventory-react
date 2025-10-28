-- Migration: Add case_progress field to bug_reports
-- MySQL Version

-- Add case_progress column
ALTER TABLE bug_reports
ADD COLUMN case_progress INT DEFAULT 0
COMMENT 'Progress percentage 0-100';
