-- Company Grouping Migration SQL
-- Adds columns needed for parent/child company relationships

-- Check if columns exist before adding (MySQL syntax)
SET @exist_parent = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
                     WHERE TABLE_SCHEMA = DATABASE() 
                     AND TABLE_NAME = 'companies' 
                     AND COLUMN_NAME = 'parent_company_id');

SET @exist_display = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
                      WHERE TABLE_SCHEMA = DATABASE() 
                      AND TABLE_NAME = 'companies' 
                      AND COLUMN_NAME = 'display_name');

SET @exist_parent_flag = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
                          WHERE TABLE_SCHEMA = DATABASE() 
                          AND TABLE_NAME = 'companies' 
                          AND COLUMN_NAME = 'is_parent_company');

-- Add parent_company_id column (foreign key to companies.id)
SET @sql_parent = IF(@exist_parent = 0,
    'ALTER TABLE companies ADD COLUMN parent_company_id INT NULL',
    'SELECT "parent_company_id column already exists" as message');
PREPARE stmt_parent FROM @sql_parent;
EXECUTE stmt_parent;
DEALLOCATE PREPARE stmt_parent;

-- Add display_name column (custom display name override)  
SET @sql_display = IF(@exist_display = 0,
    'ALTER TABLE companies ADD COLUMN display_name VARCHAR(200) NULL',
    'SELECT "display_name column already exists" as message');
PREPARE stmt_display FROM @sql_display;
EXECUTE stmt_display;
DEALLOCATE PREPARE stmt_display;

-- Add is_parent_company column (boolean flag for parent companies)
SET @sql_parent_flag = IF(@exist_parent_flag = 0,
    'ALTER TABLE companies ADD COLUMN is_parent_company BOOLEAN DEFAULT FALSE',
    'SELECT "is_parent_company column already exists" as message');
PREPARE stmt_parent_flag FROM @sql_parent_flag;
EXECUTE stmt_parent_flag;
DEALLOCATE PREPARE stmt_parent_flag;

-- Add foreign key constraint for parent_company_id (if not exists)
SET @exist_fk = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
                 WHERE TABLE_SCHEMA = DATABASE() 
                 AND TABLE_NAME = 'companies' 
                 AND CONSTRAINT_NAME = 'fk_companies_parent');

SET @sql_fk = IF(@exist_fk = 0 AND @exist_parent = 0,
    'ALTER TABLE companies ADD CONSTRAINT fk_companies_parent FOREIGN KEY (parent_company_id) REFERENCES companies(id) ON DELETE SET NULL ON UPDATE CASCADE',
    'SELECT "Foreign key constraint already exists or not needed" as message');
PREPARE stmt_fk FROM @sql_fk;
EXECUTE stmt_fk;
DEALLOCATE PREPARE stmt_fk;

-- Show the updated table structure
DESCRIBE companies;

-- Display success message
SELECT 'Company grouping migration completed successfully!' as message;
SELECT 'Columns added: parent_company_id, display_name, is_parent_company' as details;
SELECT 'Next: Visit /admin/company-grouping to set up relationships' as next_steps;