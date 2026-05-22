#
# COSC2671 Social Media and Network Analytics
# YouTube API client.

import os
import sys

from googleapiclient.discovery import build

try:
    from .youtube_credentials import YOUTUBE_API_KEY as FILE_YOUTUBE_API_KEY
except ImportError:
    FILE_YOUTUBE_API_KEY = ""


def youtubeClient():
    """
    Setup YouTube Data API v3 authentication.

    To obtain an API key:
    1. Go to https://console.cloud.google.com/
    2. Create a project or select an existing project.
    3. Enable "YouTube Data API v3".
    4. Go to Credentials -> Create Credentials -> API Key.

    @returns: YouTube API service object
    """

    try:
        apiKey = os.getenv("YOUTUBE_API_KEY") or FILE_YOUTUBE_API_KEY

        if not apiKey:
            raise ValueError("Missing YouTube API key")

        youtube = build("youtube", "v3", developerKey=apiKey)
    except Exception as e:
        sys.stderr.write("Failed to create YouTube client: {}\n".format(str(e)))
        sys.exit(1)

    return youtube
