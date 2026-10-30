# Character models (R15 and R6)

For NPCs, enemies, vendors, collectibles and any character template. A character that could read as female also follows [characters.md](characters.md); animating one is [animation.md](animation.md).

- **A look from catalog items** (hair, clothing, body parts): generate an R15 from a HumanoidDescription (below).
- **A character with its own art** (a monster, a boss, a stand, a costume): a **skin** on a standard R6 or R15 rig (Skins, below). This is the default for building a custom R6 or R15 character.

## R15: generate it, never assemble it by hand

Describe the look as a HumanoidDescription and let Roblox build the rig (Edit mode or server):

```lua
local desc = Instance.new("HumanoidDescription")
desc:SetAccessories({
	{ AssetId = hairId, AccessoryType = Enum.AccessoryType.Hair },
	{ AssetId = jacketId, AccessoryType = Enum.AccessoryType.Jacket, IsLayered = true, Order = 3 },
}, true)
desc.HeadColor = skin -- and TorsoColor, LeftArmColor, RightArmColor, LeftLegColor, RightLegColor
local model = Players:CreateHumanoidModelFromDescription(desc, Enum.HumanoidRigType.R15)
```

- **What a description can set:** body part ids (`Head`, `Torso`, ...), scales (`HeightScale`, `WidthScale`, `DepthScale`, `HeadScale`, `BodyTypeScale`, `ProportionScale`), classic `Shirt`/`Pants`, and per-accessory `Position`, `Rotation`, `Scale` and `Puffiness`.
- **Prefer layered clothing** (jacket, shirt, pants, with `IsLayered` and an `Order`, higher worn outside) to classic 2D Shirt/Pants; it reads better on 3D bodies.
- **Keep each look as data** (ids, colors, scales, adjustments), so the whole cast can be rebuilt in another place.

**Then fix what the generator leaves** (`RigAudit.seat` and `RigAudit.clean` do 1-4):
1. **Seat every accessory.** Set each Handle's CFrame to where its AccessoryWeld holds it. The generator leaves handles where the catalog asset sat (seen 13 to 2,800 studs away), and only physics pulls them in. Anchored models, viewports and previews then show floating hair and clothes.
2. **Remove the generated scripts** (Animate, Health) when the project animates characters itself.
3. **Remove the default face under a face accessory:** the Head's Decal and the head MeshPart's TextureID (the default head texture is a face, which shows through as two dots). `clean` handles Face accessories; a hair or hat with a face built in needs the same by hand.
4. **Remove the handles' TouchInterests** unless the game listens for Touched on accessories. Catalog accessories arrive with one saved in, and it stays until removed.
5. **Finish the template:** name it, put metadata in attributes, keep the HumanoidRootPart as PrimaryPart, and store it in ReplicatedStorage only when clients show it (ServerStorage otherwise).

**What it is made of** (all of it stays):
- **Root:** the HumanoidRootPart, 2×2×1, invisible: the PrimaryPart and pivot.
- **Body:** 15 MeshParts: Head, UpperTorso, LowerTorso, and Left/Right UpperArm, LowerArm, Hand, UpperLeg, LowerLeg and Foot.
- **Joints:** one per part (Root, Waist, Neck, Shoulder, Elbow, Wrist, Hip, Knee, Ankle), held by the child part between two same-named `<Joint>RigAttachment`s.
  - Generated rigs use an AnimationConstraint, a limited BallSocketConstraint (none at Root) and NoCollisionConstraints between neighbours. Imported and older rigs use Motor6Ds with the same names. Animations play on both.
  - `Humanoid:BuildRigFromAttachments()` rebuilds every joint from the rig attachments.
- **Accessory points** (Attachments named `<Point>Attachment`):
  - Head: Hair, Hat, FaceFront, FaceCenter;
  - UpperTorso: Neck, BodyFront, BodyBack, LeftCollar, RightCollar;
  - LowerTorso: WaistFront, WaistCenter, WaistBack;
  - upper arms: Left/RightShoulder; hands: Left/RightGrip; feet: Left/RightFoot; root: Root.
- **Accessory:** a Handle holding one Attachment named like a body point, and an AccessoryWeld (Handle to that body part) that brings the two together. `Humanoid:AddAccessory` makes the weld. Layered clothing adds a WrapLayer on the Handle, which wraps the WrapTarget cage inside each body part.
- **Humanoid:** an Animator, the HumanoidDescription (the applied look), six scale NumberValues with AutomaticScalingEnabled, and HipHeight (2.19 at default scale; the floor sits at the root's bottom minus HipHeight).
- **Scaler records:** OriginalSize and OriginalPosition (Vector3Values on parts and attachments) and AvatarPartScaleType (a StringValue on handles). Resize through the description's scales, never by resizing parts.
- **Looks:** BodyColors (skin per part) and FaceControls (dynamic heads).

**Custom bodies** (the art is the 15 parts themselves) are the exception: use one only when the shape cannot fit a standard rig (Skins, below).
- Model on an R15 skeleton ([animation.md](animation.md)) and import with the 3D Importer as an R15 rig, so the 15 parts carry R15 names and rig attachments.
- Check with `BuildRigFromAttachments` and an AnimationInspector audit, which must show no `unmatched`.

## R6

- **Parts:** six plus the root: Head (2×1×1), Torso (2×2×1), Left/Right Arm and Left/Right Leg (1×2×1), and HumanoidRootPart (2×2×1).
- **Joints:** Motor6Ds: RootJoint in the root (to the Torso), and Neck, Left/Right Shoulder and Left/Right Hip in the Torso.
- **What it lacks:** rig attachments, layered clothing and scale values. HipHeight is 0, because the legs carry the height.
- **Accessories are welded onto the part they ride on,** an AccessoryWeld through the classic points. Custom art is a skin (below), not pieces welded and positioned by hand. The points:
  - Head: Hair, Hat, FaceFront, FaceCenter;
  - Torso: Neck, BodyFront, BodyBack, collars, waist points;
  - arms: Shoulder and Grip; legs: Foot.
- **A generated R6 makes the Head its PrimaryPart;** set it to the root (`clean`).

## Skins: custom art on a standard rig (the default)

A skin dresses a standard R6 or R15 rig and never replaces it. The rig keeps its parts, joints, HipHeight, scale values, cages and hitbox, so these all work unchanged: every R6 or R15 animation, the Humanoid's movement and the game's hit detection. The art rides on top, massless and with no collision. One rig can wear many skins, and a player's own character can wear one.

Build a custom body only when the shape cannot fit the standard proportions: extra limbs, a tail that animates, a creature twice the height.

**Build around the body** *(default)*. The rig's body parts stay visible and are part of the look; the skin adds what the body lacks.
- **Color the body parts to fit** the design (`colors`), so where the body shows it reads as the character: a yellow Stand gets yellow limbs, a knight gets dark undercloth.
  - Take the color from the skin's color map: the median of its main color on the sides of its forms, with ink and hatching left out (a plain average counts the ink and comes out far too dark).
  - On a hand-painted map, don't use the palette's base color: baked shading darkens it in the texture, so a body in the base color looks pale beside the skin (seen 2026-10-30).
- **Pieces sit around the parts:** armor, pads, a helmet, tubes, trims, belts, boots. They overlap the body at their edges or stand clear of it, never coplanar with a part's face (that flickers, [modeling.md](modeling.md)).
- **A custom face is a face decal** on the rig's head (`face`), drawn for the head's front, not a modeled mask over the head. A helmet frames it. A dynamic head (FaceControls, as on a generated R15) garbles a decal (seen 2026-10-30), so `face` puts it on a classic head piece there (`Head__Face`) and hides that head.
- **Hide a body part only as a design choice:** when the design replaces it (a head that is not a head, a limb covered end to end by a piece of another shape). Never hide one to skip modeling around it.

**Which kind:**
- **R6: welded pieces.** One piece per body part (`Head`, `Torso`, `Left Arm`, ...), held to that part. A part can carry several (`Head__Halo`).
- **R15: welded pieces by default.** The art is cut at the joints, one piece per part, and each piece hinges where its part does. This reads crisp and toy-like, which suits blocky and armored characters.
- **R15: a skinned mesh** when the art must bend without a seam: a long coat over the hips, sleeves over the elbows, a creature with one continuous surface.
  - It is one mesh with Bones named after the body parts, weighted in Blender and bound so each Bone rides its part.
  - Rigid weights (each vertex on one part) move exactly like welded pieces. Blend a little at the joints for a smooth bend (`rigid_weights(..., blend=0.08)`; at most 4 influences per vertex, [animation.md](animation.md)).

**The two R15 builds:** RigSkin reads both, but their sizes differ with their scales, so fit each skin to the rig it is for (step 1). A Rig Builder R15 stands with its root 3 studs up. A rig generated from a blank HumanoidDescription stands at 3.19 studs (HipHeight 2.19), with longer legs and arms and a taller head. A player's avatar follows its own scales.
- **Rig Builder:** Motor6D joints, a Part head with a SpecialMesh, no cages and no Animator.
- **A player's avatar, or a generated rig:** AnimationConstraint joints, a MeshPart head, WrapTarget cages and accessories.

**Workflow:** [scripts/RigSkin.luau](../scripts/RigSkin.luau) runs in Studio and [scripts/roblox_rig.py](../scripts/roblox_rig.py) in Blender.
1. **Dump the rig the skin is for.** `return RigSkin.dump(rig)` in Edit gives JSON: the body parts, the joint pivots and attachments (relative to the root), and the root's height.
2. **Build its replica in Blender:** `rr.build(rr.load(path), colors=...)`. It makes the body as it looks in game, one solid part per body part (`RIG_<part>`: a box, or a rounded head), in the colors you will give it, plus an armature with one bone per part, each bone's head at its joint.
   - Blender space: the ground at 0, the character facing -Y, its left at +X, 1 unit = 1 stud.
3. **Model around the replica** with [modeling.md](modeling.md)'s workflow (and [characters.md](characters.md)).
   - [scripts/skin_kit.py](../scripts/skin_kit.py) has the R6/R15 layout (segment boxes, joint heights, the body part that owns each height), the shapes (bevelled boxes, limb wraps open toward the torso, squircle domes, outline prisms, lettering), the clay-check renders and the PBR stage.
   - The replica body stays in every clay check and render: it is part of what the player sees.
   - Cut at the joint pivots, not at the box edges.
   - Each piece covers one box and may overhang it (a helmet, a skirt), but it moves with that part only.
   - Read the wrist, ankle and other joint heights from the dump instead of guessing them.
4. **Name and export:**
   - **Welded:** name each piece after its body part (`LeftUpperArm`, `Left Arm`), or `<Part>__<Look>` for one piece per part and material (`Head__Gold`), then `rr.export_pieces(pieces, path)`.
   - **PBR** (the default, [modeling.md](modeling.md)): after the clay check, `kit.merge` joins each part's pieces into one `<Part>__Skin` (glow looks stay apart, for Neon), `kit.unwrap` packs them into one atlas, `kit.bake` bakes the four SurfaceAppearance maps, and `kit.render(..., pbr=True)` shows them.
   - **Skinned:** give the mesh vertex groups named after the body parts (`rr.rigid_weights(mesh, rig, blend)`, or painted) and parent it to the replica's armature, then `rr.export_skinned(mesh, armature, path)`.
   - **Both** put every object's origin at the scene origin. Roblox's importer keeps a mesh's vertices but drops its object's own transform, so a piece exported with its origin at its centre imports at the file origin; the `astray` rule catches this.
5. **Check and upload:** run blender-asset-qa and ZFight as for any model ([modeling.md](modeling.md)), then upload one Model asset ([assets.md](assets.md)) or bring it in with the 3D Importer.
   - Pass `qa_check` the pieces with the replica body (`RIG_*` but the root) and `--tol 0.03` (pieces stand clear of the body). An R15 replica's boxes overlap at the joints as its meshes do: its `RIG_`<->`RIG_` z-fighting is expected.
   - The importer drops textures embedded in the FBX (no TextureID or SurfaceAppearance, seen 2026-10-30): upload the four maps as images too.
6. **Dress the rig:** insert the asset, then, before moving it, call one of:
   - welded: `RigSkin.apply(rig, skin, { colors = { Body = color }, face = faceImage })`;
   - skinned: `RigSkin.bind(rig, skinned, { colors = ..., face = ... })`.

   What they do and take:
   - **The pieces** go in a `Skin` folder, massless, with CanCollide, CanTouch and CanQuery off. Dressing again is safe: weld attachments left by deleted pieces are removed first.
   - **`looks`** styles pieces by the name after `__` (`{ Gold = { Color = c, Material = Enum.Material.Metal } }`): imported MeshParts arrive gray Plastic (seen 2026-10-30). An Instance value is cloned into each piece: for PBR, `{ Skin = { SurfaceAppearance = sa } }`, with `sa` made in Studio from the uploaded maps. Game scripts can neither set nor read a SurfaceAppearance's maps (they lack the Plugin capability) but can clone one, maps and all (seen 2026-10-30), so keep `sa` with the skin in ServerStorage.
   - **`colors`** sets the body's colors by BodyColors group (`Head`, `Torso`, `LeftArm`, `RightArm`, `LeftLeg`, `RightLeg`, or `Body` for all), on the parts and in BodyColors. `RigSkin.color(rig, colors)` does it alone.
   - **`face`** puts an image on the head's face decal (an `rbxassetid://` image id; a Decal asset's id resolves to its image through `InsertService:LoadAsset`).
   - **`hide`** makes every covered body part and the face invisible (they stay the hitbox): only when the design replaces them.
   - **`hideAccessories = true`** is for a player's avatar, whose hats would otherwise float over the skin's head.
   - **`map`** sends a name that does not follow the convention to a body part.
7. **Check** (the next section): `RigSkin.audit` together with RigAudit, then one stock clip in AnimationInspector, whose findings must match the bare rig's.

**In a game:** keep the skin in ServerStorage, and dress each character on the server: clone the skin, then `apply` or `bind`. For a player, do it after `Player.CharacterAppearanceLoaded`, so `hideAccessories` finds the hats and the colors are not overwritten by the avatar's own (applying a HumanoidDescription again resets them).
- **Mid-animation is fine.** RigSkin measures the rig's rest pose from its joints, not where the parts are posed.
- **Each piece is held by a RigidConstraint named `SkinWeld`.** A Humanoid's death (`BreakJointsOnDeath`, on by default) breaks every Weld and WeldConstraint in the character, which drops welded pieces through the floor. A RigidConstraint keeps each piece on its limb as the body falls apart.

## Check every character model before use

1. **Audit:** `return select(2, RigAudit.audit(model))` in Edit mode must report 0 errors ([scripts/RigAudit.luau](../scripts/RigAudit.luau)).
   - The rules are `parts`, `joint`, `root`, `rig`, `anchored`, `unwelded`, `unseated`, `unmatched`, `layered`, `touch`, `default-face` and `script`.
   - `seat` and `clean` fix the generator's side effects. A `parts`, `joint` or `layered` error needs a rebuild.
2. **A skinned rig:** `return select(2, RigSkin.audit(rig))` must also report 0 errors.
   - The rules are `unwelded`, `unseated`, `astray` (a piece clear of its part, or a Bone outside it), `anchored`, `collision`, `mass`, `unbound`, `bare` (a part hidden with no skin over it), `hidden` (a warning for every hidden body part: fine only when the design replaces it) and `stale` (weld attachments left by deleted pieces: dress again).
   - Play-test one walk: the skin must stay on.
3. **Look** at it front and side: nothing floats, it has a face, and the clothes sit on the body.
