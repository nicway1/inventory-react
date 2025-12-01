# Comprehensive Ticket System Testing Instructions

## Overview
Test all ticket categories and features to ensure the system is working correctly. Follow each section sequentially and report any errors or unexpected behavior.

---

## Pre-Testing Setup

1. **Login Credentials**: Ensure you have admin access
2. **Test Data Ready**:
   - At least 3 customers in different companies
   - At least 5 assets in stock
   - At least 10 accessories with available quantity > 0
   - At least 1 custom ticket status created

---

## Part 1: Test All Ticket Categories

### 1.1 PIN Request Ticket
**Steps:**
1. Navigate to "Create Ticket"
2. Select Category: "PIN Request"
3. Fill in:
   - Subject: "Test PIN Request - [Your Name]"
   - Description: "Testing PIN request functionality"
   - Select an asset (search by serial number)
   - Select customer
   - Add notes
4. Click "Create Ticket"
5. **Expected Result**: Ticket created successfully, redirects to ticket view

**Verify:**
- [ ] Ticket displays correct category
- [ ] Asset information shows correctly
- [ ] Customer information displays

---

### 1.2 Asset Repair Ticket
**Steps:**
1. Create Ticket → Category: "Asset Repair"
2. Fill in:
   - Subject: "Test Asset Repair - [Your Name]"
   - Description: "Testing repair workflow"
   - Select asset
   - Damage description: "Screen crack test"
   - Select repair status
3. Submit

**Verify:**
- [ ] Repair status field appears
- [ ] Damage description saves correctly
- [ ] Ticket shows repair-specific fields in view

---

### 1.3 Asset Checkout (various carriers)
**Test each carrier separately:**

#### a) Asset Checkout - SingPost
1. Category: "Asset Checkout (SingPost)"
2. Subject: "Test Checkout SingPost - [Your Name]"
3. Fill shipping address, tracking number
4. Add accessories if available
5. Submit

**Verify:**
- [ ] Carrier defaults to SingPost
- [ ] Tracking number saves
- [ ] Shipping address displays

#### b) Asset Checkout - DHL
1. Category: "Asset Checkout (DHL)"
2. Test same as above with DHL carrier

#### c) Asset Checkout - UPS
1. Category: "Asset Checkout (UPS)"
2. Test same as above

#### d) Asset Checkout (claw) - Multi-Package
**Special Test:**
1. Category: "Asset Checkout (claw)"
2. Add multiple tracking numbers (use up to 5 packages)
3. Add multiple accessories
4. Submit

**Verify:**
- [ ] All 5 tracking fields work
- [ ] Each package has carrier selection
- [ ] Accessories appear in ticket

---

### 1.4 Asset Return (claw)
**Steps:**
1. Category: "Asset Return (claw)"
2. Fill in:
   - Subject: "Test Return - [Your Name]"
   - Select customer
   - Return description: "Testing return workflow"
   - Return tracking number
   - Return carrier: Select any
   - Add accessories being returned
3. Submit

**Verify:**
- [ ] Return-specific fields show
- [ ] Customer company displays
- [ ] Return tracking saves
- [ ] Accessories list appears

---

### 1.5 Asset Intake
**Steps:**
1. Category: "Asset Intake"
2. Fill in:
   - Title: "Test Asset Intake - [Your Name]"
   - Description: "Testing intake workflow"
   - Upload packing list (any PDF/image)
   - Upload asset CSV (use sample or create one)
   - Select customer
   - Add notes
3. Submit

**Verify:**
- [ ] File uploads work
- [ ] Files are attached to ticket
- [ ] Customer name displays in ticket view
- [ ] Notes appear correctly

---

### 1.6 Internal Transfer ⭐ (NEW FEATURE)
**Steps:**
1. Category: "Internal Transfer"
2. Fill in:
   - **Offboarding Customer**: Select customer A
   - **Offboarding Device Details**: "MacBook Pro 16" M2, Serial: ABC123"
   - **Offboarding Address**: (should auto-fill from customer)
   - **Tracking Link**: "https://tracking.example.com/123" (optional)
   - **Onboarding Customer**: Select customer B from SAME company
   - **Onboarding Address**: (should auto-fill from customer)
   - **Notes**: "Test internal transfer"
3. Submit

**Verify:**
- [ ] Offboarding customer dropdown works
- [ ] Onboarding customer dropdown filters by same company
- [ ] Addresses auto-fill when customers selected
- [ ] Subject auto-generates as "Internal Transfer: [Offboarding] → [Onboarding]"
- [ ] Ticket view shows:
  - [ ] 📤 Offboarding Customer with name, company
  - [ ] Device details
  - [ ] Offboarding address
  - [ ] 📥 Onboarding Customer with name, company
  - [ ] Onboarding address

---

### 1.7 Bulk Delivery Quotation
**Steps:**
1. Category: "Bulk Delivery Quotation"
2. Fill basic fields
3. Submit

**Verify:**
- [ ] Ticket creates successfully

---

### 1.8 Repair Quote
**Steps:**
1. Category: "Repair Quote"
2. Fill in repair-specific information
3. Submit

**Verify:**
- [ ] Quote fields appear
- [ ] Data saves correctly

---

### 1.9 ITAD Quote
**Steps:**
1. Category: "ITAD Quote"
2. Fill required fields
3. Submit

**Verify:**
- [ ] Ticket creates successfully

---

## Part 2: Custom Ticket Status Testing ⭐ (NEW FEATURE)

### 2.1 Create Custom Status
**Steps:**
1. Navigate to Admin → Manage Ticket Statuses
2. Click "Add Status"
3. Fill in:
   - **Name**: `TEST_STATUS_1`
   - **Display Name**: "Test Status One"
   - **Color**: Blue
   - **Active**: ✓ Checked
   - **Auto-return to stock**: ✗ Unchecked
4. Save

**Verify:**
- [ ] Status appears in list
- [ ] Shows blue badge
- [ ] Shows "Active" badge

### 2.2 Create Auto-Return Status ⭐
**Steps:**
1. Click "Add Status" again
2. Fill in:
   - **Name**: `CASE_CLOSED_ORDER_CANCELED`
   - **Display Name**: "Case Closed - Order Canceled"
   - **Color**: Red
   - **Active**: ✓ Checked
   - **Auto-return to stock**: ✓ Checked ⭐
3. Save

**Verify:**
- [ ] Status appears with red badge
- [ ] Shows "Auto-Return" orange badge ⭐
- [ ] Tooltip shows "Automatically returns assets to stock"

### 2.3 Test Custom Status on Ticket
**Steps:**
1. Open any existing ticket
2. Change status to "Test Status One"
3. Save

**Verify:**
- [ ] Custom status appears in dropdown under "Custom Statuses" optgroup
- [ ] Status badge displays correctly with chosen color
- [ ] Long status names wrap properly (not cut off)
- [ ] Underscores replaced with spaces in display

---

## Part 3: Auto-Return to Stock Testing ⭐ (CRITICAL NEW FEATURE)

### 3.1 Setup Test Ticket with Assets and Accessories
**Steps:**
1. Create an "Asset Checkout (claw)" ticket
2. Assign 2-3 assets to the ticket
3. Assign 2-3 accessories with quantities
4. Save ticket
5. **Note down**:
   - Asset IDs and their current status
   - Accessory IDs and their available quantities
   - Total accessories assigned

### 3.2 Test Auto-Return Functionality
**Steps:**
1. Open the ticket created above
2. Note current inventory levels:
   - Check asset statuses (should NOT be "In Stock")
   - Check accessory quantities in inventory
3. Change ticket status to "Case Closed - Order Canceled"
4. Save ticket

**Verify:**
- [ ] Success message appears: "Status updated to 'Case Closed - Order Canceled' - All assets and accessories returned to stock"
- [ ] Navigate to Assets page and verify:
  - [ ] All assigned assets now show status = "IN_STOCK"
  - [ ] Assets are no longer linked to the ticket
- [ ] Navigate to Accessories page and verify:
  - [ ] Available quantities increased by the amounts that were assigned
  - [ ] Accessories no longer show as assigned to ticket
- [ ] Return to ticket view:
  - [ ] Status shows "Case Closed - Order Canceled" with red badge
  - [ ] Asset list is empty (cleared)
  - [ ] Accessory list is empty (cleared)

---

## Part 4: Bulk Import Testing

### 4.1 Download Sample CSV
**Steps:**
1. Navigate to "Bulk Import 1stbase Returns"
2. Click "Download Sample CSV" button (green, top right)

**Verify:**
- [ ] CSV file downloads
- [ ] Opens in Excel/Sheets
- [ ] Contains sample data with proper columns

### 4.2 Test Bulk Import
**Steps:**
1. Use the downloaded sample CSV (or modify it)
2. Upload the CSV file
3. Review preview
4. Confirm import

**Verify:**
- [ ] Preview shows correct data
- [ ] Duplicate detection works
- [ ] Customer creation works
- [ ] Tickets created successfully

---

## Part 5: Ticket Update and Management

### 5.1 Update Ticket Details
**Steps:**
1. Open any ticket
2. Update:
   - Priority
   - Status (system status)
   - Assigned user
   - Notes
   - Tracking numbers
3. Save

**Verify:**
- [ ] All changes save correctly
- [ ] Updated timestamp changes
- [ ] History/audit trail updated

### 5.2 Add Comments
**Steps:**
1. Add a comment to ticket
2. Save

**Verify:**
- [ ] Comment appears
- [ ] Timestamp correct
- [ ] User attribution correct

### 5.3 Attach Files
**Steps:**
1. Upload attachment to ticket
2. Save

**Verify:**
- [ ] File uploads successfully
- [ ] File appears in attachments list
- [ ] File can be downloaded

---

## Part 6: Search and Filter

### 6.1 Search Tickets
**Steps:**
1. Navigate to ticket list
2. Search by:
   - Ticket ID
   - Customer name
   - Serial number
   - Subject

**Verify:**
- [ ] Search returns correct results
- [ ] Filters work correctly

### 6.2 Filter by Category
**Steps:**
1. Filter tickets by each category
2. Verify results match category

**Verify:**
- [ ] All categories filter correctly
- [ ] Internal Transfer tickets show with proper icon/indicator

### 6.3 Filter by Custom Status
**Steps:**
1. Filter by custom status created earlier
2. Verify only tickets with that status appear

**Verify:**
- [ ] Custom status filter works
- [ ] Badge colors display correctly in list view

---

## Part 7: Edge Cases and Error Handling

### 7.1 Validation Testing
**Test required fields:**
1. Try to create ticket without subject → Should show error
2. Try to create ticket without category → Should show error
3. Internal Transfer without offboarding customer → Should show error
4. Internal Transfer without device details → Should show error

**Verify:**
- [ ] All validations work
- [ ] Error messages are clear
- [ ] Form doesn't submit with missing data

### 7.2 Company Filtering in Internal Transfer
**Steps:**
1. Create Internal Transfer ticket
2. Select offboarding customer from Company A
3. Check onboarding customer dropdown

**Verify:**
- [ ] Only shows customers from Company A
- [ ] Doesn't show customers from other companies
- [ ] If no customers in same company, shows helpful message

---

## Part 8: UI/UX Verification

### 8.1 Badge Display
**Check all status badges:**
- [ ] System statuses display correctly
- [ ] Custom statuses display with correct colors
- [ ] Long status names wrap properly (no truncation)
- [ ] Underscores converted to spaces
- [ ] Emojis display correctly (📤 📥 in Internal Transfer)

### 8.2 Responsive Design
**Test on different screen sizes:**
- [ ] Desktop view works
- [ ] Tablet view works
- [ ] Mobile view works (if applicable)

### 8.3 Loading States
**Verify:**
- [ ] Forms show loading states during submission
- [ ] No double-submission possible
- [ ] Proper feedback on success/error

---

## Part 9: Performance Testing

### 9.1 Large Data Sets
**Test with:**
1. Ticket with 50+ comments
2. Ticket with 10+ attachments
3. Ticket with 20+ accessories

**Verify:**
- [ ] Page loads in reasonable time
- [ ] No browser crashes
- [ ] Data displays correctly

---

## Part 10: Reporting Issues

### For Each Failed Test:
**Report the following:**
1. Test section and step number
2. Expected behavior
3. Actual behavior
4. Error messages (screenshot if possible)
5. Browser and OS information
6. Steps to reproduce

---

## Test Completion Checklist

- [ ] All ticket categories tested
- [ ] Custom statuses created and tested
- [ ] Auto-return to stock verified with assets and accessories
- [ ] Internal Transfer with offboarding/onboarding tested
- [ ] Bulk import tested
- [ ] Sample CSV download tested
- [ ] All UI elements display correctly
- [ ] All validations working
- [ ] No console errors observed
- [ ] Performance acceptable

---

## Summary Report Template

**Date:** ___________
**Tester Name:** ___________
**Total Tests:** 100+
**Tests Passed:** ___________
**Tests Failed:** ___________
**Critical Issues:** ___________
**Minor Issues:** ___________

**Critical Bugs Found:**
1.
2.
3.

**Minor Issues Found:**
1.
2.
3.

**Recommendations:**
1.
2.
3.

**Overall System Status:** ☐ Ready for Production  ☐ Needs Fixes  ☐ Major Issues

---

## Notes
- Test in a staging/development environment first
- Do NOT test auto-return to stock on production data initially
- Keep track of test data created for cleanup
- Report security concerns immediately
- Document any unexpected behavior, even if not breaking

---

**Good luck with testing! 🚀**