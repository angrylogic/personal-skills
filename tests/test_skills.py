import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'skills.py'
spec = importlib.util.spec_from_file_location('skills', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Workflow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'upstream'
        self.repo.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.email', 'test@example.com')
        self.git('config', 'user.name', 'Test')
        self.source = self.repo / 'pack' / 'demo'
        self.source.mkdir(parents=True)
        (self.source / 'SKILL.md').write_text('---\nname: demo\ndescription: Test workflow\nmetadata:\n  author: Alice # keep this\n---\nDo the task.\n')
        (self.source / 'a.txt').write_text('original\n')
        (self.source / 'b.txt').write_text('original\n')
        self.commit()
        self.baseline = self.git('rev-parse', 'HEAD').strip()
        self.local = self.root / 'personal'
        self.run_cli('import', 'demo', str(self.repo), 'pack/demo')
        self.skill = self.local / 'skills' / 'demo'

    def git(self, *args):
        return subprocess.check_output(['git', *args], cwd=self.repo, stderr=subprocess.PIPE, text=True)

    def commit(self):
        self.git('add', '.')
        self.git('commit', '-qm', 'change')

    def run_cli(self, *args, code=0):
        result = subprocess.run([sys.executable, str(SCRIPT), '--root', str(self.local), *args], capture_output=True, text=True)
        self.assertEqual(result.returncode, code, result.stderr)
        return result

    def test_import_diff_and_no_overwrite(self):
        content = (self.skill / 'SKILL.md').read_text()
        self.assertIn(self.baseline, content)
        self.assertIn('author: Alice # keep this', content)
        self.assertEqual(self.run_cli('diff', 'demo').stdout, '')
        (self.skill / 'a.txt').write_text('personal\n')
        patch = self.run_cli('diff', 'demo', code=1).stdout
        self.assertIn('+personal', patch)
        self.assertNotIn('upstream_revision', patch)
        self.run_cli('import', 'demo', str(self.repo), 'pack/demo', code=2)
        self.assertEqual((self.skill / 'a.txt').read_text(), 'personal\n')

    def test_update_preserves_local_changes_and_modes(self):
        (self.skill / 'a.txt').write_text('personal\n')
        (self.source / 'b.txt').write_text('new upstream\n')
        (self.source / 'run.sh').write_text('#!/bin/sh\nexit 0\n')
        (self.source / 'run.sh').chmod(0o755)
        self.commit()
        self.run_cli('update', 'demo', '--ref', 'HEAD')
        self.assertEqual((self.skill / 'a.txt').read_text(), 'personal\n')
        self.assertEqual((self.skill / 'b.txt').read_text(), 'new upstream\n')
        self.assertTrue((self.skill / 'run.sh').stat().st_mode & 0o111)
        self.assertIn(self.git('rev-parse', 'HEAD').strip(), (self.skill / 'SKILL.md').read_text())
        self.assertNotIn('new upstream', self.run_cli('diff', 'demo', code=1).stdout)

    def test_conflict_leaves_original_unchanged(self):
        (self.skill / 'a.txt').write_text('personal\n')
        before = module.files(self.skill)
        (self.source / 'a.txt').write_text('upstream\n')
        self.commit()
        review = self.root / 'review'
        self.run_cli('update', 'demo', '--ref', 'HEAD', '--output', str(review), code=2)
        self.assertEqual(before, module.files(self.skill))
        self.assertIn('<<<<<<< local', (review / 'a.txt').read_text())

    def test_deletions_and_additions(self):
        (self.source / 'a.txt').unlink()
        (self.skill / 'custom.txt').write_text('mine')
        (self.source / 'new.txt').write_text('new')
        self.commit()
        self.run_cli('update', 'demo', '--ref', 'HEAD')
        self.assertFalse((self.skill / 'a.txt').exists())
        self.assertEqual((self.skill / 'custom.txt').read_text(), 'mine')
        self.assertEqual((self.skill / 'new.txt').read_text(), 'new')

    def test_review_does_not_apply(self):
        before = module.files(self.skill)
        (self.source / 'b.txt').write_text('new')
        self.commit()
        review = self.root / 'review'
        self.run_cli('update', 'demo', '--ref', 'HEAD', '--output', str(review))
        self.assertEqual(before, module.files(self.skill))
        self.assertEqual((review / 'b.txt').read_text(), 'new')

    def test_nonoverlapping_edits_in_same_file(self):
        text = ''.join(f'line {i}\n' for i in range(30))
        (self.source / 'a.txt').write_text(text)
        self.commit()
        self.run_cli('update', 'demo', '--ref', 'HEAD')
        (self.skill / 'a.txt').write_text(text.replace('line 2\n', 'local edit\n'))
        (self.source / 'a.txt').write_text(text.replace('line 25\n', 'upstream edit\n'))
        self.commit()
        self.run_cli('update', 'demo', '--ref', 'HEAD')
        merged = (self.skill / 'a.txt').read_text()
        self.assertIn('local edit', merged)
        self.assertIn('upstream edit', merged)

    def test_binary_and_delete_conflicts(self):
        (self.source / 'binary').write_bytes(b'base\x00')
        self.commit()
        self.run_cli('update', 'demo', '--ref', 'HEAD')
        (self.skill / 'binary').write_bytes(b'local\x00')
        (self.skill / 'a.txt').write_text('local edit')
        (self.source / 'binary').write_bytes(b'upstream\x00')
        (self.source / 'a.txt').unlink()
        self.commit()
        before = module.files(self.skill)
        review = self.root / 'conflicts'
        result = self.run_cli('update', 'demo', '--ref', 'HEAD', '--output', str(review), code=2)
        self.assertIn('a.txt', result.stderr)
        self.assertIn('binary', result.stderr)
        self.assertEqual(module.files(self.skill), before)
        self.assertEqual((review / 'binary').read_bytes(), b'local\x00')

    def test_unsafe_paths_and_symlinks(self):
        self.run_cli('import', '../bad', str(self.repo), 'pack/demo', code=2)
        self.run_cli('import', 'bad', str(self.repo), '../outside', code=2)
        (self.source / 'link').symlink_to('/etc/passwd')
        self.commit()
        self.run_cli('import', 'bad', str(self.repo), 'pack/demo', code=2)
        self.assertFalse((self.local / 'skills' / 'bad').exists())


if __name__ == '__main__':
    unittest.main()
