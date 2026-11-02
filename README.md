# Reels While You Wait

A Chrome extension that plays short-form video while an AI chatbot is thinking, and pauses it the moment the answer is ready.

Send a message in ChatGPT, Claude, Gemini or another supported chat. A small window opens beside your chat with Instagram Reels, YouTube Shorts or TikTok. It plays and auto-scrolls while the AI writes. When the response finishes, the video pauses.

## Contents

- [Features](#features)
- [Install](#install)
- [First run](#first-run)
- [Using it](#using-it)
- [Supported sites](#supported-sites)
- [How it works](#how-it-works)
- [Permissions and privacy](#permissions-and-privacy)
- [Troubleshooting](#troubleshooting)
- [Limitations](#limitations)
- [Customizing](#customizing)
- [Project structure](#project-structure)

## Features

- **Opens and plays automatically** when a response starts generating, and **pauses** when it finishes.
- **Three video sources:** Instagram Reels, YouTube Shorts and TikTok.
- **Auto-scroll:** moves to the next video when the current one ends or loops, only while an AI is generating.
- **Doesn't steal focus.** You keep typing in your chat while the video window sits beside it.
- **Handles several chats at once.** It keeps playing until the last response finishes.
- **Remembers where you put the window** and respects it if you close it.
- **Never touches your normal browsing** on Instagram, YouTube or TikTok. It only controls the window it opened.

## Install

The extension isn't on the Chrome Web Store, so you load it as an unpacked extension.

1. Unzip the project folder.
2. Open `chrome://extensions`.
3. Turn on **Developer mode** (top right).
4. Click **Load unpacked** and choose the `reels-while-you-wait` folder.

AI tabs that were already open are picked up automatically, so there's no need to refresh them. Requires Chrome 110 or newer. Other Chromium browsers (Edge, Brave, Arc) should also work.

To update, replace the folder with the new version and click the reload icon on the extension's card in `chrome://extensions`.

## First run

1. Send a message in a supported AI chat.
2. A video window opens on the right edge of your screen.
3. **Log in** to the video site in that window. Instagram's Reels page needs an account.
4. **Click once** inside the window if you want sound. Chrome blocks autoplay with sound until you interact with the page, so videos play muted until then.
5. Drag or resize the window wherever you like. The extension remembers the position.

## Using it

Click the extension icon to open the popup.

| Control | What it does |
| --- | --- |
| **Enabled** | Master switch. When off, nothing opens or plays. |
| **Play from** | Instagram Reels, YouTube Shorts or TikTok. Changing it navigates an open window to the new source. |
| **Auto-scroll** | Advance to the next video when one ends or loops. On by default. |
| **Bring window to front** | When on, the video window keeps focus when it opens. Off by default so you stay in your chat. |
| **Play reels now / Pause reels** | Manual override, handy for testing. Pausing also clears a stuck "generating" state. |

The line under the title shows the current status. On a chat tab it also reads **This tab: watching for responses ✓** when detection is active there.

**Closing the window** is respected: it won't reopen until the next response starts. If you leave it open, it stays paused between responses and is raised to the front when the next one begins, with focus handed straight back to your chat.

## Supported sites

Chat sites the extension watches:

| Site | Detection |
| --- | --- |
| ChatGPT (`chatgpt.com`, `chat.openai.com`) | Stop button |
| Claude (`claude.ai`) | Stop button |
| Gemini (`gemini.google.com`) | Stop button |
| Perplexity (`www.perplexity.ai`) | Stop button |
| Microsoft Copilot (`copilot.microsoft.com`) | Stop button |
| Grok (`grok.com`) | Stop button |
| Mistral Le Chat (`chat.mistral.ai`) | Stop button |
| DeepSeek (`chat.deepseek.com`) | Generic "Stop" label fallback only |

Video sources: Instagram Reels, YouTube Shorts and TikTok.

Detection depends on each site's markup, which can change without notice. If a site stops working, see [Customizing](#customizing).

## How it works

Three scripts cooperate:

1. **`ai-detector.js`** runs on the chat sites and looks for the "Stop generating" button. When it appears, a response has started. When it disappears, the response is done. Two short delays (0.7 s to start, 1.8 s to stop) keep brief flickers, such as between tool calls, from causing false signals.
2. **`background.js`** is a service worker that tracks every AI tab. It opens one popup window, sends play and pause messages, places the window, and stays playing until the last active response finishes.
3. **`reels-controller.js`** runs on Instagram, YouTube and TikTok but only acts if the background worker says the tab is the one it opened. It plays the video most in view, pauses all videos on request, and handles auto-scroll by sending the ArrowDown shortcut, falling back to scrolling the feed by one screen.

After a pause, the controller keeps pausing for about 2.5 seconds so the site can't auto-resume. After that you can press play yourself.

## Permissions and privacy

| Permission | Why it's needed |
| --- | --- |
| `storage` | Saves your settings and the window position locally in your browser. |
| `system.display` | Finds your screen size so the window can open on the right edge. |
| `scripting` | Re-attaches the detector to already-open AI tabs after an update. |
| Chat site access | Lets the detector run on the supported AI sites listed above. |
| Video site access | Lets the controller play and pause in the window it opened. |

The extension does not make network requests of its own, collect analytics, or send anything anywhere. The detector only checks whether a "Stop" button is present on the page. It does not read your messages or the AI's responses. Settings stay in your browser's local extension storage.

## Troubleshooting

**The window doesn't open.**
Click the extension icon while on your chat tab. If it doesn't say the tab is being watched, that site isn't supported or its stop button isn't recognized. See [Customizing](#customizing). Also check that **Enabled** is on.

**The video is muted.**
Click once inside the video window. Chrome allows sound only after you interact with the page.

**The video pauses by itself.**
If another window completely covers the video window, Chrome may treat it as hidden and pause playback. Keep the two side by side, or drag the video window somewhere clear.

**Instagram shows a login screen.**
Log in once in the video window. The Reels page requires an account.

**Videos keep playing after the answer is done.**
Open the popup and press **Pause reels**. That also clears any stuck "generating" state. If it happens often on one site, its stop button likely changed markup.

**Auto-scroll isn't advancing.**
It triggers when a video ends or loops, so a long video plays through once first. If a site ignores both the ArrowDown shortcut and scrolling, auto-scroll will stall on that site.

## Limitations

- Autoplay with sound needs a click in the video window first. Until then videos play muted.
- A fully covered or minimized window can't play video. The extension restores a minimized window when a response starts.
- Selectors are best-effort. Chat sites change their interfaces, and the extension may need small updates to keep up.
- Raising the existing window briefly takes focus before handing it back to your chat, which may cause a brief flicker on some systems.
- If your chat window is maximized, it can cover the video window on the right edge. Move the video window once to fix it.

## Customizing

**Add or fix a chat site.** Open `ai-detector.js` and edit `SITE_SELECTORS`, which maps a hostname to a list of CSS selectors for that site's stop button:

```js
const SITE_SELECTORS = {
  'claude.ai': ['button[aria-label="Stop response"]'],
  // 'your-site.example': ['button[aria-label="Stop"]'],
};
```

Then add the site's URL pattern in two places in `manifest.json`: the `matches` list of the `ai-detector.js` content script, and `host_permissions`. Reload the extension.

**Change the window size.** Edit `WINDOW_SIZE` at the top of `background.js`.

**Change the timing.** `START_DELAY` and `STOP_DELAY` at the top of `ai-detector.js` control how long the page must look busy or idle before the extension reacts.

**Change the video sources.** Edit the `SOURCES` object in `background.js`, and add the matching option in `popup.html`. A new source's site also needs entries in the `reels-controller.js` match list in `manifest.json`.

## Project structure

```
reels-while-you-wait/
├── manifest.json         Extension manifest (Manifest V3)
├── background.js         Service worker: window, state, play/pause
├── ai-detector.js        Detects when an AI is generating
├── reels-controller.js   Plays, pauses and auto-scrolls the video
├── popup.html            Popup interface
├── popup.css             Popup styles (light and dark)
├── popup.js              Popup logic and status
├── icons/                Extension icons (16, 32, 48, 128)
└── README.md
```
