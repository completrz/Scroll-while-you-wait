"""Regression tests for the packaged extension. Run: python -m unittest discover -s tests"""
import json
import subprocess
import sys
import unittest
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ZIP=ROOT/"reels-while-you-wait-auto-minimize.zip"

class BuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run([sys.executable,str(ROOT/"scripts/build-auto-minimize.py")],check=True,cwd=ROOT)
    def test_expected_files(self):
        with zipfile.ZipFile(ZIP) as z:
            base="reels-while-you-wait/"
            for name in ("manifest.json","background.js","popup.js","popup.html","dashboard.js","dashboard.html","reels-controller.js","ai-detector.js"):
                self.assertIn(base+name,z.namelist())
    def test_manifest(self):
        with zipfile.ZipFile(ZIP) as z:
            manifest=json.loads(z.read("reels-while-you-wait/manifest.json"))
            self.assertEqual(manifest["manifest_version"],3)
            self.assertEqual(manifest["version"],"1.2.0")
            self.assertEqual(len(manifest["content_scripts"]),2)
    def test_weekly_comparison_ui(self):
        with zipfile.ZipFile(ZIP) as z:
            base="reels-while-you-wait/"
            html=z.read(base+"dashboard.html").decode()
            js=z.read(base+"dashboard.js").decode()
            self.assertIn('id="week"', html)
            self.assertIn("previous 7 days", js)
    def test_session_study_controls(self):
        with zipfile.ZipFile(ZIP) as z:
            base="reels-while-you-wait/"
            html=z.read(base+"popup.html").decode()
            script=z.read(base+"background.js").decode()
            popup=z.read(base+"popup.js").decode()
            self.assertIn('id="studyconsent"',html)
            self.assertIn('id="studystart"',html)
            self.assertIn('id="studyend"',html)
            self.assertIn("currentFocusStudy",script)
            self.assertIn("studySessionId",script)
            self.assertIn("const settings = await getSettings();",script)
            self.assertIn("rec.videoEnabled = settings.enabled",script)
            self.assertIn("30*60*1000",popup)
    def test_no_remote_analytics(self):
        with zipfile.ZipFile(ZIP) as z:
            scripts="\n".join(z.read(n).decode("utf-8") for n in z.namelist() if n.endswith(".js"))
            self.assertNotIn("supabase.co",scripts)
            self.assertNotIn("/ingest",scripts)
    def test_controls(self):
        with zipfile.ZipFile(ZIP) as z:
            html=z.read("reels-while-you-wait/popup.html").decode()
            self.assertIn('id="autominimize"',html)
            self.assertIn('id="dashboard"',html)

if __name__=="__main__":
    unittest.main()
