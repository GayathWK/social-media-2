#
# COSC2671 Social Media and Network Analytics
# YouTube API client.

import os
import sys
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

def youtubeClient():
    """
    Setup YouTube Data API v3 authentication.
    Loads API key from .env file (YOUTUBE_API_KEY).
    """
    try:
        apiKey = os.getenv("YOUTUBE_API_KEY")
        if not apiKey:
            raise ValueError("YOUTUBE_API_KEY not found. Add it to your .env file.")
        youtube = build("youtube", "v3", developerKey=apiKey)
    except Exception as e:
        sys.stderr.write("Failed to create YouTube client: {}\n".format(str(e)))
        sys.exit(1)
    return youtube