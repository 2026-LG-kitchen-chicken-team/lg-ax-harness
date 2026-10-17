"""Adversarial native metadata fixtures; never execute fixture command text."""
import json
from pathlib import Path
import tempfile
import unittest

from backend.native_calls import command_skill, literal_commands, project_calls

TS = '2026-10-17T13:10:00Z'
END = '2026-10-17T13:10:10Z'
CMD = 'uv run python skills/evidence-retrieval/scripts/run.py retrieve_reviews --input input.json'


def row(kind, payload, ts=TS):
    return {'type': kind, 'timestamp': ts, 'payload': payload}


def start(command=CMD, call='call-1', **kwargs):
    return row('response_item', {'type': 'function_call', 'name': 'exec_command', 'call_id': call,
                                'arguments': json.dumps({'cmd': command, **kwargs})})


class NativeCallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp.name).resolve()

    def tearDown(self):
        self.temp.cleanup()

    def project(self, rows):
        return project_calls([row('event_msg', {'type': 'task_started', 'turn_id': 'turn'})] + rows, self.workspace)

    def test_real_entrypoint_start_is_available_before_result(self):
        call, = self.project([start()])
        self.assertEqual((call['skill'], call['operation'], call['status']), ('evidence-retrieval', 'retrieve_reviews', 'running'))
        self.assertNotIn('input.json', json.dumps(call))

    def test_instruction_is_distinct_from_work(self):
        call, = self.project([start(CMD.replace('retrieve_reviews', 'get_work_instructions'))])
        self.assertEqual(call['category'], 'instruction')

    def test_read_print_search_python_inline_and_shell_branches_do_not_execute_skill(self):
        for command in ('echo '+CMD, 'Get-Content '+CMD, 'rg "'+CMD+'" .', 'python -c "'+CMD+'"',
                        'false && '+CMD, CMD+'; echo private', CMD.replace('retrieve_reviews', 'invented_op')):
            self.assertIsNone(command_skill(command, None, self.workspace), command)

    def test_scope_and_traversal_are_not_a_current_product_call(self):
        self.assertIsNone(command_skill(CMD, self.workspace.parent, self.workspace))
        self.assertIsNone(command_skill(CMD.replace('skills/', '../skills/'), self.workspace, self.workspace))

    def test_quoted_interpreter_and_windows_shell_argv(self):
        command='& "C:/Program Files/Python/python.exe" "skills/feature-comparison/scripts/run.py" match_product_scope --input x.json'
        call, = self.project([start(command)])
        self.assertEqual(call['skill'], 'feature-comparison')
        spec=command_skill(['powershell.exe', '-Command', command], None, self.workspace)
        self.assertEqual(spec['operation'], 'match_product_scope')

    def test_only_verified_shell_executables_can_unwrap_command_options(self):
        for executable in ('echo', 'printf', 'unknown.exe', 'python'):
            self.assertIsNone(command_skill([executable, '-c', CMD], None, self.workspace))
            call,=self.project([row('event_msg',{'type':'item_started','item':{'type':'CommandExecution','id':'not-a-skill','command':[executable,'-c',CMD]}})])
            self.assertIsNone(call['skill'])

    def test_shell_syntax_only_and_file_options_never_become_execution(self):
        for argv in (['bash','-n','-c',CMD],['sh','--noexec','-c',CMD],['powershell.exe','-File','-Command',CMD],['cmd.exe','/unknown','/c',CMD]):
            self.assertIsNone(command_skill(argv,None,self.workspace))
        self.assertIsNotNone(command_skill(['powershell.exe','-NoProfile','-NonInteractive','-Command',CMD],None,self.workspace))
        self.assertIsNotNone(command_skill(['bash','--noprofile','-c',CMD],None,self.workspace))

    def test_literal_code_mode_single_and_parallel_calls(self):
        single='text(await tools.exec_command({cmd:'+json.dumps(CMD)+',login:false}));'
        self.assertEqual(literal_commands(single)[0]['cmd'], CMD)
        batch='const r = await Promise.all([tools.exec_command({cmd:'+json.dumps(CMD)+'}), tools.exec_command({cmd:'+json.dumps(CMD.replace('evidence-retrieval','feature-comparison').replace('retrieve_reviews','match_product_scope'))+'})]); text(r);'
        calls=self.project([row('response_item',{'type':'custom_tool_call','name':'exec','call_id':'batch','input':batch})])
        self.assertEqual({c['skill'] for c in calls},{'evidence-retrieval','feature-comparison'})
        self.assertTrue(all(c['status']=='running' for c in calls))

    def test_conditional_dynamic_quoted_examples_and_duplicate_keys_fail_closed(self):
        for code in ('if(false){await tools.exec_command({cmd:'+json.dumps(CMD)+'});}',
                     'await tools.exec_command({cmd:secret});',
                     'text('+json.dumps('await tools.exec_command({cmd:'+json.dumps(CMD)+'});')+');',
                     'await tools.exec_command({cmd:'+json.dumps(CMD)+',cmd:"echo"});',
                     'await tools.exec_command({cmd:`'+CMD+'`});'):
            self.assertEqual(literal_commands(code), [], code)

    def test_command_receipt_closes_existing_call_and_preserves_failed_result(self):
        receipt=row('event_msg',{'type':'item_completed','item':{'type':'CommandExecution','id':'command-1','command':['powershell.exe','-Command',CMD],'cwd':str(self.workspace),'status':'completed','exit_code':1,'aggregated_output':'PRIVATE'}}, END)
        call,=self.project([start(),receipt])
        self.assertEqual((call['status'],call['observer_call_id'],call['ended_at']),('failed','command-1',END))
        self.assertNotIn('PRIVATE',json.dumps(call))

    def test_command_receipt_tool_failure_is_not_successful_exit(self):
        receipt=row('event_msg',{'type':'item_completed','item':{'type':'CommandExecution','id':'command-1','command':CMD,'status':'completed','exit_code':0,'aggregated_output':'{"ok":false,"error":"private"}'}}, END)
        self.assertEqual(self.project([start(),receipt])[0]['status'],'failed')

    def test_tool_output_without_command_exit_never_certifies_success(self):
        call,=self.project([start(),row('response_item',{'type':'function_call_output','call_id':'call-1','output':'PRIVATE exit code 0'},END)])
        self.assertEqual(call['status'],'unknown')

    def test_known_background_process_stays_open_until_exit(self):
        first=row('event_msg',{'type':'item_completed','item':{'type':'CommandExecution','id':'command-1','command':CMD,'status':'in_progress','process_id':'process-1'}})
        output=row('response_item',{'type':'function_call_output','call_id':'call-1','output':'PRIVATE'})
        call,=self.project([start(),first,output])
        self.assertEqual(call['status'],'running')
        end=row('event_msg',{'type':'item_completed','item':{'type':'CommandExecution','id':'command-2','command':[], 'process_id':'process-1','status':'completed','exit_code':0}},END)
        call,=self.project([start(),first,output,end])
        self.assertEqual(call['status'],'completed')

    def test_cancellation_and_other_turn_completion_do_not_invent_success(self):
        call,=self.project([start(),row('event_msg',{'type':'task_complete','turn_id':'other'},END)])
        self.assertEqual(call['status'],'running')
        call,=self.project([start(),row('event_msg',{'type':'turn_aborted','turn_id':'turn'},END)])
        self.assertEqual(call['status'],'cancelled')

    def test_browser_task_is_specific_without_fabricating_a_skill(self):
        call,=self.project([row('response_item',{'type':'function_call','namespace':'mcp__cua_repl','name':'js','call_id':'browser','arguments':'{"code":"PRIVATE"}'})])
        self.assertEqual(call['category'],'browser');self.assertIsNone(call['skill'])
        self.assertNotIn('PRIVATE',json.dumps(call))

    def test_only_public_tool_metadata_is_used(self):
        self.assertEqual(self.project([row('response_item',{'type':'reasoning','text':CMD}),row('response_item',{'type':'message','role':'user','content':CMD})]),[])


if __name__=='__main__':
    unittest.main()
