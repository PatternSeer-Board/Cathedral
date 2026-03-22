#!/usr/bin/env python3
"""
Auto-update cathedral website with latest Substack posts.
Fetches RSS directly from Substack. No third party API.
"""
import requests, os, json, subprocess, re
from datetime import datetime
import xml.etree.ElementTree as ET

SITE_DIR = os.path.expanduser("~/cathedral-website")
INDEX = os.path.join(SITE_DIR, "index.html")
FEED_URL = "https://apatternseer.substack.com/feed"

def fetch_posts():
    try:
        resp = requests.get(FEED_URL, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            channel = root.find("channel")
            items = channel.findall("item") if channel is not None else []
            posts = []
            for item in items[:6]:
                title = item.findtext("title", "")
                link = item.findtext("link", "")
                pub = item.findtext("pubDate", "")
                desc = item.findtext("description", "")
                desc = re.sub(r'<[^>]+>', '', desc)[:200]
                date = pub[:16] if pub else ""
                posts.append({"title": title, "link": link, "date": date, "desc": desc})
            return posts
    except Exception as e:
        print(f"Fetch error: {e}")
    return []

def update_fallback(posts):
    if not posts or not os.path.exists(INDEX):
        return False

    with open(INDEX) as f:
        html = f.read()

    cards = ""
    for p in posts:
        title = p["title"].replace('"', '&quot;')
        cards += f'''<a href="{p['link']}" target="_blank" class="mc reveal">
<div class="mc-date">{p['date']}</div>
<div class="mc-title">{title}</div>
<div class="mc-ex">{p['desc']}</div>
<span class="mc-read">Read on Substack</span>
</a>
'''

    pattern = r'(id="pgrid"[^>]*>)(.*?)(</div>\s*</section>)'
    match = re.search(pattern, html, re.DOTALL)
    if match:
        new_html = html[:match.start(2)] + "\n" + cards + "\n" + html[match.end(2):]
    else:
        pattern2 = r'(class="posts-grid"[^>]*>)(.*?)(</div>\s*</section>)'
        match2 = re.search(pattern2, html, re.DOTALL)
        if match2:
            new_html = html[:match2.start(2)] + "\n" + cards + "\n" + html[match2.end(2):]
        else:
            return False

    if new_html != html:
        with open(INDEX, 'w') as f:
            f.write(new_html)
        return True
    return False

def git_push():
    try:
        subprocess.run(["git", "add", "-A"], cwd=SITE_DIR, capture_output=True, timeout=10)
        result = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=SITE_DIR, capture_output=True, timeout=10)
        if result.returncode != 0:
            subprocess.run(["git", "commit", "-m", f"Auto-update posts {datetime.now().strftime('%Y-%m-%d %H:%M')}"],
                cwd=SITE_DIR, capture_output=True, timeout=10)
            subprocess.run(["git", "push"], cwd=SITE_DIR, capture_output=True, timeout=30)
            return True
    except:
        pass
    return False

if __name__ == "__main__":
    posts = fetch_posts()
    if posts:
        print(f"Fetched {len(posts)} posts")
        for p in posts:
            print(f"  {p['title']}")
        updated = update_fallback(posts)
        if updated:
            pushed = git_push()
            print(f"Updated and pushed: {pushed}")
        else:
            print("No HTML changes needed")
    else:
        print("No posts fetched")
