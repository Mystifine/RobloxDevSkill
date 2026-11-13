# Watching video

An agent cannot play a video. [scripts/watch_video.py](../../scripts/watch_video.py) turns one into what it can read: a shot list, labelled contact sheets, a loudness timeline and stills. Use it for any video given as a reference (a cutscene, an effect, an animation, a UI flow, another game) and to watch your own work in motion. Its header records how each setting was chosen.

## ffmpeg
- **Assumed installed.** `python scripts/watch_video.py find` names the one in use; it also searches the usual install folders, so an install made after the shell started is found.
- **Exit code 3 means it is missing:** ask the user whether to install it, and only on a yes run `python scripts/watch_video.py install` (winget's `Gyan.FFmpeg` on Windows, Homebrew on macOS, apt on Linux, which asks for sudo). Sheets and the timeline also need Pillow (`pip install Pillow`).
- **Input** is a file or a direct media URL. A page (YouTube, a post) is not a video file: ask the user for the file.

## Watch, cheapest first
1. **Run `python scripts/watch_video.py watch VIDEO -o DIR`,** with DIR in the session's scratch folder. Read the printed summary before any image: length, size and frame rate, every shot with its start and length, rapid runs, the audio peak, onsets (and how many land on a cut) and silences.
2. **Look in this order, and stop when the task has what it needs:**
   - `overview.png`: 24 frames across the video, about 3,000 tokens.
   - `shots.png`: each shot's in, middle and out frame (a rapid run as one), and six frames from in to out for the longer half of the shots, about 3,100 tokens a page for 12 shots (a 45-shot clip takes three pages, about 7,700). Read each shot's camera move and the path of its action across its tiles: the middle alone hid both in 10 of a clip's 22 shots and runs, and in, middle and out skipped four beats inside one 6.8 s shot. A long shot can wrap to the next row; its labels (`2/6`) say so.
   - `timeline.png`: loudness with cuts and onsets marked, about 500 tokens.
3. **Zoom in only where it matters:**
   - `burst VIDEO --start T --duration 1 -o OUT.png`: each new frame of one second, at most 36, labelled with source frame numbers, so a gap is a hold. Use it for anticipation, impact frames, how long a pose holds and a flash's rhythm. A rapid run in the summary is one of these.
   - `sheet VIDEO --start T --end T --count 18 -o OUT.png`: one stretch in more detail.
   - `frames VIDEO --at T,T -o DIR`: full-size stills, to match color, framing or UI exactly.
4. **Never pull every frame or a fixed 30 or 60 a second.** Decoding is cheap and viewing is not: an image costs about width × height / 750 tokens, and a sheet shows 18 to 36 moments for the price of one large still.
5. **Write down what you read as numbers,** per shot: its length, holds in frames, beat times and where sounds land against cuts; its size (wide, full, waist-up, close), where the subject sits in the frame and which way it faces or moves, the camera (static, push in, pan, orbit, shake), the lens (long and flat, or wide and deep), the light's direction and the main colors. A one-line description per shot loses most of this. Build from those numbers and check the result against the same ones.
6. **Keep the analysis with the work's record:** `summary.md` and the sheets you read go in the project's notes, so a later change starts from them. The video stays where the user keeps it.

**Speech:** `python scripts/watch_video.py words VIDEO [--language en]` prints each word's time from a local speech model (faster-whisper, through `uv` if this Python lacks it; a model downloads on first use), with the onsets beside them. Use it to time captions and beats, and to screen a track's language before upload. Word times are a guess under music or a hum: one word came back over a second early inside a steady hum, so check each start against the onsets.

**What it misses:**
- A dissolve or slow fade is not a cut, so a long shot can hide one: sheet it.
- Two shots that look alike are one.
- A still border (an app's panels, black bars) dilutes the cut score: a clip filling 45% of the frame gave 6 of its 29 shots. Crop it out (`record --crop`).
- A variable frame rate (a screen recording, often) is named in the summary: frame numbers land on the wrong moments there, so frames are sought by timestamp.
- Onsets inside continuous music are its rhythm, not events.
- `--threshold` (0.35) finds subtler cuts lower down but splits flashes; higher up it loses real cuts.

## Watch your own work (Windows)
- **Record only the 3D view:** Studio's panels fill over half of a recorded window, shrinking the game in every tile and hiding cuts (above). Make a short first recording, take `frames OUT.mp4 --at 1 -o DIR` at full size, read the 3D view's width, height, left and top off it, and pass them as `--crop W:H:X:Y` from then on.
- **Record a window while it plays:** start `python scripts/watch_video.py record OUT.mp4 --window "Roblox Studio" --seconds 12 --crop W:H:X:Y` in the background, trigger the cutscene or effect through the game's own entry point, then `watch OUT.mp4`. For repeatable runs of a real match, start the action from a separate call: a temporary LocalScript waits on a workspace attribute and then uses the game's entry point, and setting the attribute once recording has begun gave runs with no input timing problems.
- **The two modes:** by default it grabs the window's own surface, which brought Studio's 3D view through (not black) at about 28 fps. `--mode screen` records the screen area instead, so whatever is on top is recorded. Keep Studio in front either way, since it can stop rendering 3D behind other windows ([ui.md](../ui/ui.md)).
- **Compare by the same numbers, then by picture:** shot count and lengths, beats, holds; then `compare REFERENCE OUT.mp4 --pairs 2.3=1.6,7=5.2 -o OUT.png`, which sets each reference moment beside yours. Pair the in, middle and out of each reference shot with the recording's moments built for them (the recording's own times: one cut found in it and matched to its keyed time gives the offset for the whole recording, even when strong color grades hide the other cuts from the detector). Look for a different shot size, the subject on the other side, a missing element, a color that drifted. Frame-exact checks still use the Studio-only clock hold ([cutscenes.md](cutscenes.md)).
- **Judge motion and effects from a Play recording, not stills:** inspector sheets and Blender renders could not show whether a run stepped; a recording with a scripted side camera following the character, then `burst`, showed planted feet and flight, and exposed a skill's smoke burying its crescent and a red floor disc reading as a pool. The camera re-reads the current character every frame: equipping respawned it and a stale reference filmed the wrong spot.
- **When the game pulls the player back** (a teleport home, walls in the way), film a client-side stand-in: clone the character on the client (`Archivable` on, scripts removed), anchor it in profile beside the camera's target and play the clip at the game's rate (WalkSpeed / 14.5 for R6 walks); `record --crop` around it, then `burst`, shows one stride.
- **Clean up:** delete recordings and their output folders when done, since they hold the user's screen.
