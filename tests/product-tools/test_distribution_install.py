import hashlib
import importlib.util
import io
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('lgax_distribution_install', ROOT/'adapters/common/distribution/install.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


class DistributionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.version = 'product-v0.16.1'
        self.archive = self.root/f'lg-ax-judge-{self.version}.zip'
        self.sums = self.root/'SHA256SUMS.txt'

    def tearDown(self):
        self.temp.cleanup()

    def bundle(self, extra=None, mutate=False, version=None):
        files = {'README.md': b'readme', 'judge.py': b'# fixture', 'codex/AGENTS.md': b'agent', 'start_codex_cli.sh': b'#!/bin/bash\n'}
        if extra: files.update(extra)
        record = {'format':'lgax-judge-bundle-v1','release': version or self.version,
                  'files':[{'path': n,'sha256': hashlib.sha256(raw).hexdigest()} for n,raw in files.items()]}
        if mutate: files['judge.py'] = b'altered'
        with zipfile.ZipFile(self.archive, 'w') as z:
            for n,raw in files.items(): z.writestr(n,raw)
            z.writestr('bundle-manifest.json', json.dumps(record))
        self.sums.write_text(m.digest(self.archive)+'  '+self.archive.name+'\n',encoding='utf-8')
        return self.archive,self.sums

    def test_verified_extract_and_executable_mode(self):
        self.bundle(); m.verify_checksum(self.archive,self.sums)
        target=self.root/'new'; target.mkdir()
        self.assertEqual(m.unpack_verified(self.archive,target,self.version),5)
        self.assertEqual((target/'judge.py').read_bytes(),b'# fixture')

    def test_checksum_mismatch_and_duplicate(self):
        self.bundle()
        self.sums.write_text('0'*64+'  '+self.archive.name)
        with self.assertRaisesRegex(ValueError,'SHA256'): m.verify_checksum(self.archive,self.sums)
        self.bundle(); self.sums.write_text(self.sums.read_text()*2)
        with self.assertRaises(ValueError): m.verify_checksum(self.archive,self.sums)

    def test_archive_file_digest_mismatch(self):
        self.bundle(mutate=True)
        with self.assertRaisesRegex(ValueError,'file SHA256'): m.unpack_verified(self.archive,self.root/'out',self.version)

    def test_version_mismatch(self):
        self.bundle(version='product-v0.0.0')
        with self.assertRaisesRegex(ValueError,'version'): m.unpack_verified(self.archive,self.root/'out',self.version)

    def test_archive_traversal_and_windows_aliases(self):
        for name in ('../escape','/escape','C:/escape','x\\escape','x/CON.txt','x/space.','a/./b'):
            with self.subTest(name=name), self.assertRaises(ValueError): m.safe_name(name)

    def test_symlink_rejected(self):
        self.bundle()
        with zipfile.ZipFile(self.archive,'a') as z:
            link=zipfile.ZipInfo('link'); link.create_system=3; link.external_attr=(stat.S_IFLNK|0o777)<<16
            z.writestr(link,'../escape')
        with self.assertRaisesRegex(ValueError,'symbolic'): m.unpack_verified(self.archive,self.root/'out',self.version)

    def test_untracked_member_rejected(self):
        self.bundle()
        with zipfile.ZipFile(self.archive,'a') as z: z.writestr('untracked','bad')
        with self.assertRaisesRegex(ValueError,'manifest'): m.unpack_verified(self.archive,self.root/'out',self.version)

    def test_case_collision_rejected(self):
        self.bundle(extra={'readme.md':b'case collision'})
        with self.assertRaisesRegex(ValueError,'Duplicate'): m.unpack_verified(self.archive,self.root/'out',self.version)

    def test_existing_target_is_untouched_and_not_downloaded(self):
        target=self.root/'existing'; target.mkdir(); marker=target/'notes'; marker.write_text('keep')
        with patch.object(m,'download_release') as download, self.assertRaisesRegex(ValueError,'already exists'):
            m.install(m.DEFAULT_REPO,self.version,'gh',target,'codex')
        download.assert_not_called(); self.assertEqual(marker.read_text(),'keep')

    def test_download_only_and_setup_exact_folder(self):
        self.bundle()
        with patch.object(m,'download_release',return_value=(self.archive,self.sums)), patch.object(m.subprocess,'run') as run:
            result=m.install(m.DEFAULT_REPO,self.version,'gh',self.root/'only','codex',True)
            self.assertFalse(result['prepared']); run.assert_not_called()
        with patch.object(m,'download_release',return_value=(self.archive,self.sums)), patch.object(m.shutil,'which',return_value='uv'), patch.object(m.subprocess,'run') as run:
            run.return_value.returncode=0
            result=m.install(m.DEFAULT_REPO,self.version,'gh',self.root/'prepared','claude')
            self.assertTrue(result['prepared'])
            self.assertEqual(run.call_args.args[0][-3:],['setup','--engine','claude'])
            self.assertEqual(run.call_args.kwargs['cwd'],self.root/'prepared')

    def test_preparation_failure_preserves_extracted_folder(self):
        self.bundle()
        with patch.object(m,'download_release',return_value=(self.archive,self.sums)), patch.object(m.shutil,'which',return_value='uv'), patch.object(m.subprocess,'run') as run:
            run.return_value.returncode=1
            with self.assertRaisesRegex(RuntimeError,'Preparation failed'):
                m.install(m.DEFAULT_REPO,self.version,'gh',self.root/'failed','codex')
        self.assertTrue((self.root/'failed/README.md').exists())

    def test_gh_failure_does_not_fallback_or_echo_output(self):
        with patch.object(m.shutil,'which',return_value='gh'), patch.object(m.subprocess,'run') as run, patch.object(m,'download_public') as public:
            run.return_value.returncode=1; run.return_value.stderr=b'private detail'
            with self.assertRaises(RuntimeError) as error: m.download_release(m.DEFAULT_REPO,self.version,'gh',self.root/'cache')
            self.assertNotIn('private detail',str(error.exception)); public.assert_not_called()

    def test_public_uses_fixed_release_assets(self):
        cache=self.root/'public'; cache.mkdir(); urls=[]
        def fetch(url,target,limit): urls.append(url); target.write_bytes(b'fixture')
        with patch.object(m,'download_public',side_effect=fetch), patch.object(m.subprocess,'run') as run:
            m.download_release(m.DEFAULT_REPO,self.version,'public',cache); run.assert_not_called()
        self.assertEqual(len(urls),2)
        self.assertTrue(all('/releases/download/product-v0.16.1/' in u for u in urls))

    def test_invalid_source(self):
        for repo,version in [('../repo',self.version),('owner/repo;bad',self.version),(m.DEFAULT_REPO,'latest')]:
            with self.assertRaises(ValueError): m.validate_source(repo,version)


if __name__=='__main__': unittest.main()
