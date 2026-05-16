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

    # Look for post containers (Substack specific selectors)
    posts = soup.find_all('div', {'class': re.compile('post.*')})

    for post in posts:
        try:
            title_elem = post.find('h2') or post.find('h3')
            if not title_elem:
                continue

            title = title_elem.get_text(strip=True)

            # Extract date
            date_elem = post.find('time')
            date_str = date_elem.get('datetime') if date_elem else None

            # Extract excerpt
            excerpt_elem = post.find('p')
            excerpt = excerpt_elem.get_text(strip=True) if excerpt_elem else ""

            # Extract link
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

    # Create filename from title
    filename = re.sub(r'[^a-z0-9]+', '-', essay['title'].lower()).strip('-')
    filepath = DOCS_DIR / f"{filename}.mdx"

    # Skip if file exists
    if filepath.exists():
        return None

    # Create content
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

def update_docs_json(filepath, category):
    """Update docs.json navigation."""
    if not DOCS_JSON.exists():
        return

    with open(DOCS_JSON) as f:
        config = json.load(f)

    # Get relative path for nav
    rel_path = filepath.relative_to(DOCS_JSON.parent)
    path_str = str(rel_path).replace('.mdx', '').replace(os.sep, '/')

    # Find category in navigation
    for item in config.get('navigation', []):
        if item.get('group') == category.replace('-', ' ').title():
            if 'items' not in item:
                item['items'] = []

            # Check if already exists
            if not any(i.get('path') == path_str for i in item['items']):
                item['items'].append({
                    'path': path_str
                })
                break

    with open(DOCS_JSON, 'w') as f:
        json.dump(config, f, indent=2)

def pull_quotes():
    """Pull quotes from existing essays if no new ones."""
    if not DOCS_DIR.exists():
        return []

    quotes = []
    for essay_file in list(DOCS_DIR.glob('*.mdx'))[:3]:  # Get first 3 essays
        content = essay_file.read_text()

        # Extract first substantive paragraph
        lines = [line.strip() for line in content.split('\n') if line.strip() and not line.startswith('---')]
        for line in lines[5:]:  # Skip frontmatter and title
            if len(line) > 50:
                quotes.append(line[:150])
                break

    return quotes

def save_commit_message(message):
    """Save commit message for workflow."""
    Path('/tmp/commit_message.txt').write_text(message)

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
                update_docs_json(filepath, category)
                added.append(essay['title'])
                print(f"✓ Added: {essay['title']}")

    if added:
        message = f"Add new essay{'s' if len(added) > 1 else ''}: {', '.join(added[:2])}"
        save_commit_message(message)
        print(f"Added {len(added)} new essay(ies)")
    else:
        print("No new essays found. Pulling quotes from existing essays...")
        quotes = pull_quotes()
        if quotes:
            save_commit_message("Update featured quotes from essays")
            print(f"Updated {len(quotes)} featured quotes")
        else:
            print("No quotes to update")

if __name__ == '__main__':
    main()
