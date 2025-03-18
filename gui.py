import tkinter as tk
from scraper import run_scraper, run_seed_finder

def scrape_from_url(url_entry):
    url = url_entry.get()
    if url:
        run_scraper([url])

def find_seeds_and_scrape(seed_entry):
    seed_url = seed_entry.get()
    if seed_url:
        run_seed_finder(seed_url)

def create_gui():
    root = tk.Tk()
    root.title("Language Text Scraper")
    root.geometry("400x200")

    tk.Label(root, text="URL to Scrape From:").pack(pady=5)
    url_entry = tk.Entry(root, width=50)
    url_entry.pack(pady=5)
    tk.Button(root, text="Scrape", command=lambda: scrape_from_url(url_entry)).pack(pady=5)

    tk.Label(root, text="Seed Finder URL:").pack(pady=5)
    seed_entry = tk.Entry(root, width=50)
    seed_entry.pack(pady=5)
    tk.Button(root, text="Find Seeds", command=lambda: find_seeds_and_scrape(seed_entry)).pack(pady=5)

    root.mainloop()