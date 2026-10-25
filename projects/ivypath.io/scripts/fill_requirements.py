#!/usr/bin/env python3
"""Find official English-requirement pages, ask the class model to extract
IELTS/TOEFL/SAT, and keep only answers whose quote is found on the page.
Writes data/proposals.csv. Does not change universities.csv."""

import csv, json, re, sys, time
from datetime import date
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import requests

CSV = "data/universities.csv"
CHECK = "data/page-check.csv"
OUT = "data/proposals.csv"
TODAY = date.today().isoformat()
UA = "ivypath-check/1.0 (student project; 1 request/second)"
API = "http://127.0.0.1:19040/v1/chat/completions"
MODEL = "dsv41"
DELAY = 1.1

SKIP_EXT = (".pdf", ".jpg", ".png", ".zip", ".doc", ".docx", ".xls", ".xlsx")

class Text(HTMLParser):
    def __init__(self):
        super().__init__(); self.out=[]; self.skip=0
    def handle_starttag(self, tag, attrs):
        if tag in ("script","style","noscript","svg"): self.skip+=1
    def handle_endtag(self, tag):
        if tag in ("script","style","noscript","svg") and self.skip: self.skip-=1
    def handle_data(self, data):
        if not self.skip: self.out.append(data)

class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.links=[]; self.href=None; self.txt=[]
    def handle_starttag(self, tag, attrs):
        if tag=="a":
            self.href=dict(attrs).get("href"); self.txt=[]
    def handle_data(self, data):
        if self.href is not None: self.txt.append(data)
    def handle_endtag(self, tag):
        if tag=="a" and self.href:
            self.links.append((self.href," ".join(self.txt))); self.href=None

def clean(html):
    p=Text(); p.feed(html)
    return re.sub(r"\s+"," "," ".join(p.out)).strip()

def norm(s):
    return re.sub(r"\s+"," ",s).strip().lower()

def sentences(text):
    return re.split(r"(?<=[.!?])\s+", text)

def relevant(text):
    ss=sentences(text); keep=[]
    for i,s in enumerate(ss):
        if re.search(r"IELTS|TOEFL|SAT\b|English language|language proficiency|English proficiency", s, re.I):
            keep.extend(ss[max(0,i-1):i+2])
    out=" ".join(dict.fromkeys(keep))
    return out[:16000]

def get(url):
    r=requests.get(url, headers={"User-Agent":UA}, timeout=25, allow_redirects=True)
    return r

def same_site(a,b):
    ha=urlparse(a).hostname or ""; hb=urlparse(b).hostname or ""
    return ha==hb or ha.endswith("."+hb) or hb.endswith("."+ha)

def score_link(href, txt, base):
    s=(href+" "+txt).lower()
    if any(href.lower().endswith(e) for e in SKIP_EXT): return -1
    if href.startswith(("mailto:","javascript:","tel:","#")): return -1
    if not same_site(urljoin(base,href), base): return -1
    n=0
    for w,p in [("english",5),("language",4),("ielts",4),("toefl",4),
                ("international",2),("requirement",2),("admission",1),("apply",1)]:
        if w in s: n+=p
    return n

def candidates(base_html, base_url):
    l=Links(); l.feed(base_html)
    seen=set(); out=[]
    for href,txt in l.links:
        u=urljoin(base_url,href).split("#")[0]
        if u in seen: continue
        seen.add(u)
        sc=score_link(href,txt,base_url)
        if sc>=6: out.append((sc,u))
    out.sort(reverse=True)
    return [u for _,u in out[:4]]

def ask(text, url):
    prompt=("You read one university web page and extract English-test requirements for undergraduate international applicants. "
            "Use ONLY the text below. Never use outside knowledge. Return JSON only, no markdown.\n"
            'Schema: {"ielts":{"status":"value|not_required|varies|not_stated","value":null,"note":"","quote":""},'
            '"toefl":{"status":"value|not_required|varies|not_stated","value":null,"note":"","quote":""},'
            '"sat":{"status":"value|not_required|varies|not_stated","value":null,"note":"","quote":""}}\n'
            "Rules: status=value if the page gives one minimum overall score, or a table/range by course: "
            "then use the LOWEST published overall score and note='минимум; зависит от программы, до X'. "
            "If it gives a minimum plus higher scores for some programmes, use value and say that in note. "
            "Use status=varies only if the page says requirements vary and gives no number. "
            "status=not_required only if the page says the test is not required. "
            "status=not_stated if the page does not state it. "
            "note must be Russian, max 100 chars. quote must be copied word for word from the text (one sentence).\n"
            f"URL: {url}\nTEXT:\n{text}")
    body={"model":MODEL,"messages":[{"role":"user","content":prompt}],"temperature":0,"max_tokens":700}
    r=requests.post(API,json=body,timeout=90)
    r.raise_for_status()
    out=r.json()["choices"][0]["message"]["content"]
    m=re.search(r"\{.*\}", out, re.S)
    if not m: raise ValueError("no JSON: "+out[:200])
    return json.loads(m.group(0))

def main():
    limit=int(sys.argv[1]) if len(sys.argv)>1 else 999
    only=sys.argv[2].lower() if len(sys.argv)>2 else ""
    rows=list(csv.DictReader(open(CSV,encoding="utf-8")))
    check={r["name"]:r for r in csv.DictReader(open(CHECK,encoding="utf-8"))}
    todo=[r for r in rows if not only or only in r["name"].lower()][:limit]
    done=set()
    try:
        done={r["name"] for r in csv.DictReader(open(OUT,encoding="utf-8"))}
    except FileNotFoundError:
        pass
    fields=["name","fact","status","value","note","quote","source","checked"]
    exists=False
    try:
        exists=bool(done)
    except Exception:
        pass
    f=open(OUT,"a",encoding="utf-8",newline="")
    w=csv.DictWriter(f,fieldnames=fields)
    if not exists: w.writeheader(); f.flush()
    for i,u in enumerate(todo,1):
        if u["name"] in done:
            print(f"[{i}/{len(todo)}] skip {u['name']}",flush=True); continue
        c=check.get(u["name"],{})
        start=c.get("final_url") or u["admissions_url"]
        urls=[start]
        try:
            r=get(start); time.sleep(DELAY)
            if r.status_code!=200:
                root=f"{urlparse(start).scheme}://{urlparse(start).netloc}/"
                if root!=start: urls=[root]
            else:
                urls=[start]+candidates(r.text,start)
                html0=r.text
        except Exception as e:
            print(f"[{i}/{len(todo)}] {u['name']}: fetch {e}",flush=True)
            continue
        found=False
        for url in urls[:4]:
            try:
                if url!=start or 'html0' not in dir():
                    r=get(url); time.sleep(DELAY)
                else:
                    r.requests=None
                if r.status_code!=200: continue
                txt=clean(r.text); rel=relevant(txt)
                if not rel or not re.search(r"IELTS|TOEFL", rel, re.I): continue
                ans=ask(rel,url)
                time.sleep(0.3)
                for fact in ("ielts","toefl","sat"):
                    a=ans.get(fact) or {}
                    q=(a.get("quote") or "").strip()
                    if not q or norm(q)[:110] not in norm(txt):
                        continue
                    status=a.get("status")
                    if status not in ("value","not_required","varies","not_stated"): continue
                    val=a.get("value")
                    if status=="value" and val in (None,""): continue
                    w.writerow({"name":u["name"],"fact":fact,"status":status,"value":val,
                                "note":a.get("note",""),"quote":q,"source":url,"checked":TODAY})
                    f.flush(); found=True
                if found:
                    print(f"[{i}/{len(todo)}] {u['name']}: {url} OK",flush=True)
                    break
            except Exception as e:
                print(f"[{i}/{len(todo)}] {u['name']}: {url} {type(e).__name__} {e}"[:300],flush=True)
        if not found:
            print(f"[{i}/{len(todo)}] {u['name']}: nothing",flush=True)
    f.close()

if __name__=="__main__":
    main()
