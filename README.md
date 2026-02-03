# 📦 sysdupd

### A modern, cross-platform system updater built with libadwaita and Python.

> "Have you ever wanted to just fully update your system and forgot how? This is the solution for you!"

![license](https://img.shields.io/badge/license-MIT-pink) 
![platform](https://img.shields.io/badge/platform-linux-peach)
![style](https://img.shields.io/badge/design-libadwaita-blue)

---

## Features? We have plenty of those...

* **System Overview** – Shows your specs right on the main dashboard (neofetch style but really clean and straightforward).
* **Notifications** – Get pinged when your system is falling behind.
* **Background service** – Optional daemon to check for updates while you're busy.
* **The "risky" button** – Auto-apply updates in the background. Live life on the edge.
* **History** – A full log of what you've updated and when.
* **Ignore list** – Keep those flaky packages exactly where they are.
* **Terminal integration** – This uses your preferred terminal emulator.
* **Desktop entry** – Easily generate a `.desktop` file for your app drawer, never run the `sysdupd` command ever again!

## Screenshots

![screenshot](sample/image.png) 
---

## Installation

If you're on arch (which you should be, honestly *wink wink*), just grab it from the AUR:

```bash
# stable version
yay -S sysdupd

# bleeding edge
yay -S sysdupd-git
```

