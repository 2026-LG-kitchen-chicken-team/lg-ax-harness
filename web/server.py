"""Serve a read-only local visual viewer. Never launch a CLI or model."""
from __future__ import annotations
import argparse
import base64
import hashlib
import ipaddress
import json
import mimetypes
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import threading
import time
import uuid
import urllib.parse
import urllib.request
import webbrowser
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from visuals import VisualRegistry, strict_json, write_json, link, private_data

ROOT=Path(__file__).resolve().parents[1]
STATIC=Path(__file__).parent/'static'

class WebServer(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self,address,registry):
        if address[0] not in ('127.0.0.1','::1'):raise ValueError('localhost 주소만 지원합니다.')
        self.registry=registry
        self.ui_seen=0
        super().__init__(address,Handler)

class Handler(BaseHTTPRequestHandler):
    protocol_version='HTTP/1.1'
    def log_message(self,*args):pass
    def handle(self):
        try:super().handle()
        except ConnectionError:pass
    def guard(self,asset=False):
        port=self.server.server_address[1]
        hosts={f'127.0.0.1:{port}',f'localhost:{port}',f'[::1]:{port}'}
        if self.headers.get('Host') not in hosts:raise PermissionError('잘못된 Host')
        origin=self.headers.get('Origin')
        if origin and origin not in {'http://'+host for host in hosts} and not (asset and origin=='null'):
            raise PermissionError('다른 웹사이트의 요청은 허용되지 않습니다.')
    def reply(self,status,raw,kind='application/json; charset=utf-8',asset=False,download=None):
        self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(raw)))
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer')
        if asset:
            csp="sandbox allow-scripts; default-src 'none'; script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; media-src 'self' blob:; worker-src 'none'; frame-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'self'"
            self.send_header('Access-Control-Allow-Origin','null')
        else:csp="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: https:; connect-src 'self'; frame-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
        self.send_header('Content-Security-Policy',csp)
        if download:self.send_header('Content-Disposition',"attachment; filename*=UTF-8''"+urllib.parse.quote(download,safe=''))
        self.end_headers();self.wfile.write(raw)
    def json(self,status,value):self.reply(status,json.dumps(value,ensure_ascii=False,allow_nan=False).encode())
    def do_GET(self):
        try:
            url=urllib.parse.urlsplit(self.path);query=urllib.parse.parse_qs(url.query)
            asset=url.path.startswith('/api/assets/');self.guard(asset=asset)
            if url.path=='/api/state':
                if self.headers.get('X-Viewer-UI')=='1':self.server.ui_seen=time.monotonic()
                return self.json(200,{**self.server.registry.state(),'viewer_id':getattr(self.server.registry,'viewer_id',None)})
            if url.path=='/api/data':return self.json(200,self.server.registry.data(query.get('watch',[''])[0],query.get('id',[''])[0],query.get('name',[''])[0]))
            if asset:
                parts=url.path.split('/',5)
                if len(parts)!=6:raise ValueError('시각 자료 주소 오류')
                watch,identifier,name=parts[3],parts[4],urllib.parse.unquote(parts[5])
                raw=self.server.registry.read(watch,identifier,name)
                kind=mimetypes.guess_type(name)[0] or 'application/octet-stream'
                if Path(name).suffix.lower() in ('.html','.htm','.js','.mjs','.css','.json','.svg'):kind+='; charset=utf-8'
                return self.reply(200,raw,kind,asset=True,download=Path(name).name if 'download' in query else None)
            files={'/':'index.html','/index.html':'index.html','/app.js':'app.js','/data-view.js':'data-view.js','/style.css':'style.css'}
            if url.path not in files:return self.json(404,{'error':'화면 파일을 찾을 수 없습니다.'})
            path=STATIC/files[url.path];kind=mimetypes.guess_type(path.name)[0] or 'text/plain'
            return self.reply(200,path.read_bytes(),kind+'; charset=utf-8')
        except PermissionError as exc:self.json(403,{'error':str(exc)})
        except (ValueError,OSError,UnicodeError,RecursionError) as exc:self.json(400,{'error':str(exc)[:500]})
    def do_POST(self):
        self.close_connection=True;self.json(405,{'error':'이 화면은 파일 표시만 합니다. 요청과 실행은 원래 CLI에서 진행하세요.'})
    do_PUT=do_POST
    do_PATCH=do_POST
    do_DELETE=do_POST

def public_image(url):
    if not isinstance(url,str) or len(url)>4096:return None
    try:parsed=urllib.parse.urlsplit(url)
    except ValueError:return None
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password:return None
    host=parsed.hostname.lower()
    if host=='localhost' or host.endswith(('.localhost','.local','.internal')):return None
    try:
        if not ipaddress.ip_address(host).is_global:return None
    except ValueError:pass
    return url

def output_documents(packet):
    """Whitelist public visual payloads; never copy prompts, reasoning or arbitrary logs."""
    name=str(packet.get('tool_name',''));input_value=packet.get('tool_input') or {}
    command=str(input_value.get('command',input_value.get('cmd',input_value.get('code','')))) if isinstance(input_value,dict) else ''
    output=packet.get('tool_response');documents=[]
    def images(value,depth=0,image_list=False):
        if depth>5:return
        if isinstance(value,dict):
            kind=value.get('type')
            if kind in ('reasoning','thinking'):return
            if kind in ('image','image_url','input_image','output_image') or image_list:
                url=value.get('image_url',value.get('url'));url=url.get('url') if isinstance(url,dict) else url
                if public_image(url):documents.append({'kind':'remote_image','url':url,'caption':str(value.get('caption','CLI가 반환한 이미지'))[:200]})
                mime=value.get('mimeType',value.get('mime_type'))
                encoded=value.get('data')
                if mime in ('image/png','image/jpeg','image/webp','image/gif') and isinstance(encoded,str) and len(encoded)<3*1024*1024:
                    try:base64.b64decode(encoded,validate=True);documents.append({'kind':'inline_image','data_url':'data:'+mime+';base64,'+encoded,'caption':'CLI가 반환한 이미지'})
                    except ValueError:pass
            if kind=='text':images(value.get('text',''),depth+1)
            for key in ('content','images','results','output','image'):
                if key in value:images(value[key],depth+1,key in ('images','image'))
        elif isinstance(value,list):
            for item in value[:100]:images(item,depth+1,image_list)
        elif isinstance(value,str):
            if value.lstrip().startswith(('{','[')) and len(value)<3*1024*1024:
                try:images(strict_json(value.encode()),depth+1,image_list)
                except (ValueError,RecursionError):pass
            for caption,url in re.findall(r'!\[([^\]]*)\]\((https://[^\s)]+)\)',value[:1024*1024]):
                if public_image(url):documents.append({'kind':'remote_image','url':url,'caption':caption[:200]})
    images(output)
    if packet.get('hook_event_name')=='Stop':images(packet.get('last_assistant_message',''))
    structured=output.get('structuredContent',output.get('structured_content')) if isinstance(output,dict) else None
    if isinstance(structured,dict) and not private_data(structured) and isinstance(structured.get('columns'),list) and isinstance(structured.get('rows'),list):
        columns=structured['columns'];rows=structured['rows']
        if all(isinstance(c,str) for c in columns) and all(isinstance(row,list) for row in rows):
            documents.append({'kind':'matrix','columns':columns[:40],'rows':[row[:40] for row in rows[:200]],'total_rows':len(rows),'note':'실제 도구에 명시된 표 데이터'})
    elif isinstance(structured,dict) and not private_data(structured) and isinstance(structured.get('rows'),list):
        rows=structured['rows']
        if rows and all(isinstance(row,dict) for row in rows):
            documents.append({'kind':'table','value':rows[:200],'note':'실제 도구의 구조화된 반환 자료'})
    harness=bool(re.search(r'(?:product-tools[/\\]cli\.py|skills[/\\][\w-]+[/\\]scripts[/\\]run\.py)',command))
    retrieval=(harness and any(operation in command for operation in ('retrieve_reviews','retrieve_product_facts'))) or bool(re.search(r'(?:^|__)retrieve_(?:reviews|product_facts)$',name))
    if output is not None:
        values=[]
        def unpack(value,depth=0):
            if depth>3:return
            if isinstance(value,str):
                text=value[:2*1024*1024];decoder=json.JSONDecoder()
                for match in list(re.finditer(r'[\[{]',text))[:100]:
                    try:found,_=decoder.raw_decode(text,match.start());values.append(found)
                    except (ValueError,RecursionError):pass
            elif isinstance(value,dict):
                values.append(value)
                for key in ('stdout','output','text','content','aggregated_output','structuredContent','structured_content'):
                    if key in value:unpack(value[key],depth+1)
            elif isinstance(value,list):
                for item in value[:20]:unpack(item,depth+1)
        unpack(output)
        for value in values:
            if not isinstance(value,dict):continue
            known_contract=(isinstance(value.get('data_version'),str) and re.fullmatch(r'[a-f0-9]{64}',str(value.get('dataset_fingerprint',''))) and isinstance(value.get('scope'),dict) and value.get('semantic_status')=='unverified')
            if not retrieval and not known_contract:continue
            rows=next((value[key] for key in ('records','sources','results','items') if isinstance(value.get(key),list)),None)
            if not rows or not all(isinstance(row,dict) and ('source_id' in row or 'model_id' in row) for row in rows):continue
            columns=['source_id','model_id','model_version','document_version','kind','text','location','data_version','origin']
            projected=[{key:row.get(key) for key in columns} for row in rows[:200]]
            if private_data(projected):continue
            documents.append({'kind':'table','value':projected,'data_version':value.get('data_version'),'total':value.get('total'),'truncated':value.get('truncated'),'purpose':value.get('purpose'),'synthetic':value.get('synthetic'),'note':'실제 도구 반환 자료 · 의미 검토 미확인'});break
    return documents

def load_config(args):
    config=strict_json(args.config.read_bytes()) if args.config.is_file() else {}
    return config

def cached_evidence(config,state):
    """Project the harness's existing retrieval cache through a read-only connection."""
    warnings=[];incoming=Path(state)/'incoming'
    for workspace in config.get('workspaces',[]):
        database=Path(workspace)/'runtime-data/product.sqlite'
        if not database.is_file():continue
        if any(link(part) for part in (Path(workspace),database.parent,database)):
            warnings.append('연결된 폴더의 조회 DB는 읽지 않습니다. 실제 하네스 폴더를 지정하세요.');continue
        try:
            with closing(sqlite3.connect(database.absolute().as_uri()+'?mode=ro',uri=True,timeout=.5)) as connection:
                connection.execute('PRAGMA query_only=ON')
                rows=connection.execute('SELECT cache_key,payload,payload_hash FROM retrieval_cache WHERE length(payload)<=1048576 ORDER BY rowid DESC LIMIT 200').fetchall()
            for key,payload,expected in rows:
                value=strict_json(payload.encode())
                canonical=json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)
                if hashlib.sha256(canonical.encode()).hexdigest()!=expected:
                    warnings.append('저장된 근거 조회 자료의 지문이 달라 해당 자료를 추가하지 않았습니다.');continue
                records=value.get('records') if isinstance(value,dict) else None
                if not isinstance(records,list) or not records:continue
                projected=[{k:record.get(k) for k in ('source_id','model_id','model_version','document_version','kind','text','location','data_version','origin')} for record in records[:200] if isinstance(record,dict)]
                if private_data(projected):continue
                wrapper={'viewer_record':'public_cli_output_v1','source':'하네스에 저장된 조회 자료','kind':'table','value':projected,'data_version':value.get('data_version'),'synthetic':value.get('synthetic'),'purpose':value.get('purpose'),'truncated':value.get('truncated'),'note':'저장된 조회 결과 · 현재 요청과의 연결/원문 의미는 미확인','cache_key':key}
                suffix=hashlib.sha256((str(database.absolute())+str(key)+expected).encode()).hexdigest()[:24]
                destination=incoming/('저장된 근거-'+suffix+'.json')
                if not destination.exists():write_json(destination,wrapper)
        except (sqlite3.Error,ValueError,OSError,UnicodeError):warnings.append('저장된 근거 조회 자료를 아직 읽을 수 없습니다. 다음 관찰에서 다시 확인합니다.')
    return list(dict.fromkeys(warnings))

def viewer_id(args):
    material=str(args.state.absolute()).encode()+(args.config.read_bytes() if args.config.is_file() else b'')
    for path in (Path(__file__),Path(__file__).with_name('visuals.py')):material+=path.read_bytes()
    return hashlib.sha256(material).hexdigest()

def ensure_viewer(args):
    url=f'http://127.0.0.1:{args.port}/api/state'
    def available():
        try:
            with urllib.request.urlopen(url,timeout=.5) as response:
                value=json.load(response)
                return value.get('scope')=='saved_local_files' and value.get('viewer_id')==viewer_id(args)
        except (OSError,ValueError):return False
    if available():return
    args.state.mkdir(parents=True,exist_ok=True)
    lock=args.state/'startup.lock'
    try:fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    except FileExistsError:
        if time.time()-lock.stat().st_mtime>15:lock.unlink()
        for _ in range(25):
            if available():return
            time.sleep(.1)
        raise ValueError('로컬 뷰어 시작을 확인하지 못했습니다.')
    try:
        os.close(fd)
        with (args.state/'service.log').open('ab') as log:
            options={'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {'start_new_session':True}
            subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),'--config',str(args.config),'--state',str(args.state),'--port',str(args.port),'--auto-open'],stdin=subprocess.DEVNULL,stdout=log,stderr=log,**options)
        for _ in range(15):
            if available():break
            time.sleep(.1)
        if not available():raise ValueError('로컬 뷰어 주소를 확인하세요. 이미 다른 프로그램이 사용 중일 수 있습니다.')
    finally:lock.unlink(missing_ok=True)

def receive_hook(args,packet):
    config=load_config(args);cwd=Path(str(packet.get('cwd',''))).absolute()
    if not any(cwd==Path(path).absolute() for path in config.get('workspaces',[])):raise ValueError('등록된 하네스 작업 폴더의 자료만 수집합니다.')
    event=packet.get('hook_event_name')
    if event not in ('SessionStart','PostToolUse','Stop'):return
    ensure_viewer(args)
    incoming=args.state/'incoming';incoming.mkdir(parents=True,exist_ok=True)
    documents=output_documents(packet)
    for document in documents:
        wrapper={'viewer_record':'public_cli_output_v1','source':'실제 CLI 공개 출력','tool':str(packet.get('tool_name',''))[:100],'session_id':str(packet.get('session_id',''))[:160],**document}
        digest=hashlib.sha256(json.dumps(wrapper,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:24]
        label='검색 이미지' if document['kind'] in ('remote_image','inline_image') else '조사한 근거'
        write_json(incoming/(label+'-'+digest+'.json'),wrapper)
    write_json(args.state/'callbacks'/(uuid.uuid4().hex+'.json'),{'event':event,'session_id':str(packet.get('session_id',''))[:160],'time':time.time(),'documents':len(documents),'scope':'public_visual_outputs_only'})
    if event=='PostToolUse':
        response=packet.get('tool_response') or {}
        if isinstance(response,str) and response.lstrip().startswith('{'):
            try:response=strict_json(response.encode())
            except ValueError:pass
        content=response.get('content',[]) if isinstance(response,dict) else []
        if isinstance(response,str):content=[{'type':'text','text':response}]
        if documents or any(isinstance(block,dict) and block.get('type')=='text' and re.match(r"\s*\{\s*operation:\s*['\"]retrieve_(?:reviews|product_facts)['\"],\s*ok:\s*true",block.get('text','')) for block in content):
            write_json(args.state/'reveal.json',{'time':time.time(),'reason':'public_retrieval_returned','session_id':str(packet.get('session_id',''))[:160]})

def install_hook(args,workspace,engine):
    workspace=workspace.absolute()
    if workspace==Path.home() or not workspace.is_dir():raise ValueError('실제 하네스 폴더를 지정하세요.')
    config=load_config(args)
    if not any(workspace==Path(path).absolute() for path in config.get('workspaces',[])):raise ValueError('viewer 설정의 workspaces에 먼저 등록하세요.')
    code="& "+' '.join("'"+str(value).replace("'","''")+"'" for value in [sys.executable,str(Path(__file__).resolve()),'--hook','--config',args.config,'--state',args.state,'--port',str(args.port)])
    command='powershell.exe -NoProfile -NonInteractive -Command "'+code+'"' if os.name=='nt' else __import__('shlex').join([sys.executable,str(Path(__file__).resolve()),'--hook','--config',str(args.config),'--state',str(args.state),'--port',str(args.port)])
    path=workspace/('.codex/hooks.json' if engine=='codex' else '.claude/settings.local.json')
    settings=strict_json(path.read_bytes()) if path.is_file() else {};hooks=settings.setdefault('hooks',{})
    for event in ('SessionStart','PostToolUse','Stop'):
        groups=hooks.setdefault(event,[])
        if any(handler.get('command')==command for group in groups for handler in group.get('hooks',[])):continue
        handler={'type':'command','command':command,'timeout':8}
        if event=='PostToolUse':handler['async']=True
        group={'hooks':[handler]}
        if event=='SessionStart':group['matcher']='startup|resume|clear|fork'
        groups.append(group)
    if path.is_file():
        backup=args.state/'hook-backups'/(engine+'-'+hashlib.sha256(str(path).encode()).hexdigest()[:12]+'.json')
        if not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(path.read_bytes())
    write_json(path,settings)
    return path

def open_on_new_output(server,changes,enabled,last_open=None,now=None,opener=webbrowser.open):
    now=time.monotonic() if now is None else now
    if not enabled or not changes or now-server.ui_seen<=10:return last_open
    if last_open is not None and now-last_open<=30:return last_open
    if opener(f'http://127.0.0.1:{server.server_address[1]}'):return now
    return last_open

def main():
    parser=argparse.ArgumentParser(description='CLI 출력의 시각 자료를 한 페이지에서 보는 로컬 뷰어')
    parser.add_argument('--watch',action='append',help='관찰할 출력 폴더. 여러 번 지정 가능')
    parser.add_argument('--config',type=Path,default=ROOT/'.harness/viewer.json')
    parser.add_argument('--state',type=Path,default=ROOT/'.harness/viewer')
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--auto-open',action='store_true',help='새 시각 자료가 생길 때만 브라우저를 자동으로 엽니다')
    parser.add_argument('--hook',action='store_true',help='기존 native CLI의 관찰 hook')
    parser.add_argument('--install-hook',choices=('codex','claude'))
    parser.add_argument('--workspace',type=Path)
    args=parser.parse_args()
    args.config=args.config.absolute();args.state=args.state.absolute()
    config=load_config(args)
    if args.install_hook:
        if not args.workspace:parser.error('--workspace가 필요합니다')
        print(install_hook(args,args.workspace,args.install_hook));return
    if args.hook:
        packet={}
        try:
            raw=sys.stdin.buffer.read(4*1024*1024+1)
            if len(raw)>4*1024*1024:raise ValueError('hook 입력 상한')
            packet=strict_json(raw)
            if not isinstance(packet,dict):raise ValueError('hook 입력은 JSON 객체여야 합니다.')
            receive_hook(args,packet)
        except (ValueError,OSError,UnicodeError) as exc:
            args.state.mkdir(parents=True,exist_ok=True)
            with (args.state/'hook-errors.log').open('a',encoding='utf-8') as log:log.write(type(exc).__name__+': '+str(exc)[:300]+'\n')
        if isinstance(packet,dict) and packet.get('hook_event_name')=='Stop':print('{}')
        return
    watches=[{'path':p,'label':Path(p).name or '시각 자료'} for p in args.watch] if args.watch else config.get('watch',[{'path':str(ROOT/'runtime-data/exports'),'label':'하네스 결과'},{'path':str(ROOT/'runtime-data/visuals'),'label':'시각 자료'}])
    if not isinstance(watches,list) or not watches or len(watches)>8 or any(not isinstance(w,dict) or not isinstance(w.get('path'),str) or not w['path'] for w in watches):raise ValueError('출력 폴더를 1~8개 지정하세요.')
    watches.extend({'path':str(Path(path)),'label':'CLI 시각 자료','new_only':True} for path in config.get('workspaces',[]))
    watches.append({'path':str(args.state/'incoming'),'label':'실행 중 나온 자료','collected':True})
    registry=VisualRegistry(args.state,watches);registry.viewer_id=viewer_id(args);registry.extra_warnings=cached_evidence(config,args.state);registry.scan()
    stopped=threading.Event()
    server=WebServer(('127.0.0.1',args.port),registry)
    last_open=None
    reveal_path=args.state/'reveal.json'
    last_reveal=reveal_path.stat().st_mtime_ns if reveal_path.is_file() else 0
    def watch():
        nonlocal last_open,last_reveal
        while not stopped.wait(1):
            try:
                registry.extra_warnings=cached_evidence(config,args.state)
                changes=registry.scan()
                reveal=args.state/'reveal.json'
                if reveal.is_file() and reveal.stat().st_mtime_ns>last_reveal:
                    last_reveal=reveal.stat().st_mtime_ns
                    if registry.state()['items']:changes=changes or [{'id':'public_retrieval_returned'}]
                before_open=last_open
                last_open=open_on_new_output(server,changes,args.auto_open,last_open)
                if last_open!=before_open:write_json(args.state/'browser-open.json',{'opened_at':time.time(),'url':f'http://127.0.0.1:{server.server_address[1]}','trigger':'new_visual_output','os_browser_launch_returned':True,'asset_ids':[item['id'] for item in changes]})
            except OSError:pass
    threading.Thread(target=watch,daemon=True).start()
    print(f'Visual viewer: http://127.0.0.1:{server.server_address[1]}',flush=True)
    try:server.serve_forever(poll_interval=.25)
    except KeyboardInterrupt:pass
    finally:stopped.set();server.server_close()

if __name__=='__main__':main()
