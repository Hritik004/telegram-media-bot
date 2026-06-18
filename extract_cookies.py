"""
Cookie bootstrap script.

Reads the YOUTUBE_COOKIES environment variable (Netscape cookie file format)
and writes it to cookies.txt so yt-dlp can authenticate with YouTube.

If the env var is not set the existing cookies.txt (baked into the image at
build time) is left untouched.  If neither exists the bot will still attempt
downloads but may be blocked by YouTube's bot-detection.

Usage (called automatically by the Dockerfile CMD before bot.py):
    python extract_cookies.py
"""

import os
import sys

COOKIES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.txt")


def main() -> None:
    cookie_data = os.getenv("YOUTUBE_COOKIES", "").strip()

    if not cookie_data:
        if os.path.exists(COOKIES_FILE):
            print("[cookies] YOUTUBE_COOKIES not set — using baked-in cookies.txt")
        else:
            print(
                "[cookies] WARNING: YOUTUBE_COOKIES not set and no cookies.txt found. "
                "YouTube downloads may fail due to bot detection."
            )
        return

    with open(COOKIES_FILE, "w", encoding="utf-8") as fh:
        # Ensure the file starts with the required Netscape header
        if not cookie_data.startswith("# Netscape HTTP Cookie File"):
            fh.write("# Netscape HTTP Cookie File\n")
        fh.write(cookie_data)
        if not cookie_data.endswith("\n"):
            fh.write("\n")

    print(f"[cookies] cookies.txt written from YOUTUBE_COOKIES env var ({len(cookie_data)} bytes)")


if __name__ == "__main__":
    main()
