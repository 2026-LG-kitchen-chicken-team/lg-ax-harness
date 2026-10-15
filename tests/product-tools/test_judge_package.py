"""Judge ZIP is self-contained and excludes runtime, credentials and dev harness."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[2]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module
package=load('judge_package',ROOT/'adapters/common/package_judge.py')
helper=load('judge_helper',ROOT/'adapters/common/judge.py')

class JudgePackageTests(unittest.TestCase):
    def test_followup_observer_does_not_stop_at_old_completed_turn(self):
        cold=helper.observe_command('codex',Path('codex'),latest=True)
        self.assertIn('--latest',cold)
        self.assertNotIn('--until-complete',cold)
        fresh=helper.observe_command('codex',Path('codex'))
        self.assertIn('--wait',fresh)
        self.assertIn('--until-complete',fresh)

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
                self.assertFalse(any(set(Path(n).parts)&package.FORBIDDEN for n in names))
                self.assertFalse(any('evaluation-O' in n for n in names))
                z.extractall(base/'extracted')
            self.assertEqual('product-v0.15.0',helper.checked(base/'extracted')['release'])
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
