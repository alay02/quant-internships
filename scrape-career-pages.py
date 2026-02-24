#!/usr/bin/env python3
"""
Direct career page scraper for top quant firms.
Uses curl to fetch career pages and extract internship listings.
"""

import re
import subprocess
import json
from datetime import datetime
from pathlib import Path

REPO_DIR = Path.home() / "quant-internships"
MARKDOWN_FILE = REPO_DIR / "Quant Internships 2026.md"

# Career page URLs and their API endpoints
CAREER_PAGES = [
    {
        "company": "Two Sigma",
        "url": "https://careers.twosigma.com/careers/SearchJobs/?3_56_3=778&3_56_3=779&3_56_3=780&3_56_3=781&3_56_3=782",
        "type": "html",
    },
    {
        "company": "Citadel",
        "url": "https://www.citadel.com/careers/details/quantitative-research-intern-2026/",
        "type": "html",
    },
    {
        "company": "Hudson River Trading",
        "url": "https://www.hudsonrivertrading.com/careers/?_4118765=Internship",
        "type": "html",
    },
    {
        "company": "Optiver",
        "url": "https://optiver.com/working-at-optiver/career-opportunities/?filter=internship",
        "type": "html",
    },
    {
        "company": "DRW",
        "url": "https://drw.com/work-at-drw/category/campus/",
        "type": "html",
    },
    {
        "company": "IMC Trading",
        "url": "https://careers.imc.com/us/en/c/internships-jobs",
        "type": "html",
    },
    {
        "company": "Akuna Capital",
        "url": "https://akunacapital.com/careers#internships",
        "type": "html",
    },
    {
        "company": "Jump Trading",
        "url": "https://www.jumptrading.com/careers/?titleSearch=intern&sortBy=posted_date",
        "type": "html",
    },
]

# Greenhouse/Lever API-based career pages (structured JSON)
API_CAREER_PAGES = [
    {
        "company": "Jane Street",
        "url": "https://boards-api.greenhouse.io/v1/boards/janestreet/jobs?content=true",
        "type": "greenhouse",
    },
    {
        "company": "Hudson River Trading",
        "url": "https://boards-api.greenhouse.io/v1/boards/hudsonrivertrading/jobs?content=true",
        "type": "greenhouse",
    },
    {
        "company": "Five Rings",
        "url": "https://boards-api.greenhouse.io/v1/boards/fiveringsllc/jobs?content=true",
        "type": "greenhouse",
    },
    {
        "company": "Old Mission",
        "url": "https://boards-api.greenhouse.io/v1/boards/oldmissioncapital/jobs?content=true",
        "type": "greenhouse",
    },
    {
        "company": "Tower Research",
        "url": "https://boards-api.greenhouse.io/v1/boards/towerresearchcapital/jobs?content=true",
        "type": "greenhouse",
    },
]


def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


def fetch_url(url, timeout=15):
    """Fetch URL content via curl"""
    result = subprocess.run(
        ["curl", "-s", "-L", "-A", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)", url],
        capture_output=True, text=True, timeout=timeout
    )
    if result.returncode != 0:
        return None
    return result.stdout


def parse_greenhouse_jobs(json_text, company):
    """Parse Greenhouse API JSON for intern roles"""
    listings = []
    try:
        data = json.loads(json_text)
        jobs = data.get("jobs", [])
        
        for job in jobs:
            title = job.get("title", "")
            if not any(kw in title.lower() for kw in ["intern", "co-op", "summer"]):
                continue
            
            url = job.get("absolute_url", "")
            location = ""
            if job.get("location"):
                location = job["location"].get("name", "")
            
            listings.append({
                "company": company,
                "role": title,
                "location": location,
                "url": url,
                "source": "career_page",
            })
    except (json.JSONDecodeError, KeyError) as e:
        log(f"  Error parsing Greenhouse JSON for {company}: {e}")
    
    return listings


def get_existing_urls():
    """Get existing URLs from markdown"""
    if not MARKDOWN_FILE.exists():
        return set()
    
    content = MARKDOWN_FILE.read_text()
    urls = set()
    
    for line in content.split('\n'):
        if '|' in line and 'http' in line:
            match = re.search(r'\[Apply\]\((https://[^\)]+)\)', line)
            if match:
                urls.add(match.group(1).split('?')[0].rstrip('/'))
    
    return urls


def url_is_new(url, existing_urls):
    """Check if URL is new"""
    clean = url.split('?')[0].rstrip('/')
    for existing in existing_urls:
        existing_clean = existing.split('?')[0].rstrip('/')
        if clean == existing_clean or clean in existing_clean or existing_clean in clean:
            return False
    return True


def add_listings_to_markdown(new_listings):
    """Add new listings to markdown"""
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


def git_commit_and_push(count, source):
    """Commit and push"""
    date_str = datetime.now().strftime('%Y-%m-%d')
    
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True, cwd=REPO_DIR
    )
    if not result.stdout.strip():
        return False
    
    subprocess.run(["git", "add", "-A"], cwd=REPO_DIR)
    subprocess.run(
        ["git", "commit", "-m", f"Auto-update: {count} new listings from {source} ({date_str})"],
        capture_output=True, text=True, cwd=REPO_DIR
    )
    subprocess.run(["git", "push"], capture_output=True, text=True, cwd=REPO_DIR)
    return True


def main():
    log("=" * 60)
    log("Career Page Scraper - Top Quant Firms")
    log("=" * 60)
    
    existing_urls = get_existing_urls()
    log(f"Existing URLs: {len(existing_urls)}")
    
    all_listings = []
    
    # Scrape Greenhouse API pages
    for page in API_CAREER_PAGES:
        log(f"Fetching {page['company']} (Greenhouse API)...")
        content = fetch_url(page["url"])
        if content:
            listings = parse_greenhouse_jobs(content, page["company"])
            log(f"  Found {len(listings)} intern roles")
            all_listings.extend(listings)
        else:
            log(f"  Failed to fetch")
    
    # Filter new listings
    new_listings = [l for l in all_listings if url_is_new(l['url'], existing_urls)]
    log(f"\nNew listings not in markdown: {len(new_listings)}")
    
    if new_listings:
        for l in new_listings:
            log(f"  ✓ {l['company']}: {l['role']} ({l['location']})")
        
        if add_listings_to_markdown(new_listings):
            if git_commit_and_push(len(new_listings), "career pages"):
                log(f"🎉 Added {len(new_listings)} new listings!")
            else:
                log("⚠️ Added but failed to push")
    else:
        log("✅ No new listings from career pages")
    
    log("=" * 60)


if __name__ == "__main__":
    main()
