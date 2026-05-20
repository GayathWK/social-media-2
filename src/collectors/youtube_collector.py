"""
youtube_collector.py
--------------------
Collects YouTube comments from videos about AI coding assistants.

Data collected per video:
  - Video metadata (title, channel, view count, publish date, description)

Data collected per comment thread:
  - Top-level comment (author, text, likes, published date, reply count)
  - All replies (author, text, likes, published date, parent comment id)

Network structure captured:
  - author -> parentAuthor (reply relationship, directed edge)
  - author -> videoId (commenter participation, bipartite)

Output saved to: data/raw/youtube/
  - videos_metadata.json        — one entry per video
  - comments_raw.json           — all top-level comments + replies, flat list
  - reply_edges.json            — directed edges for network construction

Usage:
  python src/collectors/youtube_collector.py
  or run via notebooks/01_youtube_collection.ipynb
"""

import os
import json
import time
import logging
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)

# Target videos
# These are well-known, high-comment videos covering the tools in our study.
# Add or remove video IDs here. Get IDs from the URL: youtube.com/watch?v=VIDEO_ID
TARGET_VIDEOS = [
    # GitHub Copilot reviews / debates
    {"id": "Fi3AJZZregI", "tool": "copilot",    "label": "GitHub Copilot Full Review"},
    {"id": "4RfD5qu0KSQ", "tool": "copilot",    "label": "Copilot vs Manual Coding"},
    {"id": "Rj443bFSGy8", "tool": "copilot",    "label": "Is GitHub Copilot Worth It?"},

    # Cursor AI
    {"id": "oXeVH_X8hSg", "tool": "cursor",     "label": "Cursor AI Review 2024"},
    {"id": "1CC88QGQiEA", "tool": "cursor",     "label": "Cursor vs Copilot"},

    # Claude Code / Anthropic
    {"id": "7K0OABcHJnY", "tool": "claude",     "label": "Claude Code Full Demo"},

    # Vibe coding / AI agents
    {"id": "u1PNFOaFtCM", "tool": "general",    "label": "Vibe Coding Explained"},
    {"id": "Tw18-4U7mts", "tool": "general",    "label": "AI Coding Tools Compared"},

    # Sceptical / critical perspectives (important for trust/distrust balance)
    {"id": "tNmgmwEo33Y", "tool": "general",    "label": "Why I Stopped Using AI Coding Tools"},
    {"id": "s7KO3NbRYPY", "tool": "general",    "label": "AI Code Is a Liability"},
]


# Quota tracking
# commentThreads.list = 1 unit per page (100 comments)
# comments.list (replies) = 1 unit per page (100 replies)
# Default daily quota = 10,000 units
# We track and stop safely before hitting the limit.
QUOTA_LIMIT = 9500          # Leave 500 unit buffer
MAX_COMMENTS_PER_VIDEO = 500  # Top-level comments per video (5 pages of 100)
MAX_REPLIES_PER_THREAD = 100  # Replies per top-level comment

class QuotaExhaustedError(Exception):
    pass

class YouTubeCollector:
    def __init__(self, api_key: str, output_dir: str = "data/raw/youtube"):
        self.youtube = build("youtube", "v3", developerKey=api_key)
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.units_used = 0

    # Quota helpers
    def _charge(self, units: int):
        self.units_used += units
        log.debug(f"Quota used: {self.units_used}/{QUOTA_LIMIT}")
        if self.units_used >= QUOTA_LIMIT:
            raise QuotaExhaustedError(f"Quota limit reached ({self.units_used} units used). Save and stop.")

    # Video metadata
    def get_video_metadata(self, video_id: str) -> dict:
        """Fetch title, channel, views, likes, publish date, description."""
        try:
            self._charge(1)
            response = self.youtube.videos().list(
                part="snippet,statistics",
                id=video_id
            ).execute()

            if not response.get("items"):
                log.warning(f"No metadata found for video {video_id}")
                return {}

            item = response["items"][0]
            snippet = item["snippet"]
            stats = item.get("statistics", {})

            return {
                "video_id": video_id,
                "title": snippet.get("title", ""),
                "channel": snippet.get("channelTitle", ""),
                "published_at": snippet.get("publishedAt", ""),
                "description": snippet.get("description", "")[:500],  # Truncate long descriptions
                "view_count": int(stats.get("viewCount", 0)),
                "like_count": int(stats.get("likeCount", 0)),
                "comment_count": int(stats.get("commentCount", 0)),
                "collected_at": datetime.utcnow().isoformat()
            }

        except HttpError as e:
            log.error(f"HTTP error fetching metadata for {video_id}: {e}")
            return {}

    # Comment threads (top-level comments)
    def get_comment_threads(self, video_id: str, tool_label: str) -> list[dict]:
        """
        Fetch top-level comments for a video.
        Returns a flat list of comment dicts.
        Each comment includes: id, author, text, likes, reply_count, published_at.
        """
        comments = []
        next_page_token = None
        pages_fetched = 0
        max_pages = MAX_COMMENTS_PER_VIDEO // 100

        log.info(f"  Fetching top-level comments for video {video_id}...")

        while pages_fetched < max_pages:
            try:
                self._charge(1)
                kwargs = {
                    "part": "snippet",
                    "videoId": video_id,
                    "maxResults": 100,
                    "order": "relevance",   # relevance surfaces high-engagement comments
                    "textFormat": "plainText"
                }
                if next_page_token:
                    kwargs["pageToken"] = next_page_token

                response = self.youtube.commentThreads().list(**kwargs).execute()

                for item in response.get("items", []):
                    top = item["snippet"]["topLevelComment"]["snippet"]
                    comments.append({
                        "comment_id": item["id"],
                        "video_id": video_id,
                        "tool": tool_label,
                        "type": "top_level",
                        "author": top.get("authorDisplayName", ""),
                        "author_channel_id": top.get("authorChannelId", {}).get("value", ""),
                        "text": top.get("textDisplay", ""),
                        "like_count": top.get("likeCount", 0),
                        "reply_count": item["snippet"].get("totalReplyCount", 0),
                        "published_at": top.get("publishedAt", ""),
                        "parent_comment_id": None,
                        "parent_author": None,
                        "collected_at": datetime.utcnow().isoformat()
                    })

                next_page_token = response.get("nextPageToken")
                pages_fetched += 1

                if not next_page_token:
                    break

                time.sleep(0.5)  

            except HttpError as e:
                if e.resp.status == 403:
                    log.warning(f"Comments disabled for video {video_id}")
                else:
                    log.error(f"HTTP error on video {video_id}: {e}")
                break

        log.info(f"  Collected {len(comments)} top-level comments from video {video_id}")
        return comments

    # Replies (children of top-level comments)
    def get_replies(self, comment_id: str, parent_author: str, video_id: str, tool_label: str) -> list[dict]:
        """
        Fetch replies to a top-level comment.
        Each reply records parent_author to enable directed reply-graph edges.
        """
        replies = []
        try:
            self._charge(1)
            response = self.youtube.comments().list(
                part="snippet",
                parentId=comment_id,
                maxResults=MAX_REPLIES_PER_THREAD,
                textFormat="plainText"
            ).execute()

            for item in response.get("items", []):
                s = item["snippet"]
                replies.append({
                    "comment_id": item["id"],
                    "video_id": video_id,
                    "tool": tool_label,
                    "type": "reply",
                    "author": s.get("authorDisplayName", ""),
                    "author_channel_id": s.get("authorChannelId", {}).get("value", ""),
                    "text": s.get("textDisplay", ""),
                    "like_count": s.get("likeCount", 0),
                    "reply_count": 0,
                    "published_at": s.get("publishedAt", ""),
                    "parent_comment_id": comment_id,
                    "parent_author": parent_author,
                    "collected_at": datetime.utcnow().isoformat()
                })

        except HttpError as e:
            log.error(f"Error fetching replies for comment {comment_id}: {e}")

        return replies

    # Build reply edges for network analysis
    def build_reply_edges(self, all_comments: list[dict]) -> list[dict]:
        """
        Extract directed edges: replier -> original commenter.
        These become directed edges in our user interaction network.
        Each edge also carries video_id and tool as edge attributes.
        """
        edges = []
        for c in all_comments:
            if c["type"] == "reply" and c["parent_author"]:
                edges.append({
                    "source": c["author"],
                    "source_channel_id": c["author_channel_id"],
                    "target": c["parent_author"],
                    "video_id": c["video_id"],
                    "tool": c["tool"],
                    "comment_id": c["comment_id"],
                    "published_at": c["published_at"]
                })
        return edges

    # Main collection run
    def collect_all(self):
        """
        Full collection pipeline for all TARGET_VIDEOS.
        Saves three JSON files:
          - videos_metadata.json
          - comments_raw.json
          - reply_edges.json
        """
        all_metadata = []
        all_comments = []

        log.info(f"Starting YouTube collection. Target: {len(TARGET_VIDEOS)} videos.")
        log.info(f"Quota budget: {QUOTA_LIMIT} units\n")

        for video in TARGET_VIDEOS:
            vid_id = video["id"]
            tool = video["tool"]
            label = video["label"]

            log.info(f"[{vid_id}] {label} ({tool})")

            try:
                # 1. Metadata
                meta = self.get_video_metadata(vid_id)
                if meta:
                    meta["tool"] = tool
                    meta["label"] = label
                    all_metadata.append(meta)

                # 2. Top-level comments
                top_comments = self.get_comment_threads(vid_id, tool)
                all_comments.extend(top_comments)

                # 3. Replies — only fetch for comments that have replies (save quota)
                comments_with_replies = [c for c in top_comments if c["reply_count"] > 0]
                log.info(f"  Fetching replies for {len(comments_with_replies)} threaded comments...")

                for i, comment in enumerate(comments_with_replies):
                    replies = self.get_replies(
                        comment["comment_id"],
                        comment["author"],
                        vid_id,
                        tool
                    )
                    all_comments.extend(replies)

                    # Brief pause every 10 reply requests
                    if i > 0 and i % 10 == 0:
                        time.sleep(1)

                log.info(f"  Quota used so far: {self.units_used} units")
                log.info("")

            except QuotaExhaustedError as e:
                log.warning(str(e))
                log.warning("Saving partial data and stopping.")
                break

            # Pause between videos to avoid bursting
            time.sleep(1)

        # Build network edges
        reply_edges = self.build_reply_edges(all_comments)

        # Save outputs
        self._save(all_metadata, "videos_metadata.json")
        self._save(all_comments, "comments_raw.json")
        self._save(reply_edges, "reply_edges.json")

        # Summary
        log.info("=" * 50)
        log.info("Collection complete.")
        log.info(f"  Videos collected:   {len(all_metadata)}")
        log.info(f"  Total comments:     {len(all_comments)}")
        log.info(f"  Reply edges:        {len(reply_edges)}")
        log.info(f"  Quota units used:   {self.units_used}")
        log.info(f"  Quota remaining:    {QUOTA_LIMIT - self.units_used}")
        log.info("=" * 50)

        return {
            "videos": all_metadata,
            "comments": all_comments,
            "edges": reply_edges
        }

    def _save(self, data: list, filename: str):
        path = os.path.join(self.output_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        size_kb = os.path.getsize(path) / 1024
        log.info(f"Saved {filename} — {len(data)} records ({size_kb:.1f} KB)")


# Entry point
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()  # Loads .env from the project root

    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "YOUTUBE_API_KEY not found. Copy .env.example to .env and add your key."
        )

    collector = YouTubeCollector(api_key=api_key)
    collector.collect_all()
