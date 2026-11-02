#!/usr/bin/env python3
"""Build an auto-minimize release from the original GitHub extension ZIP.

Usage: python scripts/build-auto-minimize.py
Requires only Python's standard library. The original ZIP remains untouched.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile, ZIP_DEFLATED
import json

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "reels-while-you-wait.zip"
OUTPUT = ROOT / "reels-while-you-wait-auto-minimize.zip"

def replace_one(text, before, after, label):
    if text.count(before) != 1:
        raise RuntimeError(f"{label}: expected 1 match, found {text.count(before)}")
    return text.replace(before, after, 1)

with TemporaryDirectory() as temp:
    root = Path(temp)
    with ZipFile(SOURCE) as z:
        if any(Path(n).is_absolute() or ".." in Path(n).parts for n in z.namelist()):
            raise ValueError("Unsafe ZIP path")
        z.extractall(root)
    ext = root / "reels-while-you-wait"
    bg = ext / "background.js"
    s = bg.read_text()
    s = replace_one(s,
        "focusOnStart: true };",
        "focusOnStart: true, autoMinimize: true };",
        "default settings")
    s = replace_one(s,
        "async function pauseReels(state) {",
        "async function pauseReels(state, settings) {",
        "pause function")
    s = replace_one(s,
        "  chrome.tabs.sendMessage(state.reels.tabId, { type: 'reels-pause' }).catch(() => {});\n}",
        """  await chrome.tabs.sendMessage(state.reels.tabId, { type: 'reels-pause' }).catch(() => {});
  if (settings.autoMinimize && !state.forced) {
    const win = await chrome.windows.get(state.reels.windowId).catch(() => null);
    if (win && win.state === 'normal') {
      await chrome.windows.update(win.id, { state: 'minimized' }).catch(() => {});
    }
  }
}""",
        "pause and minimize")
    s = replace_one(s, "else await pauseReels(state);", "else await pauseReels(state, settings);", "reconcile")
    s = replace_one(s, "changes.enabled || changes.source)) return;",
                    "changes.enabled || changes.source || changes.autoMinimize)) return;",
                    "settings listener")
    bg.write_text(s)

    popup = ext / "popup.js"
    s = popup.read_text()
    s = replace_one(s,
        "autoScroll: true };",
        "autoScroll: true, autoMinimize: true };",
        "popup defaults")
    s = replace_one(s,
        "  $('autoscroll').checked = s.autoScroll;",
        """  $('autoscroll').checked = s.autoScroll;
  $('autominimize').checked = s.autoMinimize;
  $('autominimize').addEventListener('change', (e) =>
    chrome.storage.local.set({ autoMinimize: e.target.checked }));""",
        "popup binding")
    popup.write_text(s)

    html = ext / "popup.html"
    s = html.read_text()
    s = replace_one(s,
        '  <button id="toggle" type="button">Play reels now</button>',
        """  <label class="row">
    <span>Auto-minimize on completion
      <small>Restore on the next response</small>
    </span>
    <input type="checkbox" id="autominimize" class="switch">
  </label>
  <button id="toggle" type="button">Play reels now</button>""",
        "popup control")
    html.write_text(s)

    manifest = ext / "manifest.json"
    m = json.loads(manifest.read_text())
    m["version"] = "1.2.0"
    manifest.write_text(json.dumps(m, indent=2) + "\n")

    with ZipFile(OUTPUT, "w", ZIP_DEFLATED) as z:
        for file in ext.rglob("*"):
            if file.is_file():
                z.write(file, file.relative_to(root))
print(f"Built: {OUTPUT}")
