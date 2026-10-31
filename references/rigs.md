# Character models (R15 and R6)

For NPCs, enemies, vendors, collectibles and any character template. A character that could read as female also follows [characters.md](characters.md); animating one is [animation.md](animation.md).

- **A look from catalog items** (hair, clothing, body parts): generate an R15 from a HumanoidDescription (below).
- **A character with its own art** (a monster, a boss, a stand, a costume): a **skin** on a standard R6 or R15 rig (Skins, below). This is the default for building a custom R6 or R15 character.
- **Either way, no Humanoid** *(default)*: build it with one, then swap it for an AnimationController (Without a Humanoid, below). Keep the Humanoid only for what needs one.

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
6. **Swap the Humanoid** *(default)*: `RigAudit.controller(model)`, last, once accessories (and a skin) are on (Without a Humanoid, below).

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

## Without a Humanoid (the default)

A Humanoid is costly; a rig that only animates plays the same clips through an AnimationController *(default)*. Build it with the Humanoid as above (the generator, `AddAccessory` and the scales need one), dress it, then in Studio `RigAudit.controller(model)` (`{ Anchored = false }` for a root held by movers) and audit (Check, below).

- **`controller`** moves the Animator to an AnimationController, anchors the root, removes the Animate and Health scripts, and records `RootHeight`: studs from the floor to the root's centre where the Humanoid stood it (3.19 on a blank generated R15, 3 on R6). It gives each textured body part an Overlay SurfaceAppearance: without a Humanoid a dynamic head showed its texture untinted, white whatever its Color. Game scripts cannot set that map, so convert in Studio.
- **Unchanged** (generated R6 and R15 in Play): parts, joints, attachments, cages, accessories, layered clothing (bending with the limbs), skins, gear, and every R6 or R15 clip, replicated to clients, with AnimationInspector findings equal to the Humanoid rig's.
- **Place the root at `RootHeight`:** unanchored and unheld it sank about 2 studs, legs through the floor (only the root, head and torso collide). Move an anchored root by CFrame, or hold an unanchored one with AlignPosition and AlignOrientation. Walking NPCs: [gameplay.md](gameplay.md).
- **BodyColors no longer recolors the parts:** set their colors (`RigSkin.color` sets both).
- **Keep the Humanoid** (skip `controller`) for a player's character, and for one that needs `MoveTo`, walking physics, jumping, climbing, a Seat or a Tool (gear on a Motor6D works without); `Health`, `Died`, `BreakJointsOnDeath` or the name and health display; classic Shirt and Pants (they stop showing; layered clothing and skins still show); or `AddAccessory`, `ApplyDescription` or automatic scaling after the build.

## Skins: custom art on a standard rig (the default)

A skin dresses a standard R6 or R15 rig and never replaces it. The rig keeps its parts, joints, HipHeight, scale values, cages and hitbox, so these all work unchanged: every R6 or R15 animation, the Humanoid's movement and the game's hit detection. The art rides on top, massless and with no collision. One rig can wear many skins, and a player's own character can wear one.

Build a custom body only when the shape cannot fit the standard proportions: extra limbs, a tail that animates, a creature twice the height.

**Build around the body** *(default)*. The rig's body parts stay visible and are part of the look; the skin adds what the body lacks.
- **Color the body parts to fit** the design (`colors`), so where the body shows it reads as the character: a yellow Stand gets yellow limbs, a knight gets dark undercloth.
  - Take the color from the skin's color map: the median of its main color on the sides of its forms, with ink and hatching left out (a plain average counts the ink and comes out far too dark).
  - On a hand-painted map, don't use the palette's base color: baked shading darkens it in the texture, so a body in the base color looks pale beside the skin.
- **Pieces sit around the parts:** armor, pads, a helmet, tubes, trims, belts, boots. They overlap the body at their edges or stand clear of it, never coplanar with a part's face (that flickers, [modeling.md](modeling.md)).
- **A wrap closes all the way around** *(default)*. Whatever reads as worn around a limb or the torso (a sleeve, gauntlet, boot, trouser leg or bodysuit, or a coat of scales, fur or plate) covers every side of it, including the sides that touch a neighbour at rest: an arm's and a leg's inner side, the torso's flanks. The rest pose hides those sides and any swing shows them (a dragon's scale sleeves and leggings, open on those sides, passed every audit and clay view yet showed bare limbs on every step).
  - **Clipping there is fine:** the limb is moving whenever that side shows, so a closed side may cut into the torso or the other leg. Never leave a side open to avoid it. Flicker is still not fine, so use `wrap`'s `tuck` (step 3), which keeps the wall out of the neighbour's planes at rest.
  - **Leave a side open only when the design does:** a piece that belongs to one side of the limb, such as a wing or feather sleeve along the outer arm, a shoulder plate, a fin or a cape. Decide piece by piece, say which in the plan, and list the side in `gaps`' `open_sides`. References rarely show these sides: carry the material around them unless it reads as one-sided.
  - **Detail goes around too:** scale rows, fur and trim continue onto those sides, so they don't show as a plain strip. Each half of a split skirt rides its own leg, so it closes as well.
- **A custom face is a face decal** on the rig's head (`face`), drawn for the head's front, not a modeled mask over the head. A helmet frames it. A dynamic head (FaceControls, as on a generated R15) garbles a decal, so `face` puts it on a classic head piece there (`Head__Face`) and hides that head.
  - **Its layout:** a 512x512 transparent PNG spans the head's front: `y = (head top - z) / head height * 512`, `x = 256 + studs from the centre * 512 / 1.2`. Measure the eyes, nose and mouth on the reference and convert them. Under a fringe the eyes sit below the head's centre: on a head 1.2 tall, eye centres at (151, 335) and (361, 335) and the mouth at y 438 clear a bob's fringe.
  - **Its style:** the skin's resolved linework and shading, not the standalone-icon fallback ([modeling.md](modeling.md), Art drawn for a model).
- **A layer that hangs past the hips** (a tabard, a coat skirt) is cut in two down its centre, each half on its own leg, so a stride swings it instead of a leg cutting through it; a band on the hip part laps the tops of both. It stands in front of the boots and knee plates it overlaps, so its depth grows as it falls.
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
   - [scripts/skin_kit.py](../scripts/skin_kit.py) has the R6/R15 layout (segment boxes, joint heights, the body part that owns each height), the shapes (bevelled boxes, limb wraps, squircle domes, outline prisms, lettering, hair), the clay-check renders and the PBR stage. Hair follows Hair, below.
   - Close a limb's wrap with `kit.wrap(..., tuck=a['inner'])` and the torso's with `tuck='x'`. `open_side` is only for a side the design leaves open.
   - The replica body stays in every clay check and render: it is part of what the player sees.
   - Cut at the joint pivots, not at the box edges.
   - Each piece covers one box and may overhang it (a helmet, a skirt), but it moves with that part only.
   - Read the wrist, ankle and other joint heights from the dump instead of guessing them. Scale a design from `L['legs'][side]['hip']`, never a leg's `hi`: a generated R15's upper leg box runs 0.2 studs above its joint, into the lower torso. Heights as fractions of each segment fit one design to R6 and R15.
   - **Armor, trims and plates that follow the body:** `kit.Form`, with `band`, `ribbon`, `plate` and `blade` laid on its surface and `Pieces.cut` cutting at the joints (the kit's header). A rounded wrap clears a box corner only when `w - 0.293 * r` is more than the box's half size: `kit.pokes(rig, pieces)` lists corners that come through, which show as a hairline unless the piece is the body's color.
   - **Hidden faces count:** a shell's inner face on the body's or the other leg's, two rims cut in one plane, plates' undersides at one depth, the two ends of a strip right round a form. Give each its own depth, and keep a leg's wall thinner than its gap past the centre line. `kit.coplanar(pieces)` lists them with positions.
   - **Check the wraps at the clay stage:** `kit.gaps(rig, pieces, open_sides)` must return `{}`. It lists each body part's bare sides and heights, wherever pieces cover the front and back or three sides. Close each one, or list it as open by design (`{a['upper']: a['inner']}`, or `'x'` for both flanks, as for a sleeveless top's corners at the shoulders). No rest-pose view shows these sides, so also render them with the limbs pulled clear: `kit.render(out_dir, 'apart', views=kit.INNER, apart=1.5, res=(900, 900))`. `gaps` and `apart` read welded pieces; for a skinned mesh, pose its armature and look.
4. **Name, validate and texture:** run blender-asset-qa on the clay geometry before UVs and baking. Pass the pieces with the replica body (`RIG_*` but the root) and `--tol 0.03` (pieces stand clear of the body); only an R15 replica's `RIG_`<->`RIG_` joint overlaps are expected. Preserve separate ornaments when gathering pieces; welding their coincident vertices can create non-manifold joins.
   - **Welded:** name each piece after its body part (`LeftUpperArm`, `Left Arm`), or `<Part>__<Look>` for one piece per part and material (`Head__Gold`).
   - **Anime ink in full PBR**, when selected by Style precedence (the skin fallback, [modeling.md](modeling.md)): after the clay check, `kit.sharpen` crisps the rims and `kit.merge` joins each part's pieces into one `<Part>__Skin` (glow looks stay apart, for Neon). Then for each of `kit.regions(skins)` (head, torso, arms, legs): `kit.unwrap` packs one atlas, with hollow islands split and hidden faces given little of it, and `kit.paint` makes the four 1024x1024 maps. Wrap the body in cloth pieces, closed over the hand's end and the sole. `kit.render(..., pbr=True)` shows them.
   - **Realistic PBR,** when selected: `kit.unwrap` one atlas per region, `kit.bake` the four maps.
   - **Skinned:** give the mesh vertex groups named after the body parts (`rr.rigid_weights(mesh, rig, blend)`, or painted) and parent it to the replica's armature.
   - **Both** put every object's origin at the scene origin. Roblox's importer keeps a mesh's vertices but drops its object's own transform, so a piece exported with its origin at its centre imports at the file origin; the `astray` rule catches this.
5. **Check, export and upload:** repeat blender-asset-qa on the finished geometry (UV checks on for PBR; the replica has no UVs and its own joints overlap, so those two findings on `RIG_` parts alone do not count), then `rr.export_pieces(pieces, path)` or `rr.export_skinned(mesh, armature, path)`, which refuse a mesh that overlaps itself ([modeling.md](modeling.md)). Re-import the FBX to verify names, triangle counts, bounds and UVs. Upload one Model asset ([assets.md](assets.md)) or bring it in with the 3D Importer; run ZFight after dressing in Studio ([modeling.md](modeling.md)).
   - Upload every map as an image too. `export_pieces` and `export_skinned` keep textures out of the FBX: embedded, they arrive as a SurfaceAppearance on each piece, which competes with the maps you set and can leave a piece plain gray.
   - A map that failed stays failed on what holds it, and one can fail for minutes after approval, or for good: one fetched as Success while the part stayed gray, and a fresh upload of the same file fixed it. Check each map before it goes on with `RigSkin.preload(images)`, which reads them through ImageLabels: `PreloadAsync` on a bare id string reports Failure for a good map in Edit, and on a SurfaceAppearance reports nothing. Then look at the result in Studio: audits do not see this.
6. **Dress the rig** (weapons and shields come after: Gear, below): insert the asset, then, before moving it, call one of:
   - welded: `RigSkin.apply(rig, skin, { colors = { Body = color }, face = RigSkin.image(faceId), surfaces = { Head = RigSkin.surface(head), Torso = ..., Arms = ..., Legs = ... } })`, with `head` the region's `{ color, normal, metal, rough }` Decal asset ids;
   - skinned: `RigSkin.bind(rig, skinned, { colors = ..., face = ... })`.

   What they do and take:
   - **The pieces** go in a `Skin` folder, massless, with CanCollide, CanTouch and CanQuery off. Dressing again is safe: weld attachments left by deleted pieces are removed first.
   - **`surfaces`** gives each piece its region's SurfaceAppearance by the body part it rides, replacing any already there. Game scripts can neither set nor read a SurfaceAppearance's maps (they lack the Plugin capability) but can clone one, maps and all, so keep them with the skin in ServerStorage.
   - **`looks`** styles pieces by the name after `__` (`{ Gold = { Color = c, Material = Enum.Material.Metal } }`): imported MeshParts arrive gray Plastic. An Instance value is cloned into each piece.
   - **`DoubleSided`** goes on every MeshPart in the rig, the generated body included.
   - **`colors`** sets the body's colors by BodyColors group (`Head`, `Torso`, `LeftArm`, `RightArm`, `LeftLeg`, `RightLeg`, or `Body` for all), on the parts and in BodyColors. `RigSkin.color(rig, colors)` does it alone.
   - **`face`** puts an image on the head's face decal (an `rbxassetid://` image id; a Decal asset's id resolves to its image through `InsertService:LoadAsset`).
   - **`hide`** makes every covered body part and the face invisible (they stay the hitbox): only when the design replaces them.
   - **`hideAccessories = true`** is for a player's avatar, whose hats would otherwise float over the skin's head.
   - **`map`** sends a name that does not follow the convention to a body part.
7. **Swap the Humanoid** *(default)*: `RigAudit.controller(rig)`.
8. **Check** (the next section): `RigSkin.audit` together with RigAudit, then one stock clip in AnimationInspector, whose findings must match the bare rig's.

## Hair

A skin's hair is a `Head__Hair` piece built with `kit.Hair` ([skin_kit.py](../scripts/skin_kit.py)). A style the reference draws as one smooth volume with a jagged hem, such as a bob, is built with `H.shell`, not locks, which come out as a comb of teeth around a dome: a darker shell whose `H.points` and `H.teeth` make the fringe and hem, and a lighter one over it (`off=.035`), shorter, for two tones. `H.bob` keeps it against the cheeks, or the face sits in a dark hood. Read from 48 anime hair meshes on the classic head (in studs for a head 1.2 tall):
- **A volume, not a helmet.** The hair is a dome over the head: its top stands about 0.42 above the head's (at least 0.2), it sits about 0.22 off the scalp and bulges about 0.33 behind but only 0.14 at the temples, so the head reads taller, not wider. The skill's monster hair, a cap 0.09 off the head and 0.13 over it, read as a helmet.
- **A cap and locks.** A smooth cap over the crown (`cap`), and locks rooted in it that hide its edge. A lock (`lock`) is a flat blade, a flattened diamond about a quarter as thick as wide, broad, ending in a sharp point; a flowing lock keeps its width until near the tip. Never a round tube with a blunt end: identical rounded tubes read as sausages or a comb, and narrow locks as noodles.
- **Locks overlap like shingles** (`layer`): each wider than its spacing, alternate ones a little further out, an outer layer over the roots of the one under it, no scalp between them.
- **Lengths vary.** The hem zigzags: 5 to 12 points across the back, 0.15 to 0.3 deep. Bangs (`bangs`) are 2 to 5 broad locks flowing from the crown, usually swept away from a part, their tips 0.3 to 0.6 apart in height with gaps that reach well up, often one lock longer; the face decal's eyes stay clear. A straight-cut fringe is a design choice.
- **Covered:** the crown, back and upper sides, and the nape unless the style is a crop or an updo; the ears may show.
- **Spiky styles** (`spike`): broad leaf blades about 0.7 long and 0.4 wide at the root, in offset rows from the top of the dome to the nape, sweeping up and back and overlapping like artichoke leaves; never straight out (a sea urchin) or sideways (wings).
- **Budget:** one mesh of 1,000 to 4,800 triangles (2,250 typical).
- **Check at the clay stage:** `kit.hair_check(L['head'], hair_pieces)` must return `{}`; `leave=` names what the design leaves bare or straight (`'nape'`, `'back'`, `'fringe'`). It measures volume and coverage, not shape, so also render the head close up from the front, side, back and three-quarter view beside the reference (noodle locks and a sea urchin of spikes both passed it).

A catalog or Toolbox hair whose style fits beats modeling one ([assets.md](assets.md)).

## Gear: weapons and shields

A weapon or shield is **always its own model**, never part of a skin: it swaps freely, spends its own map on a small object, and animates. One mesh serves R6 and R15.

- **Model it around its own origin,** in its own Blender scene, with the gear's name as the part: `P.put('Halberd', 'Gold', ...)`, then `kit.sharpen`, `merge`, `unwrap` and `paint` as for a skin, and `rr.export_pieces`. In a held weapon the origin is the middle of the handle, on its axis, where the hand closes; its length runs forward (-Y in Blender, the way the rig faces), thin across X. In a shield the origin is the centre of its face.
- **Held at the base of the arm, perpendicular to it,** the way a Roblox tool sits: the shaft runs forward through the fist, and a blade hangs below it. Size it to the ground: a 4.8-stud axe with 1.9 studs under the grip clears the floor at rest.
- **Built to the fist.** A block hand is about a stud deep and the handle passes through it, so only the handle enters the fist: at most 0.13 studs from its axis, for 0.62 studs ahead of and behind the grip (half the hand and a glove). The guard, blade and pommel start at least 0.67 studs from the grip, and the handle runs past that at the back, so a one-handed handle is at least 1.35 studs long. A knuckle bow or ring under the hand is fine. At the clay stage `kit.grip_fit(pieces)` must return `{}`; for a glove thicker than 0.1, pass `fist=kit.fist(arm, skin_pieces)`. A sword's guard and blade began 0.3 studs ahead of the grip and cut into the hand, and its handle ran along the outside of the fist.
- **On a Motor6D,** so animations can move it: `RigSkin.equip(rig, gear, { side = "Right", name = "Halberd" })`, called with the asset as inserted, before it moves. The joint runs from the hand (`Right Arm` on R6) to the gear, with the handle's axis 0.16 studs above the hand's end, inside the fist (the grip attachment sits on the end face; `seat` changes it). The gear's name is what a clip keys. A plain weld cannot be animated. An AnimationConstraint also works.
- **Worn gear,** such as a shield on the forearm or a sheath on the back: `{ part = "LeftLowerArm", at = cframe, name = "ShieldLeft" }`, with `at` in the skin's file space (ground at 0).
- **Place worn gear by measurement, not by eye.** `kit.clear_of(place, ob, armor, pad=.06)` finds the first spot where `kit.clips` is false. Rigid gear cutting into armor is easy to miss from the front (a gauntlet showing through a shield's face).
- It stays out of the hitbox: massless, no collision, in a `Gear` folder under the rig. Dying breaks its Motor6D, so it falls, as a dropped weapon should.

**In a game:** keep the skin in ServerStorage, and dress each character on the server: clone the skin, then `apply` or `bind`. For a player, do it after `Player.CharacterAppearanceLoaded`, so `hideAccessories` finds the hats and the colors are not overwritten by the avatar's own (applying a HumanoidDescription again resets them).
- **Mid-animation is fine.** RigSkin measures the rig's rest pose from its joints, not where the parts are posed.
- **Each piece is held by a RigidConstraint named `SkinWeld`.** A Humanoid's death (`BreakJointsOnDeath`, on by default) breaks every Weld and WeldConstraint in the character, which drops welded pieces through the floor. A RigidConstraint keeps each piece on its limb as the body falls apart.

## Check every character model before use

1. **Audit:** `return select(2, RigAudit.audit(model))` in Edit mode must report 0 errors ([scripts/RigAudit.luau](../scripts/RigAudit.luau)).
   - The rules are `parts`, `joint`, `root`, `rig`, `anchored`, `unwelded`, `unseated`, `unmatched`, `layered`, `touch`, `default-face` and `script`, plus, with no Humanoid, `standing` (an unanchored root with no AlignPosition), `clothing` (classic Shirt or Pants) and `untinted` (a textured body part with no SurfaceAppearance).
   - `seat` and `clean` fix the generator's side effects, and `controller` fixes `untinted`. A `parts`, `joint` or `layered` error needs a rebuild.
2. **A skinned rig:** `return select(2, RigSkin.audit(rig))` must also report 0 errors.
   - The rules are `unwelded`, `unseated`, `astray` (a piece clear of its part, or a Bone outside it), `anchored`, `collision`, `mass`, `unbound`, `bare` (a part hidden with no skin over it), `hidden` (a warning for every hidden body part: fine only when the design replaces it), `stale` (weld attachments left by deleted pieces: dress again), `single-sided` (a MeshPart without `DoubleSided`) and `gear` (gear with no Motor6D to the rig). A held weapon is measured against the hand and its skin: `seat`, `fist`, `handle` and `facing` (Gear, above), `floor` (under the ground at rest) and `unread` (a mesh the place may not read; look at the hand from below instead).
   - Play-test one walk: the skin must stay on. A file holding `--@use RigSkin` and `return RigSkin.playtest({ workspace.MyRig })`, run with `python scripts/studio_mcp.py play FILE`, starts Play, walks the rig on the server, reports how far the limbs moved and the skin strayed, and stops Play.
3. **Look** at it front and side: nothing floats, it has a face, and the clothes sit on the body. Then look mid-walk from a three-quarter view, since a front or side walk sheet misses a bare inner side, and at a held weapon's hand from below.
