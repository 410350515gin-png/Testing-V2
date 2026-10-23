
from flask import Flask, jsonify, request
import requests, re, time
from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlencode
from datetime import datetime, timezone, timedelta
import threading, json, os

app = Flask(__name__)
UA = "Mozilla/5.0 (compatible; YouthCourseRadar/1.0; +https://youth-course-radar-tw-2026.onrender.com)"
requests.packages.urllib3.disable_warnings()
S = requests.Session()
S.headers.update({"User-Agent": UA, "Accept-Language":"zh-TW,zh;q=0.9,en;q=0.6"})

TODAY = "2026-10-23"

SOURCES = {
    "taiwanjobs": "https://course.taiwanjobs.gov.tw/",
    "taiwanjobs_conditions": "https://course.taiwanjobs.gov.tw/course/conditions",
    "yip": "https://ttms.etraining.gov.tw/eYVTR/YipClassApply",
    "youthfirst": "https://youthfirst.yda.gov.tw/index.php/subject/index/1",
    "startup": "https://startup.sme.gov.tw/home/modules/calendar/",
    "taipei": "https://youth.gov.taipei/",
    "ntpc": "https://www.youth.ntpc.gov.tw/youth/ch/app/course/list?id=181&module=course",
    "taichung": "https://1catchjob.taichung.gov.tw/Default.aspx",
    "kaohsiung": "https://youth.kcg.gov.tw/",
}

def get(url, params=None):
    host = urlparse(url).netloc.lower()
    headers = {
        "User-Agent": UA,
        "Accept-Language":"zh-TW,zh;q=0.9,en;q=0.6",
        "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Cache-Control":"no-cache",
        "Pragma":"no-cache",
        "Upgrade-Insecure-Requests":"1",
    }
    protected = any(x in host for x in ["startup.sme.gov.tw","youthfirst.yda.gov.tw","1catchjob.taichung.gov.tw","youth.kcg.gov.tw"])
    if protected:
        r = cffi_requests.get(url, params=params, headers=headers, timeout=30, allow_redirects=True, verify=False, impersonate="chrome124")
        if r.status_code >= 400:
            r.raise_for_status()
        return r
    r = S.get(url, params=params, headers=headers, timeout=30, allow_redirects=True, verify=False)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or r.encoding
    return r

def clean(s):
    return re.sub(r"\s+", " ", (s or "")).strip()

def absolute(base, href):
    return urljoin(base, href or "")

def roc_to_ad(s):
    # 115-11-14 / 115/11/14
    m = re.search(r'(?<!\d)(1\d{2})[/-](\d{1,2})[/-](\d{1,2})(?!\d)', s or "")
    if not m: return None
    y,mn,d = map(int,m.groups())
    return f"{y+1911:04d}-{mn:02d}-{d:02d}"

def ad_date(s):
    m = re.search(r'(20\d{2})[/-](\d{1,2})[/-](\d{1,2})', s or "")
    if not m: return None
    y,mn,d=map(int,m.groups())
    return f"{y:04d}-{mn:02d}-{d:02d}"

def extract_dates(text):
    dates=[]
    for m in re.finditer(r'(?<!\d)(1\d{2})[/-](\d{1,2})[/-](\d{1,2})(?!\d)', text or ""):
        y,mn,d=map(int,m.groups()); dates.append(f"{y+1911:04d}-{mn:02d}-{d:02d}")
    for m in re.finditer(r'(20\d{2})[/-](\d{1,2})[/-](\d{1,2})', text or ""):
        y,mn,d=map(int,m.groups()); dates.append(f"{y:04d}-{mn:02d}-{d:02d}")
    # stable unique
    out=[]
    for x in dates:
        if x not in out: out.append(x)
    return out

def generic_links(url, include_patterns=(), exclude_patterns=(), max_items=500):
    r=get(url); soup=BeautifulSoup(r.text,"html.parser")
    out=[]
    for a in soup.find_all("a", href=True):
        href=absolute(r.url,a.get("href"))
        txt=clean(a.get_text(" ", strip=True))
        if not txt: continue
        key=(txt+" "+href).lower()
        if include_patterns and not any(p.lower() in key for p in include_patterns): continue
        if any(p.lower() in key for p in exclude_patterns): continue
        out.append({"title":txt,"url":href,"context":clean(a.parent.get_text(" ",strip=True))[:500] if a.parent else txt})
        if len(out)>=max_items: break
    # dedupe url
    seen=set(); ded=[]
    for x in out:
        if x["url"] in seen: continue
        seen.add(x["url"]); ded.append(x)
    return ded

def scrape_ntpc():
    items=[]; seen=set()
    for page in range(1,30):
        r=get(SOURCES["ntpc"], params={"id":"181","module":"course","page":page,"pageSize":15})
        soup=BeautifulSoup(r.text,"html.parser")
        found=0
        for a in soup.find_all("a", href=True):
            href=absolute(r.url,a["href"])
            if "/course/view" not in href: continue
            title=clean(a.get_text(" ",strip=True))
            if not title or href in seen: continue
            context=clean(a.parent.get_text(" ",strip=True)) if a.parent else title
            ds=extract_dates(context+" "+title)
            items.append({"source":"新北市青年局","title":title,"url":href,"dates":ds,"context":context[:500]})
            seen.add(href); found+=1
        # stop after no unique item on a page
        if found==0:
            if page>3: break
    return items

def scrape_yip():
    r=get(SOURCES["yip"])
    soup=BeautifulSoup(r.text,"html.parser")
    items=[]; seen=set()
    for a in soup.find_all("a", href=True):
        href=absolute(r.url,a["href"])
        txt=clean(a.get_text(" ",strip=True))
        if not txt: continue
        if "Detail" not in href and "課程明細" not in txt: continue
        if href in seen: continue
        row=a.find_parent("tr")
        context=clean(row.get_text(" ",strip=True)) if row else clean(a.parent.get_text(" ",strip=True))
        title=txt
        if row:
            cells=[clean(td.get_text(" ",strip=True)) for td in row.find_all(["td","th"])]
            if len(cells)>=3: title=cells[2]
        items.append({"source":"青年職訓資源網／產業新尖兵","title":title,"url":href,"dates":extract_dates(context),"context":context[:600]})
        seen.add(href)
    return items

def scrape_startup():
    items=[]; seen=set(); empty=0
    # crawl upcoming from today; site handles its own pagination
    for page in range(1,80):
        params={"start_date":TODAY,"page":page}
        r=get(SOURCES["startup"],params=params)
        soup=BeautifulSoup(r.text,"html.parser")
        found=0
        # detail links typically live under calendar module; capture event/course links, exclude pagination
        for a in soup.find_all("a",href=True):
            href=absolute(r.url,a["href"])
            title=clean(a.get_text(" ",strip=True))
            if not title: continue
            key=href.lower()
            if "/calendar/" not in key: continue
            if any(x in key for x in ["?page=","javascript:"]): continue
            if href.rstrip("/") == r.url.split("?")[0].rstrip("/"): continue
            context=clean(a.parent.get_text(" ",strip=True)) if a.parent else title
            # require a date or activity/course-ish context to avoid nav
            if not extract_dates(context) and not re.search(r'課程|活動|競賽|線上|開始時間',context):
                continue
            if href in seen: continue
            items.append({"source":"經濟部新創圓夢網","title":title,"url":href,"dates":extract_dates(context),"context":context[:600]})
            seen.add(href); found+=1
        if found==0: empty+=1
        else: empty=0
        if empty>=2 and page>3: break
    return items

def scrape_youthfirst():
    items=[]; seen=set()
    for page in range(1,8):
        url=f"https://youthfirst.yda.gov.tw/index.php/subject/index/1/{page}" if page>1 else SOURCES["youthfirst"]
        try:r=get(url)
        except Exception:continue
        soup=BeautifulSoup(r.text,"html.parser")
        page_count=0
        for a in soup.find_all("a",href=True):
            raw=a.get("href") or ""
            m=re.search(r'(?:index\.php/)?subject/content/(\d+)', raw)
            if not m: continue
            cid=m.group(1)
            href=f"https://youthfirst.yda.gov.tw/index.php/subject/content/{cid}"
            if href in seen: continue
            title=clean(a.get_text(" ",strip=True))
            parent=a.find_parent(["li","div","article"])
            context=clean(parent.get_text(" ",strip=True)) if parent else title
            if not title or len(title)<3: title=f"青年第一讚資源 {cid}"
            items.append({"source":"青年第一讚","title":title,"url":href,"dates":extract_dates(context),"context":context[:1200]})
            seen.add(href); page_count+=1
        if page>1 and page_count==0:
            break
    return items

def scrape_taichung():
    items=[]; seen=set(); urls=[
        SOURCES["taichung"],
        "https://1catchjob.taichung.gov.tw/more.aspx?cat=new",
        "https://1catchjob.taichung.gov.tw/more.aspx?cat=hot",
        "https://1catchjob.taichung.gov.tw/calendar.aspx?cat=21",
    ]
    for url in urls:
        try:r=get(url)
        except Exception:continue
        html=r.text; soup=BeautifulSoup(html,"html.parser")
        # anchor route
        for a in soup.find_all("a",href=True):
            raw=a.get("href") or ""
            m=re.search(r'detail\.aspx\?act=(\d+)',raw,re.I)
            if not m: continue
            aid=m.group(1); href=f"https://1catchjob.taichung.gov.tw/detail.aspx?act={aid}"
            if href in seen: continue
            title=clean(a.get_text(" ",strip=True))
            parent=a.find_parent(["li","div","tr","article"])
            context=clean(parent.get_text(" ",strip=True)) if parent else title
            items.append({"source":"臺中市就業服務一鍵Catch","title":title or f"臺中就業活動 {aid}","url":href,"dates":extract_dates(context),"context":context[:1000]})
            seen.add(href)
        # raw HTML fallback
        for aid in re.findall(r'detail\.aspx\?act=(\d+)',html,re.I):
            href=f"https://1catchjob.taichung.gov.tw/detail.aspx?act={aid}"
            if href not in seen:
                items.append({"source":"臺中市就業服務一鍵Catch","title":f"臺中就業活動 {aid}","url":href,"dates":[],"context":""})
                seen.add(href)
    return items

def crawl_domain_candidates(start, domain, keywords, max_pages=120, max_depth=2):
    # bounded BFS for sites without a clean listing endpoint; only same-domain and course-like URLs/text.
    todo=[(start,0)]; seen_pages=set(); items=[]; item_urls=set()
    while todo and len(seen_pages)<max_pages:
        url,depth=todo.pop(0)
        if url in seen_pages: continue
        seen_pages.add(url)
        try:r=get(url)
        except Exception:continue
        if "text/html" not in r.headers.get("content-type","text/html"): continue
        soup=BeautifulSoup(r.text,"html.parser")
        for a in soup.find_all("a",href=True):
            href=absolute(r.url,a["href"])
            p=urlparse(href)
            if p.netloc and domain not in p.netloc: continue
            title=clean(a.get_text(" ",strip=True)); context=clean(a.parent.get_text(" ",strip=True)) if a.parent else title
            key=(title+" "+href+" "+context).lower()
            if any(k.lower() in key for k in keywords):
                if href not in item_urls and title and len(title)>=4:
                    items.append({"title":title,"url":href,"dates":extract_dates(context),"context":context[:900]})
                    item_urls.add(href)
                if depth<max_depth and href not in seen_pages and href.startswith("http"):
                    todo.append((href,depth+1))
            elif depth<1 and href.startswith("http") and any(k in href.lower() for k in ["course","news","activity","class","event"]):
                todo.append((href,depth+1))
    return items, len(seen_pages)

def scrape_taipei():
    items=[]; seen=set()
    seeds=["https://class.tpyd.gov.taipei/","https://class.tpyd.gov.taipei/participate/?node=0"]
    for url in seeds:
        try:r=get(url)
        except Exception:continue
        soup=BeautifulSoup(r.text,"html.parser")
        for a in soup.find_all("a",href=True):
            href=absolute(r.url,a["href"]); title=clean(a.get_text(" ",strip=True))
            if not title or href in seen: continue
            parent=a.find_parent(["li","div","article","section"])
            context=clean(parent.get_text(" ",strip=True)) if parent else title
            if not re.search(r'報名|活動|課程|學堂|工作坊|講座',context): continue
            if href.rstrip("/") in [r.url.rstrip("/"),"https://class.tpyd.gov.taipei/participate"]: continue
            items.append({"source":"臺北市政府青年局","title":title,"url":href,"dates":extract_dates(context),"context":context[:1200]})
            seen.add(href)
    return items

def scrape_kaohsiung():
    items=[]; seen=set()
    seeds=[
      "https://youth.kcg.gov.tw/ResourceSearch.aspx?n=41&sms=10164",
      "https://youth.kcg.gov.tw/News.aspx?n=293&sms=10305&PageSize=50&page=1",
    ]
    for url in seeds:
        try:r=get(url)
        except Exception:continue
        soup=BeautifulSoup(r.text,"html.parser")
        for a in soup.find_all("a",href=True):
            href=absolute(r.url,a["href"]); title=clean(a.get_text(" ",strip=True))
            if not title or href in seen: continue
            parent=a.find_parent(["li","div","article","tr"])
            context=clean(parent.get_text(" ",strip=True)) if parent else title
            if "ResourceSearch" in r.url:
                if not re.search(r'課程時間|課程地點|費用|申請資格|課程',context): continue
            else:
                if "News_Content.aspx" not in href: continue
                if not re.search(r'課程|培訓|工作坊|講座|報名|人才培育|短影音|新媒體|行銷', title+" "+context): continue
            items.append({"source":"高雄市政府青年局","title":title,"url":href,"dates":extract_dates(context),"context":context[:1500]})
            seen.add(href)
    return items

def inspect_taiwanjobs():
    r=get(SOURCES["taiwanjobs_conditions"])
    soup=BeautifulSoup(r.text,"html.parser")
    forms=[]
    for f in soup.find_all("form"):
        forms.append({"action":absolute(r.url,f.get("action")),"method":(f.get("method") or "get").lower(),
                      "inputs":[{"name":i.get("name"),"value":i.get("value"),"type":i.get("type")} for i in f.find_all(["input","select"])[:80]]})
    scripts=[absolute(r.url,s.get("src")) for s in soup.find_all("script",src=True)]
    links=[]
    for a in soup.find_all("a",href=True):
        txt=clean(a.get_text(" ",strip=True)); href=absolute(r.url,a["href"])
        if any(k in (txt+" "+href) for k in ["課程","course","training"]): links.append({"title":txt,"url":href})
    return {"forms":forms[:10],"scripts":scripts[-30:],"links":links[:120],"html_len":len(r.text),"title":clean(soup.title.get_text(" ",strip=True)) if soup.title else ""}

SCRAPERS={"ntpc":scrape_ntpc,"yip":scrape_yip,"startup":scrape_startup,"youthfirst":scrape_youthfirst,
          "taichung":scrape_taichung,"taipei":scrape_taipei,"kaohsiung":scrape_kaohsiung}


def background_audit():
    time.sleep(3)
    summary={}
    for name,fn in SCRAPERS.items():
        t=time.time()
        try:
            items=fn()
            result={"ok":True,"count":len(items),"sample_titles":[x.get("title") for x in items[:5]],"seconds":round(time.time()-t,2)}
        except Exception as e:
            result={"ok":False,"error":repr(e),"seconds":round(time.time()-t,2)}
        summary[name]=result
        print("CRAWL_SOURCE "+name+" "+json.dumps(result,ensure_ascii=False),flush=True)
    try:
        tj=inspect_taiwanjobs()
        result={"ok":True,"forms":tj.get("forms",[])[:3],"scripts":len(tj.get("scripts",[])),"links":len(tj.get("links",[]))}
    except Exception as e:
        result={"ok":False,"error":repr(e)}
    summary["taiwanjobs"]=result
    print("CRAWL_SOURCE taiwanjobs "+json.dumps(result,ensure_ascii=False),flush=True)
    print("CRAWL_STATUS "+json.dumps(summary,ensure_ascii=False),flush=True)

@app.get("/")
def root():
    return jsonify({"ok":True,"service":"Youth Course Radar crawler","sources":list(SOURCES.keys()),"date":TODAY})

@app.get("/api/status")
def status():
    out={}
    for name,fn in SCRAPERS.items():
        t=time.time()
        try:
            items=fn()
            out[name]={"ok":True,"count":len(items),"sample":items[:5],"seconds":round(time.time()-t,2)}
        except Exception as e:
            out[name]={"ok":False,"error":repr(e),"seconds":round(time.time()-t,2)}
    try: out["taiwanjobs_inspect"]={"ok":True,**inspect_taiwanjobs()}
    except Exception as e: out["taiwanjobs_inspect"]={"ok":False,"error":repr(e)}
    return jsonify(out)

@app.get("/api/source/<name>")
def source(name):
    if name=="taiwanjobs":
        return jsonify(inspect_taiwanjobs())
    fn=SCRAPERS.get(name)
    if not fn:return jsonify({"error":"unknown source"}),404
    return jsonify({"source":name,"items":fn()})

threading.Thread(target=background_audit, daemon=True).start()

if __name__=="__main__":
    app.run(host="0.0.0.0",port=10000)
