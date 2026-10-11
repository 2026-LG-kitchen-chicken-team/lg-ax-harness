"""Read-only watched outputs with bounded, immutable local previews."""
from __future__ import annotations
import csv
import hashlib
from html.parser import HTMLParser
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import threading
import time
import urllib.parse
import uuid

TYPES={'.html':'html','.htm':'html','.png':'image','.jpg':'image','.jpeg':'image','.webp':'image','.gif':'image','.svg':'image','.pdf':'pdf','.csv':'csv','.tsv':'csv','.json':'json'}
ASSETS=set(TYPES)|{'.js','.mjs','.css','.woff','.woff2','.ttf','.wasm'}
SKIP={'.git','.venv','.harness','node_modules','__pycache__','credentials','secrets','auth','config','configs','settings','cache','caches','uv-cache','logs','sessions','inputs','requests'}
PRIVATE_KEYS={'password','passwd','secret','clientsecret','credentials','credential','accesstoken','refreshtoken','idtoken','authtoken','authorization','apikey','privatekey','auth','token','reasoning','thinking'}
MAX_FILE=20*1024*1024
MAX_BUNDLE=32*1024*1024
MAX_ITEMS=80
MAX_VERSIONS=240
MAX_STORED=512*1024*1024

def sha(raw):return hashlib.sha256(raw).hexdigest()

def write_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix('.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,allow_nan=False),encoding='utf-8')
    os.replace(temp,path)

def link(path):
    try:return path.is_symlink() or bool(getattr(path.lstat(),'st_file_attributes',0)&0x400)
    except OSError:return False

def confined_read(root,path):
    root=Path(root).absolute();path=Path(path).absolute()
    resolved=path.resolve(strict=True)
    if not path.is_relative_to(root) or not resolved.is_relative_to(root.resolve(strict=True)):
        raise ValueError('등록된 자료 폴더 밖의 파일은 읽지 않습니다.')
    for part in [path,*path.parents]:
        if link(part):raise ValueError('링크·junction 파일은 표시하지 않습니다.')
        if part==root:break
    if not resolved.is_file() or resolved.suffix.lower() not in ASSETS:raise ValueError('지원하지 않는 파일입니다.')
    before=resolved.stat()
    if before.st_size>MAX_FILE:raise ValueError('파일 미리보기는 20MiB까지 지원합니다.')
    with resolved.open('rb') as stream:raw=stream.read(MAX_FILE+1)
    after=resolved.stat()
    if len(raw)>MAX_FILE or (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):
        raise ValueError('파일 작성이 끝나면 다시 확인합니다.')
    return raw

def text_bytes(raw):
    if raw.startswith((b'\xff\xfe',b'\xfe\xff')):return raw.decode('utf-16')
    return raw.decode('utf-8-sig')

def strict_json(raw):
    def pairs(items):
        value={}
        for key,item in items:
            if key in value:raise ValueError('중복 JSON 키: '+key)
            value[key]=item
        return value
    def invalid(value):raise ValueError('유효하지 않은 JSON 숫자: '+value)
    def finite(value):
        number=float(value)
        if not math.isfinite(number):raise ValueError('유한하지 않은 JSON 숫자')
        return number
    return json.loads(text_bytes(raw),object_pairs_hook=pairs,parse_constant=invalid,parse_float=finite)

def categories(kind,value=None):
    if kind in ('html','image','pdf'):return ['visuals']
    if not isinstance(value,dict):return ['evidence']
    if value.get('viewer_record')=='public_cli_output_v1':
        return ['visuals'] if value.get('kind') in ('remote_image','inline_image') else ['evidence']
    if isinstance(value.get('turns'),list) and isinstance(value.get('session_id'),str):
        found=set()
        for turn in value['turns']:
            if not isinstance(turn,dict):continue
            state=turn.get('state') or {}
            if not isinstance(state,dict):continue
            candidates=turn.get('candidates')
            results=[state.get('latest_result')]+[c.get('result') for c in (candidates if isinstance(candidates,list) else []) if isinstance(c,dict)]
            if state.get('last_validation') or state.get('status') in ('held','failed','needs_revision','cancelled'):found.add('review')
            for result in results:
                if not isinstance(result,dict):continue
                if result.get('evidence_refs'):found.add('evidence')
                if any(result.get(key) for key in ('pains','existing_features','remaining_pains')):found.add('analysis')
                if result.get('concepts'):found.add('planning')
                if result.get('validation_findings'):found.add('review')
        return sorted(found) or ['planning']
    return ['evidence']

def private_data(value):
    """Reject credential keys at every level, including typed table columns."""
    def denied(key):return isinstance(key,str) and re.sub(r'[^a-z0-9]','',key.lower()) in PRIVATE_KEYS
    stack=[(value,0)];visited=0
    while stack:
        item,depth=stack.pop();visited+=1
        if depth>32 or visited>100000:return True
        if isinstance(item,dict):
            if any(denied(key) for key in item):return True
            for key,child in item.items():
                if isinstance(key,str) and re.sub(r'[^a-z0-9]','',key.lower())=='columns' and isinstance(child,list) and any(denied(column) for column in child):return True
                if isinstance(child,(dict,list)):stack.append((child,depth+1))
        elif isinstance(item,list):stack.extend((child,depth+1) for child in item if isinstance(child,(dict,list)))
    return False

def public_file(raw,suffix):
    if suffix=='.json':
        if private_data(strict_json(raw)):raise ValueError('설정·인증 또는 비공개 필드가 있는 자료는 표시하지 않습니다.')
    elif suffix in ('.csv','.tsv'):
        csv.field_size_limit(MAX_FILE)
        try:header=next(csv.reader(io.StringIO(text_bytes(raw)),delimiter='\t' if suffix=='.tsv' else ','),[])
        except csv.Error as exc:raise ValueError('표의 헤더를 아직 읽을 수 없습니다.') from exc
        if private_data({'columns':header}):raise ValueError('설정·인증 필드가 있는 표는 표시하지 않습니다.')

def output_json(value):
    if private_data(value):return False
    if isinstance(value,list):return bool(value) and all(isinstance(row,(dict,list)) for row in value)
    if not isinstance(value,dict):return False
    return (isinstance(value.get('rows'),list) or isinstance(value.get('records'),list)
            or isinstance(value.get('turns'),list) or isinstance(value.get('series'),list)
            or isinstance(value.get('datasets'),list) or isinstance(value.get('concepts'),list)
            or isinstance(value.get('items'),list) or isinstance(value.get('data'),list))

class References(HTMLParser):
    def __init__(self):super().__init__();self.values=[]
    def handle_starttag(self,tag,attrs):
        for key,value in attrs:
            if key in ('src','href','poster') and value:self.values.append(value)

class VisualRegistry:
    def __init__(self,state,watches):
        self.base=Path(state)/'assets';self.lock=threading.RLock();self.watches=[];self.observed={}
        for number,item in enumerate(watches,1):
            path=Path(item['path']).absolute()
            if link(path):raise ValueError('관찰 폴더는 링크·junction이 아닌 실제 폴더를 지정하세요.')
            key=sha(os.path.normcase(str(path)).encode())[:32]
            if any(w['id']==key for w in self.watches):continue
            watch={'id':key,'label':str(item.get('label') or f'자료 폴더 {number}')[:100],'path':path,'new_only':bool(item.get('new_only')),'collected':bool(item.get('collected'))}
            self.watches.append(watch)
            directory=self.base/key;directory.mkdir(parents=True,exist_ok=True)
            if not (directory/'index.json').exists():
                baseline={}
                if watch['new_only']:
                    for file in self.files(path)[0]:
                        try:info=file.stat();baseline[file.relative_to(path).as_posix()]=[info.st_size,info.st_mtime_ns]
                        except OSError:pass
                write_json(directory/'index.json',{'items':[],'history':[],'versions':[],'stored_bytes':0,'warnings':[],'baseline':baseline})

    def index(self,key):
        if not any(w['id']==key for w in self.watches):raise ValueError('등록되지 않은 자료 폴더입니다.')
        return json.loads((self.base/key/'index.json').read_text(encoding='utf-8'))

    def files(self,root):
        if not root.is_dir() or link(root):return [],False
        found=[];count=0
        def stamp(path):
            try:return path.stat().st_mtime_ns
            except OSError:return 0
        for directory,dirs,names in os.walk(root,followlinks=False):
            dirs[:]=[d for d in dirs if d.lower() not in SKIP and not d.startswith('.') and not link(Path(directory)/d)]
            if len(Path(directory).relative_to(root).parts)>8:dirs[:]=[];continue
            for name in names:
                count+=1
                if count>5000:return sorted(found,key=stamp,reverse=True)[:MAX_ITEMS],True
                path=Path(directory)/name
                if path.suffix.lower() in TYPES and not name.startswith('.') and not link(path):
                    try:found.append(path)
                    except OSError:pass
        return sorted(found,key=stamp,reverse=True)[:MAX_ITEMS],len(found)>MAX_ITEMS

    def bundle(self,root,path):
        folder=path.parent;queue=[path];resources={};warnings=[];total=0
        while queue and len(resources)<64:
            current=queue.pop(0)
            try:
                key=current.absolute().relative_to(folder.absolute()).as_posix()
                if key in resources:continue
                if '..' in PurePosixPath(key).parts or any(p.startswith('.') for p in PurePosixPath(key).parts):continue
                raw=confined_read(folder,current);public_file(raw,current.suffix.lower());total+=len(raw)
                if total>MAX_BUNDLE:raise ValueError('HTML 관련 파일은 합계 32MiB까지 지원합니다.')
                resources[key]=raw;refs=[]
                if current.suffix.lower() in ('.html','.htm'):
                    parser=References();parser.feed(text_bytes(raw));refs=parser.values
                elif current.suffix.lower() in ('.js','.mjs','.css'):
                    refs=re.findall(r'(?:url\(\s*|(?:from|import|fetch)\s*\(?\s*)[\'\"]([^\'\"]+)[\'\"]',text_bytes(raw))
                for ref in refs:
                    parsed=urllib.parse.urlsplit(ref)
                    if parsed.scheme or parsed.netloc:
                        if parsed.scheme not in ('data','mailto'):warnings.append('외부 자원은 미리보기에서 연결하지 않습니다. 로컬 파일 또는 단일 HTML로 저장하세요.')
                        continue
                    if not parsed.path:continue
                    candidate=(current.parent/urllib.parse.unquote(parsed.path)).absolute()
                    if '..' in candidate.parts: candidate=candidate.resolve()
                    if candidate.is_relative_to(folder.absolute()) and candidate.suffix.lower() in ASSETS:queue.append(candidate)
                    elif parsed.path:warnings.append('HTML 폴더 밖의 자원은 표시하지 않습니다.')
            except (OSError,ValueError,UnicodeError) as exc:warnings.append(str(exc)[:200])
        if queue:warnings.append('관련 파일 64개를 넘어 일부 자원을 생략했습니다.')
        return resources,list(dict.fromkeys(warnings))[:8]

    def scan(self):
        with self.lock:
            changes=[]
            for watch in self.watches:
                key,root=watch['id'],watch['path'];index=self.index(key);latest={item['path']:item for item in index['items']}
                paths,limited=self.files(root);present=set();warnings=[]
                if limited:warnings.append('최근 시각 파일 80개까지만 표시합니다. 큰 폴더는 출력 폴더를 따로 지정하세요.')
                for path in paths:
                    relative=path.relative_to(root).as_posix();present.add(relative)
                    try:
                        stamp=(path.stat().st_size,path.stat().st_mtime_ns)
                        if watch['new_only']:
                            if path.suffix.lower()=='.json' and not path.name.endswith('.visual.json') and not output_json(strict_json(confined_read(root,path))):continue
                            if index.get('baseline',{}).get(relative)==list(stamp) and relative not in latest:continue
                        previous=self.observed.get((key,relative));self.observed[(key,relative)]=stamp
                        if previous!=stamp and time.time()-path.stat().st_mtime<.4:continue
                        old=latest.get(relative,{})
                        stamps=old.get('resource_stamps')
                        if stamps and not old.get('warnings'):
                            unchanged=True
                            for name,expected in stamps.items():
                                source=path.parent/name
                                try:
                                    actual=source.stat()
                                    if link(source) or [actual.st_size,actual.st_mtime_ns]!=expected:unchanged=False;break
                                except OSError:unchanged=False;break
                            if unchanged:continue
                        resources,notes=self.bundle(root,path) if path.suffix.lower() in ('.html','.htm') else ({path.name:confined_read(root,path)},[])
                        if path.name not in resources:raise ValueError('HTML 원본 파일을 아직 읽을 수 없습니다.')
                        raw=resources[path.name]
                        public_file(raw,path.suffix.lower())
                        value=strict_json(raw) if path.suffix.lower()=='.json' else None
                        if path.suffix.lower() in ('.csv','.tsv'):text_bytes(raw)
                        fingerprint=sha(json.dumps({k:sha(v) for k,v in resources.items()},sort_keys=True).encode())
                        if latest.get(relative,{}).get('bundle_sha256')==fingerprint:continue
                        size=sum(len(v) for v in resources.values())
                        if len(index['versions'])>=MAX_VERSIONS or index['stored_bytes']+size>MAX_STORED:
                            warnings.append('보관 상한에 도달했습니다. 기존 미리보기와 원본은 유지합니다.');break
                        source_stamps={}
                        for name,content in resources.items():
                            source=path.parent/name;before=source.stat()
                            if sha(confined_read(path.parent,source))!=sha(content):raise ValueError('관련 파일 작성이 끝나면 다시 확인합니다.')
                            after=source.stat()
                            if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise ValueError('관련 파일을 다시 확인합니다.')
                            source_stamps[name]=[after.st_size,after.st_mtime_ns]
                        asset=uuid.uuid4().hex;folder=self.base/key/asset;folder.mkdir();manifest={}
                        for name,content in resources.items():
                            storage=sha(content)+Path(name).suffix.lower();(folder/storage).write_bytes(content)
                            manifest[name]={'storage':storage,'sha256':sha(content),'size':len(content)}
                        write_json(folder/'bundle.json',manifest)
                        latest[relative]={'id':asset,'watch_id':key,'folder':watch['label'],'path':relative,'name':path.name,'kind':TYPES[path.suffix.lower()],'entry':path.name,'sha256':sha(raw),'bundle_sha256':fingerprint,'size':len(raw),'modified':path.stat().st_mtime,'warnings':notes,'on_disk':True,'resource_stamps':source_stamps}
                        latest[relative]['source_key']=sha(os.path.normcase(str(path.absolute())).encode())
                        latest[relative]['categories']=categories(TYPES[path.suffix.lower()],value)
                        latest[relative]['collected']=watch['collected']
                        if watch['collected'] and isinstance(value,dict) and value.get('session_id'):latest[relative]['session_id']=value['session_id']
                        index.setdefault('history',[]).append({k:v for k,v in latest[relative].items() if k!='resource_stamps'})
                        changes.append(latest[relative])
                        index['versions'].append(asset);index['stored_bytes']+=size
                    except (OSError,ValueError,UnicodeError,RecursionError) as exc:warnings.append(relative+': '+str(exc)[:200])
                for item in latest.values():item['on_disk']=True if item['path'] in present else None if limited else False
                index['items']=sorted(latest.values(),key=lambda i:i['modified'],reverse=True)[:MAX_ITEMS]
                index['warnings']=list(dict.fromkeys(warnings))[:12]
                write_json(self.base/key/'index.json',index)
            return changes

    def state(self):
        with self.lock:
            watches=[];items=[];history=[];warnings=list(getattr(self,'extra_warnings',[]))
            for watch in self.watches:
                index=self.index(watch['id']);items.extend(index['items']);history.extend(index.get('history',[]));warnings.extend(index['warnings'])
                watches.append({'id':watch['id'],'label':watch['label'],'available':watch['path'].is_dir() and not link(watch['path'])})
            unique={}
            for item in sorted(items,key=lambda x:x['modified']):unique.setdefault(item.get('source_key',item['id']),item)
            public=[{k:v for k,v in item.items() if k!='resource_stamps'} for item in unique.values()]
            seen={(i.get('source_key',i['path']),i.get('bundle_sha256',i['sha256'])) for i in public}
            older=[]
            for item in sorted(history,key=lambda i:i['modified'],reverse=True):
                identity=(item.get('source_key',item['path']),item.get('bundle_sha256',item['sha256']))
                if identity in seen:continue
                seen.add(identity);older.append(item)
            return {'watches':watches,'items':sorted(public,key=lambda i:i['modified'],reverse=True),'history':older,'warnings':warnings,'scope':'saved_local_files','updated':time.time()}

    def read(self,key,asset,name):
        with self.lock:
            index=self.index(key)
            if not re.fullmatch('[a-f0-9]{32}',asset) or asset not in index['versions']:raise ValueError('등록되지 않은 시각 자료입니다.')
            folder=self.base/key/asset
            manifest=json.loads((folder/'bundle.json').read_text(encoding='utf-8'))
            if name not in manifest:raise ValueError('등록된 시각 자료의 파일만 읽습니다.')
            entry=manifest[name];storage=entry['storage']
            if not re.fullmatch(r'[a-f0-9]{64}\.[a-z0-9]+',storage):raise ValueError('보관 경로 오류')
            raw=confined_read(folder,folder/storage)
            if sha(raw)!=entry['sha256']:raise ValueError('원본 지문이 일치하지 않습니다.')
            public_file(raw,Path(name).suffix.lower())
            return raw

    def data(self,key,asset,name):
        raw=self.read(key,asset,name)
        if Path(name).suffix.lower()=='.json':
            value=strict_json(raw);collected=any(w['id']==key and w['collected'] for w in self.watches)
            image_allowed=False
            if collected and isinstance(value,dict) and value.get('kind')=='remote_image':
                from server import public_image
                image_allowed=bool(public_image(value.get('url')))
            return {'format':'json','value':value,'collected':collected,'image_allowed':image_allowed}
        if Path(name).suffix.lower() not in ('.csv','.tsv'):raise ValueError('표 데이터가 아닙니다.')
        csv.field_size_limit(MAX_FILE)
        reader=csv.reader(io.StringIO(text_bytes(raw)),delimiter='\t' if Path(name).suffix.lower()=='.tsv' else ',')
        try:
            header=next(reader,[]);rows=[];count=0
            for row in reader:
                count+=1
                if count<=200:rows.append(row[:40])
        except csv.Error as exc:raise ValueError('CSV를 읽을 수 없습니다: '+str(exc)) from exc
        return {'format':'csv','columns':header[:40],'rows':rows,'total_rows':count,'omitted_columns':max(0,len(header)-40)}
