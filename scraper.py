import scrapy
from scrapy.crawler import CrawlerProcess
import os
from langdetect import detect
import re

class TextSpider(scrapy.Spider):
    name = "text_spider"
    allowed_domains = ["substack.com"]
    max_files = 100
    file_count = 0

    def __init__(self, start_urls=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_urls = start_urls or []
        self.seen_urls = set()

    def parse(self, response):
        if self.file_count >= self.max_files:
            return

        # Extract text from article pages
        if "/p/" in response.url:
            text = " ".join(response.css("p::text").getall()).strip()
            if text:
                lang = detect(text[:500])  # Detect language from first 500 chars
                seed_key = re.sub(r"[^\w]", "_", self.start_urls[0])  # Clean seed URL for folder
                self.save_text(text, lang, seed_key)
                self.file_count += 1

        # Crawl for more links (breadth-first via Scrapy’s default)
        for href in response.css("a[href*='substack.com']::attr(href)").getall():
            if href not in self.seen_urls and self.file_count < self.max_files:
                self.seen_urls.add(href)
                yield scrapy.Request(href, callback=self.parse)

    def save_text(self, text, lang, seed_key):
        # Save by language
        lang_dir = f"output/language/{lang}"
        os.makedirs(lang_dir, exist_ok=True)
        lang_file = f"{lang_dir}/text_{self.file_count}.txt"
        with open(lang_file, "w", encoding="utf-8") as f:
            f.write(text)

        # Save by seed
        seed_dir = f"output/corpus_{seed_key}"
        os.makedirs(seed_dir, exist_ok=True)
        seed_file = f"{seed_dir}/text_{self.file_count}.txt"
        with open(seed_file, "w", encoding="utf-8") as f:
            f.write(text)

def run_scraper(start_urls):
    process = CrawlerProcess(settings={
        "LOG_LEVEL": "INFO",
        "DOWNLOAD_DELAY": 1,  # Avoid overwhelming servers
    })
    process.crawl(TextSpider, start_urls=start_urls)
    process.start()

def run_seed_finder(seed_url):
    # Mini-crawl to find Substack seeds
    class SeedSpider(scrapy.Spider):
        name = "seed_spider"
        start_urls = [seed_url]
        allowed_domains = ["substack.com"]
        max_seeds = 10
        seeds = []

        def parse(self, response):
            for href in response.css("a[href*='substack.com/@']::attr(href)").getall():
                if len(self.seeds) < self.max_seeds and href not in self.seeds:
                    self.seeds.append(href)
            for next_page in response.css("a[href]::attr(href)").getall():
                if len(self.seeds) < self.max_seeds:
                    yield scrapy.Request(next_page, callback=self.parse)

    process = CrawlerProcess(settings={"LOG_LEVEL": "INFO"})
    process.crawl(SeedSpider)
    process.start()
    if SeedSpider.seeds:
        run_scraper(SeedSpider.seeds)  # Pass found seeds to main scraper
