# Asset Return Bulk Import - CSV Format Guide

## Overview
This CSV format allows you to bulk import Asset Return (Claw) tickets with automatic customer creation.

## CSV Columns

### Required Customer Fields
- **customer_name**: Full name of the customer (REQUIRED)
- **customer_email**: Customer's email address (REQUIRED for auto-creation)
- **customer_phone**: Customer's phone number (Optional but recommended)
- **customer_company**: Customer's company name (Optional)
- **customer_country**: Customer's country (REQUIRED - must match: SINGAPORE, USA, INDIA, JAPAN, etc.)

### Required Return Fields
- **return_description**: Description of the return/issue (REQUIRED)

### Optional Asset Fields
- **asset_serial_number**: Serial number of the asset being returned (Optional)

### Optional Ticket Management Fields
- **priority**: Ticket priority (Low, Medium, High, Critical - defaults to Medium)
- **queue_name**: Name of the queue to assign ticket (Optional)
- **case_owner_email**: Email of the user to assign as case owner (Optional)
- **notes**: Additional notes for the ticket (Optional)

## Customer Auto-Creation Logic
The system will:
1. Check if a customer exists with the provided email
2. If found, use the existing customer
3. If not found, create a new customer with the provided details
4. Customer country MUST match one of the system's supported countries

## Important Notes
- Headers must match exactly (case-sensitive)
- Empty cells are allowed for optional fields
- Date format: System will use current timestamp
- Maximum file size: 10MB
- Priority values: Low, Medium, High, Critical

## Example Usage
See `asset_return_bulk_import_sample.csv` for examples of:
- Customer with all details
- Customer with minimal details (auto-creation)
- Tickets with asset serial numbers
- Different priority levels
- Queue and case owner assignment

## Error Handling
The import will:
- Skip rows with missing required fields
- Report errors for invalid data (invalid country, priority)
- Continue processing valid rows even if some rows fail
- Provide a summary of successful and failed imports
