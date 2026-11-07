# Audio: sound effects, music and mixing

An agent cannot hear, so every choice here is made from numbers: what a file contains, when it peaks and how loud the mix gets. Toolbox rules for sounds: [assets.md](../safety/assets.md).

## Find
- **Licensed libraries first:** Pro Sound Effects (userId `7462895450`) and APM (userId `7462718749`). Their audio plays in any experience; audio other creators upload is often private to their own. Moderation does not clear copyright: when the owner treats any Toolbox sound as cleared, say so once, then follow them.
- **Search them through the Toolbox API**, since Studio MCP search cannot filter by creator: `GET https://apis.roblox.com/toolbox-service/v1/marketplace/3?keyword=<words>&creatorTargetId=<userId>&creatorType=1&limit=<n>` (3 is audio) lists ids, and `GET https://apis.roblox.com/toolbox-service/v1/items/details?assetIds=<id,...>` gives each one's title, artist, `audioType` (`SoundEffect` or `Music`), category, duration and description, which confirms the publisher.
- Choose by description, then measure (below) before it goes in the sound table.

## Measure
- **Probe silently:** wire an `AudioPlayer` only to an `AudioAnalyzer`, with no `AudioDeviceOutput` on the wire. Nothing reaches the speakers, but `RmsLevel` and `PeakLevel` read true levels, so many files can be compared at once, even in the owner's open session.
- **Bin a one-shot's loudness over time** (quarter-second bins) before trusting one peak reading. Bins show what a peak hides: a file holding a second and third hit, a long quiet tail, a candidate peaking at 0.04 that its name made sound usable.
- From the bins read duration, onset, peak time and loudness, and the spectrum (`AudioAnalyzer:GetSpectrum()`), so each sound lands on its beat and sits in the mix.
- **Subtract a load delay first:** exact zeros at the start of a reading are the file starting late, not silence in it. In one probe of 13 files every envelope had one nonzero bin, then 0.6 s of exact zeros, then the sound, so every onset and peak read 0.6 s late; another probe had no delay. Find the leading exact-zero bins and subtract them before setting Start or Hit times.

## Play and mix
- Put ids in the project's sound table and play them through the project's audio path. Roblox now discourages `Sound`, `SoundGroup` and `SoundEffect` in favor of the Audio API ([audio objects](https://create.roblox.com/docs/audio/objects)): `AudioPlayer` -> `Wire` -> `AudioDeviceOutput` for 2D; `AudioPlayer` -> `Wire` -> `AudioEmitter`, heard through `AudioListener` -> `Wire` -> `AudioDeviceOutput`, for 3D; `AudioEqualizer`, `AudioCompressor` and `AudioReverb` on the wire. New audio systems use it; a project built on `Sound` stays consistent (`Volume`, `RollOffMaxDistance` and a `SoundGroup` matching the existing audio) until it migrates.
- **A few buses into a limiter** *(default)*: scene, clean (UI and stingers) and music, each wired into an `AudioLimiter` before the output. `AudioLimiter.MaxLevel` is decibels, from -12 to 0 (so -1, never 0.9).
- **Meter each bus during a real match**, with an `AudioAnalyzer` on it: layers that are fine alone stack (three sounds on one beat summed to 1.86 before the limiter; trimmed, 1.36). Trim or stagger what lands together.
- **Music needs no preload:** an `AudioPlayer` keeps a `TimePosition` set before it has loaded, so set it and call `Play`; tracks not yet loaded were ready in about 0.24 s and started from the set point. A fade-in covers that, and phones keep the memory. Music may play on an `AudioPlayer` (its `Asset`), not a `Sound`: look for both.
