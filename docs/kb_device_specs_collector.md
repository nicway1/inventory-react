# How to Use the MacBook Specs Collector

The **Device Specs Collector** is a tool that allows you to remotely collect hardware specifications from any MacBook - even in Recovery Mode. This is useful for quickly gathering device information for inventory purposes.

## Accessing the Page

Navigate to: **`/device-specs`** or click on the "MacBook Specs Collector" widget on your dashboard.

---

## Collecting Device Specs

### Step 1: Copy the Command

On the Device Specs page, you'll see a command box with:

```bash
curl -sL https://inventory.truelog.com.sg/specs | bash
```

Click the **Copy** button to copy this command to your clipboard.

### Step 2: Run on the MacBook

Open **Terminal** on the MacBook you want to collect specs from and paste the command. Press Enter to run it.

**Note:** This command also works in **macOS Recovery Mode** - just open Terminal from the Utilities menu.

### Step 3: View the Results

Once the script runs, the device specs will automatically appear on the Device Specs page. The page shows:

- **Total Submissions** - All specs collected
- **Pending Review** - New submissions not yet processed
- **Processed** - Submissions that have been added to inventory
- **Last Submission** - Time of the most recent submission

---

## Understanding the Specs Cards

Each submitted device appears as a card showing:

| Field | Description |
|-------|-------------|
| **Serial Number** | Device serial number |
| **Model** | MacBook model name (e.g., "MacBook Pro 14-inch M3") |
| **CPU** | Processor type and core count |
| **RAM** | Memory in GB |
| **Storage** | Storage capacity and type |
| **Submitted** | Date and time of submission |

### Status Indicators

- **Yellow border + "New"** - Pending review, not yet added to inventory
- **Green border + "Done"** - Already processed/added to inventory

---

## Available Actions

### View Full Details
Click **View** to see complete device specifications including:
- Hardware UUID
- Model number/ID
- CPU and GPU details
- macOS version and build
- WiFi MAC address
- IP address used during submission

### Add to Inventory
Click **Add** to create a new asset in inventory using the collected specs. The form will be pre-filled with the device information.

### Find Related Tickets
Click **Tickets** to search for any existing tickets that mention this device's serial number or model. You can then:
- **View** the ticket
- **Add to Ticket** - Create an asset and link it to the ticket

### Delete Submission
Click the **trash icon** to remove a spec submission. Use this for duplicate or erroneous submissions.

---

## Tips

1. **Recovery Mode Collection**: If a device is locked or having issues, boot into Recovery Mode (hold Command+R during startup), open Terminal from Utilities menu, and run the command. You'll still get the hardware specs.

2. **Bulk Collection**: You can run the command on multiple MacBooks. Each submission appears separately on the page.

3. **Automatic Model Detection**: The system automatically identifies the MacBook model based on the model identifier.

4. **Link to Tickets**: Use the "Find Tickets" feature to quickly associate device specs with existing support tickets.

---

## FAQ

**Q: Does the script install anything on the MacBook?**
A: No, the script only reads hardware information and sends it to the server. Nothing is installed or modified on the device.

**Q: Can I use this on Windows or Linux?**
A: No, this tool is specifically designed for macOS/MacBooks only.

**Q: What if the same device is submitted multiple times?**
A: Each submission is recorded separately. You can delete duplicates using the trash icon.

**Q: Do I need to be logged in to the inventory system to submit specs?**
A: No, the curl command works without authentication. However, you need to be logged in to view and manage the collected specs.
