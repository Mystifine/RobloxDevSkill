# Texture bakes in Blender

What goes wrong inside a bake into one atlas, from a high-poly source or from several objects. The asset workflow, map sizes and texel density are in [modeling.md](modeling.md).

- **Several objects into one atlas: bake each group alone.** Baked one after another into the same image, each bake's margin overwrote islands already baked: slivers of one group's color on another (mouth color on fur, read as wounds), then the reverse once reordered. Bake each group with margin 0 into a spare image, copy only that group's exact island mask into the atlas, then grow the margins (numpy) into empty texels only, and fill what is left with the dominant color.
- **Pack every island once, by outline.** Scale the islands that need more or less density first, then pack them all in one `bpy.ops.uv.pack_islands` call with the outline shape (`shape_method='CONCAVE'`). Packing the rest around pinned, `LOCKED` islands overlapped about 20% of another part's UVs (Blender 5.1).
- **Keep procedural detail under the texel density:** a strand noise at about 26 cycles a stud on an atlas of about 48 texels a stud (under 2 texels a cycle) aliased into grey patches; about 7 a stud (about 7 texels a cycle) read as strands.
- **Hide the high-poly source before judging a bake:** three re-bakes chased blotches and a mosaic eye that were the source z-fighting with the game mesh; the maps were fine.
- **A long call drops while the work goes on:** Blender MCP calls returned "No data received" after about 2 to 3 minutes while Blender finished the bake and wrote its files. Wait on the output files' modification times instead of baking again, or run long bakes headless ([modeling.md](modeling.md), Running Blender).
- **Blender 5.1's bundled Python has no Pillow:** run image work for a bake in the system Python.
