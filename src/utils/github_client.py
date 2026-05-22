# COSC2671 Social Media and Network Analytics
# GitHub API client.

import os
import sys
import time

import requests

try:
    from .github_credentials import GITHUB_TOKEN as FILE_GITHUB_TOKEN
except ImportError:
    FILE_GITHUB_TOKEN = ""


def githubHeaders():
    """
    Build GitHub REST API headers.

    Token options:
    1. Set environment variable GITHUB_TOKEN, or
    2. Put the token in githubCredentials.py.
    """

    token = os.getenv("GITHUB_TOKEN") or FILE_GITHUB_TOKEN

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

        response.raise_for_status()
        return response.json()

    except Exception as e:
        sys.stderr.write(f"GitHub API request failed for {url}: {e}\n")
        raise
