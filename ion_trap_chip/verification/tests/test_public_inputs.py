"""Private simulation inputs must be explicit and runs remain isolated."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from experiments.paths import input_path, run_data

ROOT = Path(__file__).resolve().parents[3]

class PublicInputs(unittest.TestCase):
    def prepare(self, *args):
        return subprocess.run([sys.executable,'-m','tools.prepare_run',*map(str,args)],cwd=ROOT,capture_output=True,text=True)

    def test_control_run_needs_no_device_model(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)/'control'
            result = self.prepare('--output',target)
            self.assertEqual(result.returncode,0,result.stderr)
            with patch.dict(os.environ,{'IONFORGE_RUN_DIR':str(target)}):
                self.assertEqual(run_data(),target.resolve())
                with self.assertRaisesRegex(ValueError,'Missing user-supplied model'):
                    input_path('model')

    def test_missing_model_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)/'run'
            result = self.prepare('--output',target,'--model',Path(folder)/'missing.mph')
            self.assertNotEqual(result.returncode,0)
            self.assertFalse(target.exists())

    def test_missing_profile_files_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)/'run'
            result = self.prepare('--output',target,'--reference-profiles',folder)
            self.assertNotEqual(result.returncode,0)
            self.assertFalse(target.exists())

    def test_existing_run_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)/'run'
            self.assertEqual(self.prepare('--output',target).returncode,0)
            config = (target/'inputs.json').read_bytes()
            self.assertNotEqual(self.prepare('--output',target).returncode,0)
            self.assertEqual((target/'inputs.json').read_bytes(),config)

if __name__ == '__main__': unittest.main()
