# Meshes built in Studio (EditableMesh)

A Blender model brought into Roblox without an FBX upload: its vertex data rebuilt in Studio as EditableMeshes and published from there, when no Open Cloud key works ([uploading.md](../safety/uploading.md)) or a model is assembled in Studio. FBX imports: [modeling.md](modeling.md).

## Build and publish
- **Export** each Blender object as triangles, flat normals and vertices in Roblox axes: Blender (x, y, z) becomes Roblox (x, z, -y), which keeps the winding. Keep the vertices in model space, with the model's pivot at its floor centre.
- **Rebuild** each in Edit as an EditableMesh (`AddVertex`, `AddTriangle`, `AddNormal`, `SetFaceNormals`) and publish it with `AssetService:CreateAssetAsync(mesh, Enum.AssetType.Mesh, ...)` to the experience's group, naming the owner (it defaults to the Studio user). 5 of 5 published, at 24-64 KB of Luau per mesh, one MCP call each.
- **Send big vertex data in several StringValues,** each under 200,000 characters: a mesh's vertex text sent to Studio in 60 KB chunks appended to one StringValue failed at 214,490 characters ("Provided string length ... is greater than or equal to max"). One StringValue per chunk in a folder, concatenated in name order by the build call, published all 11 egg meshes (up to 9,334 corners each) to the group with `CreateAssetAsync`.
- **Make the MeshParts** with `AssetService:CreateMeshPartAsync(Content.fromAssetId(id))`: their `MeshSize` equalled the exported boxes. Seconds after `CreateAssetAsync` the MeshParts had no `MeshId` yet: create them once the assets are processed, and check `MeshId` on every part before saving.
- **Save** the assembled model with `python scripts/studio_mcp.py save` into the `.rbxm` the project maps; under Rojo, read the last section first.

## Place every part at the model's origin
Meshes published from EditableMesh keep their vertices in the asset's own space and are not recentred, unlike FBX imports. Put each part's CFrame on the model's pivot, never at its bounding-box centre: five portal meshes placed at their box centres (the stone at y 10.19) drew the whole frame about 10 studs above a code-built swirl at the ring's height (10.05), the ring floating over the swirl and the plinth hanging at swirl height. On the pivot they drew exactly as modelled, the swirl centred in the ring.

## Lost mesh links
A rebuilt model whose MeshParts hold empty `MeshId`s draws as plain boxes (a portal frame's five MeshParts in a Rojo-synced `.rbxm`). `AssetService:CreateMeshPartAsync(Content.fromAssetId(id))`, then `part:ApplyMesh(source)`, restores each mesh (`MeshId` becomes the asset URI); then stand each part on the model's pivot, or the frame floats about 10 studs up.

## Under Rojo
Keep a MeshPart model assembled in Studio in Studio, and never let Rojo replace it. A chest assembled with `CreateMeshPartAsync` from eight freshly published EditableMesh assets was saved as a binary `.rbxm` and mapped in the Rojo project; Rojo's synced copy drew as plain studded boxes, every MeshPart reading `MeshId = ''` and `MeshSize = 0`. The binary file holds the mesh only in `MeshContent`, which Rojo does not read. An `.rbxmx` rewritten with `<Content name="MeshId">` and `InitialSize` synced its hinge and `PrimaryPart` but still no mesh, because live sync cannot set `MeshId` at all. What worked: keep the Studio-assembled instance (re-created after the assets were processed), remove Rojo's copy, and keep the `.rbxmx` with `MeshId` and `InitialSize` for `rojo build`. A model mapped the same way earlier only looked right because Rojo had patched the original Studio instance: its binary file carries no mesh id either, so a place built from the files shows it as boxes.
