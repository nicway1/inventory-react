#!/usr/bin/env python3
"""Script to add MacBook spec extraction article to knowledge base
Run on PythonAnywhere: python scripts/add_macbook_article.py
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
<p>This guide shows you how to extract hardware specifications from a MacBook using Terminal commands. These commands are useful for asset documentation and inventory purposes.</p>

<h2>Quick Reference Table</h2>
<table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; width: 100%;">
<thead style="background-color: #f3f4f6;">
<tr>
<th>Specification</th>
<th>Command</th>
</tr>
</thead>
<tbody>
<tr><td><strong>Model</strong></td><td><code>ioreg -c IOPlatformExpertDevice | grep "model"</code></td></tr>
<tr><td><strong>Processor</strong></td><td><code>sysctl -n machdep.cpu.brand_string</code></td></tr>
<tr><td><strong>Memory</strong></td><td><code>sysctl hw.memsize | awk '{print $2/1073741824 " GB"}'</code></td></tr>
<tr><td><strong>Serial Number</strong></td><td><code>ioreg -l | grep IOPlatformSerialNumber</code></td></tr>
<tr><td><strong>macOS Version</strong></td><td><code>sw_vers</code></td></tr>
<tr><td><strong>Storage</strong></td><td><code>diskutil list</code></td></tr>
</tbody>
</table>

<h2>Detailed Commands</h2>

<h3>1. Model Identifier</h3>
<p>Get the Mac model identifier (e.g., MacBookPro18,1):</p>
<pre><code>ioreg -c IOPlatformExpertDevice | grep "model"</code></pre>

<h3>2. Processor Information</h3>
<p>Get the CPU model and speed:</p>
<pre><code>sysctl -n machdep.cpu.brand_string</code></pre>
<p><strong>Example output:</strong> <code>Apple M1 Pro</code> or <code>Intel(R) Core(TM) i7-9750H CPU @ 2.60GHz</code></p>

<h3>3. Memory (RAM)</h3>
<p>Get total memory in GB:</p>
<pre><code>sysctl hw.memsize | awk '{print $2/1073741824 " GB"}'</code></pre>
<p><strong>Example output:</strong> <code>16 GB</code></p>

<h3>4. Serial Number</h3>
<p>Get the device serial number:</p>
<pre><code>ioreg -l | grep IOPlatformSerialNumber</code></pre>
<p><strong>Example output:</strong> <code>"IOPlatformSerialNumber" = "C02XG1XXJGH5"</code></p>

<h3>5. macOS Version</h3>
<p>Get the operating system version:</p>
<pre><code>sw_vers</code></pre>
<p><strong>Example output:</strong></p>
<pre><code>ProductName:    macOS
ProductVersion: 14.2.1
BuildVersion:   23C71</code></pre>

<h3>6. Storage Information</h3>
<p>List all drives and partitions:</p>
<pre><code>diskutil list</code></pre>

<h2>All-in-One Script</h2>
<p>Copy and run this script to get all specs at once:</p>
<pre><code>echo "=== MacBook Specifications ==="
echo ""
echo "Model:"
ioreg -c IOPlatformExpertDevice | grep "model" | head -1
echo ""
echo "Processor:"
sysctl -n machdep.cpu.brand_string
echo ""
echo "Memory:"
sysctl hw.memsize | awk '{print $2/1073741824 " GB"}'
echo ""
echo "Serial Number:"
ioreg -l | grep IOPlatformSerialNumber | awk -F'"' '{print $4}'
echo ""
echo "macOS Version:"
sw_vers
echo ""
echo "Storage:"
diskutil list | head -20</code></pre>

<h2>Tips</h2>
<ul>
<li>Open Terminal from <strong>Applications → Utilities → Terminal</strong> or press <code>Cmd + Space</code> and type "Terminal"</li>
<li>Copy the output and paste into the asset notes field in the inventory system</li>
<li>For remote machines, use SSH to run these commands</li>
</ul>
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
            KnowledgeArticle.title == "How to Extract MacBook Specifications via Terminal"
        ).first()

        if existing:
            print(f"Article already exists with ID: {existing.id}")
            return

        # Create the article
        now = datetime.now(timezone.utc)
        article = KnowledgeArticle(
            title="How to Extract MacBook Specifications via Terminal",
            content=article_content,
            summary="Step-by-step guide to extract hardware specs (Model, CPU, RAM, Serial Number, macOS version, Storage) from MacBook using Terminal commands.",
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

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
