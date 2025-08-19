# Database Migrations

This directory contains database migration scripts for the inventory system.

## Company Grouping Migration

The company grouping feature adds the ability to create parent/child relationships between companies (e.g., "Wise (Firstbase)").

### Migration Options

Choose one of these methods to add the required columns:

#### 1. Python Script (Recommended)
Uses your existing database configuration:
```bash
python3 add_company_grouping_migration_simple.py
```

#### 2. Full Migration Script
More comprehensive with error handling:
```bash
python3 migrations/add_company_grouping_columns.py
```

#### 3. Manual SQL Execution
If you prefer to run SQL directly:
```sql
-- Connect to your database and run:
source migrations/company_grouping.sql
```

### What Gets Added

The migration adds these columns to the `companies` table:

- **parent_company_id** (INT, NULL) - Foreign key to companies.id for parent company
- **display_name** (VARCHAR(200), NULL) - Custom display name override  
- **is_parent_company** (BOOLEAN, DEFAULT FALSE) - Flag for parent companies

### After Migration

1. **Restart** your Flask application
2. **Visit** `/admin/company-grouping` to manage relationships
3. **Set up** parent/child relationships:
   - Make Firstbase a parent company
   - Set Wise as child of Firstbase
   - Result: Assets show "Wise (Firstbase)" in inventory

### Example Setup

```
Firstbase (Parent)
└── Wise (Child) → Displays as "Wise (Firstbase)"
```

### Verification

Check that columns were added:
```sql
DESCRIBE companies;
```

You should see the new columns in the table structure.

### Rollback (if needed)

To remove the columns:
```sql
ALTER TABLE companies 
DROP FOREIGN KEY fk_companies_parent,
DROP COLUMN parent_company_id,
DROP COLUMN display_name, 
DROP COLUMN is_parent_company;
```

## Troubleshooting

### Foreign Key Error
If the foreign key constraint fails, the migration will continue. The parent_company_id column will still work without the constraint.

### Columns Already Exist
The migration scripts check for existing columns and will skip them if they already exist.

### Database Connection Issues
Make sure your database configuration is correct in `config.py` or environment variables.