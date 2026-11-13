# Measuring performance

Finding what makes a game slow (low frame rate, hitches, script time, memory) by measurement before changing anything. The fixes are coding rules: [coding.md](coding.md), Performance. Studio MCP mechanics: [studio-testing.md](studio-testing.md).

## Before measuring

- **Look at the screen and the camera first:** one `screen_capture` at the start. Close popups, note any weather or event running and where the character stands: the first half hour of one session's numbers were taken behind a reward window over a blurred world, during a weather event, 145 studs from the fight.
- **Check what else the machine runs** (`Get-Process`, the GPU engine counters) before trusting a frame time: with the game unchanged the same view ran 30 to 75 FPS over an hour as another Roblox client and other GPU programs ran (`Stats.RenderGPUFrameTime` 2.5 to 11 ms).

## How to measure

- **Never judge a change by absolute FPS in a shared Studio:** plain before-and-after runs contradicted each other. Use an interleaved on/off test (on 3 s, off 3 s, three times, means compared) and counters that do not depend on load: `Stats.SceneDrawcallCount`, `ShadowsDrawcallCount`, `UI2DDrawcallCount`, and `Stats.FrameRateManager`'s children `PrepareAverage`, `PerformAverage`, `AveragePresent`, `Batches`.
- **Count per rendered frame.** In Studio Play the simulation can step several times a frame: a client's `Heartbeat` fired 83 to 208 times a second while `RenderStepped` fired 22 to 50, so per-second costs of `Heartbeat` and `Stepped` handlers (Roblox's own character sounds script read as the top cost) were up to four times too high. Count both events over a few seconds.
- **Script time per function: `ScriptProfilerService` through `execute_luau`** (`os.clock` around one function for a quick check). Client call: `ClientStart(player, 1000)`, `ClientStop(player)`, `ClientRequestData(player)` and the `OnNewData(player, json)` event; Server call: `ServerStart(1000)`, `ServerStop()`, `ServerRequestData()`. The JSON (Version 2) has `Categories {Name, NodeId}`, `Nodes {TotalDuration in microseconds, NodeIds, FunctionIds}` and `Functions {Name, Source, Line}`; a node's self time is its duration minus its children's. The MicroProfiler's web server and dump are out of reach (`UserGameSettings.MicroProfilerWebServerEnabled` needs RobloxScript).
- **Lua allocation and heap** come from a temporary LocalScript in the game's VM, not an `execute_luau` call (which measures its own VM): allocation a second is the sum of positive `gcinfo()` deltas per `Heartbeat`, the heap is `gcinfo()` sampled over a few seconds.
- **Hide test subjects with `LocalTransparencyModifier`, never by reparenting:** moving a folder of 98 dressed R6 rigs out of Workspace and back made the next two measurements three times slower for several seconds (their clothing was composited again), which read as the change under test costing that.
