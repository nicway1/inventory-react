-- SQLite Company Grouping Migration
-- Adds columns needed for parent/child company relationships in SQLite

-- Check current table structure
.schema companies

-- Add parent_company_id column (integer reference to companies.id)
ALTER TABLE companies ADD COLUMN parent_company_id INTEGER;

-- Add display_name column (custom display name override)  
ALTER TABLE companies ADD COLUMN display_name TEXT;

-- Add is_parent_company column (boolean flag for parent companies)
ALTER TABLE companies ADD COLUMN is_parent_company BOOLEAN DEFAULT 0;

-- Show updated table structure
.schema companies

-- Display success message
SELECT 'SQLite company grouping migration completed successfully!' as message;
SELECT 'Columns added: parent_company_id, display_name, is_parent_company' as details;
SELECT 'Next: Visit /admin/company-grouping to set up relationships' as next_steps;

-- Note about foreign keys in SQLite
SELECT 'Note: Foreign key relationships are enforced by SQLAlchemy at application level' as foreign_key_info;