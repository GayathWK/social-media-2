# COSC2671 Social Media and Network Analytics
# GitHub API client.

import os
import sys
import time
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv():
        for start in (Path.cwd().resolve(), Path(__file__).resolve()):
            for path in (start, *start.parents):
                env_path = path / ".env"
                if not env_path.exists():
                    continue
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
                return True
        return False

load_dotenv()

def githubHeaders():
    """
    Build GitHub REST API headers.

    Set GITHUB_TOKEN in the environment or in a local .env file.
    """

    token = os.getenv("GITHUB_TOKEN", "").strip()

    if token.startswith("AIza"):
        raise ValueError(
            "GITHUB_TOKEN looks like a Google/YouTube API key. "
            "Use a GitHub personal access token instead, or leave it blank."
        )

    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "COSC2671-assignment2-github-collector",
    }

    if token and not token.startswith("<"):
        headers["Authorization"] = f"Bearer {token}"

    return headers


def githubGet(url, params=None):
    """
    Send a GET request to the GitHub REST API.

    @returns: parsed JSON response
    """

    try:
        response = requests.get(
            url,
            headers=githubHeaders(),
            params=params,
            timeout=30,
        )

        remaining = response.headers.get("X-RateLimit-Remaining")
        reset = response.headers.get("X-RateLimit-Reset")

        if response.status_code == 403 and remaining == "0":
            reset_time = time.strftime(
                "%Y-%m-%d %H:%M:%S",
                time.localtime(int(reset)),
            ) if reset else "unknown"
            sys.stderr.write(f"GitHub rate limit exceeded. Reset time: {reset_time}\n")

        if response.status_code == 401:
            raise ValueError(
                "GitHub returned 401 Unauthorized. The configured GITHUB_TOKEN is missing, "
                "expired, or not a GitHub personal access token."
            )

        response.raise_for_status()
        return response.json()

    except Exception as e:
        sys.stderr.write(f"GitHub API request failed for {url}: {e}\n")
        raise
