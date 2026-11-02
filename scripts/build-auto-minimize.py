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

    # Local-only analytics and dashboard, bundled into the extension.
    import shutil
    shutil.copy2(ROOT / "analytics/dashboard.html", ext / "dashboard.html")
    shutil.copy2(ROOT / "analytics/dashboard.js", ext / "dashboard.js")

    bg = ext / "background.js"
    s = bg.read_text()
    s = replace_one(s,
        "const DEFAULT_SETTINGS = {",
        """const MAX_ANALYTICS_SESSIONS = 2000;
const activeAnalytics = new Map();
const completedAnalytics = new Map();
let analyticsSequence = 0;
async function recordAnalyticsStart(tabId, originTab) {
  if (activeAnalytics.has(tabId)) return;
  const startedAt = Date.now();
  activeAnalytics.set(tabId, { id: String(startedAt) + '-' + (++analyticsSequence),
    startedAt, platform: (() => {
      try { return new URL(originTab.url || '').hostname; } catch { return 'unknown'; }
    })(), videoEnabled: true });
}
async function recordAnalyticsEnd(tabId) {
  const rec = activeAnalytics.get(tabId);
  if (!rec) return;
  activeAnalytics.delete(tabId);
  rec.completedAt = Date.now();
  rec.durationMs = Math.max(0, rec.completedAt - rec.startedAt);
  rec.returnLatencyMs = null;
  const { analyticsSessions = [] } = await chrome.storage.local.get('analyticsSessions');
  analyticsSessions.push(rec);
  await chrome.storage.local.set({ analyticsSessions: analyticsSessions.slice(-MAX_ANALYTICS_SESSIONS) });
  completedAnalytics.set(tabId, rec.id);
}
async function recordAnalyticsReturn(tabId) {
  const id = completedAnalytics.get(tabId);
  if (!id) return;
  const { analyticsSessions = [] } = await chrome.storage.local.get('analyticsSessions');
  const rec = analyticsSessions.find(r => r.id === id);
  if (!rec || rec.returnLatencyMs !== null) return;
  rec.returnLatencyMs = Math.max(0, Date.now() - rec.completedAt);
  await chrome.storage.local.set({ analyticsSessions });
  completedAnalytics.delete(tabId);
}
const DEFAULT_SETTINGS = {""", "analytics helpers")
    s = replace_one(s,
        "if (msg.generating) state.generating[tab.id] = true;\\n        else delete state.generating[tab.id];",
        """if (msg.generating) {
          if (!state.generating[tab.id]) await recordAnalyticsStart(tab.id, tab);
          state.generating[tab.id] = true;
        } else {
          if (state.generating[tab.id]) await recordAnalyticsEnd(tab.id);
          delete state.generating[tab.id];
        }""", "tracking events")
    s = replace_one(s,
        "// ---- cleanup ---------------------------------------------------------------",
        """chrome.tabs.onActivated.addListener(({ tabId }) => enqueue(async () => {
  await recordAnalyticsReturn(tabId);
}));
chrome.windows.onFocusChanged.addListener(windowId => {
  if (windowId === chrome.windows.WINDOW_ID_NONE) return;
  enqueue(async () => {
    const tabs = await chrome.tabs.query({ active: true, windowId }).catch(() => []);
    if (tabs[0]) await recordAnalyticsReturn(tabs[0].id);
  });
});
// ---- cleanup ---------------------------------------------------------------""", "return interaction")
    bg.write_text(s)

    popup = ext / "popup.html"
    s = popup.read_text()
    s = replace_one(s,
        '  <button id="toggle" type="button">Play reels now</button>',
        '  <button id="dashboard" type="button">My Focus Dashboard</button>\\n  <button id="toggle" type="button">Play reels now</button>',
        "dashboard button")
    popup.write_text(s)

    popup = ext / "popup.js"
    s = popup.read_text()
    s += """\\n$('dashboard').addEventListener('click', () => {
  chrome.tabs.create({ url: chrome.runtime.getURL('dashboard.html') });
});\\n"""
    popup.write_text(s)
    with ZipFile(OUTPUT, "w", ZIP_DEFLATED) as z:
        for file in ext.rglob("*"):
            if file.is_file():
                z.write(file, file.relative_to(root))
print(f"Built: {OUTPUT}")
