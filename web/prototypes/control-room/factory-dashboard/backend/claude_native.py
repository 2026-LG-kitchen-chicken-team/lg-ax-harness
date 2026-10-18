"""Read public Claude tool receipts for observer-selected calls only.

No prompts, commands, output, paths or reasoning are returned. Existing installs
benefit from strict mapping without executing or replacing their observer.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sqlite3

MAX_BYTES=16*1024*1024
ID=re.compile(r'^[A-Za-z0-9_.:-]{1,200}$')


class ClaudeReceipts:
    def __init__(self, workspace, root=None):
        self.workspace=Path(workspace).resolve()
        self.root=Path(root) if root else Path(os.environ.get('CLAUDE_CONFIG_DIR',Path.home()/'.claude'))/'projects'
        spec=importlib.util.spec_from_file_location('factory_claude_observer',Path(__file__).resolve().parents[3]/'agent-office/observe.py')
        self.ob=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.ob)
        self.ob.use_harness(self.workspace)
        self.cached=None
        self.db_cached=None

    def bound_snapshot(self,expected):
        try:
            path=self.workspace/'runtime-data/product.sqlite'
            signature=[tuple(expected.get(k) for k in ('session_id','turn_id','request_key'))]
            for file in (path,Path(str(path)+'-wal'),Path(str(path)+'-journal')):
                if file.is_symlink():return None
                info=file.stat() if file.exists() else None
                signature.append((info.st_size,info.st_mtime_ns,info.st_ctime_ns) if info else None)
            if self.db_cached and self.db_cached[0]==signature:return self.db_cached[1]
            result=self.ob.snapshot_db(expected)
            self.db_cached=(signature,result)
            return result
        except (OSError,ValueError,TypeError,sqlite3.Error):return None

    def rows(self,session):
        if not isinstance(session,str) or not ID.fullmatch(session) or not self.root.is_dir() or self.root.is_symlink():return []
        candidates=list(self.root.glob('*/'+session+'.jsonl'))[:8]
        for path in candidates:
            try:
                if path.is_symlink() or path.parent.is_symlink() or not path.resolve().is_relative_to(self.root.resolve()):continue
                stat=path.stat();key=(str(path),stat.st_size,stat.st_mtime_ns,stat.st_ctime_ns)
                if stat.st_size>MAX_BYTES:continue
                if self.cached and self.cached[0]==key:return self.cached[1]
                rows=[];verified=False
                with path.open(encoding='utf-8') as handle:
                    for line in handle:
                        if not line.endswith('\n'):continue
                        try:row=json.loads(line)
                        except ValueError:continue
                        if not isinstance(row,dict) or row.get('sessionId')!=session:continue
                        if isinstance(row.get('cwd'),str) and Path(row['cwd']).resolve()==self.workspace:verified=True
                        rows.append(row)
                if verified:
                    # Raw native text is retained only during this read, never cached.
                    facts=self.facts(rows)
                    self.cached=(key,facts)
                    return facts
            except (OSError,ValueError,TypeError):continue
        return []

    def facts(self,rows):
        facts=[]
        for row in rows:
            if isinstance(row.get('cwd'),str) and Path(row['cwd']).resolve()!=self.workspace:continue
            stamp=row.get('timestamp')
            if not isinstance(stamp,str) or not re.match(r'^\d{4}-\d{2}-\d{2}T',stamp):continue
            message=row.get('message')
            content=message.get('content') if isinstance(message,dict) else None
            if isinstance(content,list):
                for part in content:
                    if not isinstance(part,dict):continue
                    key=part.get('id') if part.get('type')=='tool_use' else part.get('tool_use_id')
                    if not isinstance(key,str) or not ID.fullmatch(key):continue
                    if row.get('type')=='assistant' and part.get('type')=='tool_use':
                        args=part.get('input') if isinstance(part.get('input'),dict) else {}
                        if part.get('name') in ('Bash','PowerShell'):
                            spec=self.ob.command_spec(args.get('command'),str(self.workspace))
                            facts.append({'kind':'call','call':key,'spec':spec,'time':stamp})
                        elif part.get('name')=='TaskOutput':
                            facts.append({'kind':'task_read','call':key,'task':self.ob.token(args.get('task_id')),'time':stamp})
                    if row.get('type')=='user' and part.get('type')=='tool_result':
                        result=row.get('toolUseResult')
                        result=result if isinstance(result,dict) else {}
                        text=part.get('content')
                        interrupted=result.get('interrupted') is True or part.get('is_error') is True and isinstance(text,str) and text.strip() in ('[Request interrupted by user]','Request interrupted by user','Interrupted by user')
                        task=result.get('task') if isinstance(result.get('task'),dict) else result
                        status=task.get('status') if task.get('status') in ('completed','failed','cancelled','running') else None
                        visible=text if isinstance(text,str) else '\n'.join(p.get('text','') for p in text if isinstance(p,dict) and isinstance(p.get('text'),str)) if isinstance(text,list) else ''
                        safe={'kind':'result','call':key,'time':stamp,'background':self.ob.background_result(result),
                              'interrupted':interrupted,'failed':part.get('is_error') is True or bool(self.ob.tool_error(result or visible)),
                              'binding':self.ob.business_binding(result),'task_status':status}
                        if not safe['binding'] and isinstance(text,str):safe['binding']=self.ob.business_binding(text)
                        facts.append(safe)
            notice=content if isinstance(content,str) else '\n'.join(p.get('text','') for p in content if isinstance(p,dict) and p.get('type')=='text' and isinstance(p.get('text'),str)) if isinstance(content,list) else ''
            if row.get('type')=='user' and notice.lstrip().startswith('<task-notification>'):
                task=re.search(r'<task-id>([A-Za-z0-9_.:-]{1,80})</task-id>',notice[:4096])
                status=re.search(r'<status>(completed|failed|cancelled)</status>',notice[:4096])
                if task and status:facts.append({'kind':'task_done','task':task[1],'status':status[1],'time':stamp})
        calls={f['call']:f for f in facts if f['kind']=='call'}
        for fact in facts:
            if fact['kind']=='result':
                call=calls.get(fact['call'],{})
                entered=self.ob.command_input_binding(call.get('spec'),str(self.workspace),before=call.get('time')) if not fact['background'] else {}
                reported=fact['binding']
                fact['binding']={} if entered and reported and entered!=reported else reported or entered
        for call in calls.values():
            if call['spec']:call['spec']={k:call['spec'][k] for k in ('skill','op')}
        return facts[-4000:]

    def project(self,events):
        sessions={e['session'] for e in events if e['src']=='claude'}
        output=list(events)
        for session in sessions:
            facts=self.rows(session)
            if not facts:continue
            calls={f['call']:f for f in facts if f['kind'] in ('call','task_read')}
            results={f['call']:f for f in facts if f['kind']=='result'}
            tasks={};cancelled_calls=set()
            for i,event in enumerate(output):
                if event['session']!=session or not event['call'] or event['src']!='claude':continue
                call=calls.get(event['call'])
                if not call or call['kind']!='call':continue
                changed={**event,'detail':dict(event['detail'])};spec=call['spec']
                if not spec:
                    if event['kind']=='skill_op':changed.update(kind='shell',node=event['actor'],op=None,ops=[],basis='observed')
                else:
                    changed.update(kind='skill_op',node=spec['skill'],op=spec['op'],ops=[{'skill':spec['skill'],'op':spec['op']}],basis='command_based_mapping')
                changed['detail']['mapping_version']=2
                result=results.get(event['call'])
                if result and event['phase'] in ('end','fail'):
                    changed['detail'].update(result['background'])
                    if result['interrupted']:changed['detail']['interrupted']=True
                    if result['failed']:changed['phase']='fail'
                    changed['detail'].pop('business_binding',None)
                    changed['detail'].update(result['binding'])
                output[i]=changed
                if result and result['interrupted'] and changed['actor']=='main' and not changed['agent_id'] and event['call'] not in cancelled_calls:
                    cancelled_calls.add(event['call'])
                    key='claude-cancel-'+hashlib.sha256((session+event['call']+result['time']).encode()).hexdigest()[:20]
                    output.append({**changed,'id':key,'ts':result['time'],'hook':'Stop','kind':'turn_cancelled','node':'main','op':None,'ops':[],'call':None,'tool':None,'phase':'point','basis':'observed','detail':{'interrupted':True}})
                if result and result['background']:
                    tasks[result['background']['background_task_id']]=changed
            for fact in facts:
                task=fact.get('task')
                status=fact.get('status')
                if fact['kind']=='result' and fact.get('task_status') in ('completed','failed','cancelled'):
                    source=calls.get(fact['call'],{})
                    task=source.get('task');status=fact['task_status']
                if not task or task not in tasks or status not in ('completed','failed','cancelled'):continue
                original=tasks[task]
                key='claude-task-'+hashlib.sha256((session+task+fact['time']).encode()).hexdigest()[:20]
                detail={**original['detail'],'background':False,'background_task_id':task,'task_status':status}
                if status=='cancelled':detail['interrupted']=True
                output.append({**original,'id':key,'ts':fact['time'],'ts_basis':'reader_received','hook':'PostToolUseFailure' if status=='failed' else 'PostToolUse','phase':'fail' if status=='failed' else 'end','detail':detail})
        return output
