# language_text_scraper
 A scraper for collecting texts in different languages. 


# Language Text Scraper
Crawl and scrape text corpora from Substack.

## Setup
1. Install: `pip install scrapy langdetect`
2. Run: `python main.py`

## Files
- `gui.py`: UI for inputting URLs
- `scraper.py`: Crawler and scraper logic

## Usage
- "URL to Scrape From": Paste a Substack URL (e.g., `https://substack.com/@someauthor`), click "Scrape"
- "Seed Finder URL": Paste a hub (e.g., `https://www.google.com/search?q=russian+substack+writers`), click "Find Seeds"
- Output: Texts saved in `output/language/` and `output/corpus_seed_url/`

