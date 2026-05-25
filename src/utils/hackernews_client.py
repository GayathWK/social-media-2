# Hacker News API client.

import sys
import time

import requests

HN_FIREBASE_BASE_URL = "https://hacker-news.firebaseio.com/v0"
HN_ALGOLIA_BASE_URL = "https://hn.algolia.com/api/v1"


def hackerNewsGet(url, params=None, sleepSeconds=0.02):
    
    #parsed JSON response
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        time.sleep(sleepSeconds)
        return response.json()
    except Exception as e:
        sys.stderr.write(f"Hacker News API request failed for {url}: {e}\n")
        raise


def hackerNewsItem(itemId):
    # Gets ID

    url = f"{HN_FIREBASE_BASE_URL}/item/{itemId}.json"
    return hackerNewsGet(url)


def searchHackerNewsStories(query, maxStories=50):
    #returns list of story search results

    stories = []
    page = 0
    hits_per_page = 100
        
    while len(stories) < maxStories:
        url = f"{HN_ALGOLIA_BASE_URL}/search"
        params = {
            "query": query,
            "tags": "story",
            "hitsPerPage": hits_per_page,
            "page": page,
        }

        data = hackerNewsGet(url, params=params)
        hits = data.get("hits", [])

        if not hits:
            break

        for hit in hits:
            stories.append(hit)

            if len(stories) >= maxStories:
                break

        page += 1

        if page >= data.get("nbPages", 0):
            break

    return stories