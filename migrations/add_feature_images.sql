-- Add images column to feature_requests table
-- Stores JSON array of image paths

-- For MySQL
ALTER TABLE feature_requests
ADD COLUMN images TEXT NULL;

-- For SQLite (comment out the MySQL line above and use this instead)
-- ALTER TABLE feature_requests ADD COLUMN images TEXT;
