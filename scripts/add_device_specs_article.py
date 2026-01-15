#!/usr/bin/env python3
"""Script to add Device Specs Collector article to knowledge base
Run on PythonAnywhere: python scripts/add_device_specs_article.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models.knowledge_article import KnowledgeArticle, ArticleStatus, ArticleVisibility
from models.knowledge_category import KnowledgeCategory
from models.user import User
from datetime import datetime, timezone

article_content = """
<h2>Overview</h2>
<p>The <strong>MacBook Specs Collector</strong> is a tool that allows you to remotely collect hardware specifications from any MacBook - even in Recovery Mode. This is useful for quickly gathering device information for inventory purposes.</p>

<h2>Accessing the Page</h2>
<p>Navigate to <code>/device-specs</code> or click on the <strong>"MacBook Specs Collector"</strong> widget on your dashboard.</p>

<hr>

<h2>Collecting Device Specs (Recovery Mode)</h2>

<p>Follow these steps to collect specs from a MacBook in Recovery Mode:</p>

<h3>Step 1: Enter Recovery Mode</h3>
<ol>
<li>Hold the <strong>Power Button</strong> on the MacBook until the startup options screen appears</li>
<li>You will see the "Options" page with startup disks</li>
</ol>

<h3>Step 2: Open Safari and Get the Command</h3>
<ol>
<li>Click on <strong>Safari</strong> from the menu or options</li>
<li>In the Safari address bar, go to <strong>tinyurl.com</strong></li>
<li>Type <strong>12888x</strong> in the URL field (this redirects to the specs page)</li>
<li>The page will load showing the command to copy</li>
<li><strong>Copy the command</strong> from the page</li>
<li>Exit Safari when done</li>
</ol>

<h3>Step 3: Run the Command in Terminal</h3>
<ol>
<li>From the menu bar, go to <strong>Utilities &gt; Terminal</strong></li>
<li><strong>Paste the command</strong> you copied and press Enter</li>
<li>Wait for the script to complete - it will collect all device specifications</li>
</ol>

<h3>Step 4: Process the Submission</h3>
<ol>
<li>Go to the <strong>MacBook Specs Collector</strong> widget on your dashboard (or navigate to <code>/device-specs</code>)</li>
<li>Find the newly submitted device spec card</li>
<li>Click the <strong>Tickets</strong> button to search for related tickets</li>
<li><strong>Verify the specifications are correct</strong> - check serial number, RAM, storage, and model</li>
<li>If a related ticket is found, click <strong>Add to Ticket</strong> to create the asset and link it</li>
<li>If no ticket is found, click <strong>Add</strong> to add the asset to inventory</li>
</ol>

<hr>

<h2>Alternative: Running from Normal macOS</h2>

<p>If the MacBook boots normally, you can also run the command directly:</p>

<h3>Step 1: Copy the Command</h3>
<p>On the Device Specs page, you'll see a command box with:</p>
<pre><code>curl -sL https://inventory.truelog.com.sg/specs | bash</code></pre>
<p>Click the <strong>Copy</strong> button to copy this command to your clipboard.</p>

<h3>Step 2: Run on the MacBook</h3>
<p>Open <strong>Terminal</strong> (Applications &gt; Utilities &gt; Terminal) and paste the command. Press Enter to run it.</p>

<h3>Step 3: View the Results</h3>
<p>Once the script runs, the device specs will automatically appear on the Device Specs page. The page shows:</p>
<ul>
<li><strong>Total Submissions</strong> - All specs collected</li>
<li><strong>Pending Review</strong> - New submissions not yet processed</li>
<li><strong>Processed</strong> - Submissions that have been added to inventory</li>
<li><strong>Last Submission</strong> - Time of the most recent submission</li>
</ul>

<hr>

<h2>Understanding the Specs Cards</h2>
<p>Each submitted device appears as a card showing:</p>
<table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; width: 100%;">
<thead style="background-color: #f3f4f6;">
<tr>
<th>Field</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr><td><strong>Serial Number</strong></td><td>Device serial number</td></tr>
<tr><td><strong>Model</strong></td><td>MacBook model name (e.g., "MacBook Pro 14-inch M3")</td></tr>
<tr><td><strong>CPU</strong></td><td>Processor type and core count</td></tr>
<tr><td><strong>RAM</strong></td><td>Memory in GB</td></tr>
<tr><td><strong>Storage</strong></td><td>Storage capacity and type</td></tr>
<tr><td><strong>Submitted</strong></td><td>Date and time of submission</td></tr>
</tbody>
</table>

<h3>Status Indicators</h3>
<ul>
<li><span style="color: #eab308;"><strong>Yellow border + "New"</strong></span> - Pending review, not yet added to inventory</li>
<li><span style="color: #22c55e;"><strong>Green border + "Done"</strong></span> - Already processed/added to inventory</li>
</ul>

<hr>

<h2>Available Actions</h2>

<h3>View Full Details</h3>
<p>Click <strong>View</strong> to see complete device specifications including:</p>
<ul>
<li>Hardware UUID</li>
<li>Model number/ID</li>
<li>CPU and GPU details</li>
<li>macOS version and build</li>
<li>WiFi MAC address</li>
<li>IP address used during submission</li>
</ul>

<h3>Add to Inventory</h3>
<p>Click <strong>Add</strong> to create a new asset in inventory using the collected specs. The form will be pre-filled with the device information.</p>

<div style="background-color: #fef3c7; border-left: 4px solid #f59e0b; padding: 12px; margin: 16px 0;">
<strong>Important:</strong> Always verify the collected specifications are correct before adding to the system. Double-check the serial number, RAM, storage, and model information match the physical device.
</div>

<h3>Find Related Tickets</h3>
<p>Click <strong>Tickets</strong> to search for any existing tickets that mention this device's serial number or model. This is useful when you need to link a device to an existing support case.</p>

<h4>How to Add Device to a Ticket:</h4>
<ol>
<li>Click the <strong>Tickets</strong> button on the device spec card</li>
<li>The system will search for tickets matching the device's serial number or model</li>
<li>If matching tickets are found, you'll see a list of related tickets</li>
<li>Click <strong>View</strong> to open the ticket in a new tab</li>
<li>Click <strong>Add to Ticket</strong> to create an asset and automatically link it to that ticket</li>
<li>If no tickets are found, you can click <strong>Add Asset Without Ticket</strong> to add it to inventory without linking</li>
</ol>

<p>This feature is especially useful for:</p>
<ul>
<li>Repair tickets - Link the device being repaired to the ticket</li>
<li>Asset intake tickets - Associate incoming devices with their intake records</li>
<li>Return tickets - Connect returned devices to their return case</li>
</ul>

<h3>Delete Submission</h3>
<p>Click the <strong>trash icon</strong> to remove a spec submission. Use this for duplicate or erroneous submissions.</p>

<hr>

<h2>Tips</h2>
<ol>
<li><strong>Recovery Mode Collection:</strong> If a device is locked or having issues, boot into Recovery Mode (hold Command+R during startup), open Terminal from Utilities menu, and run the command. You'll still get the hardware specs.</li>
<li><strong>Bulk Collection:</strong> You can run the command on multiple MacBooks. Each submission appears separately on the page.</li>
<li><strong>Automatic Model Detection:</strong> The system automatically identifies the MacBook model based on the model identifier.</li>
<li><strong>Link to Tickets:</strong> Use the "Find Tickets" feature to quickly associate device specs with existing support tickets.</li>
</ol>

<hr>

<h2>FAQ</h2>

<h3>Does the script install anything on the MacBook?</h3>
<p>No, the script only reads hardware information and sends it to the server. Nothing is installed or modified on the device.</p>

<h3>Can I use this on Windows or Linux?</h3>
<p>No, this tool is specifically designed for macOS/MacBooks only.</p>

<h3>What if the same device is submitted multiple times?</h3>
<p>Each submission is recorded separately. You can delete duplicates using the trash icon.</p>

<h3>Do I need to be logged in to submit specs?</h3>
<p>No, the curl command works without authentication. However, you need to be logged in to view and manage the collected specs.</p>
"""

def main():
    db = SessionLocal()
    try:
        # Find or create IT Support category
        category = db.query(KnowledgeCategory).filter(
            KnowledgeCategory.name.ilike('%IT%')
        ).first()

        if not category:
            category = db.query(KnowledgeCategory).filter(
                KnowledgeCategory.name.ilike('%Hardware%')
            ).first()

        if not category:
            category = db.query(KnowledgeCategory).first()

        if not category:
            # Create a category
            category = KnowledgeCategory(
                name="IT Support",
                description="IT support guides and documentation",
                sort_order=1
            )
            db.add(category)
            db.flush()
            print(f"Created category: IT Support")

        # Get first admin/developer user as author
        author = db.query(User).filter(
            User.user_type.in_(['DEVELOPER', 'SUPER_ADMIN', 'ADMIN'])
        ).first()

        if not author:
            author = db.query(User).first()

        if not author:
            print("Error: No users found in database")
            return

        # Check if article already exists
        existing = db.query(KnowledgeArticle).filter(
            KnowledgeArticle.title == "How to Use the MacBook Specs Collector"
        ).first()

        now = datetime.now(timezone.utc)

        if existing:
            # Update existing article
            existing.content = article_content
            existing.summary = "Learn how to remotely collect MacBook hardware specifications using the Device Specs Collector tool. Works even in Recovery Mode."
            existing.updated_at = now
            db.commit()

            print(f"Successfully updated article!")
            print(f"  ID: {existing.id}")
            print(f"  Title: {existing.title}")
            print(f"  Updated at: {now}")
            print(f"")
            print(f"View at: /knowledge/article/{existing.id}")
            return

        # Create the article
        article = KnowledgeArticle(
            title="How to Use the MacBook Specs Collector",
            content=article_content,
            summary="Learn how to remotely collect MacBook hardware specifications using the Device Specs Collector tool. Works even in Recovery Mode.",
            category_id=category.id if category else None,
            author_id=author.id,
            visibility=ArticleVisibility.INTERNAL,
            status=ArticleStatus.PUBLISHED,
            created_at=now,
            updated_at=now,
            view_count=0
        )

        db.add(article)
        db.commit()

        print(f"Successfully created article!")
        print(f"  ID: {article.id}")
        print(f"  Title: {article.title}")
        print(f"  Category: {category.name if category else 'None'}")
        print(f"  Author: {author.username}")
        print(f"  Status: Published")
        print(f"")
        print(f"View at: /knowledge/article/{article.id}")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
