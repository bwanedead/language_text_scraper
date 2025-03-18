import scrapy
from scrapy.crawler import CrawlerProcess
import os
from langdetect import detect
import re
import pathlib
from urllib.parse import urlparse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        self.current_seed = None
        self.files_by_seed = {}

    def parse(self, response):
        text = " ".join(response.css("p::text").getall()).strip()
        word_count = len(text.split()) if text else 0
        if word_count >= 50 and word_count <= 2000:
            if text:
                lang = detect(text[:500])
                seed_key = re.sub(r"[^\w]", "_", self.current_seed)
                self.save_or_replace_text(text, lang, seed_key, word_count, response.url)
                if self.callback:
                    self.callback(urls=len(self.seen_urls), files=len(self.files_by_seed.get(self.current_seed, [])),
                                  target_200=self.target_200_plus_count)

        for href in response.css("a[href]::attr(href)").getall():
            if href not in self.seen_urls and self.target_200_plus_count < self.max_files_per_seed_target:
                if not href.startswith(('http://', 'https://')):
                    href = response.urljoin(href)
                self.seen_urls.add(href)
                yield scrapy.Request(href, callback=self.parse)
                if self.callback:
                    self.callback(urls=len(self.seen_urls), files=len(self.files_by_seed.get(self.current_seed, [])),
                                  target_200=self.target_200_plus_count)

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
    class SeedSpider(scrapy.Spider):
        name = "seed_spider"
        start_urls = [seed_url]
        seeds = []

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.max_seeds = max_seeds

        def parse(self, response):
            for href in response.css("a[href]::attr(href)").getall():
                if len(self.seeds) < self.max_seeds and href not in self.seeds:
                    self.seeds.append(href)
                    if callback:
                        callback(seeds=len(self.seeds))
            for next_page in response.css("a[href]::attr(href)").getall():
                if len(self.seeds) < self.max_seeds:
                    if not next_page.startswith(('http://', 'https://')):
                        next_page = response.urljoin(next_page)
                    yield scrapy.Request(next_page, callback=self.parse)

    process = CrawlerProcess(settings={
        "LOG_LEVEL": "INFO",
        "DOWNLOAD_DELAY": 1,
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "RETRY_TIMES": 2,
        "RETRY_HTTP_CODES": [403, 500, 502, 503, 504],
    })
    process.crawl(SeedSpider)
    process.start()
    seeds = SeedSpider.seeds
    logger.info(f"Collected seeds: {seeds}")
    if seeds:
        for url in seeds:
            process.crawl(TextSpider, start_urls=[url], callback=callback)
        process.start()

with open(".gitignore", "a") as f:
    path = r"C:\Users\dawki\OneDrive\Documents\random_projects\corpora_archive\language_sorted_corpora"
    gitignore_content = open(".gitignore").read()
    if path not in gitignore_content:
        f.write(f"\n{path}/")
