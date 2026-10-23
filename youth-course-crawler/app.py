
from flask import Flask, jsonify, request
import requests, re, time
from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlencode
from datetime import datetime, timezone, timedelta
import threading, json, os, hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)
UA = "Mozilla/5.0 (compatible; YouthCourseRadar/1.0; +https://youth-course-radar-tw-2026.onrender.com)"
requests.packages.urllib3.disable_warnings()
S = requests.Session()
S.headers.update({"User-Agent": UA, "Accept-Language":"zh-TW,zh;q=0.9,en;q=0.6"})

TODAY = "2026-10-23"
CACHE_ITEMS=[]
CACHE_HEALTH={}
CACHE_UPDATED=None
CACHE_LOCK=threading.Lock()

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
    "smelearning": "https://smelearning.sme.gov.tw/class_all.php",
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
    protected = any(x in host for x in ["startup.sme.gov.tw","youthfirst.yda.gov.tw","1catchjob.taichung.gov.tw","youth.kcg.gov.tw","smelearning.sme.gov.tw"])
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
    for page in range(1,50):
        url=f"https://www.youth.ntpc.gov.tw/youth/ch/app/course/list?id=181&module=course&page={page}&pageSize=15"
        try:
            r=get(url)
        except Exception:
            if page==1: raise
            break
        soup=BeautifulSoup(r.text,"html.parser")
        found=0
        for a in soup.find_all("a",href=True):
            href=absolute(r.url,a["href"])
            if "/course/view" not in href: continue
            title=clean(a.get_text(" ",strip=True))
            if not title or href in seen: continue
            parent=a.find_parent(["li","div","article","tr"])
            context=clean(parent.get_text(" ",strip=True)) if parent else title
            items.append({"source":"新北市青年局／新北有課","title":title,"url":href,"dates":extract_dates(context),"context":context[:1500]})
            seen.add(href); found+=1
        if found==0: break
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
    items=[]; seen=set(); detail_urls=[]
    for url in ["https://class.tpyd.gov.taipei/","https://class.tpyd.gov.taipei/participate/?node=0"]:
        try: r=get(url)
        except Exception: continue
        soup=BeautifulSoup(r.text,"html.parser")
        for a in soup.find_all("a",href=True):
            href=absolute(r.url,a["href"])
            if "mode=detail" in href and re.search(r'node=\d+',href) and href not in detail_urls:
                detail_urls.append(href)
    for href in detail_urls:
        try: r=get(href)
        except Exception: continue
        soup=BeautifulSoup(r.text,"html.parser")
        title=""
        for tag in ["h1","h2","h3"]:
            h=soup.find(tag)
            if h:
                title=clean(h.get_text(" ",strip=True))
                if title: break
        text=clean(soup.get_text(" ",strip=True))
        if not title or title in ["活動總覽","開放報名中","活動詳情"]:
            title=clean(soup.title.get_text(" ",strip=True)) if soup.title else ""
            title=re.sub(r'[-｜|].*$','',title).strip()
        if not title or len(title)<3: continue
        items.append({"source":"臺北市政府青年局","title":title,"url":href,"dates":extract_dates(text),"context":text[:2200]})
        seen.add(href)
    return items

def scrape_kaohsiung():
    items=[]; seen=set()
    url="https://youth.kcg.gov.tw/ResourceSearch.aspx?n=41&sms=10164"
    r=get(url); soup=BeautifulSoup(r.text,"html.parser")
    for a in soup.find_all("a",href=True):
        href=absolute(r.url,a["href"]); title=clean(a.get_text(" ",strip=True))
        if not title or href in seen or title in ["找課程","找資源","更多"]: continue
        # Walk upward until the entire resource card is captured.
        node=a
        context=title
        for _ in range(7):
            node=node.parent if node else None
            if not node: break
            txt=clean(node.get_text(" ",strip=True))
            if "課程時間" in txt and ("課程地點" in txt or "申請資格" in txt):
                context=txt; break
        if not re.search(r'課程時間',context): continue
        items.append({"source":"高雄市政府青年局／找課程","title":title,"url":href,"dates":extract_dates(context),"context":context[:2200]})
        seen.add(href)
    return items

def _parse_sme_page(page):
    last=None
    for attempt in range(3):
        try:
            r=get(SOURCES["smelearning"],params={"page":page,"price_sort":0})
            last=r
            break
        except Exception:
            time.sleep(0.35*(attempt+1))
    if last is None: raise RuntimeError(f"SME page {page} failed after retries")
    r=last
    soup=BeautifulSoup(r.text,"html.parser")
    out=[]; seen=set()
    for a in soup.find_all("a",href=True):
        raw=a.get("href") or ""
        m=re.search(r'class\.php\?course=(\d+)',raw)
        if not m: continue
        cid=m.group(1)
        href=f"https://smelearning.sme.gov.tw/class.php?course={cid}"
        if href in seen: continue
        node=a; context=clean(a.get_text(" ",strip=True)); heading=""
        for _ in range(10):
            node=node.parent if node else None
            if not node: break
            txt=clean(node.get_text(" ",strip=True))
            h=node.find(["h2","h3","h4","h5"])
            if h: heading=clean(h.get_text(" ",strip=True))
            if re.search(r'\d+\s*分鐘',txt) and ("免費" in txt or "收費" in txt):
                context=txt; break
        title=heading or clean(a.get_text(" ",strip=True))
        if not title or title in ["免費課程","收費課程","所有課程","課程分類"]:
            # Last fallback: search nearest heading around link.
            par=a.find_parent(["article","li","div","section"])
            hh=par.find(["h2","h3","h4","h5"]) if par else None
            title=clean(hh.get_text(" ",strip=True)) if hh else ""
        if not title: continue
        mm=re.search(r'(\d{1,4})\s*分鐘',context)
        mins=int(mm.group(1)) if mm else None
        out.append({"source":"中小企業網路大學校","title":title,"url":href,"dates":[],"context":context[:2200],
                    "hours":round(mins/60,2) if mins is not None else None,
                    "cost":0 if "免費" in context else None,"mode":"線上"})
        seen.add(href)
    return out

def scrape_smelearning():
    items=[]; seen=set(); failures=[]
    # Official site currently exposes 47 pagination pages. Use modest concurrency + retries to avoid dropped pages.
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs={ex.submit(_parse_sme_page,p):p for p in range(1,48)}
        for fut in as_completed(futs):
            p=futs[fut]
            try: rows=fut.result()
            except Exception as e:
                failures.append({"page":p,"error":repr(e)}); continue
            for x in rows:
                if x["url"] in seen: continue
                seen.add(x["url"]); items.append(x)
    # Read the site's own advertised total for completeness checking.
    advertised=None
    try:
        r=get(SOURCES["smelearning"])
        m=re.search(r'共有\s*([0-9,]+)\s*堂課程',clean(BeautifulSoup(r.text,"html.parser").get_text(" ",strip=True)))
        if m: advertised=int(m.group(1).replace(",",""))
    except Exception: pass
    for x in items:
        x["advertised_total"]=advertised
        x["crawl_failures"]=len(failures)
    print("SME_AUDIT "+json.dumps({"advertised":advertised,"actual":len(items),"failures":failures},ensure_ascii=False),flush=True)
    return items

def inspect_taiwanjobs():
    r=get(SOURCES["taiwanjobs_conditions"])
    soup=BeautifulSoup(r.text,"html.parser")
    scripts=[absolute(r.url,s.get("src")) for s in soup.find_all("script",src=True)]
    links=[]
    for a in soup.find_all("a",href=True):
        txt=clean(a.get_text(" ",strip=True)); href=absolute(r.url,a["href"])
        if any(k in (txt+" "+href).lower() for k in ["課程","course","training"]):
            links.append({"title":txt,"url":href})
    controls=[]
    for el in soup.find_all(["input","select","button","textarea"]):
        if el.get("id") or el.get("name"):
            controls.append({"tag":el.name,"id":el.get("id"),"name":el.get("name"),"value":el.get("value"),"type":el.get("type")})
    hints=set()
    raw=r.text
    for pat in [r'["\']([^"\']*(?:course|api|condition|query|search)[^"\']*)["\']',r'url\s*:\s*["\']([^"\']+)']:
        for m in re.finditer(pat,raw,re.I):
            x=clean(m.group(1))
            if 2<len(x)<300: hints.add(x)
    # Inspect same-domain JS bundles for AJAX endpoint strings.
    for js in scripts:
        if "course.taiwanjobs.gov.tw" not in js: continue
        try:
            rr=get(js); txt=rr.text
        except Exception: continue
        for m in re.finditer(r'["\']([^"\']*(?:/course/|api/|ajax|conditions)[^"\']*)["\']',txt,re.I):
            x=clean(m.group(1))
            if 2<len(x)<300: hints.add(x)
    api_context=[]
    for js in scripts:
        if "course.taiwanjobs.gov.tw" not in js: continue
        try:
            rr=get(js); txt=rr.text
        except Exception: continue
        for needle in ["/api/Course/paging","CourseTypeList","SourceType","courseLocation","CategoryMajorNames"]:
            pos=txt.find(needle)
            if pos>=0:
                api_context.append({"script":js,"needle":needle,"context":txt[max(0,pos-1800):pos+3500]})
    return {"scripts":scripts[-30:],"links":links[:120],"controls":controls[:250],"hints":sorted(hints)[:250],
            "api_context":api_context[:20],"html_len":len(r.text),"title":clean(soup.title.get_text(" ",strip=True)) if soup.title else ""}

SCRAPERS={"ntpc":scrape_ntpc,"yip":scrape_yip,"startup":scrape_startup,"youthfirst":scrape_youthfirst,
          "taichung":scrape_taichung,"taipei":scrape_taipei,"kaohsiung":scrape_kaohsiung,"smelearning":scrape_smelearning}


def infer_city(text):
    cities=["臺北市","新北市","桃園市","臺中市","臺南市","高雄市","基隆市","新竹市","新竹縣","宜蘭縣","苗栗縣","彰化縣","南投縣","雲林縣","嘉義市","嘉義縣","屏東縣","花蓮縣","臺東縣","澎湖縣","金門縣","連江縣"]
    for city in cities:
        if city in text: return city
    if "線上" in text or "online" in text.lower(): return "線上"
    return "地點待確認"

def infer_category(text):
    x=text.lower()
    rules=[
      ("資安／半導體",["資安","半導體","cyber","紅隊","藍隊"]),
      ("軟體開發／自動化",["java","python","程式","軟體","docker","雲端","自動化","agent","coding"]),
      ("數據分析／行銷科技",["數據","資料分析","power bi","sql","excel","輿情"]),
      ("AI／數位科技",["ai","人工智慧","chatgpt","生成式","數位轉型","iot"]),
      ("數位行銷／電商",["行銷","電商","社群","seo","短影音","品牌"]),
      ("創業／商業",["創業","商業","新創","募資","財務","稅務","補助"]),
      ("設計／影音／創意",["設計","攝影","影音","編劇","製片","藝術","表演"]),
      ("求職／職場軟實力",["職涯","就業","履歷","面試","溝通","專案管理","職場"]),
      ("工業／無人機",["無人機","製造","機電","木作","營造","bim"]),
      ("生活／自我發展",["靜心","彩妝","生活","心理","自我探索"]),
    ]
    for cat,ks in rules:
        if any(k in x for k in ks): return cat
    return "其他／跨域"

def infer_cost(text, explicit=None):
    if explicit is not None: return explicit
    if "免費" in text: return 0
    m=re.search(r'(?:NT\$|新臺幣|費用[:：]?)\s*([0-9,]+)',text,re.I)
    if m:
        try:return int(m.group(1).replace(",",""))
        except:return None
    return None

def infer_hours(text, explicit=None):
    if explicit is not None:return explicit
    m=re.search(r'(\d+(?:\.\d+)?)\s*小時',text)
    if m:return float(m.group(1))
    m=re.search(r'(\d+)\s*分鐘',text)
    if m:return round(int(m.group(1))/60,2)
    return None

def normalize_item(source_key,row):
    title=clean(row.get("title",""))
    context=clean(row.get("context",""))
    if not title:return None
    dates=row.get("dates") or extract_dates(context)
    text=" ".join([title,context,row.get("source","")])
    url=row.get("url") or SOURCES.get(source_key,"")
    uid=hashlib.sha1((source_key+"|"+url+"|"+title).encode("utf-8")).hexdigest()[:16]
    end=max(dates) if dates else None
    archived=bool(end and end < TODAY)
    mode=row.get("mode") or ("線上" if ("線上" in text or "online" in text.lower()) else "實體／待確認")
    return {
      "id":uid,"source_key":source_key,"source":row.get("source") or source_key,
      "title":title,"url":url,"context":context,"dates":dates,
      "city":infer_city(text),"mode":mode,"category":infer_category(text),
      "hours":infer_hours(text,row.get("hours")),"cost":infer_cost(text,row.get("cost")),
      "archived":archived,"data_level":"A" if len(context)>180 and url else "B",
      "last_checked_at":datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")
    }

def dedupe_items(items):
    out=[]; seen={}
    for x in items:
        # Same normalized title + date signature counts as same opportunity across sources.
        name=re.sub(r'[^0-9a-zA-Z\u4e00-\u9fff]+','',x["title"]).lower()
        sig=name+"|"+("|".join(x.get("dates") or []))
        if sig in seen:
            old=seen[sig]
            if x["source"] not in old.setdefault("sources",[old["source"]]): old["sources"].append(x["source"])
            if len(x.get("context",""))>len(old.get("context","")): old["context"]=x["context"]
            continue
        x["sources"]=[x["source"]];seen[sig]=x;out.append(x)
    return out

def background_audit():
    global CACHE_ITEMS,CACHE_HEALTH,CACHE_UPDATED
    time.sleep(3)
    all_items=[]; health={}
    for name,fn in SCRAPERS.items():
        t=time.time()
        try:
            rows=fn()
            norm=[normalize_item(name,x) for x in rows]
            norm=[x for x in norm if x]
            all_items.extend(norm)
            result={"ok":True,"count":len(rows),"normalized":len(norm),"seconds":round(time.time()-t,2)}
        except Exception as e:
            result={"ok":False,"count":0,"error":repr(e),"seconds":round(time.time()-t,2)}
        health[name]=result
        print("CRAWL_SOURCE "+name+" "+json.dumps(result,ensure_ascii=False),flush=True)
    try:
        tj=inspect_taiwanjobs()
        result={"ok":True,"count":0,"diagnostic":True,"scripts":len(tj.get("scripts",[])),"links":len(tj.get("links",[])),
                "controls":tj.get("controls",[])[:40],"hints":tj.get("hints",[])[:80],"api_context":tj.get("api_context",[])[:8]}
    except Exception as e:
        result={"ok":False,"count":0,"error":repr(e)}
    health["taiwanjobs"]=result
    print("CRAWL_SOURCE taiwanjobs "+json.dumps(result,ensure_ascii=False),flush=True)
    with CACHE_LOCK:
        CACHE_ITEMS=dedupe_items(all_items)
        CACHE_HEALTH=health
        CACHE_UPDATED=datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")
    print("CRAWL_TOTAL "+json.dumps({"total":len(CACHE_ITEMS),"health":health},ensure_ascii=False),flush=True)

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

@app.after_request
def cors(resp):
    resp.headers["Access-Control-Allow-Origin"]="*"
    resp.headers["Cache-Control"]="no-store"
    return resp

@app.get("/api/all")
def api_all():
    with CACHE_LOCK:
        items=list(CACHE_ITEMS);health=dict(CACHE_HEALTH);updated=CACHE_UPDATED
    include_archive=request.args.get("archive","0")=="1"
    if not include_archive: items=[x for x in items if not x.get("archived")]
    return jsonify({"items":items,"total":len(items),"health":health,"updated_at":updated,"archive_included":include_archive})

@app.get("/api/health")
def api_health():
    with CACHE_LOCK:return jsonify({"health":CACHE_HEALTH,"updated_at":CACHE_UPDATED,"cached_items":len(CACHE_ITEMS)})

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
