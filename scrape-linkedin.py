#!/usr/bin/env python3
"""
LinkedIn public job search scraper for quant/trading internships.
Uses LinkedIn's public job search (no login required) and parses HTML.
"""

import re
import subprocess
import json
from datetime import datetime
from pathlib import Path

REPO_DIR = Path.home() / "quant-internships"
MARKDOWN_FILE = REPO_DIR / "Quant Internships 2026.md"

# LinkedIn public search queries
SEARCH_QUERIES = [
    "quantitative intern 2026",
    "quant trading intern summer 2026",
    "quantitative developer intern 2026",
    "quantitative research intern 2026",
    "algorithmic trading intern 2026",
]

# Relevant companies and keywords to filter for
QUANT_KEYWORDS = [
    "quant", "quantitative", "trading", "algorithmic", "systematic",
    "hedge fund", "prop trading", "derivatives", "risk", "stochastic",
    "financial engineer", "alpha", "portfolio", "execution",
]

QUANT_COMPANIES = [
    "jane street", "citadel", "two sigma", "hrt", "hudson river",
    "optiver", "sig", "susquehanna", "jump trading", "drw", "imc",
    "akuna", "tower research", "five rings", "old mission", "virtu",
    "schonfeld", "millennium", "point72", "de shaw", "renaissance",
    "aqr", "blackrock", "goldman sachs", "morgan stanley", "jp morgan",
    "bank of america", "barclays", "ubs", "deutsche bank", "gelber",
    "garda", "graham capital", "hudson advisors", "summittx",
    "infinitequant", "pnc", "cme group", "wolfe research",
    "balyasny", "brevan howard", "man group", "winton",
    "janus henderson", "state street", "neuberger berman",
]


def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


def fetch_linkedin_public(query, max_results=50):
    """Fetch LinkedIn public job search results via curl"""
    encoded_query = query.replace(" ", "+")
    # f_TPR=r604800 = past week
    url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={encoded_query}&location=United+States&f_TPR=r604800&start=0"
    
    result = subprocess.run(
        ["curl", "-s", "-A", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)", url],
        capture_output=True, text=True, timeout=30
    )
    
    if result.returncode != 0:
        log(f"Error fetching LinkedIn for '{query}': {result.stderr}")
        return []
    
    return parse_linkedin_html(result.stdout)


def parse_linkedin_html(html):
    """Parse LinkedIn job listing HTML"""
    listings = []
    
    # Extract job cards
    # LinkedIn public API returns <li> items with job data
    job_cards = re.findall(
        r'<div class="base-card[^"]*"[^>]*>.*?</div>\s*</div>\s*</div>',
        html, re.DOTALL
    )
    
    if not job_cards:
        # Try alternate pattern
        job_cards = re.findall(r'<li>.*?</li>', html, re.DOTALL)
    
    for card in job_cards:
        title_match = re.search(r'<h3[^>]*class="[^"]*title[^"]*"[^>]*>\s*(.*?)\s*</h3>', card, re.DOTALL)
        company_match = re.search(r'<h4[^>]*class="[^"]*subtitle[^"]*"[^>]*>\s*<a[^>]*>\s*(.*?)\s*</a>', card, re.DOTALL)
        location_match = re.search(r'<span[^>]*class="[^"]*location[^"]*"[^>]*>\s*(.*?)\s*</span>', card, re.DOTALL)
        url_match = re.search(r'<a[^>]*class="[^"]*card[^"]*"[^>]*href="([^"]*)"', card)
        
        if title_match:
            title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
            company = re.sub(r'<[^>]+>', '', company_match.group(1)).strip() if company_match else "Unknown"
            location = re.sub(r'<[^>]+>', '', location_match.group(1)).strip() if location_match else ""
            url = url_match.group(1).split("?")[0] if url_match else ""
            
            if title and url:
                listings.append({
                    'company': company,
                    'role': title,
                    'location': location,
                    'url': url,
                    'source': 'LinkedIn'
                })
    
    return listings


def is_quant_relevant(listing):
    """Check if a listing is relevant to quant/trading"""
    text = f"{listing['company']} {listing['role']}".lower()
    
    # Check company match
    for company in QUANT_COMPANIES:
        if company in text:
            return True
    
    # Check keyword match (need at least one quant keyword + intern/internship)
    has_quant = any(kw in text for kw in QUANT_KEYWORDS)
    has_intern = "intern" in text
    
    return has_quant and has_intern


def get_existing_urls():
    """Get existing URLs from markdown file"""
    if not MARKDOWN_FILE.exists():
        return set()
    
    content = MARKDOWN_FILE.read_text()
    urls = set()
    
    for line in content.split('\n'):
        if '|' in line and 'http' in line:
            url_match = re.search(r'\[Apply\]\((https://[^\)]+)\)', line)
            if url_match:
                # Normalize URL for comparison
                url = url_match.group(1).split('?')[0].rstrip('/')
                urls.add(url)
    
    return urls


def url_is_new(url, existing_urls):
    """Check if URL is new (not already in our list)"""
    clean = url.split('?')[0].rstrip('/')
    
    for existing in existing_urls:
        existing_clean = existing.split('?')[0].rstrip('/')
        if clean == existing_clean or clean in existing_clean or existing_clean in clean:
            return False
    
    return True


def add_listings_to_markdown(new_listings):
    """Add new listings to the markdown file"""
    if not new_listings:
        return False
    
    content = MARKDOWN_FILE.read_text()
    lines = content.split('\n')
    
    insert_index = 0
    for i, line in enumerate(lines):
        if line.startswith('| ---'):
            insert_index = i + 1
            break
    
    date_added = datetime.now().strftime('%Y-%m-%d')
    new_rows = []
    
    for listing in new_listings:
        row = f"| {listing['company']} | {listing['role']} | {listing['location']} | [Apply]({listing['url']}) | {date_added} | ✅ Open |"
        new_rows.append(row)
    
    lines = lines[:insert_index] + new_rows + lines[insert_index:]
    MARKDOWN_FILE.write_text('\n'.join(lines))
    
    return True


def git_commit_and_push(count):
    """Commit and push changes"""
    date_str = datetime.now().strftime('%Y-%m-%d')
    
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True, cwd=REPO_DIR
    )
    
    if not result.stdout.strip():
        return False
    
    subprocess.run(["git", "add", "-A"], cwd=REPO_DIR)
    subprocess.run(
        ["git", "commit", "-m", f"Auto-update: {count} new listings from LinkedIn ({date_str})"],
        capture_output=True, text=True, cwd=REPO_DIR
    )
    subprocess.run(["git", "push"], capture_output=True, text=True, cwd=REPO_DIR)
    
    return True


def main():
    log("=" * 60)
    log("LinkedIn Quant Internship Scraper")
    log("=" * 60)
    
    existing_urls = get_existing_urls()
    log(f"Existing URLs in markdown: {len(existing_urls)}")
    
    all_listings = []
    seen_urls = set()
    
    for query in SEARCH_QUERIES:
        log(f"Searching LinkedIn: '{query}'")
        listings = fetch_linkedin_public(query)
        log(f"  Found {len(listings)} raw results")
        
        for listing in listings:
            url = listing['url'].split('?')[0]
            if url not in seen_urls and is_quant_relevant(listing):
                seen_urls.add(url)
                all_listings.append(listing)
    
    log(f"Total relevant listings: {len(all_listings)}")
    
    # Filter for new ones
    new_listings = [l for l in all_listings if url_is_new(l['url'], existing_urls)]
    log(f"New listings not in markdown: {len(new_listings)}")
    
    if new_listings:
        for l in new_listings:
            log(f"  ✓ {l['company']}: {l['role']} ({l['location']})")
        
        if add_listings_to_markdown(new_listings):
            if git_commit_and_push(len(new_listings)):
                log(f"🎉 Added {len(new_listings)} new listings!")
            else:
                log("⚠️ Added but failed to push")
    else:
        log("✅ No new listings found")
    
    log("=" * 60)


if __name__ == "__main__":
    main()
