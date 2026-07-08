#!/usr/bin/env python3
"""
wire_harvest.py — build/refresh wire_archive.json for the money map's Global Wire.
Reads feeds (wire_feeds.json from rss_probe.py, else the built-in list), pulls
items via feedparser, filters to FINANCIAL accountability relevance, drops noise
and small/one-off incidents, categorises into the money lenses, dedupes by link,
and keeps the newest 2000. No API key, no account, no cost. Runs in GitHub Actions.
"""
import json, time, datetime, re, os, sys
try: import feedparser
except ImportError: sys.exit("pip install feedparser")

CAP=2000
ARCHIVE="wire_archive.json"
UA="Mozilla/5.0 (compatible; money-map-wire/1.0)"

# financial relevance (must hit one) — mirrors the map's Live filter
FIN=['budget','fiscal','public spending','public funds','public money','procurement','tender',
 'contract award','audit','auditor','comptroller','oversight','watchdog','corruption','bribery',
 'embezzle','kickback','graft','fraud','money laundering','illicit','shell company',
 'beneficial ownership','offshore','tax','tax haven','tax evasion','tax avoidance','revenue',
 'treasury','central bank','regulator','financial regulator','basel','bailout','bank collapse',
 'sovereign debt','default','deficit','inflation','monetary policy','interest rate','subsidy',
 'sovereign wealth','sanctions','fatf','imf','world bank','oecd','asset declaration',
 'company register','financial crime','fincen','misappropriat','state capture','kleptocra',
 'public accounts','securities','stock exchange','pension fund','anti-corruption']
STOP=['football','soccer','celebrity','recipe','horoscope','box office','fashion','obituary',
 'weather forecast','sports','webinar','register now','join us','rsvp','sign up','watch live',
 'apply now','fellowship','job opening','call for applications','book launch']
BIG=['reform','overhaul','sweeping','landmark','billion','million','budget','audit','investigation',
 'probe','inquiry','regulator','central bank','bailout','sanctions','laundering','corruption',
 'fraud','scandal','tax','procurement','watchdog','oversight','treasury','imf','world bank',
 'collapse','crackdown','ruling','settlement','fine','penalty','embezzle','bribery','default','seized','frozen']
SMALL=['councillor','local council','mayor of','resign','quit','stepped down','apolog',
 'expenses claim','affair','wedding','gaffe','by-election','personal',' dies','hospital']
CATS=[('international',['international','treaty','imf','world bank','oecd','g20','fatf','sanctions','cross-border','offshore']),
 ('budgets',['budget','appropriation','public spending','deficit','fiscal','public funds']),
 ('audit',['audit','auditor','oversight','watchdog','comptroller','public accounts']),
 ('procurement',['procurement','tender','public contract','contract award','bid rigging']),
 ('corruption',['corruption','bribery','embezzle','kickback','graft','fraud','scandal','state capture']),
 ('tax',['tax','tax evasion','tax avoidance','tax haven','revenue','transfer pricing']),
 ('banking',['bank','central bank','regulator','basel','bailout','supervision']),
 ('laundering',['money laundering','illicit','shell company','beneficial ownership','fincen','kleptocra']),
 ('debt',['debt','sovereign debt','default','bailout','austerity','bond']),
 ('monetary',['inflation','interest rate','monetary policy','currency','cbdc']),
 ('ownership',['beneficial ownership','company register','asset declaration','disclosure','registry'])]

def feeds():
    if os.path.exists("wire_feeds.json"):
        try: return [(f["name"],f["feed"]) for f in json.load(open("wire_feeds.json"))]
        except Exception: pass
    return [["ICIJ","https://www.icij.org/feed/"],["OCCRP","https://www.occrp.org/en/feed"],
      ["ProPublica","https://www.propublica.org/feeds/propublica/main"],
      ["Tax Justice Network","https://taxjustice.net/feed/"],
      ["Global Witness","https://www.globalwitness.org/en/rss/"],
      ["The Lever","https://www.levernews.com/rss/"],
      ["Bureau of Investigative Journalism","https://www.thebureauinvestigates.com/feed"]]

def sig(t):
    s=' '+t.lower()+' '; sc=0
    for w in BIG:   sc+= 2 if w in s else 0
    for w in SMALL: sc-= 3 if w in s else 0
    for w in FIN:   sc+= 1 if w in s else 0
    return sc
def cat(t):
    s=' '+t.lower()+' '; best='other'; bo=0
    for cid,terms in CATS:
        n=sum(1 for w in terms if w in s)
        if n>bo: bo=n; best=cid
    return best

def main():
    feedparser.USER_AGENT=UA
    try: arch=json.load(open(ARCHIVE))
    except Exception: arch=[]
    seen={x.get("link") for x in arch}
    added=0
    for name,url in feeds():
        try: d=feedparser.parse(url)
        except Exception: continue
        for it in d.entries[:40]:
            title=(getattr(it,"title","") or ""); desc=(getattr(it,"summary","") or "")
            hay=(title+" "+desc).lower()
            if not title or getattr(it,"link","") in seen: continue
            if any(w in hay for w in STOP): continue
            if not any(w in hay for w in FIN): continue
            if sig(title+" "+desc) < 2: continue          # drop small/one-off
            try: dt=int(time.mktime(it.published_parsed))*1000
            except Exception: dt=int(time.time()*1000)
            arch.append({"name":name,"title":title[:300],"link":it.link,
                         "date":dt,"cat":cat(title+" "+desc),"sig":sig(title+" "+desc)})
            seen.add(it.link); added+=1
    arch.sort(key=lambda x:-x.get("date",0))
    arch=arch[:CAP]
    json.dump(arch,open(ARCHIVE,"w"),ensure_ascii=False)
    print(f"added {added}; archive now {len(arch)} (cap {CAP})")

if __name__=="__main__": main()
