# Database Migrations

This directory contains database migration scripts for the inventory system.

## Customer Country Column Migration

Changes `customer_users.country` from ENUM to VARCHAR(100) to support custom country names.

### Migration Options

#### 1. Python Script (Recommended)
```bash
python3 migrations/migrate_customer_country.py
```

The script will:
- Check current column type
- Ask for confirmation before proceeding
- Safely migrate the column type
- Preserve all existing data
- Show progress and success/failure messages

#### 2. Manual SQL Execution
```bash
mysql -u username -p database_name < migrations/change_customer_country_to_string.sql
```

### What It Does

- Creates a temporary `country_temp` column (VARCHAR)
- Copies all data from `country` to `country_temp`
- Drops the old ENUM `country` column
- Renames `country_temp` to `country`

### After Migration

You can now:
- Select from predefined countries (USA, Japan, Singapore, etc.)
- Click the **+** button to enter custom country names (e.g., "North Korea")
- Custom countries automatically appear in future dropdowns

### Rollback

⚠️ **Warning**: No automatic rollback. Backup your database first!

To manually rollback:
```sql
-- Ensure all custom countries are in the Country enum first
ALTER TABLE customer_users
MODIFY COLUMN country ENUM('USA', 'JAPAN', ...) NOT NULL;
```

---

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