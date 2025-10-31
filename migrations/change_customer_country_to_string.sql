-- Migration: Change customer_users.country from ENUM to VARCHAR(100)
-- This allows custom country names to be entered

-- Step 1: Add a temporary column
ALTER TABLE customer_users ADD COLUMN country_temp VARCHAR(100);

-- Step 2: Copy data from enum to string, handling both enum values and potential custom values
UPDATE customer_users SET country_temp = country;

-- Step 3: Drop the old enum column
ALTER TABLE customer_users DROP COLUMN country;

-- Step 4: Rename the temp column to country
ALTER TABLE customer_users CHANGE COLUMN country_temp country VARCHAR(100) NOT NULL;

-- Note: After running this migration, you can add any custom country values
