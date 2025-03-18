import scrapy
from scrapy.crawler import CrawlerProcess
import os
from langdetect import detect
import re
import pathlib
from urllib.parse import urlparse
import logging
import time
from twisted.internet import reactor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SeedSpider(scrapy.Spider):
    name = "seed_spider"
    seeds = []

    def __init__(self, start_urls=None, max_seeds=10, callback=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_urls = start_urls or []
        self.max_seeds = max_seeds
        self.callback = callback
        SeedSpider.seeds = []  # Reset class variable on initialization
        self.seen_urls = set()  # Track URLs we've already seen

    def parse(self, response):
        logger.info(f"Processing URL: {response.url}")
        # Broader selector with delay for dynamic content
        time.sleep(1)  # Allow page to load
        
        # Extract all links from the page with broader selectors
        links = set()
        for selector in ["a::attr(href)", "link::attr(href)", "[data-href]::attr(data-href)", 
                         "[src]::attr(src)", "iframe::attr(src)"]:
            for href in response.css(selector).getall():
                if href and not href.startswith(("#", "javascript:", "mailto:", "tel:")):
                    links.add(href)
        
        # Process extracted links
        for href in links:
            if len(SeedSpider.seeds) < self.max_seeds and href not in self.seen_urls:
                if not href.startswith(('http://', 'https://')):
                    href = response.urljoin(href)
                
                # Basic URL validation
                if href.startswith(('http://', 'https://')) and len(href) < 500:
                    SeedSpider.seeds.append(href)
                    self.seen_urls.add(href)
                    logger.info(f"Added seed: {href}")
                    if self.callback:
                        self.callback(seeds=len(SeedSpider.seeds))
        
        # Continue crawling even if we got some seeds already
        for next_page in response.css("a::attr(href)").getall():
            if len(SeedSpider.seeds) < self.max_seeds:
                if not next_page.startswith(('http://', 'https://')):
                    next_page = response.urljoin(next_page)
                
                # Only follow links we haven't seen yet
                if next_page not in self.seen_urls and next_page.startswith(('http://', 'https://')):
                    self.seen_urls.add(next_page)
                    yield scrapy.Request(next_page, callback=self.parse, dont_filter=True, 
                                        errback=self.handle_error)
    
    def handle_error(self, failure):
        # Log errors but continue crawling
        logger.warning(f"Request failed: {failure.request.url}, {str(failure.value)}")
        return None  # Continue with other requests

class TextSpider(scrapy.Spider):
    name = "text_spider"
    max_files_per_seed_target = 100  # Target 100 files with 200+ words
    max_files_per_seed = 500  # Cap at 500 files per seed
    target_200_plus_count = 0

    def __init__(self, start_urls=None, callback=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_urls = start_urls or []
        self.seen_urls = set()
        self.callback = callback
        self.base_path = r"C:\Users\dawki\OneDrive\Documents\random_projects\corpora_archive\language_sorted_corpora"
        
        # Set current_seed based on start_urls
        self.current_seed = self.start_urls[0] if self.start_urls else None
        logger.info(f"TextSpider initialized with seed: {self.current_seed}")
        
        self.files_by_seed = {}
        # Ensure the output directory exists
        os.makedirs(self.base_path, exist_ok=True)

    def parse(self, response):
        logger.info(f"TextSpider processing: {response.url}")
        try:
            text = " ".join(response.css("p::text, article::text, .content::text, div::text").getall()).strip()
            word_count = len(text.split()) if text else 0
            
            if word_count >= 50 and word_count <= 2000:
                if text:
                    try:
                        lang = detect(text[:500])
                        seed_key = re.sub(r"[^\w]", "_", self.current_seed)
                        self.save_or_replace_text(text, lang, seed_key, word_count, response.url)
                        logger.info(f"Extracted text ({word_count} words) in {lang} from {response.url}")
                        
                        if self.callback:
                            self.callback(urls=len(self.seen_urls), 
                                          files=len(self.files_by_seed.get(self.current_seed, [])),
                                          target_200=self.target_200_plus_count)
                    except Exception as e:
                        logger.error(f"Error saving text: {str(e)}")
            
            # Extract and follow links
            for href in response.css("a::attr(href)").getall():
                if href not in self.seen_urls and self.target_200_plus_count < self.max_files_per_seed_target:
                    if not href.startswith(('http://', 'https://')):
                        href = response.urljoin(href)
                    
                    if href.startswith(('http://', 'https://')) and len(href) < 500:
                        self.seen_urls.add(href)
                        yield scrapy.Request(href, callback=self.parse, 
                                            errback=self.handle_error,
                                            dont_filter=True)
                        
                        if self.callback:
                            self.callback(urls=len(self.seen_urls), 
                                         files=len(self.files_by_seed.get(self.current_seed, [])),
                                         target_200=self.target_200_plus_count)
        except Exception as e:
            logger.error(f"Error processing {response.url}: {str(e)}")
    
    def handle_error(self, failure):
        logger.warning(f"Request failed: {failure.request.url}, {str(failure.value)}")
        return None  # Continue with other requests

    def save_or_replace_text(self, text, lang, seed_key, word_count, url):
        lang_dir = os.path.join(self.base_path, lang)
        os.makedirs(lang_dir, exist_ok=True)

        lang_files = [f for f in os.listdir(lang_dir) if f.startswith(f"text_{seed_key}_") and f.endswith(".txt")]
        max_num = max([int(f.split("_")[-1].split(".")[0]) for f in lang_files] or [0]) if lang_files else 0
        file_num = max_num + 1

        current_seed_files = self.files_by_seed.get(self.current_seed, [])
        if word_count >= 200:
            self.target_200_plus_count += 1
            if len(current_seed_files) < self.max_files_per_seed:
                self.save_text(text, lang, seed_key, file_num, url, word_count)
                current_seed_files.append(file_num)
            elif len(current_seed_files) >= self.max_files_per_seed and self.target_200_plus_count <= self.max_files_per_seed_target:
                to_replace = min(current_seed_files, key=lambda x: self.get_word_count(lang_dir, seed_key, x, url) if self.get_word_count(lang_dir, seed_key, x, url) else 2000)
                if self.get_word_count(lang_dir, seed_key, to_replace, url) < 200:
                    self.delete_text(lang_dir, seed_key, to_replace, url)
                    current_seed_files.remove(to_replace)
                    self.save_text(text, lang, seed_key, file_num, url, word_count)
                    current_seed_files.append(file_num)
        elif word_count >= 50 and len(current_seed_files) < self.max_files_per_seed and self.target_200_plus_count < self.max_files_per_seed_target:
            self.save_text(text, lang, seed_key, file_num, url, word_count)
            current_seed_files.append(file_num)

        self.files_by_seed[self.current_seed] = current_seed_files

    def save_text(self, text, lang, seed_key, file_num, url, word_count):
        url_basename = re.sub(r"[^\w]", "_", os.path.basename(urlparse(url).path) or urlparse(url).netloc)
        filename = f"text_{seed_key}_{url_basename}_{file_num}.txt"
        lang_file = os.path.join(self.base_path, lang, filename)
        logger.info(f"Saving file: {lang_file}")
        with open(lang_file, "w", encoding="utf-8") as f:
            f.write(text)
        if self.callback:
            self.callback(lang=lang, filename=filename, word_count=word_count)

    def delete_text(self, lang_dir, seed_key, file_num, url):
        url_basename = re.sub(r"[^\w]", "_", os.path.basename(urlparse(url).path) or urlparse(url).netloc)
        lang_file = os.path.join(lang_dir, f"text_{seed_key}_{url_basename}_{file_num}.txt")
        if os.path.exists(lang_file):
            os.remove(lang_file)

    def get_word_count(self, dir_path, seed_key, file_num, url):
        url_basename = re.sub(r"[^\w]", "_", os.path.basename(urlparse(url).path) or urlparse(url).netloc)
        file_path = os.path.join(dir_path, f"text_{seed_key}_{url_basename}_{file_num}.txt")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                return len(f.read().split())
        return None

def scrape_all(seed_url, callback=None, max_seeds=10):
    """Find seeds from a URL and then scrape content from those seeds"""
    logger.info(f"Starting seed collection from: {seed_url}")
    
    # Create crawler process with settings
    process = CrawlerProcess(settings={
        "LOG_LEVEL": "INFO",
        "DOWNLOAD_DELAY": 1,
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "RETRY_TIMES": 2,
        "RETRY_HTTP_CODES": [403, 500, 502, 503, 504],
        "DOWNLOAD_TIMEOUT": 30,  # 30 seconds timeout
        "ROBOTSTXT_OBEY": False,  # Don't obey robots.txt for better results
    })
    
    # Start crawling with SeedSpider
    deferred = process.crawl(SeedSpider, start_urls=[seed_url], max_seeds=max_seeds, callback=callback)
    
    # After SeedSpider finishes, start TextSpider for each collected seed
    def after_seed_spider(_):
        logger.info(f"Seed collection finished. Found {len(SeedSpider.seeds)} seeds.")
        if callback:
            callback(seeds=len(SeedSpider.seeds))
        
        # If no seeds found, use the original URL as a seed
        if not SeedSpider.seeds:
            logger.warning("No seeds found, using original URL as seed")
            SeedSpider.seeds = [seed_url]
            if callback:
                callback(seeds=1)
        
        # Start TextSpider for each seed
        for url in SeedSpider.seeds:
            logger.info(f"Starting content spider for seed: {url}")
            TextSpider.target_200_plus_count = 0  # Reset counter for each seed
            spider = TextSpider(start_urls=[url], callback=callback)
            spider.current_seed = url
            process.crawl(spider)
    
    deferred.addBoth(after_seed_spider)
    
    # Start the reactor only once
    process.start()
    logger.info("Scraping completed")

# Wrapper functions for GUI integration
def run_scraper(urls, callback=None):
    """Function called by GUI to directly scrape from provided URLs"""
    logger.info(f"Starting direct scraping of {len(urls)} URLs")
    
    # Create crawler process with settings
    process = CrawlerProcess(settings={
        "LOG_LEVEL": "INFO",
        "DOWNLOAD_DELAY": 1,
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "RETRY_TIMES": 2,
        "RETRY_HTTP_CODES": [403, 500, 502, 503, 504],
        "DOWNLOAD_TIMEOUT": 30,
        "ROBOTSTXT_OBEY": False,
    })
    
    # Add each URL as a TextSpider crawl job
    for url in urls:
        if url.strip():
            logger.info(f"Setting up spider for URL: {url.strip()}")
            TextSpider.target_200_plus_count = 0  # Reset counter for each seed
            spider = TextSpider(start_urls=[url.strip()], callback=callback)
            spider.current_seed = url.strip()
            process.crawl(spider)
    
    # Start the reactor
    process.start()
    logger.info("Direct scraping completed")

def run_seed_finder(seed_url, callback=None, max_seeds=10):
    """Function called by GUI to find seeds and then scrape from them"""
    if seed_url.strip():
        logger.info(f"Starting seed finder for URL: {seed_url.strip()} with max seeds: {max_seeds}")
        scrape_all(seed_url.strip(), callback, max_seeds)
    else:
        logger.error("Empty seed URL provided")

# Handle gitignore file
try:
    with open(".gitignore", "a+") as f:
        path = r"C:\Users\dawki\OneDrive\Documents\random_projects\corpora_archive\language_sorted_corpora"
        f.seek(0)
        gitignore_content = f.read()
        if path not in gitignore_content:
            f.write(f"\n{path}/")
except Exception as e:
    logger.warning(f"Could not update .gitignore: {str(e)}")
