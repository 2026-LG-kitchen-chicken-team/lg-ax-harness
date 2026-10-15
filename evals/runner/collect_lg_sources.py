"""Development collection of public LG pages. No model call or answer selection.

Keeps raw HTML and observed excerpts outside Git. Exact SKU is taken from the
publisher DOM, never obtained by deleting a suffix. This is a static HTML
adapter: dynamic next pages, option attribution and sufficiency need review.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
from html import unescape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import time
from urllib.request import Request, build_opener
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "product-tools"))
from product_tools.contracts import canonical
from product_tools.dataset import Dataset
from product_tools.state import StateStore
from product_tools.conversation import Conversation
from product_tools.web_evidence import MAX_PAGE_BYTES, NoRedirect, PublicHTTPSHandler, WebEvidence, public_url

COLLECTION_UA='LG-AX-evidence-collection/1.0'
ROBOTS_CACHE={}


def robots_permission(lines,url,agent=COLLECTION_UA):
    rules=RobotFileParser();rules.parse(lines)
    return rules.can_fetch(agent,url)


def require_robots(url,opener):
    parsed=urlsplit(url);origin=parsed.scheme+'://'+parsed.netloc
    if origin not in ROBOTS_CACHE:
        try:
            with opener.open(Request(origin+'/robots.txt',headers={'User-Agent':COLLECTION_UA,'Accept-Encoding':'identity'}),timeout=8) as response:
                raw=response.read(262145)
                if len(raw)>262144:raise ValueError('Robots response exceeds policy limit')
                ROBOTS_CACHE[origin]=raw.decode(response.headers.get_content_charset() or 'utf-8').splitlines()
        except HTTPError as error:
            if error.code not in (404,410):raise ValueError('Robots policy unavailable; collection not attempted') from error
            ROBOTS_CACHE[origin]=[]
    if not robots_permission(ROBOTS_CACHE[origin],url):
        raise ValueError('Publisher robots policy disallows this collector UA; use an actually authorized channel, never impersonate another bot')


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts=[]; self.hidden=0
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"): self.hidden+=1
    def handle_endtag(self, tag):
        if tag in ("script", "style"): self.hidden=max(0,self.hidden-1)
    def handle_data(self, value):
        if not self.hidden:self.parts.append(value)


def visible(raw):
    parser=VisibleText();parser.feed(raw)
    return " ".join(" ".join(parser.parts).split())


class SectionText(VisibleText):
    """Only the publisher spec container; navigation/FAQ are not model specs."""
    def __init__(self, class_name='spec_container'):
        super().__init__(); self.depth=0; self.selected=False;self.class_name=class_name
    def handle_starttag(self,tag,attrs):
        if not self.selected and self.depth==0 and self.class_name in dict(attrs).get('class','').split():
            self.selected=True;self.depth=1;return
        if self.depth:
            if tag not in ('img','input','br','hr','meta','link','source','wbr','area','embed','param','track','col'):self.depth+=1
            super().handle_starttag(tag,attrs)
    def handle_endtag(self,tag):
        if self.depth and tag not in ('img','input','br','hr','meta','link','source','wbr','area','embed','param','track','col'):
            super().handle_endtag(tag);self.depth-=1
    def handle_data(self,value):
        if self.depth:super().handle_data(value)


def spec_section(raw):
    parser=SectionText();parser.feed(raw)
    return ' '.join(' '.join(parser.parts).split())


def digest(value):return hashlib.sha256(value).hexdigest()
def save(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding="utf-8")


def fetch(url, folder):
    url=public_url(url)
    opener=build_opener(NoRedirect(),PublicHTTPSHandler())
    require_robots(url,opener)
    request=Request(url,headers={"User-Agent":COLLECTION_UA,"Accept-Encoding":"identity"})
    start=time.monotonic()
    with opener.open(request,timeout=8) as response:
        encoding=response.headers.get("Content-Encoding","identity").lower()
        if encoding not in ("","identity"):raise ValueError("Unsupported encoded response")
        raw=response.read(MAX_PAGE_BYTES+1)
        if len(raw)>MAX_PAGE_BYTES:raise ValueError("Page exceeds retained raw limit")
        if response.headers.get_content_type() not in ("text/html","text/plain"):raise ValueError("Native PDF reader required")
        charset=response.headers.get_content_charset() or "utf-8"
        text=raw.decode(charset)
    name=digest(url.encode())[:20]
    (folder/(name+".html")).write_bytes(raw)
    return text,{"url":url,"raw_sha256":digest(raw),"raw_bytes":len(raw),"charset":charset,"seconds":time.monotonic()-start,"retained_file":name+".html"}


def sku_header(raw):
    headers=[]
    for match in re.finditer(r"<[^>]+\bdata-product-code\s*=\s*([\"'])(.*?)\1[^>]*>",raw,re.S|re.I):
        if match[2].strip():headers.append((unescape(match[2]).strip(),match[0]))
    products=[]
    for script in re.finditer(r'<script\b[^>]*type\s*=\s*([\"\'])application/ld\+json\1[^>]*>(.*?)</script>',raw,re.S|re.I):
        try:objects=json.loads(script[2])
        except ValueError:continue
        if isinstance(objects,dict):objects=objects.get("@graph",[objects])
        if not isinstance(objects,list):continue
        for item in objects:
            if isinstance(item,dict) and item.get("@type")=="Product" and isinstance(item.get("sku"),str):
                products.append((item["sku"],script[2]))
    if headers:
        if len({sku for sku,_ in headers})!=1 or any(sku!=headers[0][0] for sku,_ in products):
            raise ValueError("Ambiguous publisher exact SKU signals; do not select the first related product or infer an alias")
        return headers[0]
    if len(products)==1:
        sku,source=products[0]
        literal=re.search(r'"sku"\s*:\s*"'+re.escape(sku)+'"',source)
        if literal:return sku,literal[0]
    raise ValueError("No unambiguous publisher exact SKU attribute/Product JSON-LD; do not infer an alias")


def review_rows(raw):
    starts=list(re.finditer(r"<li\b[^>]*\bdata-review-id\s*=\s*([\"'])(.*?)\1[^>]*>",raw,re.S|re.I))
    rows=[]
    for match in starts:
        depth=1;end=None
        for tag in re.finditer(r'</?li\b[^>]*>',raw[match.end():],re.S|re.I):
            depth+=-1 if tag[0].startswith('</') else 1
            if depth==0:
                end=match.end()+tag.end();break
        if end is None:continue
        part=raw[match.start():end]
        paragraph=re.search(r"<p\b[^>]*class\s*=\s*([\"'])[^\"']*\bmessage\b[^\"']*\1[^>]*>(.*?)</p>",part,re.S|re.I)
        if not paragraph:continue
        text=visible(paragraph[2]);date=re.search(r"구매 일자</em>\s*([^<]+)",part)
        mid=re.search(r'data-model-id\s*=\s*([\"\'])(.*?)\1',match[0])
        rows.append({"review_id":unescape(match[2]),"text":text,"purchase_date":date[1].strip().replace(".","-") if date else None,
            "publisher_product_id":unescape(mid[2]) if mid else None,
            "metadata":visible(part[:paragraph.start()]),"text_coverage":"static_message_paragraph_observed; expansion/photos/replies and author option identity not certified"})
    return rows


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plan",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--replay",type=Path,help="Reuse immutable captured raw HTML, preserving its SHA; no fresh HTTP observation")
    args=ap.parse_args()
    if args.out.exists():ap.error("Use a fresh output folder; originals are never replaced")
    args.out.mkdir(parents=True);raw_folder=args.out/"raw";raw_folder.mkdir()
    store=StateStore(args.out/"runtime-data/product.sqlite",Dataset(ROOT/"data/business/empty"))
    conversation=Conversation(store,args.out);web=WebEvidence(store.path,args.out)
    plan=json.loads(args.plan.read_text(encoding="utf-8"));observations=[];models=[];reviews=[];scans=[];requests=[];seen=set()
    started=datetime.now(timezone.utc).isoformat()
    if args.replay:
        old=json.loads((args.replay/'collection.json').read_text(encoding='utf-8'))
        retained={s['url']:s for s in old['scans'] if s.get('status')=='observed' and s.get('retained_file')}
    def obtain(url):
        if not args.replay:return fetch(url,raw_folder)
        trace=dict(retained[url]);raw=(args.replay/'raw'/trace['retained_file']).read_bytes()
        if digest(raw)!=trace['raw_sha256']:raise ValueError('Replay original SHA mismatch')
        (raw_folder/trace['retained_file']).write_bytes(raw)
        trace['replayed_from']=str(args.replay);trace['fresh_http']=False
        return raw.decode(trace['charset']),trace
    # This is development corpus preparation, not a timed native AI task.
    try:
        for index,target in enumerate(plan["products"]):
            request=conversation.open_request({"question":target["question"],"user_submitted":True})
            research=request["research_id"];requests.append(request)
            web.configure({"research_id":research,"max_pages":100,"reason":"Static corpus preparation; page cap is not sufficiency certification"})
            def capture(url,text,label):
                return web.collect({"research_id":research,"page_id":label,"url":url,"observed_text":text,
                    "native_tool_name":"exec_command public HTTPS static DOM extraction; no JavaScript/browser execution","preview_chars":256},browser=True)
            try:
                page,trace=obtain(target["url"]);scans.append({**trace,"family":target["family"],"kind":"product_document","status":"observed"})
                sku,header=sku_header(page)
                if sku in seen:
                    scans[-1]["registration"]="same exact SKU already retained";continue
                seen.add(sku)
                scope={"model_id":sku,"model_version":"unspecified","document_version":"observed-"+datetime.now(timezone.utc).date().isoformat().replace("-","")}
                identity_id="identity-"+digest(sku.encode())[:16]
                snap=capture(target["url"],header,"identity-"+str(index))
                models.append({**scope,"name":target.get("name",sku),"product_family":target["family"],"synthetic":False,"spec_source_id":identity_id,
                    "identity_review":{"source_id":identity_id,"manufacturer":"LG전자","authority":"manufacturer","rationale":"Observed publisher DOM exact product code on its public product page; no base/SKU equivalence or hardware version certified"}})
                def entry(sid,kind,text,snapshot,location):
                    return {"snapshot_id":snapshot["snapshot_id"],"source_id":sid,"kind":kind,"scope":scope,"location":location,"text":text,"support_quote":text,
                        "published_date":None,"model_matching":"explicit_model_verified","purchase_verified":None,"sponsorship":None}
                observations.append({**entry(identity_id,"product_fact",header,snap,"Exact SKU in manufacturer DOM attribute"),"feature_key":"product_identity","availability":"present","research_id":research})
                spec=spec_section(page)
                if not spec:raise ValueError('Publisher spec container not observed; no generic FAQ fallback')
                # Preserve all extracted section chunks, not just the first few facts.
                for piece in range(0,len(spec),2800):
                    quote=spec[piece:piece+2800]
                    snapshot=capture(target["url"],header+"\n"+quote,"spec-"+str(index)+"-"+str(piece))
                    observations.append({**entry("spec-"+digest((sku+str(piece)).encode())[:16],"product_fact",quote,snapshot,"Observed spec section text window "+str(piece)),
                        "feature_key":"observed_spec_section_"+str(piece),"availability":"present","research_id":research})
                product_ids=list(dict.fromkeys(re.findall(r"\bMD[0-9]{6,}\b",target["url"])))
                if not product_ids:raise ValueError("No observed product identity query for review discovery")
                review_url="https://www.lge.co.kr/mkt/review/"+product_ids[0]+"/pdpReviewListPopup"
                body,trace=obtain(review_url);scans.append({**trace,"family":target["family"],"kind":"review_list","status":"observed"})
                review_sku,review_header=sku_header(body)
                if review_sku!=sku:raise ValueError("Review exact SKU differs; do not transfer reviews")
                rows=review_rows(body)
                for row in rows:
                    review_meta={**row,"model_id":sku,"source_url":review_url,"source_ids":[],"research_id":research}
                    if row['publisher_product_id']!=product_ids[0]:
                        review_meta['disposition']='wrong_model' if row['publisher_product_id'] else 'uncertain_identity'
                        reviews.append(review_meta);continue
                    if not row["text"]:
                        review_meta["disposition"]="insufficient_context";reviews.append(review_meta);continue
                    snapshot=capture(review_url,review_header+"\n"+"data-review-id=\""+row["review_id"]+"\"\n"+row["metadata"]+"\n"+row["text"],"review-"+str(index)+"-"+row["review_id"])
                    for offset in range(0,len(row["text"]),2800):
                        sid="review-"+digest((review_url+row["review_id"]+str(offset)).encode())[:18]
                        observations.append({**entry(sid,"review",row["text"][offset:offset+2800],snapshot,"Publisher review ID "+row["review_id"]+" text offset "+str(offset)),"model_matching":"product_page_association","research_id":research})
                        review_meta["source_ids"].append(sid)
                    review_meta.update(snapshot_id=snapshot["snapshot_id"],disposition="retained")
                    reviews.append(review_meta)
                scans[-1].update(static_review_list_count=len(rows),limitations=["initial server list; no dynamic pagination executed","option/author identity not verified","positive/negative/long-term representativeness not certified"])
            except Exception as exc:
                scans.append({"url":target["url"],"family":target["family"],"status":"failed_or_partial","reason":type(exc).__name__+": "+str(exc)})
            save(args.out/"progress.json",{"models":len(models),"review_observations":len(reviews),"source_records":len(observations),"scans":scans})
    finally:
        web.close();store.close()
    # Different requests have distinct snapshot journals; import each request separately.
    grouped=[]
    for request in requests:
        rid=request["research_id"];records=[{k:v for k,v in o.items() if k!="research_id"} for o in observations if o["research_id"]==rid]
        active_scopes={canonical(o["scope"]) for o in records}
        selected=[m for m in models if canonical({k:m[k] for k in ("model_id","model_version","document_version")}) in active_scopes]
        if records:
            file="import-"+str(len(grouped))+".json";save(args.out/file,{"research_id":rid,"data_version":"collected-"+digest(rid.encode())[:16],"new_models":selected,"observations":records});grouped.append({"input_file":file,"research_id":rid,"records":len(records)})
    result={"started_utc":started,"ended_utc":datetime.now(timezone.utc).isoformat(),"models":models,"review_observations":reviews,
        "scans":scans,"imports":grouped,"mode":"development corpus preparation; AI native end-to-end not run","coverage_certified":False,"replay_from":str(args.replay) if args.replay else None,
        "base_model_equivalence":"not asserted","limits":["No dynamic next-page/low-star enumeration","Raw DOM is separate from visible excerpt and catalog records","Static page content and current DOM associations need independent review"]}
    save(args.out/"collection.json",result)
    print(json.dumps({"models":len(models),"reviews":len(reviews),"source_records":len(observations),"failed_or_partial":sum(s['status']!='observed' for s in scans),"coverage_certified":False}))


if __name__=="__main__":main()
