# Watching video

An agent cannot play a video. [scripts/watch_video.py](../../scripts/watch_video.py) turns one into what it can read: a shot list, labelled contact sheets, a loudness timeline and stills. Use it for any video given as a reference (a cutscene, an effect, an animation, a UI flow, another game) and to watch your own work in motion. Its header records how each setting was chosen.

## ffmpeg
- **Assumed installed.** `python scripts/watch_video.py find` names the one in use; it also searches the usual install folders, so an install made after the shell started is found.
- **Exit code 3 means it is missing:** ask the user whether to install it, and only on a yes run `python scripts/watch_video.py install` (winget's `Gyan.FFmpeg` on Windows, Homebrew on macOS, apt on Linux, which asks for sudo). Sheets and the timeline also need Pillow (`pip install Pillow`).
- **Input** is a file or a direct media URL. A page (YouTube, a post) is not a video file: ask the user for the file.

## Watch, cheapest first
1. **Run `python scripts/watch_video.py watch VIDEO -o DIR`,** with DIR in the session's scratch folder. Read the printed summary before any image: length, size and frame rate, every shot with its start and length, rapid runs, the audio peak, onsets (and how many land on a cut) and silences.
2. **Look in this order, and stop when the task has what it needs:**
   - `overview.png`: 16 frames across the video, about 2,000 tokens.
   - `shots.png`: the middle of each shot, a rapid run as one tile.
   - `timeline.png`: loudness with cuts and onsets marked, about 500 tokens.
3. **Zoom in only where it matters:**
   - `burst VIDEO --start T --duration 1 -o OUT.png`: each new frame of one second, at most 24, labelled with source frame numbers, so a gap is a hold. Use it for anticipation, impact frames, how long a pose holds and a flash's rhythm. A rapid run in the summary is one of these.
   - `sheet VIDEO --start T --end T --count 12 -o OUT.png`: one stretch in more detail.
   - `frames VIDEO --at T,T -o DIR`: full-size stills, to match color, framing or UI exactly.
4. **Never pull every frame or a fixed 30 or 60 a second.** Decoding is cheap and viewing is not: an image costs about width × height / 750 tokens, and a sheet shows 12 to 24 moments for the price of one large still.
5. **Write down what you read as numbers:** shot order and lengths, holds in frames, beat times, where sounds land against cuts, and the camera in each shot (static, push in, pan, orbit, shake). Build from those numbers and check the result against the same ones.

**What it misses:**
- A dissolve or slow fade is not a cut, so a long shot can hide one: sheet it.
- Two shots that look alike are one.
- Onsets inside continuous music are its rhythm, not events.
- `--threshold` (0.35) finds subtler cuts lower down but splits flashes; higher up it loses real cuts.

## Watch your own work (Windows)
- **Record a window while it plays:** start `python scripts/watch_video.py record OUT.mp4 --window "Roblox Studio" --seconds 12` in the background, trigger the cutscene or effect through the game's own entry point, then `watch OUT.mp4`.
- **The two modes:** by default it grabs the window's own surface, which brought Studio's 3D view through (not black) at about 28 fps. `--mode screen` records the screen area instead, so whatever is on top is recorded. Keep Studio in front either way, since it can stop rendering 3D behind other windows ([ui.md](../ui/ui.md)).
- **Compare by the same numbers:** shot count and lengths, beats, holds. Frame-exact checks still use the Studio-only clock hold ([cutscenes.md](cutscenes.md)).
- **Clean up:** delete recordings and output folders when done, since they hold the user's screen.
