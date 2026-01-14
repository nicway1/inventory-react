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

<h2>Collecting Device Specs</h2>

<h3>Step 1: Copy the Command</h3>
<p>On the Device Specs page, you'll see a command box with:</p>
<pre><code>curl -sL https://inventory.truelog.com.sg/specs | bash</code></pre>
<p>Click the <strong>Copy</strong> button to copy this command to your clipboard.</p>

<h3>Step 2: Run on the MacBook</h3>
<p>Open <strong>Terminal</strong> on the MacBook you want to collect specs from and paste the command. Press Enter to run it.</p>
<div style="background-color: #fef3c7; border-left: 4px solid #f59e0b; padding: 12px; margin: 16px 0;">
<strong>Note:</strong> This command also works in <strong>macOS Recovery Mode</strong> - just open Terminal from the Utilities menu.
</div>

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

<h3>Find Related Tickets</h3>
<p>Click <strong>Tickets</strong> to search for any existing tickets that mention this device's serial number or model. You can then:</p>
<ul>
<li><strong>View</strong> the ticket</li>
<li><strong>Add to Ticket</strong> - Create an asset and link it to the ticket</li>
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

        if existing:
            print(f"Article already exists with ID: {existing.id}")
            print(f"View at: /knowledge/article/{existing.id}")
            return

        # Create the article
        now = datetime.now(timezone.utc)
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
