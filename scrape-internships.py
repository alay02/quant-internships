#!/usr/bin/env python3
"""
Automated scraper for quant/trading internships from multiple sources.
Runs daily to check for new postings and updates the markdown file.
"""

import re
import subprocess
from datetime import datetime
from pathlib import Path

# Configuration
REPO_DIR = Path.home() / "quant-internships"
MARKDOWN_FILE = REPO_DIR / "Quant Internships 2026.md"
TEMP_FILE = REPO_DIR / "simplify_temp.md"

# Target companies for filtering
TARGET_COMPANIES = [
    "Jane Street", "Citadel", "Two Sigma", "HRT", "Hudson River Trading",
    "Optiver", "SIG", "Susquehanna", "Jump Trading", "DRW", "IMC",
    "Akuna", "Tower Research", "Five Rings", "Old Mission", "Virtu",
    "Schonfeld", "Millennium", "Point72", "DE Shaw", "Renaissance",
    "AQR", "BlackRock", "Goldman Sachs", "Morgan Stanley", "JP Morgan",
    "Bank of America", "Barclays", "Credit Suisse", "UBS", "Deutsche Bank",
    "Gelber", "Garda", "Neuberger Berman", "State Street", "BMO",
    "Bank of Montreal", "Royal Bank", "RBC", "Microsoft"
]

def log(message):
    """Print with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def download_simplify_jobs():
    """Download the SimplifyJobs README"""
    log("Downloading SimplifyJobs Summer 2026 Internships...")
    url = "https://raw.githubusercontent.com/SimplifyJobs/Summer2026-Internships/dev/README.md"
    result = subprocess.run(
        ["curl", "-s", url],
        capture_output=True,
        text=True,
        cwd=REPO_DIR
    )
    
    if result.returncode != 0:
        log(f"Error downloading SimplifyJobs: {result.stderr}")
        return None
    
    TEMP_FILE.write_text(result.stdout)
    log(f"Downloaded {len(result.stdout)} bytes")
    return result.stdout

def extract_quant_section(content):
    """Extract the Quantitative Finance section"""
    quant_start = content.find('## 📈 Quantitative Finance Internship Roles')
    if quant_start == -1:
        log("ERROR: Quantitative Finance section not found!")
        return None
    
    next_section = content.find('\n## ', quant_start + 10)
    if next_section == -1:
        quant_section = content[quant_start:]
    else:
        quant_section = content[quant_start:next_section]
    
    log(f"Extracted Quant Finance section ({len(quant_section)} bytes)")
    return quant_section

def extract_urls_from_section(section):
    """Extract application URLs from the section"""
    url_pattern = r'href="(https://[^"]+)"'
    urls = re.findall(url_pattern, section)
    
    # Filter and clean URLs
    app_urls = []
    for url in urls:
        if 'simplify.jobs' not in url and 'imgur.com' not in url:
            clean_url = url.split('?utm_source')[0].split('&utm_source')[0]
            if clean_url not in app_urls:
                app_urls.append(clean_url)
    
    log(f"Found {len(app_urls)} unique URLs in section")
    return app_urls

def get_existing_urls():
    """Extract URLs from existing markdown file"""
    if not MARKDOWN_FILE.exists():
        log("ERROR: Markdown file not found!")
        return set()
    
    content = MARKDOWN_FILE.read_text()
    existing_urls = set()
    
    for line in content.split('\n'):
        if '|' in line and 'http' in line:
            url_match = re.search(r'\[Apply\]\((https://[^\)]+)\)', line)
            if url_match:
                url = url_match.group(1)
                clean_url = url.split('?utm_source')[0].split('&utm_source')[0].split('?ref=')[0]
                existing_urls.add(clean_url)
    
    log(f"Found {len(existing_urls)} existing URLs in markdown")
    return existing_urls

def find_new_urls(simplify_urls, existing_urls):
    """Compare URLs to find new ones"""
    new_urls = []
    
    for url in simplify_urls:
        clean_url = url.split('?')[0]
        
        is_new = True
        for existing in existing_urls:
            existing_clean = existing.split('?')[0]
            if existing_clean == clean_url or clean_url in existing_clean or existing_clean in clean_url:
                is_new = False
                break
        
        if is_new:
            new_urls.append(url)
    
    log(f"Found {len(new_urls)} NEW URLs")
    return new_urls

def extract_listing_details(section, url):
    """Extract company, role, location for a given URL"""
    # Find the row containing this URL
    url_pos = section.find(url[:50])
    if url_pos == -1:
        return None
    
    # Find the table row
    row_start = section.rfind('<tr>', 0, url_pos)
    row_end = section.find('</tr>', url_pos)
    
    if row_start == -1 or row_end == -1:
        return None
    
    row = section[row_start:row_end]
    cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
    
    if len(cells) >= 3:
        # Parse company name
        company_match = re.search(r'<a href="[^"]+">([^<]+)</a>', cells[0])
        company = company_match.group(1) if company_match else "Unknown"
        
        # Role
        role = re.sub(r'<[^>]+>', '', cells[1]).strip()
        
        # Location
        location = re.sub(r'<br>', ', ', cells[2])
        location = re.sub(r'<[^>]+>', '', location).strip()
        
        return {
            'company': company,
            'role': role,
            'location': location,
            'url': url
        }
    
    return None

def add_new_listings(new_listings):
    """Add new listings to the markdown file"""
    if not new_listings:
        log("No new listings to add")
        return False
    
    content = MARKDOWN_FILE.read_text()
    lines = content.split('\n')
    
    # Find insertion point (after header separator)
    insert_index = 0
    for i, line in enumerate(lines):
        if line.startswith('| ---'):
            insert_index = i + 1
            break
    
    # Create new rows
    new_rows = []
    date_added = datetime.now().strftime('%Y-%m-%d')
    
    for listing in new_listings:
        row = f"| {listing['company']} | {listing['role']} | {listing['location']} | [Apply]({listing['url']}) | {date_added} | ✅ Open |"
        new_rows.append(row)
    
    # Insert new rows
    lines = lines[:insert_index] + new_rows + lines[insert_index:]
    
    # Write back
    MARKDOWN_FILE.write_text('\n'.join(lines))
    
    log(f"Added {len(new_listings)} new listings to markdown")
    return True

def git_commit_and_push():
    """Commit and push changes to git"""
    date_str = datetime.now().strftime('%Y-%m-%d')
    
    # Check if there are changes
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
        cwd=REPO_DIR
    )
    
    if not result.stdout.strip():
        log("No changes to commit")
        return False
    
    # Stage changes
    subprocess.run(["git", "add", str(MARKDOWN_FILE)], cwd=REPO_DIR)
    
    # Commit
    result = subprocess.run(
        ["git", "commit", "-m", f"Auto-update: New quant internships found ({date_str})"],
        capture_output=True,
        text=True,
        cwd=REPO_DIR
    )
    
    if result.returncode != 0:
        log(f"Error committing: {result.stderr}")
        return False
    
    # Push
    result = subprocess.run(
        ["git", "push"],
        capture_output=True,
        text=True,
        cwd=REPO_DIR
    )
    
    if result.returncode != 0:
        log(f"Error pushing: {result.stderr}")
        return False
    
    log("Successfully committed and pushed changes")
    return True

def main():
    """Main scraping workflow"""
    log("="*60)
    log("Starting quant internship scraper")
    log("="*60)
    
    # Download SimplifyJobs
    content = download_simplify_jobs()
    if not content:
        return
    
    # Extract quant section
    quant_section = extract_quant_section(content)
    if not quant_section:
        return
    
    # Extract URLs
    simplify_urls = extract_urls_from_section(quant_section)
    existing_urls = get_existing_urls()
    new_urls = find_new_urls(simplify_urls, existing_urls)
    
    if not new_urls:
        log("✅ No new listings found")
        return
    
    # Extract details for new listings
    new_listings = []
    last_company = None
    
    for url in new_urls:
        details = extract_listing_details(quant_section, url)
        if details:
            # Handle continuation rows (↳)
            if details['company'] == "Unknown" and last_company:
                details['company'] = last_company
            else:
                last_company = details['company']
            
            new_listings.append(details)
            log(f"  ✓ {details['company']}: {details['role']}")
    
    # Add to file
    if add_new_listings(new_listings):
        # Commit and push
        if git_commit_and_push():
            log(f"🎉 Successfully added {len(new_listings)} new listings!")
        else:
            log("⚠️ Added listings but failed to push to git")
    
    # Cleanup
    if TEMP_FILE.exists():
        TEMP_FILE.unlink()
    
    log("="*60)
    log("Scraper completed")
    log("="*60)

if __name__ == "__main__":
    main()
