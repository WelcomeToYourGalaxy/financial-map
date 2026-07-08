#!/usr/bin/env python3
"""
rss_probe.py — discover working RSS/Atom feeds among the money map's news-type
sources, so the Global Wire harvester only pulls feeds that actually exist.

Reads combined_money_map.html in the current directory, extracts news/watchdog
sources (investigative-journalism / advocacy-opinion types, interpretive/advocacy
voices), probes each domain for a feed, validates it has recent items, and writes
    wire_feeds.json   -> [{"name":..., "site":..., "feed":..., "items": N}, ...]

Run on your Mac:
    pip3 install feedparser
    python3 rss_probe.py
Then the harvester (wire_harvest.py) reads wire_feeds.json.
No API key, no account, no cost.
"""
import json, re, sys, ssl, urllib.request, urllib.parse, concurrent.futures as cf
try:
    import feedparser
except ImportError:
    sys.exit("Install feedparser first:  pip3 install feedparser")
try:
    import certifi; CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:
    CTX = ssl._create_unverified_context()

UA = "Mozilla/5.0 (compatible; money-map-wire/1.0)"
CANDIDATES = ["/feed","/feed/","/rss","/rss.xml","/feed.xml","/atom.xml","/index.xml",
              "/rss/","/feeds/posts/default","/?feed=rss2","/en/feed/","/blog/feed/","/news/feed/"]

def html_feed_links(url):
    """Find <link rel=alternate type=...rss/atom> in a homepage."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=12, context=CTX) as r:
            html = r.read(400000).decode("utf-8","ignore")
    except Exception:
        return []
    out=[]
    for m in re.finditer(r'<link[^>]+type=["\']application/(?:rss|atom)\+xml["\'][^>]*>', html, re.I):
        h=re.search(r'href=["\']([^"\']+)["\']', m.group(0))
        if h: out.append(urllib.parse.urljoin(url, h.group(1)))
    return out

def valid_feed(feed_url):
    try:
        d = feedparser.parse(feed_url, agent=UA)
        n = len(d.entries)
        if n>=3 and (d.feed.get("title") or d.entries[0].get("title")): return n
    except Exception: pass
    return 0

def probe(name, site):
    base = re.match(r'(https?://[^/]+)', site)
    if not base: return None
    root = base.group(1)
    tried=[]
    # 1) declared feed links on the homepage (most reliable)
    for f in html_feed_links(site)[:3]:
        n=valid_feed(f)
        if n: return {"name":name,"site":site,"feed":f,"items":n}
    # 2) common feed paths
    for path in CANDIDATES:
        f=root+path
        if f in tried: continue
        tried.append(f)
        n=valid_feed(f)
        if n: return {"name":name,"site":site,"feed":f,"items":n}
    return None

def extract_sources(html):
    m=re.search(r'const trackerData\s*=\s*(\{)',html); st=m.end()-1
    d=0;i=st;ins=False;sc=''
    while i<len(html):
        ch=html[i]
        if ins:
            if ch=='\\':i+=2;continue
            if ch==sc:ins=False
        else:
            if ch in '"\'`':ins=True;sc=ch
            elif ch=='{':d+=1
            elif ch=='}':
                d-=1
                if d==0:break
        i+=1
    td=json.loads(html[st:i+1])
    allt=[t for c in td.values() for t in c.get('trackers',[])]
    allt+=[t for c in td.values() for r in (c.get('sub') or {}).values() for t in r['trackers']]
    news=[t for t in allt if t.get('type') in ('investigative-journalism','advocacy-opinion')
          or t.get('voice') in ('interpretive','advocacy')]
    seen=set(); out=[]
    for t in news:
        dom=re.match(r'https?://([^/]+)', t['url'])
        if dom and dom.group(1) not in seen:
            seen.add(dom.group(1)); out.append((t['name'], t['url']))
    return out

if __name__=="__main__":
    html=open("combined_money_map.html",encoding="utf-8").read()
    sources=extract_sources(html)
    print(f"probing {len(sources)} news-type domains for feeds...")
    found=[]
    with cf.ThreadPoolExecutor(max_workers=12) as ex:
        for i,res in enumerate(ex.map(lambda s: probe(*s), sources),1):
            if res: found.append(res); print(f"  [{len(found)}] {res['name'][:40]} -> {res['feed']}")
            if i%25==0: print(f"  ...{i}/{len(sources)} checked")
    json.dump(found, open("wire_feeds.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\nwrote wire_feeds.json ({len(found)} working feeds of {len(sources)} sources)")
