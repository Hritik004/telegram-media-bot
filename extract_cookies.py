"""
Startup script: reads the YOUTUBE_COOKIES environment variable and writes
its contents to cookies.txt (Netscape/Mozilla format) so that yt-dlp can
use them for authenticated requests.

Run this before bot.py, e.g.:
    python extract_cookies.py && python bot.py
"""

import os
import sys

COOKIES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.txt")


def main():
    cookies_content = os.getenv("YOUTUBE_COOKIES", "").strip()

    if not cookies_content:
        print(
            "[extract_cookies] WARNING: YOUTUBE_COOKIES env var is not set or empty. "
            "Skipping cookies.txt creation — bot detection bypass may not work."
        )
        return

    with open(COOKIES_FILE, "w", encoding="utf-8") as f:
        f.write(cookies_content)
        if not cookies_content.endswith("\n"):
            f.write("\n")

    print(f"[extract_cookies] cookies.txt written to {COOKIES_FILE}")


if __name__ == "__main__":
    main()
