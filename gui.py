import tkinter as tk
from tkinter import scrolledtext, ttk
from scraper import run_scraper, run_seed_finder
import os

def scrape_from_url(url_list):
    urls = url_list.get("1.0", tk.END).strip().split("\n")
    if urls and urls[0]:  # Check if list isn't empty
        status_label.config(text="Scraping... Seeds: 0 | URLs: 0 | Files: 0")
        run_scraper(urls, update_status)
        status_label.config(text="Done! Check language_sorted_corpora/ folder")

def find_seeds_and_scrape(seed_list):
    seeds = seed_list.get("1.0", tk.END).strip().split("\n")
    if seeds and seeds[0]:
        try:
            seed_count = int(seed_count_entry.get())
            if seed_count <= 0:
                raise ValueError
        except ValueError:
            seed_count = 10  # Default to 10 if invalid
        status_label.config(text="Finding seeds... Seeds: 0 | URLs: 0 | Files: 0")
        run_seed_finder(seeds[0], update_status, seed_count)  # Pass seed_count
        status_label.config(text="Done! Check language_sorted_corpora/ folder")

def update_status(seeds=0, urls=0, files=0, total=0, target_200=0):
    status_label.config(text=f"Progress: Seeds: {seeds} | URLs: {urls} | Seed Files: {files} | Total Files: {total} | 200+ Words: {target_200}")
    update_directory_view()

def update_directory_view():
    base_path = r"C:\Users\dawki\OneDrive\Documents\random_projects\corpora_archive\language_sorted_corpora"
    tree.delete(*tree.get_children())
    for lang in os.listdir(base_path):
        if os.path.isdir(os.path.join(base_path, lang)):
            lang_node = tree.insert("", "end", text=lang, open=True)
            for file in os.listdir(os.path.join(base_path, lang)):
                if file.endswith(".txt"):
                    tree.insert(lang_node, "end", text=file)

def add_url(entry, listbox):
    url = entry.get().strip()
    if url:
        listbox.insert(tk.END, url)  # Let ScrolledText handle newlines
        entry.delete(0, tk.END)

def create_gui():
    root = tk.Tk()
    root.title("Language Text Scraper")
    root.geometry("600x600")

    # Scrape URLs section
    tk.Label(root, text="URLs to Scrape From (e.g., https://substack.com/@astralcodxten):").pack(pady=5)
    url_entry = tk.Entry(root, width=50)
    url_entry.pack(pady=5)
    url_list = scrolledtext.ScrolledText(root, width=50, height=5)
    url_list.pack(pady=5)
    tk.Button(root, text="Add URL", command=lambda: add_url(url_entry, url_list)).pack(pady=5)
    tk.Button(root, text="Scrape", command=lambda: scrape_from_url(url_list)).pack(pady=5)

    # Seed Finder section
    seed_frame = tk.Frame(root)
    seed_frame.pack(pady=5)
    tk.Label(seed_frame, text="Seed Finder URLs (e.g., https://www.google.com/search?q=substack+writers):").pack(side=tk.LEFT, padx=(0, 5))
    tk.Label(seed_frame, text="Seed Count:").pack(side=tk.LEFT)
    global seed_count_entry
    seed_count_entry = tk.Entry(seed_frame, width=5)
    seed_count_entry.insert(0, "10")  # Default value
    seed_count_entry.pack(side=tk.LEFT, padx=5)
    seed_entry = tk.Entry(seed_frame, width=40)
    seed_entry.pack(side=tk.LEFT, pady=5)
    seed_list = scrolledtext.ScrolledText(root, width=50, height=5)
    seed_list.pack(pady=5)
    tk.Button(root, text="Add Seed", command=lambda: add_url(seed_entry, seed_list)).pack(pady=5)
    tk.Button(root, text="Find Seeds", command=lambda: find_seeds_and_scrape(seed_list)).pack(pady=5)

    tk.Label(root, text="Directory Contents:").pack(pady=5)
    global tree
    tree = ttk.Treeview(root, height=10)
    tree.pack(fill="both", expand=True, pady=5)
    scrollbar = ttk.Scrollbar(root, orient="vertical", command=tree.yview)
    scrollbar.pack(side="right", fill="y")
    tree.configure(yscrollcommand=scrollbar.set)

    # Status bar
    global status_label
    status_label = tk.Label(root, text="Ready", anchor="w")
    status_label.pack(fill="x", pady=5)

    root.mainloop()