"""Synthetic Claude receipts only: no installed session, model, CLI or database is run."""
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from backend.claude_native import ClaudeReceipts

SECRET='PRIVATE-SYNTHETIC-DO-NOT-EXPOSE'
STAMP='2026-10-18T01:00:00Z'

class ClaudeNativeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='claude-metadata-')
        self.workspace=Path(self.temp.name)/'harness';self.workspace.mkdir()
        self.logs=Path(self.temp.name)/'projects';(self.logs/'project').mkdir(parents=True)
        self.reader=ClaudeReceipts(self.workspace,self.logs)
    def tearDown(self):self.temp.cleanup()
    def row(self,type,content,**patch):
        return {'type':type,'sessionId':'S','cwd':str(self.workspace),'timestamp':STAMP,'message':{'content':content},**patch}
    def write(self,rows):
        (self.logs/'project/S.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows),encoding='utf-8')
    def call(self,command):return self.row('assistant',[{'type':'tool_use','id':'call','name':'Bash','input':{'command':command}}])
    def event(self,phase='start'):
        return {'v':1,'id':'event-'+phase,'ts':STAMP,'ts_basis':'hook_received','src':'claude','session':'S','prompt_id':'P','agent_id':None,'actor':'main','hook':'PreToolUse' if phase=='start' else 'PostToolUse','tool':'Bash','call':'call','kind':'skill_op','node':'needs-structuring','op':'read_evidence_batch','ops':[],'basis':'command_based_mapping','phase':phase,'detail':{}}
    def result(self,**result):
        return self.row('user',[{'type':'tool_result','tool_use_id':'call','content':'result'}],toolUseResult=result)
    def test_printed_or_sequential_paths_are_not_skill_execution(self):
        for command in [f'echo "python skills/needs-structuring/scripts/run.py read_evidence_batch {SECRET}"; sleep 5',
                        'python skills/needs-structuring/scripts/run.py read_evidence_batch && python skills/feature-comparison/scripts/run.py retrieve_product_facts']:
            self.write([self.call(command)])
            events=self.reader.project([self.event()])
            self.assertEqual(events[0]['kind'],'shell');self.assertEqual(events[0]['ops'],[])
            self.assertNotIn(SECRET,json.dumps(events))
    def test_background_launch_is_not_a_completed_skill(self):
        self.write([self.call('python skills/feature-comparison/scripts/run.py retrieve_product_facts'),self.result(backgroundTaskId='task-one')])
        events=self.reader.project([self.event(),self.event('end')])
        self.assertEqual(events[0]['node'],'feature-comparison')
        self.assertTrue(events[1]['detail']['background'])
        self.assertEqual(events[1]['detail']['background_task_id'],'task-one')
    def test_task_notice_closes_only_its_observed_call(self):
        note='<task-notification><task-id>task-one</task-id><status>completed</status><summary>'+SECRET+'</summary></task-notification>'
        self.write([self.call('python skills/feature-comparison/scripts/run.py retrieve_product_facts'),self.result(backgroundTaskId='task-one'),self.row('user',[{'type':'text','text':note}])])
        events=self.reader.project([self.event(),self.event('end')])
        self.assertEqual(events[-1]['call'],'call');self.assertEqual(events[-1]['detail']['task_status'],'completed');self.assertFalse(events[-1]['detail']['background'])
        self.assertNotIn(SECRET,json.dumps(events))
    def test_unobserved_or_other_workspace_tool_use_is_not_attached(self):
        self.write([self.call('python skills/feature-comparison/scripts/run.py retrieve_product_facts')])
        self.assertEqual(self.reader.project([]),[])
        self.write([self.call('python skills/feature-comparison/scripts/run.py retrieve_product_facts')|{'cwd':str(self.workspace.parent/'other')}])
        self.assertEqual(self.reader.project([self.event()]),[self.event()])
    def test_interrupted_native_result_is_cancellation_not_success(self):
        result=self.row('user',[{'type':'tool_result','tool_use_id':'call','content':'[Request interrupted by user]','is_error':True}],toolUseResult={'interrupted':True})
        self.write([self.call('python skills/needs-structuring/scripts/run.py read_evidence_batch'),result])
        events=self.reader.project([self.event()]);self.assertTrue(any(e['kind']=='turn_cancelled' for e in events))
    def test_redirected_output_can_bind_only_the_explicit_input_turn(self):
        runtime=self.workspace/'runtime-data';runtime.mkdir()
        (runtime/'input.json').write_text(json.dumps({'turn_id':'T','session_id':'BUSINESS','request_key':'K','extra':SECRET}),encoding='utf-8')
        os.utime(runtime/'input.json',(0,0))
        with sqlite3.connect(runtime/'product.sqlite') as db:
            db.execute('CREATE TABLE turns(session_id,turn_id,request_key)');db.execute("INSERT INTO turns VALUES('BUSINESS','T','K')")
        db.close()
        self.write([self.call('python skills/review-and-revise/scripts/run.py save_and_export --input runtime-data/input.json > runtime-data/result.json'),self.result(stdout='')])
        events=self.reader.project([self.event(),self.event('end')])
        self.assertEqual(events[-1]['detail']['business_binding'],{'session_id':'BUSINESS','turn_id':'T','request_key':'K'})
        self.assertNotIn(SECRET,json.dumps(events))
        (runtime/'input.json').write_text(json.dumps({'turn_id':'T','session_id':'WRONG'}),encoding='utf-8')
        self.reader=ClaudeReceipts(self.workspace,self.logs)
        events=self.reader.project([self.event(),self.event('end')]);self.assertNotIn('business_binding',events[-1]['detail'])
    def test_observer_mapping_rejects_nonexecution_wrappers_and_keeps_one_actual_entrypoint(self):
        ob=self.reader.ob;command='python skills/needs-structuring/scripts/run.py read_evidence_batch'
        for example in [f'echo "{command}"',f'python -c "print({command!r})"', ['bash','-n','-c',command],command+' && echo done']:
            self.assertIsNone(ob.command_spec(example,str(self.workspace)))
        self.assertEqual(ob.command_spec(command,str(self.workspace))['skill'],'needs-structuring')
        self.assertEqual(ob.command_spec(['powershell','-NoProfile','-Command',command],str(self.workspace))['skill'],'needs-structuring')
    def test_unavailable_data_is_not_a_success(self):
        ob=self.reader.ob
        self.assertEqual(ob.tool_error({'stdout':'{"ok":true,"result":{"status":"unavailable","reason":"http_404"}}'}),'source_unavailable')

    def test_exact_bound_snapshot_never_substitutes_the_newest_other_turn(self):
        runtime=self.workspace/'runtime-data';runtime.mkdir()
        db=sqlite3.connect(runtime/'product.sqlite')
        db.execute('CREATE TABLE turns(turn_id,status,revision_count,result_version,valid,created_at,session_id,request_key)')
        db.executemany('INSERT INTO turns VALUES(?,?,?,?,?,?,?,?)',[('OLD','completed',0,1,1,'2026-10-18T00:00:00Z','BUSINESS','K'),('OTHER','completed',0,1,1,'2026-10-18T01:00:00Z','FOREIGN','F')]);db.commit();db.close()
        bound={'session_id':'BUSINESS','turn_id':'OLD','request_key':'K'}
        self.assertEqual(self.reader.bound_snapshot(bound)['binding'],bound)
        self.assertIsNone(self.reader.bound_snapshot(bound|{'turn_id':'MISSING'})['binding'])
