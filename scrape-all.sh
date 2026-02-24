#!/bin/bash
# Master scraper - runs all sources
cd "$(dirname "$0")"

echo "========================================"
echo "Running all quant internship scrapers"
echo "$(date)"
echo "========================================"

echo ""
echo "--- Source 1: SimplifyJobs ---"
python3 scrape-internships.py

echo ""
echo "--- Source 2: Career Pages (Greenhouse API) ---"
python3 scrape-career-pages.py

echo ""
echo "--- Source 3: LinkedIn Public Search ---"
python3 scrape-linkedin.py

echo ""
echo "========================================"
echo "All scrapers complete!"
echo "========================================"
