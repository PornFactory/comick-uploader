# -*- coding: utf-8 -*-
"""
Comick.io CLI Uploader

Author: darwin256
Profile: https://comick.io/user/b9b6d682-3757-4fd9-9cb6-8e271a727871
Version: 1.4.0

Features:
- Intelligently skips chapters that already exist on the site, preventing unnecessary retries.
- Colorized UI for better readability.
- Validates manga URL before proceeding with setup.
- Automatically retries uploads on temporary server errors (e.g., 500, 524).
- Generates a `failed.txt` file for chapters that fail after all retries.
- Parses chapter titles directly from folder names (e.g., "1 - The Beginning").
- Supports chapter folders with integer or decimal numbers.
- Auto-detects a "./chapters" folder as the default input directory.
- Interactive prompts for group, language, volume, and scheduled release timer.
- Configurable parallelism for uploading multiple chapters simultaneously.
- Pauses at the end of execution to allow users to read the final summary.
"""
import cloudscraper, json, os, re, sys, threading, time
from pathlib import Path
from urllib.parse import urlparse, quote
from PIL import Image
import io
import concurrent.futures
import requests
from colorama import init, Fore, Style

init(autoreset=True) # Initialize Colorama

# --- Configuration & Constants ---
API_BASE_URL = "https://api.comick.io"; UPLOAD_API_BASE_URL = "https://upload.comick.io/v1.0"
COOKIES_FILE = "cookies.txt"; DEFAULT_CHAPTERS_DIR = "chapters"
SUPPORTED_EXTENSIONS = ['.jpeg', '.jpg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.heic']
MAX_RETRIES = 3; RETRY_DELAY = 10 # seconds
RETRYABLE_STATUSES = [500, 502, 503, 504, 524]
LANGUAGES = {"en": "English", "fr": "French", "es-419": "Spanish (Latin American)", "pt-br": "Brazilian Portuguese","pl": "Polish", "ru": "Russian", "ms": "Malay", "it": "Italian", "id": "Indonesian", "hi": "Hindi","de": "German", "uk": "Ukrainian", "vi": "Vietnamese", "tl": "Filipino/Tagalog", "bn": "Bengali","ar": "Arabic", "es": "Spanish (Castilian)", "tr": "Turkish"}
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:142.0) Gecko/20100101 Firefox/142.0","Accept": "application/json, text/plain, */*","Accept-Language": "en-US,en;q=0.5","Accept-Encoding": "gzip, deflate, br, zstd","Origin": "https://comick.io","Referer": "https://comick.io/","DNT": "1","Sec-GPC": "1","Sec-Fetch-Dest": "empty","Sec-Fetch-Mode": "cors","Sec-Fetch-Site": "same-site","Connection": "keep-alive"}

class Colors:
    GREEN = Fore.GREEN; RED = Fore.RED; YELLOW = Fore.YELLOW; CYAN = Fore.CYAN; RESET = Style.RESET_ALL

# --- Robust Paginated UI Renderer Class ---
class UIRenderer:
    def __init__(self, chapter_keys):
        self.lock = threading.Lock()
        self.sorted_keys = chapter_keys
        self.total_chapters = len(chapter_keys)
        self.completed_chapters = 0
        self.status = {key: {"status": "Queued", "progress": 0.0} for key in chapter_keys}
        self.height = 0; self.page_size = 25; self.view_start_index = 0

    def _render(self):
        if self.height > 0: sys.stdout.write(f"\033[{self.height}A")
        overall_progress = self.completed_chapters / self.total_chapters if self.total_chapters > 0 else 0
        overall_bar = f"[{'#' * int(overall_progress * 40):<40}]"
        sys.stdout.write(f"{Colors.CYAN}--- Uploading ({self.completed_chapters}/{self.total_chapters}) {overall_bar} {overall_progress*100:3.0f}% ---\033[K\n")
        end_index = min(self.view_start_index + self.page_size, self.total_chapters)
        chapters_to_display = self.sorted_keys[self.view_start_index:end_index]
        for key in chapters_to_display:
            info = self.status[key]; status_text, progress = info["status"], info["progress"]
            bar_color = Colors.GREEN if progress == 1.0 and ("✅" in status_text or "Skipped" in status_text) else (Colors.RED if "❌" in status_text else Colors.YELLOW)
            bar = f"[{bar_color}{'#' * int(progress * 20):<20}{Colors.RESET}]"
            status_color = Colors.GREEN if "✅" in status_text or "Skipped" in status_text else (Colors.RED if "❌" in status_text else "")
            line = f"  {key:<20.20}: {status_color}{status_text:<25.25}{Colors.RESET} {bar} {progress*100:3.0f}%"
            sys.stdout.write(f"{line}\033[K\n")
        self.height = 1 + len(chapters_to_display); sys.stdout.flush()

    def update_chapter_status(self, chap_key, status, progress=None):
        with self.lock:
            if chap_key not in self.status: self.status[chap_key] = {}
            self.status[chap_key]["status"] = status
            if progress is not None: self.status[chap_key]["progress"] = progress
            if self.status[chap_key]["progress"] == 1.0:
                self.completed_chapters += 1
                self._check_and_scroll_view()
            self._render()

    def _check_and_scroll_view(self):
        end_index = min(self.view_start_index + self.page_size, self.total_chapters)
        visible_keys = self.sorted_keys[self.view_start_index:end_index]
        if all(self.status[key]["progress"] == 1.0 for key in visible_keys):
            next_incomplete_index = next((i for i, k in enumerate(self.sorted_keys) if self.status[k]["progress"] < 1.0), -1)
            if next_incomplete_index != -1: self.view_start_index = next_incomplete_index
            else: self.view_start_index = max(0, self.total_chapters - self.page_size)

    def start(self):
        self.height = 1 + min(self.total_chapters, self.page_size); sys.stdout.write("\n" * self.height)
        with self.lock: self._render()

# --- Helper Functions ---
def natural_sort_key(s): return [float(text) if re.match(r'^-?\d+(?:\.\d+)?$', text) else text.lower() for text in re.split(r'(-?\d+(?:\.\d+)?)', str(s))]
def load_cookies():
    session = cloudscraper.create_scraper(browser={'browser': 'firefox', 'platform': 'windows', 'mobile': False}); session.headers.update(HEADERS)
    if not os.path.exists(COOKIES_FILE): print(f"{Colors.RED}Error: '{COOKIES_FILE}' not found."); return None
    try:
        cookies_dict = {};
        with open(COOKIES_FILE, 'r', encoding='utf-8') as f: cookies_data = json.load(f)
        for cookie in cookies_data: cookies_dict[cookie['name']] = cookie['value']
        session.cookies.update(cookies_dict); print(f"{Colors.GREEN}✅ Cookies loaded successfully."); return session
    except Exception as e: print(f"{Colors.RED}❌ Error loading cookies: {e}"); return None
def get_manga_slug(session):
    while True:
        url = input(f"{Colors.CYAN}Enter the manga URL: {Colors.RESET}")
        try:
            path_parts = urlparse(url).path.strip('/').split('/')
            if len(path_parts) >= 2 and path_parts[0] == 'comic':
                slug = path_parts[1]
                print(f"Validating manga '{slug}'...")
                response = session.get(f"{API_BASE_URL}/comic/{slug}")
                if response.status_code == 200:
                    print(f"{Colors.GREEN}✅ Manga found!{Colors.RESET}"); return slug
                elif response.status_code == 404:
                    print(f"{Colors.RED}❌ Manga not found. Please check the URL and try again.{Colors.RESET}")
                else:
                    print(f"{Colors.RED}❌ API Error ({response.status_code}). Could not validate manga.{Colors.RESET}")
            else:
                print(f"{Colors.RED}Invalid URL format. Please use the format: https://comick.io/comic/your-manga-slug{Colors.RESET}")
        except requests.RequestException as e:
            print(f"{Colors.RED}A network error occurred: {e}{Colors.RESET}")
def find_chapters(chapters_dir):
    if not os.path.isdir(chapters_dir): print(f"{Colors.RED}❌ Error: Directory '{chapters_dir}' not found."); return None
    chapters, chapter_pattern = {}, re.compile(r'^\d+(\.\d+)?(\s*-\s*(.+))?$')
    dir_entries = sorted(os.listdir(chapters_dir), key=natural_sort_key)
    for entry in dir_entries:
        chap_path = Path(chapters_dir) / entry; match = chapter_pattern.match(entry)
        if chap_path.is_dir() and match:
            chapter_number = match.group(0).split(' - ')[0]; title = match.group(3).strip() if match.group(3) else None
            images = sorted([f for f in chap_path.iterdir() if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS], key=lambda p: natural_sort_key(p.name))
            if images: chapters[entry] = {"number": chapter_number, "title": title, "image_paths": images}
            else: print(f"{Colors.YELLOW}⚠️ Warning: Chapter folder '{entry}' is empty. Skipping.")
    if not chapters: print(f"{Colors.RED}❌ No valid chapter folders found in '{chapters_dir}'."); return None
    return chapters
def select_group(session):
    print(f"\n{Colors.CYAN}--- Group Selection ---");
    while True:
        choice = input("Select upload type: [O]fficial, [S]earch for a group, [U]nknown/No group: ").lower()
        if choice == 'o': return {"is_official": True, "name": "Official"}
        if choice == 'u': return {"name": "Unknown/No Group"}
        if choice == 's': break
        else: print(f"{Colors.RED}Invalid choice.")
    while True:
        search_term = input("Search for a scanlation group (or 'exit'): ")
        if search_term.lower() == 'exit': return None
        try:
            response = session.get(f"{API_BASE_URL}/search/group?k={quote(search_term)}")
            response.raise_for_status(); results = response.json()
            if not results: print(f"{Colors.YELLOW}No groups found."); continue
            print("\nSearch Results:"); [print(f"  {i + 1}. {g['v']}") for i, g in enumerate(results)]; print("  0. Search again")
            while True:
                try:
                    selection = int(input("Select a group by number: "))
                    if 1 <= selection <= len(results): return {"groups": [results[selection - 1]['k']], "name": results[selection - 1]['v']}
                    elif selection == 0: break
                    else: print(f"{Colors.RED}Invalid number.")
                except ValueError: print(f"{Colors.RED}Please enter a valid number.")
        except Exception as e: print(f"{Colors.RED}❌ API Error: {e}"); return None
def select_language():
    print(f"\n{Colors.CYAN}--- Language Selection ---"); [print(f"  {name} → {code}") for code, name in LANGUAGES.items()]
    while True:
        lang_code = input("Enter the language code (default: en): ").lower();
        if not lang_code: return "en"
        if lang_code in LANGUAGES: return lang_code
        else: print(f"{Colors.RED}Invalid code '{lang_code}'.")
def select_volume():
    print(f"\n{Colors.CYAN}--- Volume Selection ---")
    while True:
        vol_str = input("Enter volume number for this batch (optional, press Enter to skip): ")
        if not vol_str: return None
        if vol_str.isdigit() and int(vol_str) > 0: return vol_str
        else: print(f"{Colors.RED}Invalid input. Please enter a positive whole number.")
def select_timer():
    print(f"\n{Colors.CYAN}--- Release Timer ---")
    while True:
        try:
            timer_str = input("Set release delay in hours (0-4, default: 0 for instant release): ")
            if not timer_str: return 0
            timer = int(timer_str)
            if 0 <= timer <= 4: return timer
            else: print(f"{Colors.RED}Please enter a number between 0 and 4.")
        except ValueError: print(f"{Colors.RED}Invalid input.")
def upload_image_to_s3(args):
    image_path, s3_url, chap_key, progress_callback = args
    try:
        with Image.open(image_path) as img:
            if img.format.upper() == 'HEIC' and 'heif_image_plugin' not in globals(): return False, "HEIC plugin not installed"
            if img.mode in ('RGBA', 'P', 'LA'): img = img.convert('RGB')
            buffer = io.BytesIO(); img.save(buffer, format='JPEG', quality=90)
            s3_headers = {"Content-Type": "image/jpeg"}
            response = requests.put(s3_url, data=buffer.getvalue(), headers=s3_headers)
            response.raise_for_status(); progress_callback(); return True, ""
    except Exception as e: return False, str(e)
def upload_chapter(session, ui_renderer, manga_slug, chap_key, chapter_info, group_info, lang_code, timer, volume):
    for attempt in range(MAX_RETRIES):
        try:
            status_prefix = f"Retrying ({attempt+1}/{MAX_RETRIES})... " if attempt > 0 else ""
            ui_renderer.update_chapter_status(chap_key, f"{status_prefix}Requesting URLs...", 0.0)
            num_images = len(chapter_info["image_paths"]); payload = {"files": [f"{i+1:03d}.jpeg" for i in range(num_images)]}
            response = session.post(f"{API_BASE_URL}/presign", json=payload)
            response.raise_for_status(); s3_urls = response.json()['urls']
            
            successful_uploads = 0; upload_lock = threading.Lock()
            def progress_callback():
                nonlocal successful_uploads
                with upload_lock:
                    successful_uploads += 1; progress_percent = 0.1 + (successful_uploads / num_images) * 0.8
                    ui_renderer.update_chapter_status(chap_key, f"{status_prefix}Uploading ({successful_uploads}/{num_images})", progress_percent)
            
            upload_tasks = [(path, url, chap_key, progress_callback) for path, url in zip(chapter_info["image_paths"], s3_urls)]
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                results = list(executor.map(upload_image_to_s3, upload_tasks))
            
            if not all(res[0] for res in results):
                first_error = next((res[1] for res in results if not res[0]), "Page upload failed")
                return {"key": chap_key, "success": False, "error": first_error}

            ui_renderer.update_chapter_status(chap_key, f"{status_prefix}Finalizing...", 0.95)
            final_payload = {"chap": chapter_info["number"], "lang": lang_code, "images": s3_urls}
            if chapter_info["title"]: final_payload["title"] = chapter_info["title"]
            if volume: final_payload["vol"] = volume
            if "is_official" in group_info: final_payload["is_official"] = True
            elif "groups" in group_info: final_payload["groups"] = group_info["groups"]
            if timer > 0: final_payload["timer"] = str(timer)
            response = session.post(f"{UPLOAD_API_BASE_URL}/comic/{manga_slug}/add-chapter", json=final_payload)
            response.raise_for_status()
            return {"key": chap_key, "success": True, "response": response.json()}

        except requests.exceptions.HTTPError as e:
            error_json = {}
            try: error_json = e.response.json()
            except json.JSONDecodeError: pass
            
            if "Chapter already exists" in error_json.get("message", ""):
                return {"key": chap_key, "success": True, "skipped": True}

            if e.response.status_code in RETRYABLE_STATUSES and attempt < MAX_RETRIES - 1:
                ui_renderer.update_chapter_status(chap_key, f"Server Error ({e.response.status_code})... Retrying", 0)
                time.sleep(RETRY_DELAY)
                continue
            else:
                error_msg = f"{e.response.status_code} {e.response.reason}"
                return {"key": chap_key, "success": False, "error": error_msg}
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                ui_renderer.update_chapter_status(chap_key, f"Network Error... Retrying", 0)
                time.sleep(RETRY_DELAY)
                continue
            else:
                return {"key": chap_key, "success": False, "error": str(e)[:40]}
    
    return {"key": chap_key, "success": False, "error": "Max retries exceeded"}
def get_thread_count():
    while True:
        try:
            threads_str = input("Enter number of parallel chapter uploads (1-10, default: 3): ")
            if not threads_str: return 3
            threads = int(threads_str)
            if 1 <= threads <= 10: return threads
            else: print(f"{Colors.RED}Please enter a number between 1 and 10.")
        except ValueError: print(f"{Colors.RED}Invalid input.")

def main():
    print(f"{Colors.CYAN}--- Comick.io Chapter Uploader ---{Colors.RESET}")
    session = load_cookies()
    if not session: input(f"\n{Colors.YELLOW}Press Enter to exit...{Colors.RESET}"); return
    
    manga_slug = get_manga_slug(session)

    while True:
        prompt = f"Enter path to parent folder for chapters"
        if os.path.isdir(DEFAULT_CHAPTERS_DIR): prompt += f" (default: ./{DEFAULT_CHAPTERS_DIR}): "
        else: prompt += ": "
        chapters_dir_input = input(prompt)
        chapters_dir = chapters_dir_input or DEFAULT_CHAPTERS_DIR if os.path.isdir(DEFAULT_CHAPTERS_DIR) else chapters_dir_input
        chapters_to_upload = find_chapters(chapters_dir)
        if chapters_to_upload: break
    print(f"\nFound {len(chapters_to_upload)} chapters to upload:")
    for name, data in chapters_to_upload.items():
        title_str = f" - {data['title']}" if data['title'] else ""
        print(f"  - Chapter {data['number']}{title_str}")
    
    volume_number = select_volume(); group_info = select_group(session)
    if not group_info: print("No group selected. Exiting."); return
    lang_code = select_language(); timer_delay = select_timer(); thread_count = get_thread_count()
    
    volume_text = volume_number if volume_number else "Not Specified"
    timer_text = f"{timer_delay} hour(s)" if timer_delay > 0 else "Instant"
    
    print(f"\n{Colors.CYAN}" + "="*25); print("   UPLOAD SUMMARY"); print("="*25)
    print(f"Manga Slug:        {manga_slug}\nChapters Path:     {chapters_dir}\nChapters Found:    {len(chapters_to_upload)}\nVolume:            {volume_text}\nUpload As:         {group_info['name']}\nLanguage:          {LANGUAGES[lang_code]} ({lang_code})\nRelease Timer:     {timer_text}\nParallel Uploads:  {thread_count}")
    print("="*25 + Style.RESET_ALL)
    if input(f"\n{Colors.YELLOW}Ready to begin uploading? (y/n): {Style.RESET_ALL}").lower() != 'y': print("Upload cancelled."); return
    
    sorted_keys = sorted(chapters_to_upload.keys(), key=natural_sort_key)
    renderer = UIRenderer(sorted_keys)
    renderer.start()
    
    failed_chapters = []; skipped_chapters = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=thread_count) as executor:
        futures = [executor.submit(upload_chapter, session, renderer, manga_slug, chap_key, chap_data, group_info, lang_code, timer_delay, volume_number) 
                   for chap_key, chap_data in chapters_to_upload.items()]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            
            if result.get("skipped", False):
                final_status = "✅ Skipped (Exists)"
                skipped_chapters.append(result['key'])
            elif result['success']:
                final_status = "✅ Done"
            else:
                final_status = f"❌ Failed: {result['error']}"
                failed_chapters.append(result['key'])
            
            renderer.update_chapter_status(result['key'], final_status, 1.0)
    
    sys.stdout.write("\n" * (renderer.height + 1))
    print(f"{Colors.CYAN}--- 🎉 All operations complete. ---{Colors.RESET}")
    
    if skipped_chapters:
        print(f"{Colors.YELLOW}🟡 {len(skipped_chapters)} chapters were skipped because they already exist on the site.")

    if failed_chapters:
        print(f"{Colors.RED}⚠️ {len(failed_chapters)} chapters failed to upload after all retries.")
        try:
            with open("failed.txt", "w", encoding="utf-8") as f:
                for chapter_key in sorted(failed_chapters, key=natural_sort_key):
                    f.write(f"{chapter_key}\n")
            print(f"A list of failed chapters has been saved to {Colors.CYAN}`failed.txt`{Colors.RESET}.")
        except Exception as e:
            print(f"{Colors.RED}Could not write to `failed.txt`: {e}")
    
    if not failed_chapters and len(chapters_to_upload) > 0:
        print(f"{Colors.GREEN}✅ All chapters were processed successfully!")

    input(f"\n{Colors.YELLOW}Press Enter to exit...{Colors.RESET}")

if __name__ == "__main__":
    try: import heif_image_plugin
    except ImportError: pass
    main()
