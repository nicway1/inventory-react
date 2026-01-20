#!/usr/bin/env python3
"""
Import TrueLog Blog Posts from scraped data

Run: python import_truelog_blog.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from database import SessionLocal
from models.blog_post import BlogPost, BlogPostStatus
import re

def slugify(text):
    """Convert text to URL-friendly slug"""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text

# All scraped blog posts from truelog.com.sg/blog/
BLOG_POSTS = [
    # October 2025
    {
        "title": "Understanding XO Permits and How to Speed Up the Process",
        "date": "2025-10-28",
        "excerpt": "Singapore's position as a global logistics and technology hub means that exports move in and out of the country every second. This guide explains what XO permits are, the four permit types, and strategies to accelerate the approval process.",
        "content": """<h2>What Are XO Permits?</h2>
<p>Singapore's position as a global logistics and technology hub means that exports move in and out of the country every second. But for products that fall under strategic goods controls, exporters must obtain XO permits before shipment.</p>

<p>XO permits authorize exports of controlled items including electronics and semiconductors, aerospace components, and other strategic goods.</p>

<h2>Four XO Permit Types</h2>
<ol>
<li><strong>Individual XO Permit</strong> — For single shipments (5-7 working days processing)</li>
<li><strong>Blanket Permit</strong> — For frequent exporters with pre-approved end-users</li>
<li><strong>Transshipment (XP) Permit</strong> — For goods passing through Singapore</li>
<li><strong>Multi-Use (BKT) Declarations</strong> — For recurring shipments to consistent clients</li>
</ol>

<h2>How to Speed Up the Process</h2>
<p>Approval speed depends on documentation quality, company compliance history, and goods classification. Key acceleration strategies include:</p>
<ul>
<li>Strengthening internal compliance programs</li>
<li>Improving TradeFIRST ratings</li>
<li>Partnering with experienced logistics providers like TrueLog</li>
</ul>

<p>TrueLog assists in classifying products and managing permits for compliance-focused exporters navigating Singapore Customs requirements.</p>""",
        "featured_image": "https://truelog.com.sg/wp-content/uploads/2025/10/image.jpeg",
        "source_url": "https://truelog.com.sg/understanding-xo-permits-and-how-to-speed-up-the-process/"
    },
    {
        "title": "A Complete Guide to Singapore's Export Control System and XO Permits",
        "date": "2025-10-13",
        "excerpt": "Singapore is one of the world's most trusted trading and logistics hubs. This comprehensive guide explains the Strategic Goods (Control) Act and XO permit requirements for exporters.",
        "content": """<h2>What Are Export Controls?</h2>
<p>Export controls regulate the movement of products, software, and technology that could be utilized for military applications. They protect international peace and security rather than restricting legitimate trade.</p>

<h2>Strategic Goods (Control) Act</h2>
<p>The SGCA mandates that exporters obtain permits before moving controlled goods outside Singapore. It aligns with international frameworks including:</p>
<ul>
<li>Nuclear Suppliers Group</li>
<li>Wassenaar Arrangement</li>
<li>Australia Group</li>
<li>Missile Technology Control Regime</li>
</ul>

<h2>Three Main Permit Types</h2>
<ul>
<li><strong>XO Permit</strong> — Export of strategic goods</li>
<li><strong>TL Permit</strong> — Transshipment through Singapore</li>
<li><strong>ST Permit</strong> — Storage/handling in transit</li>
</ul>

<h2>Controlled Item Categories</h2>
<p>The Strategic Goods (Control) List includes:</p>
<ul>
<li>Electronics and semiconductors</li>
<li>Computers and sensors</li>
<li>Lasers and aerospace technology</li>
<li>Encryption products</li>
</ul>

<p>TrueLog assists exporters by identifying controlled items, managing permit applications, and providing EOR/IOR services to facilitate global trade operations.</p>""",
        "source_url": "https://truelog.com.sg/a-complete-guide-to-singapores-export-control-system-and-xo-permits/"
    },

    # August 2025
    {
        "title": "TrueLog Expands IT Asset Management (ITAM) Services to China and South Korea",
        "date": "2025-08-26",
        "excerpt": "Both nations host advanced digital economies but face intricate logistics demands requiring specialized solutions. TrueLog's expansion brings comprehensive ITAM services to these key markets.",
        "content": """<h2>Expansion to Key Asian Markets</h2>
<p>TrueLog is pleased to announce the expansion of our IT Asset Management (ITAM) services to China and South Korea. Both nations host advanced digital economies but face intricate logistics demands requiring specialized solutions.</p>

<h2>Why China and South Korea?</h2>
<p>These markets represent critical nodes in the global ICT supply chain:</p>
<ul>
<li>Advanced manufacturing capabilities</li>
<li>Growing enterprise technology adoption</li>
<li>Complex regulatory environments requiring expert navigation</li>
</ul>

<h2>Services Offered</h2>
<ul>
<li>End-to-end IT asset lifecycle management</li>
<li>Secure data destruction and certification</li>
<li>Compliance with local regulations</li>
<li>Reverse logistics and disposition</li>
</ul>""",
        "source_url": "https://truelog.com.sg/truelog-expands-it-asset-management-itam-services-to-china-and-south-korea/"
    },
    {
        "title": "IOR/EOR Compliance in Emerging Markets: What 2025 Tells Us About Risk and Readiness",
        "date": "2025-08-26",
        "excerpt": "Growing regulatory complexity and geopolitical uncertainty characterize emerging market trade landscapes. Understanding IOR/EOR compliance is crucial for successful market entry.",
        "content": """<h2>The 2025 Compliance Landscape</h2>
<p>Growing regulatory complexity and geopolitical uncertainty characterize emerging market trade landscapes. Companies expanding into new territories must navigate an increasingly complex web of import and export regulations.</p>

<h2>Key Challenges</h2>
<ul>
<li>Varying customs requirements across jurisdictions</li>
<li>Changing tariff structures and trade agreements</li>
<li>Local entity requirements for import licenses</li>
<li>Documentation and certification needs</li>
</ul>

<h2>Risk Mitigation Strategies</h2>
<p>Successful market entry requires:</p>
<ul>
<li>Partnering with experienced IOR/EOR service providers</li>
<li>Conducting thorough regulatory due diligence</li>
<li>Building flexible supply chain structures</li>
<li>Maintaining compliance documentation</li>
</ul>""",
        "source_url": "https://truelog.com.sg/ior-eor-compliance-in-emerging-markets-what-2025-tells-us-about-risk-and-readiness/"
    },
    {
        "title": "Navigating India's New Logistics Policy: VAT, Customs & Licensing Implications for ICT Imports",
        "date": "2025-08-26",
        "excerpt": "India introduced forward-looking logistics policies addressing congestion, warehousing capacity, and environmental sustainability. Here's what ICT importers need to know.",
        "content": """<h2>India's Evolving Logistics Framework</h2>
<p>India introduced forward-looking logistics policies addressing congestion, warehousing capacity, and environmental sustainability. For ICT importers, understanding these changes is essential for smooth operations.</p>

<h2>Key Policy Changes</h2>
<ul>
<li>Updated GST/VAT structures for technology imports</li>
<li>New customs clearance procedures</li>
<li>Revised licensing requirements for IT equipment</li>
<li>Environmental compliance for e-waste</li>
</ul>

<h2>Implications for ICT Companies</h2>
<p>Companies importing technology into India should:</p>
<ul>
<li>Review current import procedures against new requirements</li>
<li>Update documentation practices</li>
<li>Consider partnering with local IOR providers</li>
<li>Plan for longer initial clearance timelines</li>
</ul>""",
        "source_url": "https://truelog.com.sg/navigating-indias-new-logistics-policy-vat-customs-licensing-implications-for-ict-imports/"
    },
    {
        "title": "TrueLog Launches IOR & EOR Services into La Reunion",
        "date": "2025-08-01",
        "excerpt": "Island location in the Indian Ocean evolves into regional digital and logistics growth center. TrueLog now offers comprehensive import/export services.",
        "content": """<h2>Expanding to La Reunion</h2>
<p>TrueLog is excited to announce our service expansion to La Reunion. This French overseas territory in the Indian Ocean is evolving into a regional digital and logistics growth center.</p>

<h2>Why La Reunion?</h2>
<ul>
<li>Strategic location for Indian Ocean trade routes</li>
<li>Growing technology sector</li>
<li>EU regulatory framework with tropical accessibility</li>
<li>Emerging data center market</li>
</ul>

<h2>Services Available</h2>
<ul>
<li>Importer of Record (IOR) services</li>
<li>Exporter of Record (EOR) services</li>
<li>Customs clearance and documentation</li>
<li>IT asset logistics management</li>
</ul>""",
        "source_url": "https://truelog.com.sg/truelog-launches-ior-eor-services-into-la-reunion/"
    },
    {
        "title": "Navigating U.S. Tariff Volatility: What ICT Logistics Leaders Need to Know",
        "date": "2025-08-01",
        "excerpt": "In late July 2025, the U.S. government announced sweeping measures aimed at curbing tariff evasion via transshipment. Here's what ICT logistics leaders need to understand.",
        "content": """<h2>Recent U.S. Tariff Changes</h2>
<p>In late July 2025, the U.S. government announced sweeping measures aimed at curbing tariff evasion via transshipment. These changes have significant implications for ICT logistics operations.</p>

<h2>Key Changes</h2>
<ul>
<li>Enhanced scrutiny of country-of-origin documentation</li>
<li>New requirements for transshipment declarations</li>
<li>Increased penalties for non-compliance</li>
<li>Additional documentation requirements for electronics</li>
</ul>

<h2>Strategies for Compliance</h2>
<p>ICT logistics leaders should:</p>
<ul>
<li>Review supply chain routing for tariff implications</li>
<li>Ensure robust country-of-origin documentation</li>
<li>Consider duty drawback opportunities</li>
<li>Work with experienced customs brokers</li>
</ul>""",
        "source_url": "https://truelog.com.sg/navigating-u-s-tariff-volatility-what-ict-logistics-leaders-need-to-know/"
    },
    {
        "title": "How Geo-Economic Shifts Are Reshaping ICT Supply Chains in 2025",
        "date": "2025-08-01",
        "excerpt": "Global ICT supply chains are facing an inflexion point. According to a July 2025 PwC report, telecom and tech firms are accelerating de-risking efforts.",
        "content": """<h2>The Changing Landscape</h2>
<p>Global ICT supply chains are facing an inflexion point. According to a July 2025 PwC report, telecom and tech firms are accelerating de-risking efforts in response to geopolitical tensions.</p>

<h2>Key Trends</h2>
<ul>
<li>Diversification away from single-source suppliers</li>
<li>Nearshoring and friend-shoring strategies</li>
<li>Increased inventory buffers for critical components</li>
<li>Investment in supply chain visibility tools</li>
</ul>

<h2>Implications for Logistics</h2>
<p>These shifts require:</p>
<ul>
<li>Flexible logistics partnerships across regions</li>
<li>Multi-modal transportation capabilities</li>
<li>Robust compliance infrastructure</li>
<li>Real-time tracking and monitoring</li>
</ul>""",
        "source_url": "https://truelog.com.sg/how-geo-economic-shifts-are-reshaping-ict-supply-chains-in-2025/"
    },

    # July 2025
    {
        "title": "Kazakhstan's Middle Corridor: What It Means for ICT Logistics in Eurasia",
        "date": "2025-07-15",
        "excerpt": "The Middle Corridor trade route presents new opportunities for ICT logistics across Eurasia. Understanding this emerging route is crucial for logistics planning.",
        "content": """<h2>The Middle Corridor Opportunity</h2>
<p>Kazakhstan's Middle Corridor has emerged as a significant alternative trade route connecting Asia and Europe. For ICT logistics, this presents both opportunities and considerations.</p>

<h2>Route Advantages</h2>
<ul>
<li>Diversification from traditional routes</li>
<li>Reduced transit times for certain markets</li>
<li>Growing infrastructure investment</li>
<li>Favorable customs arrangements</li>
</ul>

<h2>Considerations for ICT Shipments</h2>
<ul>
<li>Cold chain requirements for sensitive electronics</li>
<li>Security considerations for high-value cargo</li>
<li>Documentation requirements across multiple countries</li>
<li>Insurance and liability coverage</li>
</ul>""",
        "source_url": "https://truelog.com.sg/kazakhstans-middle-corridor-what-it-means-for-ict-logistics-in-eurasia/"
    },
    {
        "title": "TrueLog Expands to Jordan",
        "date": "2025-07-15",
        "excerpt": "Service expansion announcement strengthening Middle East ICT logistics network. TrueLog now provides comprehensive IOR/EOR services in Jordan.",
        "content": """<h2>New Country Unlocked: Jordan</h2>
<p>TrueLog is pleased to announce the expansion of our services to Jordan, further strengthening our Middle East ICT logistics network.</p>

<h2>Why Jordan?</h2>
<ul>
<li>Strategic gateway to the Middle East</li>
<li>Growing technology sector</li>
<li>Favorable trade agreements</li>
<li>Skilled workforce for technical operations</li>
</ul>

<h2>Services Offered</h2>
<ul>
<li>Importer of Record (IOR)</li>
<li>Exporter of Record (EOR)</li>
<li>Customs clearance</li>
<li>IT asset management</li>
<li>Reverse logistics</li>
</ul>""",
        "source_url": "https://truelog.com.sg/new-country-unlocked/"
    },
    {
        "title": "ATA Carnet for Broadcasting & Professional Equipment: Why Pre-Planning Is Crucial",
        "date": "2025-07-15",
        "excerpt": "Guidance on international equipment movement compliance. ATA Carnets enable temporary duty-free import of professional equipment, but careful planning is essential.",
        "content": """<h2>Understanding ATA Carnets</h2>
<p>ATA Carnets enable temporary duty-free import of professional equipment across 87+ countries. For broadcasting and professional equipment, proper planning is essential.</p>

<h2>When to Use ATA Carnets</h2>
<ul>
<li>Trade shows and exhibitions</li>
<li>Professional filming and broadcasting</li>
<li>Equipment demonstrations</li>
<li>Temporary project deployments</li>
</ul>

<h2>Pre-Planning Requirements</h2>
<ul>
<li>Detailed equipment inventory with serial numbers</li>
<li>Accurate valuation documentation</li>
<li>Understanding of destination country requirements</li>
<li>Sufficient lead time for processing (minimum 2-3 weeks)</li>
</ul>

<h2>Common Pitfalls to Avoid</h2>
<ul>
<li>Incomplete equipment lists</li>
<li>Incorrect item classifications</li>
<li>Missing re-export deadlines</li>
<li>Failure to get proper endorsements</li>
</ul>""",
        "source_url": "https://truelog.com.sg/ata-carnet-for-broadcasting-professional-equipment-why-pre-planning-is-crucial/"
    },

    # June 2025
    {
        "title": "Expansion Update: Solomon Islands",
        "date": "2025-06-04",
        "excerpt": "TrueLog expands logistics services to the Solomon Islands, addressing unique infrastructure challenges in this Pacific nation.",
        "content": """<h2>Reaching the Solomon Islands</h2>
<p>TrueLog is proud to announce the expansion of our services to the Solomon Islands, addressing the unique infrastructure challenges of this Pacific nation.</p>

<h2>Challenges Addressed</h2>
<ul>
<li>Remote island logistics coordination</li>
<li>Limited port infrastructure</li>
<li>Complex customs procedures</li>
<li>Last-mile delivery challenges</li>
</ul>

<h2>Services Available</h2>
<ul>
<li>IOR/EOR services</li>
<li>Customs clearance</li>
<li>Air and sea freight coordination</li>
<li>IT equipment deployment support</li>
</ul>""",
        "source_url": "https://truelog.com.sg/%f0%9f%93%a2-expansion-update-solomon-islands-%f0%9f%87%b8%f0%9f%87%a7/"
    },
    {
        "title": "DP World's $2.5B Bet on UAE Logistics - What It Means for ICT Deployments",
        "date": "2025-06-04",
        "excerpt": "DP World's significant investment in UAE logistics infrastructure has major implications for ICT sector expansion in the region.",
        "content": """<h2>Major Infrastructure Investment</h2>
<p>DP World's $2.5 billion investment in UAE logistics infrastructure signals a significant commitment to positioning the region as a global logistics hub.</p>

<h2>Impact on ICT Logistics</h2>
<ul>
<li>Enhanced port and free zone capabilities</li>
<li>Improved connectivity for technology deployments</li>
<li>Faster customs clearance processes</li>
<li>Better warehousing for sensitive equipment</li>
</ul>

<h2>Opportunities for ICT Companies</h2>
<ul>
<li>Use UAE as a regional distribution hub</li>
<li>Leverage improved infrastructure for faster deployments</li>
<li>Access growing Middle East technology markets</li>
<li>Benefit from favorable trade agreements</li>
</ul>""",
        "source_url": "https://truelog.com.sg/dp-worlds-2-5b-bet-on-uae-logistics-what-it-means-for-ict-deployments/"
    },
    {
        "title": "India's Logistics Infrastructure: Hosur's Emerging ICT Corridor",
        "date": "2025-06-04",
        "excerpt": "Panattoni's EUR100 million industrial and logistics park development in Tamil Nadu signals the emergence of a new ICT logistics corridor.",
        "content": """<h2>Hosur's Transformation</h2>
<p>Panattoni's EUR100 million investment in an industrial and logistics park in Tamil Nadu is transforming Hosur into an emerging ICT corridor connecting Bangalore and Chennai.</p>

<h2>Strategic Advantages</h2>
<ul>
<li>Proximity to major tech hubs</li>
<li>Excellent road and rail connectivity</li>
<li>Competitive land and labor costs</li>
<li>Supportive state government policies</li>
</ul>

<h2>Implications for ICT Companies</h2>
<ul>
<li>New warehousing and distribution options</li>
<li>Alternative to congested metropolitan areas</li>
<li>Growing skilled workforce availability</li>
<li>Potential for manufacturing and assembly operations</li>
</ul>""",
        "source_url": "https://truelog.com.sg/indias-logistics-infrastructure-hosurs-emerging-ict-corridor/"
    },
    {
        "title": "UK-EU Trade Reset - A New Era for ICT Logistics",
        "date": "2025-06-04",
        "excerpt": "The May 19, 2025 UK-EU trade agreement creates new opportunities and considerations for cross-border ICT logistics.",
        "content": """<h2>The Trade Reset</h2>
<p>The May 19, 2025 UK-EU trade agreement marks a significant shift in cross-border trade relations, with important implications for ICT logistics.</p>

<h2>Key Changes</h2>
<ul>
<li>Simplified customs procedures for certain goods</li>
<li>Mutual recognition of certifications</li>
<li>Improved data flow arrangements</li>
<li>Streamlined documentation requirements</li>
</ul>

<h2>What ICT Companies Should Do</h2>
<ul>
<li>Review current UK-EU logistics arrangements</li>
<li>Update customs procedures and documentation</li>
<li>Assess tariff classification implications</li>
<li>Consider strategic inventory positioning</li>
</ul>""",
        "source_url": "https://truelog.com.sg/uk-eu-trade-reset-a-new-era-for-ict-logistics/"
    },
    {
        "title": "WiseTech's e2open Acquisition - A Signal for Digital Supply Chain Maturity",
        "date": "2025-06-04",
        "excerpt": "WiseTech Global's $3.25 billion acquisition of e2open signals the maturation of digital supply chain platforms.",
        "content": """<h2>Industry Consolidation</h2>
<p>WiseTech Global's $3.25 billion acquisition of e2open represents significant consolidation in the digital supply chain platform space.</p>

<h2>What This Means</h2>
<ul>
<li>Increased integration of logistics technology</li>
<li>More comprehensive end-to-end visibility</li>
<li>Potential for improved automation</li>
<li>Greater data standardization across platforms</li>
</ul>

<h2>Implications for Logistics Providers</h2>
<ul>
<li>Need for technology investment to remain competitive</li>
<li>Opportunities for deeper system integration</li>
<li>Importance of data interoperability</li>
<li>Focus on customer experience improvements</li>
</ul>""",
        "source_url": "https://truelog.com.sg/wisetechs-e2open-acquisition-a-signal-for-digital-supply-chain-maturity/"
    },
    {
        "title": "New Coverage Alert: American Samoa",
        "date": "2025-06-03",
        "excerpt": "TrueLog announces service expansion to American Samoa, bringing IOR/EOR capabilities to this U.S. territory in the Pacific.",
        "content": """<h2>Expanding to American Samoa</h2>
<p>TrueLog is pleased to announce the expansion of our services to American Samoa, a U.S. territory in the South Pacific.</p>

<h2>Service Capabilities</h2>
<ul>
<li>Importer of Record services</li>
<li>Exporter of Record services</li>
<li>U.S. customs compliance</li>
<li>IT equipment deployment</li>
</ul>

<h2>Why This Matters</h2>
<p>American Samoa provides a strategic location for Pacific operations while maintaining U.S. regulatory compliance.</p>""",
        "source_url": "https://truelog.com.sg/new-coverage-alert-american-samoa-%f0%9f%87%a6%f0%9f%87%b8/"
    },
    {
        "title": "Why TrueLog's Airport FTZ Presence Is a Game Changer for ICT Logistics in Singapore",
        "date": "2025-06-03",
        "excerpt": "Singapore's logistics sector continues to grow, and TrueLog's strategic positioning in the Airport Free Trade Zone offers unique advantages.",
        "content": """<h2>Strategic FTZ Positioning</h2>
<p>TrueLog's presence in Singapore's Airport Free Trade Zone (FTZ) provides significant advantages for ICT logistics operations.</p>

<h2>Key Benefits</h2>
<ul>
<li>Duty suspension for goods in transit</li>
<li>Simplified customs procedures</li>
<li>Faster turnaround times</li>
<li>Secure storage for high-value equipment</li>
<li>24/7 operations capability</li>
</ul>

<h2>Services Enhanced by FTZ Location</h2>
<ul>
<li>Rapid deployment support</li>
<li>Consolidation and deconsolidation</li>
<li>Value-added services (configuration, testing)</li>
<li>Emergency spare parts logistics</li>
</ul>""",
        "source_url": "https://truelog.com.sg/why-truelogs-airport-ftz-presence-is-a-game-changer-for-ict-logistics-in-singapore/"
    },

    # May 2025
    {
        "title": "Huawei's Malaysia GPU Centre: A Strategic Shift and What It Means for ICT Supply Chains",
        "date": "2025-05-23",
        "excerpt": "Huawei's announcement to open a GPU centre in Malaysia marks a strategic investment in Southeast Asia's growing role in global tech infrastructure.",
        "content": """<h2>Strategic Investment in Malaysia</h2>
<p>Huawei's recent announcement to open a GPU centre in Malaysia marks a strategic investment in Southeast Asia's growing role in the global tech infrastructure.</p>

<h2>Regional Implications</h2>
<ul>
<li>Increased demand for high-tech logistics in Malaysia</li>
<li>Growth of supporting ecosystem services</li>
<li>Potential for regional supply chain shifts</li>
<li>New requirements for specialized equipment handling</li>
</ul>

<h2>What This Means for Logistics</h2>
<ul>
<li>Need for secure, climate-controlled transport</li>
<li>Specialized customs handling for sensitive technology</li>
<li>Increased regional connectivity requirements</li>
<li>Opportunities for value-added services</li>
</ul>""",
        "source_url": "https://truelog.com.sg/huaweis-malaysia-gpu-centre-a-strategic-shift-and-what-it-means-for-ict-supply-chains/"
    },
    {
        "title": "Exporter of Record (EOR) for IT & Telecom: Why It's Critical for Global Sales",
        "date": "2025-05-15",
        "excerpt": "EOR services enable IT companies to expand internationally without establishing local entities. Understanding when and why to use EOR is crucial for global growth.",
        "content": """<h2>What Is Exporter of Record?</h2>
<p>An Exporter of Record (EOR) is a third party that takes responsibility for export compliance, documentation, and customs requirements on behalf of a company.</p>

<h2>When to Use EOR Services</h2>
<ul>
<li>Entering new markets without local presence</li>
<li>Managing complex export control requirements</li>
<li>Handling strategic goods classifications</li>
<li>Simplifying multi-country distribution</li>
</ul>

<h2>Benefits for IT & Telecom Companies</h2>
<ul>
<li>Faster market entry</li>
<li>Reduced compliance risk</li>
<li>Lower operational costs</li>
<li>Expert navigation of regulations</li>
</ul>""",
        "source_url": "https://truelog.com.sg/exporter-of-record-eor-for-it-telecom-why-its-critical-for-global-sales/"
    },

    # April 2025
    {
        "title": "Understanding Compliance & Regulatory Requirements for IT Equipment Imports",
        "date": "2025-04-17",
        "excerpt": "Major global regulations including FCC, CE, and BIS require careful navigation. This guide explores compliance strategies across regions.",
        "content": """<h2>Global Compliance Landscape</h2>
<p>Importing IT equipment requires compliance with various regional regulations including FCC (US), CE (EU), and BIS (India).</p>

<h2>Key Regulatory Frameworks</h2>
<ul>
<li><strong>FCC (US)</strong> - Federal Communications Commission certifications</li>
<li><strong>CE (EU)</strong> - European conformity marking</li>
<li><strong>BIS (India)</strong> - Bureau of Indian Standards compliance</li>
<li><strong>CCC (China)</strong> - China Compulsory Certification</li>
</ul>

<h2>Compliance Strategies</h2>
<ul>
<li>Pre-shipment certification verification</li>
<li>Documentation preparation</li>
<li>Working with certified testing labs</li>
<li>Partnering with experienced IOR providers</li>
</ul>""",
        "source_url": "https://truelog.com.sg/understanding-compliance-regulatory-requirements-for-it-equipment-imports/"
    },
    {
        "title": "The Future of IT & Telecom Supply Chains: Trends & Challenges in 2025",
        "date": "2025-04-17",
        "excerpt": "AI-driven logistics, digital customs clearance, and supply chain security developments are reshaping IT and telecom supply chains.",
        "content": """<h2>2025 Supply Chain Trends</h2>
<p>The IT and telecom supply chain landscape is being transformed by several key trends in 2025.</p>

<h2>Key Trends</h2>
<ul>
<li><strong>AI-Driven Logistics</strong> - Predictive analytics and automated decision-making</li>
<li><strong>Digital Customs</strong> - Electronic documentation and automated clearance</li>
<li><strong>Supply Chain Security</strong> - Enhanced tracking and verification</li>
<li><strong>Sustainability</strong> - Green logistics and circular economy initiatives</li>
</ul>

<h2>Challenges to Address</h2>
<ul>
<li>Geopolitical uncertainties</li>
<li>Talent shortages</li>
<li>Technology integration complexity</li>
<li>Rising compliance requirements</li>
</ul>""",
        "source_url": "https://truelog.com.sg/the-future-of-it-telecom-supply-chains-trends-challenges-in-2025/"
    },
    {
        "title": "IOR vs. Traditional Importing: What IT & Telecom Companies Need to Know",
        "date": "2025-04-15",
        "excerpt": "Understanding the differences between using an Importer of Record service versus traditional importing methods is crucial for IT companies expanding globally.",
        "content": """<h2>Traditional Importing vs. IOR</h2>
<p>When expanding internationally, IT and telecom companies face a choice between establishing their own import operations or using an Importer of Record (IOR) service.</p>

<h2>Traditional Importing Requires</h2>
<ul>
<li>Local business entity registration</li>
<li>Import license applications</li>
<li>In-house compliance expertise</li>
<li>Local banking relationships</li>
</ul>

<h2>IOR Service Benefits</h2>
<ul>
<li>No local entity required</li>
<li>Immediate market access</li>
<li>Expert compliance handling</li>
<li>Reduced administrative burden</li>
</ul>

<h2>When to Choose Each Option</h2>
<p>IOR is ideal for initial market entry, project-based deployments, and companies testing new markets. Traditional importing makes sense for established high-volume operations.</p>""",
        "source_url": "https://truelog.com.sg/ior-vs-traditional-importing-what-it-telecom-companies-need-to-know/"
    },
    {
        "title": "How to Overcome Customs Challenges When Shipping IT Equipment Internationally",
        "date": "2025-04-15",
        "excerpt": "Navigating customs challenges is essential for successful IT equipment deployments. Learn strategies to overcome common obstacles.",
        "content": """<h2>Common Customs Challenges</h2>
<p>Shipping IT equipment internationally presents unique customs challenges that require careful planning and expertise.</p>

<h2>Typical Issues</h2>
<ul>
<li>Incorrect HS code classification</li>
<li>Missing or incomplete documentation</li>
<li>Export control restrictions</li>
<li>Certification requirements</li>
<li>Valuation disputes</li>
</ul>

<h2>Strategies for Success</h2>
<ul>
<li>Accurate product classification upfront</li>
<li>Complete documentation packages</li>
<li>Pre-clearance communication with customs</li>
<li>Working with experienced customs brokers</li>
<li>Understanding local regulations</li>
</ul>""",
        "source_url": "https://truelog.com.sg/how-to-overcome-customs-challenges-when-shipping-it-equipment-internationally/"
    },
    {
        "title": "How Current U.S. Tariffs Are Shaping the Future of IT Asset Logistics",
        "date": "2025-04-15",
        "excerpt": "Tariff shifts are significantly impacting IT asset management. Understanding these changes helps companies adapt their logistics strategies.",
        "content": """<h2>Tariff Impact on IT Logistics</h2>
<p>Current U.S. tariff policies are having a significant impact on IT asset logistics, requiring companies to rethink their supply chain strategies.</p>

<h2>Key Impacts</h2>
<ul>
<li>Increased costs for certain technology imports</li>
<li>Supply chain restructuring to minimize tariff exposure</li>
<li>Greater focus on country-of-origin documentation</li>
<li>Rise of nearshoring and alternative sourcing</li>
</ul>

<h2>Adaptation Strategies</h2>
<ul>
<li>Review product classifications for tariff optimization</li>
<li>Explore free trade agreement benefits</li>
<li>Consider bonded warehouse strategies</li>
<li>Evaluate alternative supply sources</li>
</ul>""",
        "source_url": "https://truelog.com.sg/how-current-u-s-tariffs-are-shaping-the-future-of-it-asset-logistics/"
    },
    {
        "title": "The Role of Importer of Record (IOR) in Global IT & Telecom Expansion",
        "date": "2025-04-09",
        "excerpt": "IT and telecom companies require dependable IOR services for navigating international regulations in today's connected marketplace.",
        "content": """<h2>IOR in Global Expansion</h2>
<p>As IT and telecom companies expand globally, the Importer of Record (IOR) function becomes increasingly critical for successful market entry.</p>

<h2>What IOR Provides</h2>
<ul>
<li>Legal import responsibility</li>
<li>Customs clearance management</li>
<li>Compliance assurance</li>
<li>Tax and duty handling</li>
</ul>

<h2>Benefits for IT & Telecom</h2>
<ul>
<li>Rapid market entry without local entity</li>
<li>Reduced compliance risk</li>
<li>Cost-effective expansion</li>
<li>Expert regulatory navigation</li>
</ul>

<h2>Choosing an IOR Partner</h2>
<p>Look for providers with IT/telecom expertise, global coverage, strong compliance track record, and responsive support.</p>""",
        "source_url": "https://truelog.com.sg/role-of-an-importer-of-record-in-it-logistics/"
    },

    # August 2024
    {
        "title": "Global Shipping Solutions at Competitive Rates",
        "date": "2024-08-06",
        "excerpt": "TrueLog's commitment to safety and compliance while managing diverse cargo types through specialized transportation services.",
        "content": """<h2>Comprehensive Shipping Solutions</h2>
<p>TrueLog offers global shipping solutions designed to meet the diverse needs of IT and technology companies while maintaining competitive rates.</p>

<h2>Our Services Include</h2>
<ul>
<li>Air freight for time-sensitive shipments</li>
<li>Sea freight for cost-effective bulk shipping</li>
<li>Multimodal transportation options</li>
<li>Door-to-door delivery coordination</li>
</ul>

<h2>Our Commitment</h2>
<ul>
<li>Safety and security of all cargo</li>
<li>Full regulatory compliance</li>
<li>Transparent pricing</li>
<li>Real-time tracking and updates</li>
</ul>""",
        "source_url": "https://truelog.com.sg/global-shipping-solutions-at-competitive-rates/"
    },
    {
        "title": "Leveraging Technology for Seamless Logistics Documentation",
        "date": "2024-08-06",
        "excerpt": "Cutting-edge technology streamlines documentation processes to ensure operational efficiency in logistics operations.",
        "content": """<h2>Digital Documentation Solutions</h2>
<p>TrueLog leverages cutting-edge technology to streamline logistics documentation, ensuring accuracy and efficiency throughout the supply chain.</p>

<h2>Technology Benefits</h2>
<ul>
<li>Automated document generation</li>
<li>Digital signature capabilities</li>
<li>Cloud-based document storage</li>
<li>Real-time document tracking</li>
</ul>

<h2>Supported Documents</h2>
<ul>
<li>Commercial invoices</li>
<li>Packing lists</li>
<li>Certificates of origin</li>
<li>Customs declarations</li>
<li>Compliance certifications</li>
</ul>""",
        "source_url": "https://truelog.com.sg/leveraging-technology-for-seamless-logistics-documentation/"
    },
    {
        "title": "Navigating Compliance with Lithium Ion Battery Shipments",
        "date": "2024-08-06",
        "excerpt": "Stringent compliance requirements for shipping lithium ion batteries under UN classifications require careful attention to regulations.",
        "content": """<h2>Lithium Battery Shipping Compliance</h2>
<p>Shipping lithium ion batteries requires strict adherence to international regulations and safety standards.</p>

<h2>Key Regulations</h2>
<ul>
<li>UN 3481 - Lithium ion batteries packed with equipment</li>
<li>UN 3480 - Lithium ion batteries alone</li>
<li>IATA Dangerous Goods Regulations</li>
<li>IMDG Code for sea freight</li>
</ul>

<h2>Compliance Requirements</h2>
<ul>
<li>Proper classification and labeling</li>
<li>State of charge limitations</li>
<li>Packaging requirements</li>
<li>Documentation and declarations</li>
</ul>

<h2>TrueLog's Support</h2>
<p>We help ensure your lithium battery shipments meet all regulatory requirements for safe, compliant transport.</p>""",
        "source_url": "https://truelog.com.sg/navigating-compliance-with-lithium-ion-battery-shipments/"
    },
    {
        "title": "Efficient Breakbulk Services: Ensuring Seamless Logistics",
        "date": "2024-08-06",
        "excerpt": "Comprehensive breakbulk logistics solutions including specialized handling and transportation methods for oversized and heavy cargo.",
        "content": """<h2>Breakbulk Logistics Solutions</h2>
<p>TrueLog provides comprehensive breakbulk services for cargo that cannot be containerized, ensuring safe and efficient handling.</p>

<h2>Our Capabilities</h2>
<ul>
<li>Heavy lift handling</li>
<li>Oversized cargo management</li>
<li>Project cargo coordination</li>
<li>Specialized equipment transport</li>
</ul>

<h2>Service Features</h2>
<ul>
<li>Expert planning and engineering</li>
<li>Specialized handling equipment</li>
<li>Route surveys and feasibility studies</li>
<li>Customs clearance support</li>
</ul>""",
        "source_url": "https://truelog.com.sg/efficient-breakbulk-services-ensuring-seamless-logistics/"
    },
]


def import_blog_posts():
    """Import all blog posts into the database"""
    db = SessionLocal()

    try:
        imported = 0
        skipped = 0

        for post_data in BLOG_POSTS:
            # Generate slug from title
            slug = slugify(post_data['title'])

            # Check if post already exists
            existing = db.query(BlogPost).filter(BlogPost.slug == slug).first()
            if existing:
                print(f"  Skipped (exists): {post_data['title'][:50]}...")
                skipped += 1
                continue

            # Parse date
            published_date = datetime.strptime(post_data['date'], '%Y-%m-%d')

            # Create blog post
            post = BlogPost(
                title=post_data['title'],
                slug=slug,
                content=post_data['content'],
                excerpt=post_data['excerpt'],
                featured_image=post_data.get('featured_image'),
                status=BlogPostStatus.PUBLISHED,
                meta_title=post_data['title'],
                meta_description=post_data['excerpt'],
                published_at=published_date,
                created_at=published_date,
            )

            db.add(post)
            imported += 1
            print(f"  Imported: {post_data['title'][:50]}...")

        db.commit()
        print(f"\nImport complete: {imported} imported, {skipped} skipped")

    except Exception as e:
        db.rollback()
        print(f"Error importing blog posts: {e}")
        raise
    finally:
        db.close()


if __name__ == '__main__':
    print("Importing TrueLog blog posts...")
    print("=" * 50)
    import_blog_posts()