#!/usr/bin/env python3
"""Sync essays from Substack to docs site."""

import os
import json
import re
from datetime import datetime
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

SUBSTACK_URL = "https://lifeonafaultline.substack.com"
DOCS_DIR = Path(__file__).parent.parent.parent / "essays"
DOCS_JSON = Path(__file__).parent.parent.parent / "docs.json"

def fetch_substack():
    """Fetch and parse Substack page for essays."""
    try:
        response = requests.get(SUBSTACK_URL, timeout=10)
        response.raise_for_status()
        return BeautifulSoup(response.content, 'html.parser')
    except Exception as e:
        print(f"Error fetching Substack: {e}")
        return None

def extract_essays(soup):
    """Extract essay information from Substack page."""
    essays = []
    if not soup:
        return essays

    posts = soup.find_all('div', {'class': re.compile('post.*')})

    for post in posts:
        try:
            title_elem = post.find('h2') or post.find('h3')
            if not title_elem:
                continue

            title = title_elem.get_text(strip=True)
            date_elem = post.find('time')
            date_str = date_elem.get('datetime') if date_elem else None
            excerpt_elem = post.find('p')
            excerpt = excerpt_elem.get_text(strip=True) if excerpt_elem else ""
            link_elem = post.find('a')
            link = link_elem.get('href') if link_elem else ""
            if link and not link.startswith('http'):
                link = urljoin(SUBSTACK_URL, link)

            if title and date_str:
                essays.append({
                    'title': title,
                    'date': date_str,
                    'excerpt': excerpt[:200],
                    'link': link
                })
        except Exception as e:
            print(f"Error extracting essay: {e}")
            continue

    return essays

def categorize_essay(title, excerpt):
    """Categorize essay based on content."""
    content = (title + " " + excerpt).lower()

    if any(word in content for word in ['death', 'loss', 'died', 'mourning', 'grieve']):
        return 'grief'
    elif any(word in content for word in ['divorce', 'marriage', 'split', 'separation']):
        return 'divorce'
    elif any(word in content for word in ['song', 'music', 'album', 'lyric', 'musician']):
        return 'music'
    elif any(word in content for word in ['dark', 'worst', 'hardest', 'survival', '3 am']):
        return 'darkest-hours'

    return 'essays'

def essay_exists(title):
    """Check if essay already exists in docs."""
    if not DOCS_DIR.exists():
        return False

    for file in DOCS_DIR.glob('*.mdx'):
        content = file.read_text()
        if title in content:
            return True
    return False

def create_essay_file(essay, category):
    """Create .mdx file for new essay."""
    if not DOCS_DIR.exists():
        DOCS_DIR.mkdir(parents=True, exist_ok=True)

    filename = re.sub(r'[^a-z0-9]+', '-', essay['title'].lower()).strip('-')
    filepath = DOCS_DIR / f"{filename}.mdx"

    if filepath.exists():
        return None

    date = essay['date'][:10] if essay['date'] else datetime.now().strftime("%Y-%m-%d")

    content = f"""---
title: "{essay['title']}"
description: "{essay['excerpt']}"
sidebarTitle: "{essay['title'][:30]}"
---

{essay['excerpt']}

This essay was published on Substack on {date}. [Read the full essay on Substack]({essay['link']})

---

<Note>
This essay is featured from [lifeonafaultline.substack.com]({SUBSTACK_URL}). Subscribe there to read the complete work and receive new essays when they're published.
</Note>
"""

    filepath.write_text(content)
    return filepath

def main():
    """Main sync function."""
    print("Starting Substack essay sync...")

    soup = fetch_substack()
    new_essays = extract_essays(soup)

    added = []
    for essay in new_essays:
        if not essay_exists(essay['title']):
            category = categorize_essay(essay['title'], essay['excerpt'])
            filepath = create_essay_file(essay, category)

            if filepath:
                added.append(essay['title'])
                print(f"✓ Added: {essay['title']}")

    if added:
        message = f"Add new essay{'s' if len(added) > 1 else ''}: {', '.join(added[:2])}"
        Path('/tmp/commit_message.txt').write_text(message)
        print(f"Added {len(added)} new essay(ies)")
    else:
        print("No new essays found")

if __name__ == '__main__':
    main()
