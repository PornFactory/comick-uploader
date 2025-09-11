# Comick.io CLI Uploader

[![License: MIT](https://img.shields.io/github/license/darwin-256/comick-uploader)](https://github.com/darwin-256/comick-uploader/blob/main/LICENSE)
[![GitHub release (latest by date)](https://img.shields.io/github/v/release/darwin-256/comick-uploader)](https://github.com/darwin-256/comick-uploader/releases/latest)
[![Last Commit](https://img.shields.io/github/last-commit/darwin-256/comick-uploader)](https://github.com/darwin-256/comick-uploader/commits/main)

---

A powerful Python CLI tool for batch-uploading manga chapters to Comick.io, featuring a dynamic UI and robust Cloudflare bypass.

---

## 🎥 Demonstration



https://github.com/user-attachments/assets/9c8769e9-289f-48c4-9945-636d2e70c17f



## ✨ Features

-   **Standalone Executable**: Easy-to-use `.exe` for Windows users—no Python installation required!
-   **Robust & Clean UI**: A modern, flicker-free interface shows real-time progress, even for very large batches.
-   **Intelligent Error Handling**:
    -   **Automatic Retries**: Automatically retries uploads on temporary server errors (`500`, `524`, etc.).
    -   **Smart Duplicate Skipping**: Intelligently detects and skips chapters that already exist on the site.
    -   **Failure Reporting**: Generates a `failed.txt` file listing any chapters that failed after all retries.
-   **Cloudflare Bypass**: Seamlessly handles JavaScript challenges and bot checks.
-   **Automatic Title Parsing**: Detects and applies chapter titles from folder names (e.g., `21.5 - The Next Step`).
-   **Flexible Configuration**: Supports decimal chapter numbers, volume tagging, multiple languages, and group selection.
-   **High Performance**: Uploads multiple chapters and pages concurrently to maximize speed.
-   **Secure Authentication**: Uses a local `cookies.txt` file, keeping your login credentials private.

## ⚙️ Installation & Setup

Choose the guide that matches your needs.

### Guide A: For Windows Users (Easy Method)

This is the recommended method for most users on Windows. No Python is required.

1.  **Download the latest release:**
    > **[Download the latest `comick-uploader-windows.zip`](https://github.com/darwin-256/comick-uploader/releases/latest)**

2.  **Extract the `.zip` file** to a location of your choice. This folder contains `uploader.exe` and other necessary files.

3.  **Configure `cookies.txt`**:
    -   Follow the instructions in the **[Configuration Details](#-configuration-details)** section below to add your cookies to this file.

4.  **Add Your Chapters**: Place your chapter folders inside the included `chapters` directory.

5.  **Run the Uploader**: 
    -   Double-click `uploader.exe` to start the program.
    -   When the script is finished, the window will pause. Simply **press Enter** to close it.

---

### Guide B: For Developers & Other OS (Python Required)

This method is for users on macOS/Linux or those who want to run the script from the source code.

1.  **Requirements**: Ensure you have Python 3.7+ and Git installed.

2.  **Clone the Repository**:
    ```bash
    git clone https://github.com/darwin-256/comick-uploader.git
    cd comick-uploader
    ```

3.  **Set Up Virtual Environment & Dependencies**:
    ```bash
    # Create and activate a virtual environment
    python -m venv venv
    # On Windows: venv\Scripts\activate
    # On macOS/Linux: source venv/bin/activate

    # Install required packages (including colorama)
    pip install -r requirements.txt
    ```

4.  **Configure `cookies.txt`**:
    -   Follow the instructions in the **[Configuration Details](#-configuration-details)** section below to add your cookies.

5.  **Run the Script**:
    ```bash
    python uploader.py
    ```

## 🛠️ Configuration Details

### 1. How to Get Your Cookies

This file is essential for authenticating your requests.

1.  **Install a Cookie Editor Extension**: Get **Cookie-Editor** for [Chrome](https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm) or [Firefox](https://addons.mozilla.org/en-US/firefox/addon/cookie-editor/).
2.  **Log in to Comick.io**.
3.  **Export Cookies**:
    - Click the Cookie-Editor extension icon.
    - Click the **Export** button.
    - Choose **JSON** as the export format and **Copy to Clipboard**.
4.  **Paste into `cookies.txt`**: Open your `cookies.txt` file and replace its contents with the JSON you copied.

> **Important**: If you encounter `403 Forbidden` errors, your Cloudflare cookie has likely expired. **Re-export your cookies** to fix this.

### 2. How to Organize Chapter Folders

The script reads the chapter number **and title** directly from the folder names. Name your folders using one of the following formats:

-   `ChapterNumber` (for chapters without a title)
-   `ChapterNumber - Chapter Title` (for chapters with a title)

The script will automatically parse the number and the title after the ` - `.

**Example Structure:**
```
/comick-uploader/
└── chapters/
    ├── 21/                  <-- Will be uploaded as Chapter 21
    ├── 21.5/                <-- Will be uploaded as Chapter 21.5
    ├── 22 - The Awakening   <-- Will be uploaded as Chapter 22 with the title "The Awakening"
    └── 23 - New Beginnings  <-- Will be uploaded as Chapter 23 with the title "New Beginnings"

```


## 🚀 How to Use

After launching the program (`uploader.exe` or `python uploader.py`), follow the interactive prompts:

-   **Manga URL**: Paste the URL of the manga series on Comick.io. The script will validate it.
-   **Chapters Folder Path**: Press **Enter** to use the default `./chapters` folder, or provide a custom path.
-   **Volume Number**: Enter a volume number for the batch or press **Enter** to skip.
-   **Group Selection**: Choose `o` for Official, `s` to Search, or `u` for Unknown.
-   **Language Selection**: Enter the language code or press **Enter** for English (`en`).
-   **Release Timer**: Set a release delay from 0 to 4 hours. Press **Enter** for an instant release.
-   **Parallel Uploads**: Choose how many chapters to upload at once (1-10) or press **Enter** for the default (3).
    > **Disclaimer**: Setting this value too high may cause the server to reject requests. The default of 3 is recommended for stability.
-   **Confirmation**: Review the summary and press `y` to begin.

## 🔍 Troubleshooting

-   **`Failed: 5xx Server Error`**: The script automatically retries these errors. If a chapter still fails, it may be a persistent server-side issue. The failed chapter will be logged in `failed.txt`.
-   **`403 Forbidden` / `401 Unauthorized`**: Your cookies are invalid or expired. **Solution**: Refresh comick.io in your browser and re-export your cookies into `cookies.txt`.
-   **`Manga not found`**: The URL you entered is incorrect or the manga does not exist. **Solution**: Double-check the manga slug in your URL.
-   **`ModuleNotFoundError`** (Python users): Dependencies are not installed. **Solution**: Activate your virtual environment and run `pip install -r requirements.txt`.
-   **UI Looks Garbled**: If the progress bar looks messy (e.g., you see `[K` or `[3A`), your terminal does not support ANSI escape codes. **Solution**: Use a modern terminal like Windows Terminal, PowerShell, or most terminals on macOS and Linux.

## ✍️ Author

This script was created by **[darwin256](https://comick.io/user/b9b6d682-3757-4fd9-9cb6-8e271a727871)**.

## 📄 License

This project is licensed under the MIT License - see the `LICENSE` file for details.
