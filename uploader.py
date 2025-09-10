# -*- coding: utf-8 -*-
"""
Comick.io CLI Uploader

This script provides a command-line interface to automate the process of uploading
manga chapters to Comick.io for users with upload permissions.

Author: darwin256
Profile: https://comick.io/user/b9b6d682-3757-4fd9-9cb6-8e271a727871
Version: 1.3.0

Features:
- Clean, dynamic CLI interface showing progress for multiple chapters at once.
- Bypasses Cloudflare's JavaScript and bot-detection challenges.
- Handles authentication via a `cookies.txt` file.
- Processes chapter folders with integer or decimal names (e.g., '1', '25.5').
- Auto-detects a "./chapters" folder as the default input directory.
- Supports various image formats, converting them to JPEG for upload.
- Interactive prompts for group selection (Official, Search, or Unknown) and language.
- Configurable parallelism for uploading multiple chapters simultaneously.
- Thread-safe progress feedback and logging.
"""

import cloudscraper
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse, quote
from PIL import Image
import io
import concurrent.futures
import requests
import threading

# --- Configuration ---
API_BASE_URL = "https://api.comick.io"
UPLOAD_API_BASE_URL = "https://upload.comick.io/v1.0"
COOKIES_FILE = "cookies.txt"
DEFAULT_CHAPTERS_DIR = "chapters"
SUPPORTED_EXTENSIONS = ['.jpeg', '.jpg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.heic']

LANGUAGES = {
    "en": "English", "fr": "French", "es-419": "Spanish (Latin American)", "pt-br": "Brazilian Portuguese",
    "pl": "Polish", "ru": "Russian", "ms": "Malay", "it": "Italian", "id": "Indonesian", "hi": "Hindi",
    "de": "German", "uk": "Ukrainian", "vi": "Vietnamese", "tl": "Filipino/Tagalog", "bn": "Bengali",
    "ar": "Arabic", "es": "Spanish (Castilian)", "tr": "Turkish"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:142.0) Gecko/20100101 Firefox/142.0",
    "Accept": "application/json, text/plain, */*", "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br, zstd", "Origin": "https://comick.io", "Referer": "https://comick.io/",
    "DNT": "1", "Sec-GPC": "1", "Sec-Fetch-Dest": "empty", "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site", "Connection": "keep-alive",
}

# --- UI and Threading Management ---
ui_lock = threading.Lock()
upload_status = {}  # Tracks the status of each chapter upload thread
log_messages = []   # Stores final messages to be printed below the dynamic UI

# --- Helper Functions ---

def clear_line():
    """Clears the current terminal line using ANSI escape codes."""
    sys.stdout.write("\033[K")

def move_cursor_up(lines):
    """Moves the terminal cursor up a specified number of lines."""
    sys.stdout.write(f"\033[{lines}A")

def render_ui():
    """Renders the dynamic progress UI. Must be called within a lock."""
    if len(upload_status) > 0:
        move_cursor_up(len(upload_status) + 1)
    clear_line()
    print("--- Upload Progress ---")
    sorted_chapters = sorted(upload_status.keys(), key=natural_sort_key)
    for chap_num in sorted_chapters:
        status_info = upload_status.get(chap_num, {"status": "Waiting...", "progress": 0})
        status_text, progress = status_info["status"], status_info["progress"]
        bar = f"[{'#' * int(progress * 20):<20}]"
        line = f"  Chapter {chap_num:<5}: {status_text:<25} {bar} {progress*100:3.0f}%"
        clear_line()
        print(line)
    sys.stdout.flush()

def update_status(chap_num, status, progress=None):
    """Thread-safe function to update a chapter's status and redraw the UI."""
    with ui_lock:
        if chap_num not in upload_status:
            upload_status[chap_num] = {}
        upload_status[chap_num]["status"] = status
        if progress is not None:
            upload_status[chap_num]["progress"] = progress
        render_ui()

def log_message(message):
    """Adds a persistent message to the log area below the dynamic UI."""
    with ui_lock:
        clear_line()
        print(message)
        log_messages.append(message)
        render_ui()

def natural_sort_key(s):
    """Creates a sort key for natural string sorting (e.g., "1", "2.5", "10")."""
    return [float(text) if re.match(r'^-?\d+(?:\.\d+)?$', text) else text.lower() for text in re.split(r'(-?\d+(?:\.\d+)?)', str(s))]

def load_cookies():
    """Loads cookies and initializes a `cloudscraper` session."""
    session = cloudscraper.create_scraper(browser={'browser': 'firefox', 'platform': 'windows', 'mobile': False})
    session.headers.update(HEADERS)
    if not os.path.exists(COOKIES_FILE):
        print(f"Error: '{COOKIES_FILE}' not found.")
        return None
    try:
        cookies_dict = {}
        with open(COOKIES_FILE, 'r', encoding='utf-8') as f:
            cookies_data = json.load(f)
        for cookie in cookies_data:
            cookies_dict[cookie['name']] = cookie['value']
        session.cookies.update(cookies_dict)
        print("✅ Cookies loaded successfully.")
        return session
    except Exception as e:
        print(f"❌ Error loading or parsing cookies: {e}")
        return None

def get_manga_slug():
    """Prompts for and extracts the manga slug from a URL."""
    while True:
        url = input("Enter the manga URL (e.g., https://comick.io/comic/official-test-manga): ")
        try:
            path_parts = urlparse(url).path.strip('/').split('/')
            if len(path_parts) >= 2 and path_parts[0] == 'comic':
                return path_parts[1]
            else:
                print("Invalid URL format.")
        except Exception as e:
            print(f"An error occurred: {e}")

def find_chapters(chapters_dir):
    """Scans for valid chapter folders and collects their image files."""
    if not os.path.isdir(chapters_dir):
        print(f"❌ Error: Directory '{chapters_dir}' not found.")
        return None
    chapters = {}
    chapter_pattern = re.compile(r'^\d+(\.\d+)?$')
    dir_entries = sorted(os.listdir(chapters_dir), key=natural_sort_key)
    for entry in dir_entries:
        chap_path = Path(chapters_dir) / entry
        if chap_path.is_dir() and chapter_pattern.match(entry):
            images = sorted(
                [f for f in chap_path.iterdir() if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS],
                key=lambda p: natural_sort_key(p.name)
            )
            if images:
                chapters[entry] = images
            else:
                print(f"⚠️ Warning: Chapter folder '{entry}' is empty. Skipping.")
    if not chapters:
        print(f"❌ No valid chapter folders found in '{chapters_dir}'.")
        return None
    return chapters

def select_group(session):
    """Handles interactive selection for Official, Searchable, or Unknown group."""
    print("\n--- Group Selection ---")
    while True:
        choice = input("Select upload type: [O]fficial, [S]earch for a group, [U]nknown/No group: ").lower()
        if choice == 'o': return {"is_official": True, "name": "Official"}
        if choice == 'u': return {"name": "Unknown/No Group"}
        if choice == 's': break
        else: print("Invalid choice.")
    while True:
        search_term = input("Search for a scanlation group (or 'exit'): ")
        if search_term.lower() == 'exit': return None
        try:
            response = session.get(f"{API_BASE_URL}/search/group?k={quote(search_term)}")
            response.raise_for_status()
            results = response.json()
            if not results:
                print("No groups found."); continue
            print("\nSearch Results:")
            for i, group in enumerate(results): print(f"  {i + 1}. {group['v']}")
            print("  0. Search again")
            while True:
                try:
                    selection = int(input("Select a group by number: "))
                    if 1 <= selection <= len(results):
                        selected_group = results[selection - 1]
                        return {"groups": [selected_group['k']], "name": selected_group['v']}
                    elif selection == 0: break
                    else: print("Invalid number.")
                except ValueError: print("Please enter a valid number.")
        except Exception as e:
            print(f"❌ API Error during group search: {e}"); return None

def select_language():
    """Displays language options and prompts the user for a selection."""
    print("\n--- Language Selection ---")
    for code, name in LANGUAGES.items(): print(f"  {name} → {code}")
    while True:
        lang_code = input("Enter the language code (default: en): ").lower()
        if not lang_code: return "en"
        if lang_code in LANGUAGES: return lang_code
        else: print(f"Invalid code '{lang_code}'.")

def upload_image_to_s3(args):
    """Worker function to process and upload a single image to S3."""
    image_path, s3_url, chap_num, total_images, progress_callback = args
    try:
        with Image.open(image_path) as img:
            if img.format.upper() == 'HEIC' and 'heif_image_plugin' not in globals():
                log_message(f"[{chap_num}] ERROR: HEIC file requires 'heif-image-plugin'.")
                return False
            if img.mode in ('RGBA', 'P', 'LA'): img = img.convert('RGB')
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=90)
            image_data = buffer.getvalue()
        s3_headers = {"Content-Type": "image/jpeg"}
        response = requests.put(s3_url, data=image_data, headers=s3_headers)
        response.raise_for_status()
        progress_callback()
        return True
    except Exception as e:
        log_message(f"[{chap_num}] ❌ Failed to upload {image_path.name}: {e}")
        return False

def upload_chapter(session, manga_slug, chap_num, image_paths, group_info, lang_code):
    """Orchestrates the upload for a single chapter with clean UI updates."""
    try:
        update_status(chap_num, "Requesting URLs...", 0.0)
        num_images = len(image_paths)
        payload = {"files": [f"{i+1:03d}.jpeg" for i in range(num_images)]}
        response = session.post(f"{API_BASE_URL}/presign", json=payload)
        response.raise_for_status()
        s3_urls = response.json()['urls']
        update_status(chap_num, "Uploading Pages...", 0.1)
        successful_uploads = 0
        upload_lock = threading.Lock()
        def progress_callback():
            nonlocal successful_uploads
            with upload_lock:
                successful_uploads += 1
                progress_percent = 0.1 + (successful_uploads / num_images) * 0.8
                update_status(chap_num, f"Uploading ({successful_uploads}/{num_images})", progress_percent)
        upload_tasks = [(path, url, chap_num, num_images, progress_callback) for path, url in zip(image_paths, s3_urls)]
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(upload_image_to_s3, upload_tasks))
        if not all(results):
            update_status(chap_num, "Failed (Page Upload)", 1.0)
            return chap_num, False
        update_status(chap_num, "Finalizing...", 0.95)
        final_payload = {"chap": chap_num, "lang": lang_code, "images": s3_urls}
        if "is_official" in group_info: final_payload["is_official"] = True
        elif "groups" in group_info: final_payload["groups"] = group_info["groups"]
        response = session.post(f"{UPLOAD_API_BASE_URL}/comic/{manga_slug}/add-chapter", json=final_payload)
        response.raise_for_status()
        update_status(chap_num, "✅ Done", 1.0)
        return chap_num, True
    except Exception as e:
        error_msg = str(e)
        if hasattr(e, 'response') and e.response: error_msg += f" | Response: {e.response.text[:100]}"
        update_status(chap_num, f"❌ Failed: {error_msg[:30]}...", 1.0)
        return chap_num, False

def get_thread_count():
    """Prompts user for the number of parallel chapter uploads."""
    while True:
        try:
            threads_str = input("Enter number of parallel chapter uploads (1-10, default: 3): ")
            if not threads_str: return 3
            threads = int(threads_str)
            if 1 <= threads <= 10: return threads
            else: print("Please enter a number between 1 and 10.")
        except ValueError: print("Invalid input.")

def main():
    """Main function to run the CLI uploader."""
    print("--- Comick.io Chapter Uploader ---")
    session = load_cookies()
    if not session: return

    manga_slug = get_manga_slug()
    
    while True:
        prompt = f"Enter path to parent folder for chapters"
        if os.path.isdir(DEFAULT_CHAPTERS_DIR):
            prompt += f" (default: ./{DEFAULT_CHAPTERS_DIR}): "
        else:
            prompt += ": "
        chapters_dir_input = input(prompt)
        chapters_dir = chapters_dir_input or DEFAULT_CHAPTERS_DIR if os.path.isdir(DEFAULT_CHAPTERS_DIR) else chapters_dir_input
        chapters_to_upload = find_chapters(chapters_dir)
        if chapters_to_upload: break
            
    print(f"\nFound {len(chapters_to_upload)} chapters to upload: {', '.join(chapters_to_upload.keys())}")
    
    group_info = select_group(session)
    if not group_info:
        print("No group selected. Exiting."); return

    lang_code = select_language()
    thread_count = get_thread_count()

    print("\n" + "="*25)
    print("   UPLOAD SUMMARY")
    print("="*25)
    print(f"Manga Slug:        {manga_slug}")
    print(f"Chapters Path:     {chapters_dir}")
    print(f"Chapters Found:    {len(chapters_to_upload)}")
    print(f"Upload As:         {group_info['name']}")
    print(f"Language:          {LANGUAGES[lang_code]} ({lang_code})")
    print(f"Parallel Uploads:  {thread_count}")
    print("="*25)
    
    confirm = input("\nReady to begin uploading? (y/n): ").lower()
    if confirm != 'y':
        print("Upload cancelled."); return
        
    for chap_num in chapters_to_upload:
        upload_status[chap_num] = {"status": "Queued", "progress": 0.0}
    
    print("\n" * (len(upload_status) + 1))
    
    with ui_lock: render_ui()

    total_chapters = len(chapters_to_upload)
    completed_count, failed_chapters = 0, []

    with concurrent.futures.ThreadPoolExecutor(max_workers=thread_count) as executor:
        futures = [executor.submit(upload_chapter, session, manga_slug, chap_num, paths, group_info, lang_code) 
                   for chap_num, paths in chapters_to_upload.items()]
        for future in concurrent.futures.as_completed(futures):
            chap_num, success = future.result()
            if success: completed_count += 1
            else: failed_chapters.append(chap_num)
    
    print("\n" * (len(upload_status) + 2))
    print("--- 🎉 All operations complete. ---")
    print(f"Successfully uploaded: {completed_count}/{total_chapters} chapters.")
    if failed_chapters:
        print(f"⚠️ Failed chapters: {', '.join(sorted(failed_chapters, key=natural_sort_key))}")

if __name__ == "__main__":
    try:
        import heif_image_plugin
    except ImportError:
        pass
    main()