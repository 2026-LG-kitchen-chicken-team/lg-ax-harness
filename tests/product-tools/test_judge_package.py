"""Judge ZIP is self-contained and excludes runtime, credentials and dev harness."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT=Path(__file__).resolve().parents[2]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module
package=load('judge_package',ROOT/'adapters/common/package_judge.py')
helper=load('judge_helper',ROOT/'adapters/common/judge.py')
source_package=load('judge_source_package',ROOT/'adapters/common/package.py')

class JudgePackageTests(unittest.TestCase):
    def test_posix_observer_replaces_wrapper_instead_of_leaving_a_child(self):
        class ExecTransfer(BaseException):
            pass
        folder=ROOT/'codex'
        command=helper.observe_command('codex',folder,keep=True,open_page=True)
        with mock.patch.object(helper.os,'name','posix'), mock.patch.object(helper.os,'chdir') as change_dir, \
                mock.patch.object(helper.os,'execv',side_effect=ExecTransfer) as replace, \
                mock.patch.object(helper.subprocess,'run') as child:
            with self.assertRaises(ExecTransfer):
                helper.run_observer(command,folder)
        change_dir.assert_called_once_with(folder)
        replace.assert_called_once_with(sys.executable,command)
        child.assert_not_called()
        for name in ('start_codex_cli.sh','start_codex_gui.sh'):
            text=(ROOT/'adapters/common/launchers'/name).read_text(encoding='utf-8')
            self.assertIn('kill "$observer"',text)
            self.assertIn('wait "$observer"',text)

    def test_windows_observer_keeps_waited_command_failure(self):
        folder=ROOT/'codex'
        command=helper.observe_command('codex',folder,keep=True)
        with mock.patch.object(helper.os,'name','nt'), mock.patch.object(helper.os,'execv') as replace, \
                mock.patch.object(helper.subprocess,'run',return_value=subprocess.CompletedProcess(command,7)) as child:
            with self.assertRaisesRegex(RuntimeError,'Command exited 7'):
                helper.run_observer(command,folder)
        child.assert_called_once_with(command,cwd=folder,check=False)
        replace.assert_not_called()

    def test_observe_entry_point_uses_pid_preserving_runner(self):
        command=helper.observe_command('codex',helper.ROOT/'codex',keep=True,open_page=True)
        with mock.patch.object(sys,'argv',['judge.py','observe','--keep-following','--open']), \
                mock.patch.object(helper,'checked',return_value={'release':'product-v0.16.0'}), \
                mock.patch.object(helper,'run_observer') as observe, mock.patch.object(helper,'run') as wrapper:
            self.assertEqual(helper.main(),0)
        observe.assert_called_once_with(command,helper.ROOT/'codex')
        wrapper.assert_not_called()

    def test_source_zip_alone_rebuilds_the_identical_judge_zip_for_both_profiles(self):
        launchers={'common/launchers/'+name for name in package.LAUNCHERS}
        self.assertEqual(launchers,{n for n in source_package.ADAPTER_FILES if n.startswith('common/launchers/')})
        with tempfile.TemporaryDirectory(prefix='lgax-judge-source-roundtrip-') as name:
            base=Path(name)
            reference=base/'reference.zip'
            package.build(base/'reference-stage',reference,'product-v0.16.0','b'*40)
            for engine in ('codex','claude'):
                with self.subTest(engine=engine):
                    source=base/(engine+'-source.zip')
                    source_package.build(engine,base/(engine+'-installed'),source)
                    extracted=base/(engine+'-source')
                    with zipfile.ZipFile(source) as z:
                        for relative in launchers:
                            self.assertEqual(z.read('adapters/'+relative),(ROOT/'adapters'/relative).read_bytes())
                        z.extractall(extracted)
                    rebuilt=base/(engine+'-judge.zip')
                    # Run the extracted script as its CLI; no source-root override or checkout imports.
                    result=subprocess.run([sys.executable,str(extracted/'adapters/common/package_judge.py'),
                        '--staging',str(base/(engine+'-rebuilt-stage')),'--archive',str(rebuilt),
                        '--version','product-v0.16.0','--source-commit','b'*40],cwd=base,
                        capture_output=True,text=True,encoding='utf-8',timeout=60)
                    self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                    self.assertEqual(reference.read_bytes(),rebuilt.read_bytes())
                    reported=json.loads(result.stdout)
                    self.assertEqual(reported['sha256'],hashlib.sha256(rebuilt.read_bytes()).hexdigest())
                    print('Extracted '+engine+' source ZIP rebuilt identical judge ZIP: '+reported['sha256'])

    def test_followup_observer_does_not_stop_at_old_completed_turn(self):
        cold=helper.observe_command('codex',Path('codex'),latest=True)
        self.assertIn('--latest',cold)
        self.assertNotIn('--until-complete',cold)
        fresh=helper.observe_command('codex',Path('codex'))
        self.assertIn('--wait',fresh)
        self.assertIn('--until-complete',fresh)
        self.assertNotIn('--open',fresh)
        # one-click start: follow the new session through followups and open the dashboard at its first record
        kept=helper.observe_command('codex',Path('codex'),keep=True,open_page=True)
        self.assertIn('--wait',kept)
        self.assertNotIn('--until-complete',kept)
        self.assertEqual('--open',kept[-1])

    def test_setup_mark_is_bound_to_release_engine_and_environment(self):
        with tempfile.TemporaryDirectory(prefix='lgax-judge-mark-') as name:
            folder=Path(name)/'claude'
            self.assertFalse(helper.is_set_up('claude',folder,'product-v0.15.1'))
            mark=folder.joinpath(*helper.SETUP_MARK);mark.parent.mkdir(parents=True)
            mark.write_text(json.dumps({'release':'product-v0.15.1','engine':'claude'}),encoding='utf-8')
            self.assertFalse(helper.is_set_up('claude',folder,'product-v0.15.1'))  # no .venv yet
            python=helper.venv_python(folder);python.parent.mkdir(parents=True);python.write_bytes(b'')
            self.assertTrue(helper.is_set_up('claude',folder,'product-v0.15.1'))
            self.assertFalse(helper.is_set_up('claude',folder,'product-v0.15.2'))
            self.assertFalse(helper.is_set_up('codex',folder,'product-v0.15.1'))

    def test_one_click_starts_open_the_runner_in_its_engine_folder(self):
        source=ROOT/'adapters/common/launchers'
        self.assertEqual(sorted(p.name for p in source.iterdir()),sorted(package.LAUNCHERS))
        for name in package.LAUNCHERS:
            engine,ui=name[len('start_'):].split('.')[0].split('_')
            raw=(source/name).read_bytes();text=raw.decode('utf-8')
            with self.subTest(name=name):
                self.assertIn('judge.py prepare --engine '+engine+' --ui '+ui,text)
                if name.endswith('.cmd'):
                    self.assertEqual(raw.count(b'\n'),raw.count(b'\r\n'))  # cmd.exe labels need CRLF
                    self.assertTrue(text.startswith('@echo off\r\nsetlocal\r\nchcp 65001'))
                    self.assertIn('cd /d "%~dp0"',text)
                else:
                    self.assertNotIn(b'\r',raw)
                    self.assertTrue(text.startswith('#!/usr/bin/env bash\n'))
                    self.assertIn('\nset -euo pipefail\n',text)
                    self.assertIn('cd "$(dirname "$0")"',text)
                runner={'claude':'claude --model claude-opus-5-5 --effort medium','codex':'codex --search --sandbox workspace-write'}[engine]
                folder={'cmd':'cd /d "%~dp0'+engine+'"','sh':'cd '+engine}[name.split('.')[-1]]
                if ui=='cli':
                    self.assertIn(runner,text)
                    self.assertLess(text.index(folder),text.index(runner))  # never at the ZIP root
                elif engine=='claude':
                    self.assertIn('judge.py desktop --engine claude',text)
                else:
                    self.assertIn('codex app "',text)
                if engine=='codex':
                    self.assertIn('judge.py observe --engine codex --keep-following --open',text)
                    self.assertLess(text.index('--keep-following'),text.index('codex app' if ui=='gui' else runner))

    def test_both_native_products_observer_and_empty_catalog_without_source_repo(self):
        with tempfile.TemporaryDirectory(prefix='lgax-judge-package-') as name:
            base=Path(name);archive=base/'judge.zip'
            result=package.build(base/'staging',archive,'product-v0.15.0','b'*40)
            with zipfile.ZipFile(archive) as z:
                names=set(z.namelist());record=json.loads(z.read('bundle-manifest.json'))
                self.assertEqual(result['files'],len(names))
                for engine in ('codex','claude'):
                    self.assertIn(engine+'/web/prototypes/agent-office/codex_follow.py',names)
                    self.assertIn(engine+'/web/prototypes/agent-office/index.html',names)
                    self.assertIn(engine+'/product-install.json',names)
                    self.assertEqual([],json.loads(z.read(engine+'/data/business/empty/models.json')))
                    self.assertEqual(b'',z.read(engine+'/data/business/empty/sources.jsonl'))
                    install=json.loads(z.read(engine+'/product-install.json'))
                    self.assertEqual(6,len(install['skills']))
                    self.assertEqual(3,len(install['native_agents']))
                for entry in record['files']:
                    self.assertEqual(entry['sha256'],hashlib.sha256(z.read(entry['path'])).hexdigest())
                self.assertFalse(names & {'AGENTS.md','CLAUDE.md','.codex/config.toml'})
                for name in package.LAUNCHERS:
                    self.assertIn(name,names)
                    self.assertEqual(z.read(name),(ROOT/'adapters/common/launchers'/name).read_bytes())
                    mode=z.getinfo(name).external_attr>>16
                    self.assertEqual(0o100755 if name.endswith('.sh') else 0o100644,mode,name)
                for entry in z.infolist():
                    self.assertEqual(entry.create_system,3,entry.filename)
                    self.assertEqual(0o100755 if entry.filename.endswith('.sh') else 0o100644,
                                     entry.external_attr>>16,entry.filename)
                self.assertIn('start_claude_cli.cmd',z.read('README.md').decode('utf-8'))
                self.assertFalse(any(set(Path(n).parts)&package.FORBIDDEN for n in names))
                self.assertFalse(any('evaluation-O' in n for n in names))
                z.extractall(base/'extracted')
            self.assertEqual('product-v0.15.0',helper.checked(base/'extracted')['release'])
            launcher=base/'extracted/start_codex_cli.cmd';original=launcher.read_bytes()
            launcher.write_bytes(original+b'echo changed\r\n')
            with self.assertRaisesRegex(ValueError,'start_codex_cli.cmd'):
                helper.checked(base/'extracted')
            launcher.write_bytes(original)
            damaged=base/'extracted/codex/web/prototypes/agent-office/codex_follow.py'
            damaged.write_text('corrupted',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'Changed/missing'):
                helper.checked(base/'extracted')
            before=archive.read_bytes()
            with self.assertRaises(ValueError):
                package.build(base/'never-created',archive,'product-v0.15.0','b'*40)
            self.assertEqual(before,archive.read_bytes())
            self.assertFalse((base/'never-created').exists())

    def test_rejects_private_absolute_and_traversal_paths(self):
        for name in ('../outside','C:/auth.json','codex/runtime-data/private.sqlite',
                     'claude/.claude/settings.local.json','codex/.env.secret','codex/adapters/private.py'):
            with self.subTest(name=name),self.assertRaises(ValueError):
                package.safe_name(name)

if __name__=='__main__':unittest.main()
