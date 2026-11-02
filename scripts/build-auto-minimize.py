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
        "if (msg.generating) state.generating[tab.id] = true;\n        else delete state.generating[tab.id];",
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
        '  <button id="dashboard" type="button">My Focus Dashboard</button>\n  <button id="toggle" type="button">Play reels now</button>',
        "dashboard button")
    popup.write_text(s)

    popup = ext / "popup.js"
    s = popup.read_text()
    s += """\n$('dashboard').addEventListener('click', () => {
  chrome.tabs.create({ url: chrome.runtime.getURL('dashboard.html') });
});\n"""
    popup.write_text(s)

    # Session crossover experiment: optional 30-minute sessions, randomized
    # first condition, alternate condition second. No per-response randomization.
    bg = ext / "background.js"
    s = bg.read_text()
    s = replace_one(s,
        "const anyGenerating = (state) => Object.keys(state.generating).length > 0;",
        """const anyGenerating = (state) => Object.keys(state.generating).length > 0;
async function currentFocusStudy() {
  const { focusStudy = null } = await chrome.storage.local.get('focusStudy');
  if (!focusStudy || !focusStudy.consent || !focusStudy.active) return null;
  if (Date.now() >= focusStudy.endsAt) {
    await chrome.storage.local.set({focusStudy: {...focusStudy, active:false, completed:Math.min(2,(focusStudy.completed||0)+1), endedAt:Date.now()}});
    return null;
  }
  return focusStudy;
}
async function studyCondition() {
  const study = await currentFocusStudy();
  return study ? study.condition : 'observational';
}""",
        "session experiment helper")
    s = replace_one(s,
        "const wantsPlay = (state, settings) => settings.enabled && (state.forced || anyGenerating(state));",
        """const wantsPlay = (state, settings) => settings.enabled &&
  (state.forced || (anyGenerating(state) && state.focusStudyCondition !== 'control'));""",
        "session condition playback")
    s = replace_one(s,
        "if (msg.generating) {",
        """if (msg.generating) {
          state.focusStudyCondition = await studyCondition();
          const settings = await getSettings();""",
        "study playback condition")
    s = replace_one(s,
        "if (!state.generating[tab.id]) await recordAnalyticsStart(tab.id, tab);",
        """if (!state.generating[tab.id]) {
            await recordAnalyticsStart(tab.id, tab);
            const rec = activeAnalytics.get(tab.id);
            if (rec) {
              const study = await currentFocusStudy();
              rec.condition = study ? study.condition : 'observational';
              rec.studySessionId = study ? study.sessionId : '';
              rec.videoEnabled = settings.enabled && (!study || study.condition === 'treatment');
            }
          }""",
        "session response metadata")
    bg.write_text(s)

    html = ext / "popup.html"
    s = html.read_text()
    s = replace_one(s,
        '  <button id="dashboard" type="button">My Focus Dashboard</button>',
        """  <section aria-label="Optional focus study">
      <strong>Optional Focus Study</strong>
      <small>Two 30-minute work sessions: normal workflow and video-assisted.
      Session order is random. Results stay on this browser.</small>
      <label class="row"><span>I agree to participate locally</span>
        <input type="checkbox" id="studyconsent" class="switch"></label>
      <div id="studystatus" role="status"></div>
      <button id="studystart" type="button">Start next 30-minute session</button>
      <button id="studyend" type="button">End study session</button>
    </section>
    <button id="dashboard" type="button">My Focus Dashboard</button>""",
        "focus study UI")
    html.write_text(s)
    popup = ext / "popup.js"
    s = popup.read_text()
    s += """
(async () => {
  const consent = $('studyconsent'), start = $('studystart'), end = $('studyend');
  const status = $('studystatus');
  async function refreshStudy() {
    const { focusStudy = null } = await chrome.storage.local.get('focusStudy');
    let active = !!(focusStudy && focusStudy.active && Date.now() < focusStudy.endsAt);
    if (focusStudy?.active && !active) {
      focusStudy.active = false;
      focusStudy.completed = Math.min(2,(focusStudy.completed||0)+1);
      focusStudy.endedAt = Date.now();
      await chrome.storage.local.set({focusStudy});
    }
    consent.checked = !!focusStudy?.consent;
    start.disabled = !consent.checked || active || (focusStudy?.completed || 0) >= 2;
    end.disabled = !active;
    status.textContent = active
      ? 'Active: '+(focusStudy.condition === 'control' ? 'normal workflow (no auto-video)' : 'video-assisted')+
        ' — ends '+new Date(focusStudy.endsAt).toLocaleTimeString()
      : (focusStudy?.completed || 0) >= 2 ? 'Both study sessions completed'
      : 'Completed: '+(focusStudy?.completed || 0)+'/2 sessions';
  }
  consent.addEventListener('change', async () => {
    const {focusStudy = {completed:0}} = await chrome.storage.local.get('focusStudy');
    await chrome.storage.local.set({focusStudy:{...focusStudy,consent:consent.checked,
      active:consent.checked && !!focusStudy.active}});
    await refreshStudy();
  });
  start.addEventListener('click',async()=>{
    const {focusStudy = {completed:0}} = await chrome.storage.local.get('focusStudy');
    if (!focusStudy.consent || focusStudy.active || focusStudy.completed >= 2) return;
    const first = focusStudy.firstCondition ||
      (crypto.getRandomValues(new Uint8Array(1))[0] < 128 ? 'control':'treatment');
    const condition = focusStudy.completed === 0 ? first :
      (first === 'control' ? 'treatment' : 'control');
    const now = Date.now();
    await chrome.storage.local.set({focusStudy:{...focusStudy, firstCondition:first,
      condition, active:true, startedAt:now, endsAt:now+30*60*1000,
      sessionId:crypto.randomUUID()}});
    await refreshStudy();
  });
  end.addEventListener('click',async()=>{
    const {focusStudy} = await chrome.storage.local.get('focusStudy');
    if(!focusStudy?.active)return;
    await chrome.storage.local.set({focusStudy:{...focusStudy,active:false,
      completed:Math.min(2,(focusStudy.completed||0)+1),endedAt:Date.now()}});
    await refreshStudy();
  });
  chrome.storage.onChanged.addListener((changes,area)=>{
    if(area==='local' && changes.focusStudy) refreshStudy();
  });
  await refreshStudy();
})();
"""
    popup.write_text(s)
    with ZipFile(OUTPUT, "w", ZIP_DEFLATED) as z:
        for file in ext.rglob("*"):
            if file.is_file():
                z.write(file, file.relative_to(root))
print(f"Built: {OUTPUT}")
