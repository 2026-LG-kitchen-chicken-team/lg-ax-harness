"""Actual file/HTTP contracts for the read-only viewer. No model subprocesses."""
import hashlib
import http.client
import json
import os
import sqlite3
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from visuals import VisualRegistry, strict_json, output_json, private_data
from server import WebServer, output_documents, public_image, install_hook, open_on_new_output, cached_evidence
from types import SimpleNamespace
from contextlib import closing

class ViewerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.output=self.root/'output';self.output.mkdir()
        self.state=self.root/'private-state';self.registry=VisualRegistry(self.state,[{'path':str(self.output),'label':'CLI 출력'}])
    def write(self,name,content):
        path=self.output/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(content if isinstance(content,bytes) else content.encode('utf-8'))
        os.utime(path,(1,1));return path
    def items(self):self.registry.scan();return self.registry.state()['items']
    def read(self,item,name=None):return self.registry.read(item['watch_id'],item['id'],name or item['entry'])
    def test_existing_output_is_automatically_listed_without_execution(self):
        self.write('chart.svg','<svg xmlns="http://www.w3.org/2000/svg"/>')
        with patch('subprocess.Popen',side_effect=AssertionError('No subprocess')):
            item=self.items()[0];self.assertEqual(item['kind'],'image');self.assertEqual(self.read(item),self.output.joinpath('chart.svg').read_bytes())
        self.assertEqual(self.registry.state()['scope'],'saved_local_files')
    def test_changed_image_preserves_immutable_old_original_and_restart(self):
        path=self.write('chart.svg','<svg>one</svg>');old=self.items()[0]
        path.write_text('<svg>longer two</svg>',encoding='utf-8');os.utime(path,(2,2));new=self.items()[0]
        self.assertNotEqual(old['id'],new['id']);self.assertEqual(self.read(old),b'<svg>one</svg>')
        restored=VisualRegistry(self.state,[{'path':str(self.output)}]);restored.scan();self.assertEqual(restored.state()['items'][0]['id'],new['id'])
        self.assertEqual(restored.read(old['watch_id'],old['id'],old['entry']),b'<svg>one</svg>')
        history=restored.state()['history'];self.assertEqual(history[0]['id'],old['id'])
    def test_deletion_shows_snapshot_without_claiming_file_still_present(self):
        path=self.write('chart.svg','<svg/>');item=self.items()[0];path.unlink();items=self.items()
        self.assertFalse(items[0]['on_disk']);self.assertEqual(self.read(item),b'<svg/>')
    def test_html_local_dependencies_changes_and_null_origin_bundle(self):
        self.write('demo.html','<script src="assets/ui.js"></script><link href="assets/ui.css" rel="stylesheet">')
        js=self.write('assets/ui.js','document.title="one";');self.write('assets/ui.css','body{color:purple}')
        old=self.items()[0];self.assertEqual(self.read(old,'assets/ui.js'),js.read_bytes())
        js.write_text('document.title="two and longer";',encoding='utf-8');os.utime(js,(2,2));new=self.items()[0]
        self.assertNotEqual(old['id'],new['id']);self.assertEqual(self.read(old,'assets/ui.js'),b'document.title="one";')
    def test_outside_dependency_and_unknown_asset_cannot_be_read(self):
        self.write('demo.html','<script src="../secret.js"></script><script src="https://example.com/a.js"></script>')
        (self.root/'secret.js').write_text('secret',encoding='utf-8');item=self.items()[0]
        self.assertTrue(item['warnings'])
        for key in ('../secret.js','bundle.json','../../private-state'):
            with self.assertRaises(ValueError):self.read(item,key)
        with self.assertRaises(ValueError):self.registry.read(item['watch_id'],'0'*32,item['entry'])
    def test_hash_tampering_and_links_are_rejected(self):
        self.write('chart.svg','<svg/>');item=self.items()[0]
        folder=self.registry.base/item['watch_id']/item['id'];manifest=json.loads((folder/'bundle.json').read_text())
        (folder/manifest[item['entry']]['storage']).write_bytes(b'<svg>tampered</svg>')
        with self.assertRaisesRegex(ValueError,'지문'):self.read(item)
    def test_symlink_file_does_not_expose_other_directory(self):
        target=self.root/'secret.svg';target.write_text('<svg>private</svg>')
        try:(self.output/'linked.svg').symlink_to(target)
        except OSError:self.skipTest('OS does not grant symlink creation')
        self.assertEqual(self.items(),[])
    def test_new_folder_can_appear_later_and_server_never_creates_it(self):
        missing=self.root/'later';registry=VisualRegistry(self.state/'later',[{'path':str(missing)}]);registry.scan()
        self.assertFalse(missing.exists());self.assertFalse(registry.state()['watches'][0]['available'])
        missing.mkdir();file=missing/'x.csv';file.write_text('name,count\na,3');os.utime(file,(1,1));registry.scan()
        self.assertEqual(len(registry.state()['items']),1)
    def test_csv_quotes_unicode_original_bytes_and_bounded_rows(self):
        raw=('이름,개수\n'+''.join('"항목,가",3\n' for _ in range(220))).encode('utf-8-sig');self.write('table.csv',raw);item=self.items()[0]
        data=self.registry.data(item['watch_id'],item['id'],item['entry']);self.assertEqual(data['columns'],['이름','개수']);self.assertEqual(data['rows'][0],['항목,가','3'])
        self.assertEqual(data['total_rows'],220);self.assertEqual(len(data['rows']),200);self.assertEqual(self.read(item),raw)
    def test_json_strict_values_and_incomplete_write_recovery(self):
        for raw in (b'{"a":1,"a":2}',b'{"a":NaN}',b'{"a":1e999}'):
            with self.assertRaises(ValueError):strict_json(raw)
        file=self.write('result.json','{"turns":');self.assertEqual(self.items(),[]);self.assertTrue(self.registry.state()['warnings'])
        file.write_text('{"status":"held"}',encoding='utf-8');os.utime(file,(2,2));self.assertEqual(len(self.items()),1)
        self.assertEqual(self.registry.state()['warnings'],[])
    def test_resources_do_not_leave_full_paths_in_public_state(self):
        self.write('demo.html','<h1>Hi</h1>');item=self.items()[0]
        self.assertNotIn('resource_stamps',item);self.assertNotIn(str(self.output),json.dumps(self.registry.state()))
    def test_stable_poll_does_not_rewrite_asset_or_read_large_unchanged_file(self):
        self.write('chart.svg','<svg/>');item=self.items()[0]
        with patch('visuals.confined_read',side_effect=AssertionError('unchanged file should use source stats')):self.registry.scan()
        self.assertEqual(self.registry.state()['items'][0]['id'],item['id'])
    def test_root_new_visuals_do_not_require_specific_save_directory(self):
        self.write('old.svg','<svg>old</svg>');registry=VisualRegistry(self.state/'new-only',[{'path':str(self.output),'new_only':True}])
        self.assertEqual(registry.scan(),[]);self.assertEqual(registry.state()['items'],[])
        self.write('anywhere/new.svg','<svg>new</svg>');changes=registry.scan();self.assertEqual(len(changes),1)
        self.assertEqual(changes[0]['path'],'anywhere/new.svg');self.assertEqual(registry.scan(),[])
    def test_structured_json_anywhere_is_collected_but_request_and_credentials_are_not(self):
        registry=VisualRegistry(self.state/'anywhere',[{'path':str(self.output),'new_only':True}])
        self.write('report.json','{"rows":[{"label":"sample","count":3}]}');self.write('request.json','{"question":"private request"}');self.write('auth.json','{"api_key":"secret","rows":[]}')
        changes=registry.scan();self.assertEqual([item['name'] for item in changes],['report.json'])
    def test_json_with_missing_candidate_array_does_not_stop_other_outputs(self):
        self.write('incomplete-schema.json','{"session_id":"test-only","turns":[{"state":{},"candidates":null}]}');self.write('valid.svg','<svg/>')
        self.assertEqual(len(self.items()),2)
    def test_recursive_credentials_and_matrix_columns_cannot_be_collected(self):
        values=[[{'api_key':'fixture-only'}],{'rows':[{'auth':{'access_token':'fixture-only'}}]},
                {'columns':['Api-Key'],'rows':[['fixture-only']]},{'rows':[{'nested':[{'Refresh Token':'fixture-only'}]}]}]
        for value in values:
            with self.subTest(value=value):
                self.assertTrue(private_data(value));self.assertFalse(output_json(value))
                packet={'tool_response':{'structuredContent':value}}
                self.assertEqual(output_documents(packet),[])
        self.assertFalse(private_data({'rows':[{'input_tokens':2,'output_tokens':1,'cost_usd':None}]}))
        packet={'tool_response':{'structuredContent':{'columns':['label','count'],'rows':[['public',3]]}}}
        self.assertEqual(output_documents(packet)[0]['kind'],'matrix')
    def test_explicit_output_names_and_html_dependencies_cannot_bypass_private_filter(self):
        self.write('private.visual.json',json.dumps({'rows':[{'secret':'fixture-only'}]}))
        self.write('private.csv','API_KEY,label\nfixture-only,test')
        self.write('demo.html','<script src="ui.js"></script>')
        self.write('ui.js','fetch("private.visual.json")')
        self.write('public.json','{"rows":[{"label":"public","count":3}]}')
        items=self.items();self.assertEqual({item['name'] for item in items},{'demo.html','public.json'})
        html=next(item for item in items if item['kind']=='html')
        with self.assertRaises(ValueError):self.read(html,'private.visual.json')
        self.assertTrue(html['warnings'])
        legacy=VisualRegistry(self.state/'legacy',[{'path':str(self.output)}])
        with patch('visuals.private_data',return_value=False):legacy.scan()
        old=next(item for item in legacy.state()['items'] if item['name']=='private.visual.json')
        with self.assertRaises(ValueError):legacy.read(old['watch_id'],old['id'],old['entry'])
    def test_private_directories_are_excluded_case_insensitively(self):
        for directory in ('Credentials','Config','Settings','Cache','Logs','Sessions'):
            self.write(directory+'/report.json','{"rows":[{"label":"fixture-only"}]}')
        self.write('reports/result.json','{"rows":[{"label":"public"}]}')
        self.assertEqual([item['path'] for item in self.items()],['reports/result.json'])
    def test_hook_collects_public_harness_rows_without_arbitrary_shell_logs(self):
        rows={'data_version':'observed-v1','total':1,'truncated':False,'records':[{'source_id':'R1','model_id':'B502S33','text':'실제 원문','origin':{'purchase_verified':None,'source_url':'https://example.com'}}]}
        packet={'hook_event_name':'PostToolUse','tool_name':'Bash','tool_input':{'command':'uv run python skills/evidence-retrieval/scripts/run.py --tool retrieve_reviews'},'tool_response':{'stdout':json.dumps(rows,ensure_ascii=False)}}
        documents=output_documents(packet);self.assertEqual(documents[0]['value'][0]['text'],'실제 원문');self.assertIsNone(documents[0]['value'][0]['origin']['purchase_verified'])
        packet['tool_input']['command']='read private credentials';self.assertEqual(output_documents(packet),[])
    def test_explicit_public_images_only_no_hidden_reasoning_or_user_text(self):
        packet={'hook_event_name':'PostToolUse','tool_response':{'content':[{'type':'image_url','image_url':'https://example.com/chart.png'},{'type':'reasoning','text':'![hidden](https://example.com/hidden.png)'}]},'prompt':'![private](https://example.com/private.png)'}
        docs=output_documents(packet);self.assertEqual(len(docs),1);self.assertEqual(docs[0]['url'],'https://example.com/chart.png')
        self.assertIsNone(public_image('https://127.0.0.1/x'));self.assertIsNone(public_image('https://user:password@example.com/x'));self.assertIsNone(public_image('javascript:alert(1)'))
    def test_typed_mcp_rows_matrix_and_json_string_image_are_collected(self):
        packet={'hook_event_name':'PostToolUse','tool_name':'mcp_tool','tool_response':{'structuredContent':{'rows':[{'month':'Jan','count':3}]}}}
        self.assertEqual(output_documents(packet)[0]['value'],[{'month':'Jan','count':3}])
        packet['tool_response']={'structuredContent':{'columns':['month','count'],'rows':[['Jan',3]]}};self.assertEqual(output_documents(packet)[0]['kind'],'matrix')
        packet['tool_response']=json.dumps({'content':[{'type':'image_url','image_url':'https://example.com/chart.png'}]});self.assertEqual(output_documents(packet)[0]['kind'],'remote_image')
    def test_watched_marker_cannot_impersonate_hook_inbox_or_allow_private_image(self):
        self.write('fake.json',json.dumps({'viewer_record':'public_cli_output_v1','kind':'remote_image','url':'https://127.0.0.1/private'}));item=self.items()[0]
        data=self.registry.data(item['watch_id'],item['id'],item['entry']);self.assertFalse(data['collected']);self.assertFalse(data['image_allowed'])
    def test_browser_opens_on_first_new_output_not_startup_or_each_update(self):
        server=SimpleNamespace(ui_seen=0,server_address=('127.0.0.1',8765));opened=[]
        opener=lambda url:opened.append(url) or True
        self.assertIsNone(open_on_new_output(server,[],True,now=100,opener=opener));self.assertEqual(opened,[])
        last=open_on_new_output(server,[{'id':'new'}],True,now=100,opener=opener);self.assertEqual(last,100);self.assertEqual(len(opened),1)
        self.assertEqual(open_on_new_output(server,[{'id':'another'}],True,last,now=101,opener=opener),100)
        server.ui_seen=150;self.assertEqual(open_on_new_output(server,[{}],True,last,now=151,opener=opener),100);self.assertEqual(len(opened),1)
    def test_existing_harness_cache_is_readonly_hash_checked_and_not_matched_to_session(self):
        database=self.output/'runtime-data/product.sqlite';database.parent.mkdir()
        value={'data_version':'observed-v1','records':[{'source_id':'R1','model_id':'B502S33','text':'원문','origin':{'purchase_verified':None}}],'synthetic':False,'truncated':False}
        payload=json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'))
        with closing(sqlite3.connect(database)) as con, con:
            con.execute('CREATE TABLE retrieval_cache(cache_key TEXT PRIMARY KEY,payload TEXT,payload_hash TEXT)')
            con.execute('INSERT INTO retrieval_cache VALUES(?,?,?)',('one',payload,hashlib.sha256(payload.encode()).hexdigest()))
        before=hashlib.sha256(database.read_bytes()).hexdigest();self.assertEqual(cached_evidence({'workspaces':[str(self.output)]},self.state),[])
        self.assertEqual(hashlib.sha256(database.read_bytes()).hexdigest(),before)
        files=list((self.state/'incoming').glob('*.json'));self.assertEqual(len(files),1)
        document=json.loads(files[0].read_text(encoding='utf-8'));self.assertEqual(document['value'][0]['text'],'원문');self.assertNotIn('session_id',document)
        cached_evidence({'workspaces':[str(self.output)]},self.state);self.assertEqual(len(list((self.state/'incoming').glob('*.json'))),1)
        with closing(sqlite3.connect(database)) as con, con:con.execute('UPDATE retrieval_cache SET payload_hash=?',('0'*64,))
        self.assertTrue(cached_evidence({'workspaces':[str(self.output)]},self.state))
    def test_hook_install_is_project_only_additive_and_idempotent(self):
        config=self.root/'viewer.json';config.write_text(json.dumps({'workspaces':[str(self.output)]}),encoding='utf-8')
        args=SimpleNamespace(config=config,state=self.state,port=8765)
        path=self.output/'.claude/settings.local.json';path.parent.mkdir();path.write_text('{"permissions":{"deny":["Bash(rm:*)"]},"hooks":{"SessionStart":[{"hooks":[{"type":"command","command":"existing-hook"}]}]}}')
        install_hook(args,self.output,'claude');first=path.read_bytes();install_hook(args,self.output,'claude');self.assertEqual(first,path.read_bytes())
        value=json.loads(first);self.assertEqual(value['permissions']['deny'],['Bash(rm:*)']);self.assertEqual(len(value['hooks']['SessionStart']),2)
        self.assertNotIn('PreToolUse',value['hooks']);self.assertNotIn('PermissionRequest',value['hooks']);self.assertTrue(value['hooks']['PostToolUse'][0]['hooks'][0]['async'])

class HTTPTests(unittest.TestCase):
    setUp=ViewerTests.setUp
    write=ViewerTests.write
    items=ViewerTests.items
    def test_readonly_routes_host_origin_csp_and_original_download(self):
        self.write('demo.html','<button>Click</button><script>document.title="Hello"</script>');item=self.items()[0]
        server=WebServer(('127.0.0.1',0),self.registry);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();port=server.server_address[1]
        def request(path,method='GET',headers=None,body=None):
            conn=http.client.HTTPConnection('127.0.0.1',port,timeout=3);conn.request(method,path,body=body,headers=headers or {});response=conn.getresponse();raw=response.read();out=(response.status,dict(response.getheaders()),raw);conn.close();return out
        try:
            route='/api/assets/'+item['watch_id']+'/'+item['id']+'/demo.html'
            status,headers,raw=request(route,headers={'Origin':'null'});self.assertEqual(status,200);self.assertEqual(raw,self.output.joinpath('demo.html').read_bytes())
            self.assertIn('sandbox allow-scripts',headers['Content-Security-Policy']);self.assertNotIn('allow-same-origin',headers['Content-Security-Policy'])
            self.assertEqual(request('/api/state',headers={'Origin':'null'})[0],403)
            self.assertEqual(request(route,headers={'Origin':'https://example.com'})[0],403)
            self.assertEqual(request('/api/state',headers={'Host':'evil.example'})[0],403)
            self.assertIn('attachment',request(route+'?download=1')[1]['Content-Disposition'])
            self.assertEqual(request(route.replace('demo.html','../secret'))[0],400)
            for method in ('POST','PUT','DELETE','PATCH'):self.assertEqual(request('/api/runs',method,body='{}')[0],405)
            for path in ('/api/terminal','/api/run','/api/tools','/.harness/viewer.json','/../AGENTS.md','/terminal-client.js','/vendor/xterm.js'):self.assertEqual(request(path)[0],404)
            self.assertEqual(request('/')[0],200)
        finally:server.shutdown();server.server_close()
