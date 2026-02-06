# MPV Remote

**Easy**, **Elegant** and **Minimalist**: MPV meets power.

---

**MPV Remote** is a lightweight, web-based remote control and media browser designed specifically for the **mpv media player**. It allows you to transform your computer or a headless media server into a home theater system that you can control comfortably from your smartphone or any browser. It has been developed on Linux Mint, but it should work on any modern Linux distribution (such as Ubuntu, Debian, or Fedora) that supports Python 3 and mpv.

Built with **Python** and **Tailwind CSS**, it bridges the gap between the raw power of mpv and the modern need for a beautiful, touch-friendly UI.

---
## Screenshots

<p align="center">  <img src="screenshot/main-screen.png" width="300" alt="Main Screen, from smartphone"> </p>
<p align="center"> <img src="screenshot/media-library.jpg" width="300" alt="Media browser from smartphone"> <img src="screenshot/media-library-with-thumb.jpg" width="300" alt="Media browser with thumb"> </p>


## Key Features

* **Sleek & Comfortable UI**: Designed with a "Volumio-inspired" dark aesthetic. Enjoy a visually pleasing interface with smooth transitions, neon accents, and a focus on content.
* **Media Library with Style**: Browse your files with ease. The UI automatically handles folder thumbnails (using `folder.jpg`) and applies a sophisticated glass-morphism effect with faded covers.
* **Live Preview**: Get a preview screenshot of what’s playing directly on your remote device—perfect for managing media from another room. If you are playing videos, the screenshot will be automatically updated every five seconds.
* **Complete Control**: Full management of playback (play/pause, seek, volume, fullscreen, stop, and quit).
* **Instant Setup**: No complex databases. No heavy dependencies. You need only python, and mpv. It scans your media folder directly and communicates with mpv via IPC socket.

---

## Quick Start

1. Make sure you have `mpv`, `python` installed on your system.
2. Clone this repository.
3. Place your media (or link your media folder) to the path defined in `mpv_remote.py` (default: `./media`), or edit `mpv_remote.py` in order to search media files in your favourite folder.
4. Launch the application
5. Open your browser and navigate to `http://<your-ip>:5000`, and enjoy!

```bash
git clone https://github.com/TheFax/MPV-Glass-Remote.git
cd MPV-Glass-Remote
python src/mpv_remote.py
```

---

## Philosophy

The main goal of **MPV Remote** is to make the media experience *effortless*.

* **Extra-Easy**: This application is absolutely easy to start and use.
* **Visual Hierarchy**: Large control buttons for touch screens.
* **Smart Thumbnails**: If a folder contains a `folder.jpg`, it becomes the background of the card, creating a premium "Netflix-style" browsing experience.
* **Responsive**: Works beautifully on iPhones, Android devices, and Tablets.

---

## Why I Built This

I started this project because I couldn't find a media controller that felt "just right." I wanted something that combined the aesthetic appeal of high-end systems with the raw performance of a lightweight script.

### The Problem with Existing Solutions

* **Volumio**: While it looks great, I found it to be quite **heavy** and **not very user-friendly** for quick setups. Most importantly, it is strictly limited to **audio only**, leaving no room for a complete media experience (for video I mean).
* **Kodi**: It is an incredible piece of software, but it has become **bloated** over the years. You can literally get lost in its endless menus and settings. Furthermore, despite its complexity, it often lacks an **optimized flow for music playback**, making it feel clunky for daily use.

### My Goal

I wanted a "third way": a tool that provides the **visual elegance** of Volumio but with the **simplicity** of a single Python script. By using **mpv** as the engine, I gained the ability to play literally any file format (video or audio) without needing hundreds of megabytes of background processes or complex configurations.

It's just you, your Python interpreter, and your media. No Node.js, no Docker, no headaches.

---

## Technical info

* **Backend**: Python
* **Frontend**: HTML5, Tailwind CSS, JavaScript
* **Player**: MPV (via JSON IPC)

The application relies on specific Linux-native features to function correctly:

* **Unix Domain Sockets**: The communication between the web interface and the player happens via `/tmp/mpv-socket`, a mechanism standard in Unix-like environments.
* **System Commands**: The backend uses `pkill` and `subprocess` to manage the media player instances directly within the OS.
* **Path Handling**: It uses standard Linux path conventions for file navigation.

While the core logic is Linux-centric, it could potentially run on **macOS** with minor adjustments to the media paths and socket locations, provided `mpv` is installed via Homebrew. However please note that this has not been tested on macOS (yet).

---

## License

This project is open-source. Feel free to fork it, or modify it and help me to improve it!
