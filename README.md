# Comick.io CLI Uploader

[![License: MIT](https://img.shields.io/github/license/PornFactory/comick-uploader)](https://github.com/PornFactory/comick-uploader/blob/main/LICENSE)
[![Last Commit](https://img.shields.io/github/last-commit/PornFactory/comick-uploader)](https://github.com/PornFactory/comick-uploader/commits/main)
[![Repo Size](https://img.shields.io/github/repo-size/PornFactory/comick-uploader)](https://github.com/PornFactory/comick-uploader)

---

A powerful Python CLI tool for batch-uploading manga chapters to Comick.io, featuring a dynamic UI and robust Cloudflare bypass.

---

## 🎥 Demonstration

![Script Demonstration GIF](https://raw.githubusercontent.com/PornFactory/comick-uploader/refs/heads/main/videos/script.gif)

## ✨ Features

-   **Clean & Dynamic UI**: A modern, in-place updating interface shows the real-time progress of multiple chapter uploads.
-   **Cloudflare Bypass**: Seamlessly handles Cloudflare's JavaScript challenges and bot checks using `cloudscraper`.
-   **Flexible Chapter Numbering**: Supports chapter folders named with integers (`21`) or decimals (`21.5`).
-   **Convenient Default Directory**: Automatically detects and suggests a `./chapters` folder for quick use.
-   **Multi-Language Support**: Allows you to select the chapter's language from a comprehensive list.
-   **Versatile Group Selection**: Choose to upload as an "Official" release, search for a specific scanlation group, or upload with no group ("Unknown").
-   **High Performance**: Uploads multiple chapters and their pages concurrently to maximize speed.
-   **Secure Authentication**: Uses a local `cookies.txt` file, keeping your login credentials off the script.

## 📋 Requirements

-   Python 3.7+
-   `pip` (Python package installer)

## ⚙️ Installation Guide

Follow these steps to get the uploader running on your system.

### 1. Clone the Repository

First, clone this repository to your local machine.

```bash
git clone https://github.com/PornFactory/comick-uploader.git
cd comick-uploader
```

### 2. Set Up a Virtual Environment (Recommended)

This isolates the script's dependencies and avoids conflicts with other Python projects.

```bash
# Create a virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

With your virtual environment active, install the required libraries from `requirements.txt`.

```bash
pip install -r requirements.txt
```

## 🛠️ Configuration

Before running the script, you must configure your authentication and chapter folders.

### 1. Create `cookies.txt`

This file is essential for authenticating your requests.

1.  **Install a Cookie Editor Extension**: Get **Cookie-Editor** for [Chrome](https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm) or [Firefox](https://addons.mozilla.org/en-US/firefox/addon/cookie-editor/).
2.  **Log in to Comick.io**.
3.  **Export Cookies**:
    - Click the Cookie-Editor extension icon.
    - Click the **Export** button.
    - Choose **JSON** as the export format and **Copy to Clipboard**.
4.  **Create the File**: Create `cookies.txt` in the script's folder and paste the copied JSON content into it.

> **Important**: If you encounter `403 Forbidden` errors, your Cloudflare cookie has likely expired. **Re-export your cookies** to fix this.

### 2. Organize Chapter Folders

The script expects a specific folder structure for your chapters.

-   Each sub-folder **must be named with the chapter number** (e.g., `21`, `22.5`).
-   Inside each folder, image files should be numbered in reading order (e.g., `01.png`, `02.png`).

The easiest way to get started is to create a folder named `chapters` in the root of the project directory.

**Default Structure:**
```
/comick-uploader/
├── uploader.py
├── requirements.txt
├── cookies.txt
└── chapters/       <-- Default folder
    ├── 21/
    │   ├── 01.png
    │   └── ...
    └── 22.5/
        ├── 001.webp
        └── ...
```

## 🚀 How to Run

1.  Activate your virtual environment (if you created one).
2.  Run the script from your terminal:
    ```bash
    python uploader.py
    ```
3.  Follow the interactive prompts:
    -   **Manga URL**: Paste the URL of the manga series on Comick.io.
    -   **Chapters Folder Path**: Press **Enter** to use the default `./chapters` folder, or provide a custom path.
    -   **Group Selection**: Choose `o` for Official, `s` to Search, or `u` for Unknown.
    -   **Language Selection**: Enter the language code or press **Enter** for English (`en`).
    -   **Parallel Uploads**: Choose how many chapters to upload at once (1-10) or press **Enter** for the default (3).
        > **Disclaimer**: Setting this value too high may cause the server to reject requests (`500 Server Error`). The default of 3 is recommended for stability. If you encounter errors, try a lower number.
    -   **Confirmation**: Review the summary and press `y` to begin.

A dynamic progress display will appear, showing the live status of your uploads.

## 🔍 Troubleshooting

-   **`Failed: 500 Server Error`**: The server rejected the request, likely due to a high volume of concurrent uploads. **Solution**: Rerun the script with a lower number of parallel uploads (e.g., the default of 3).
-   **`403 Forbidden` Error**: Your Cloudflare cookie is invalid. **Solution**: Refresh comick.io in your browser and re-export your cookies into `cookies.txt`.
-   **`ModuleNotFoundError`**: Dependencies are not installed. **Solution**: Activate your virtual environment and run `pip install -r requirements.txt`.
-   **`FileNotFoundError: 'cookies.txt'`**: **Solution**: Ensure `cookies.txt` is in the same directory as `uploader.py`.
-   **UI Looks Garbled**: If the progress bar looks messy (e.g., you see `[K` or `[3A`), your terminal does not support ANSI escape codes. **Solution**: Use a modern terminal like Windows Terminal, PowerShell, or most terminals on macOS and Linux.

## ✍️ Author

This script was created by **[darwin256](https://comick.io/user/b9b6d682-3757-4fd9-9cb6-8e271a727871)**.

## 📄 License

This project is licensed under the MIT License - see the `LICENSE` file for details.
