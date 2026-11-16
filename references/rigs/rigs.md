# Character models, creatures and articulated assets

For NPCs, enemies, vendors, creatures, bosses and character templates; also resolve joints for articulated props here. Character art follows [characters.md](../safety/characters.md); resolve appearance through [visual-style.md](../art/visual-style.md). Rigging is a functional decision, independent of style or texture maps.

## Resolve movement before modeling

- **Gameplay actors:** characters, creatures, mobs and bosses intended to act in gameplay include a functional, animation-ready rig by default. In a game-asset request, treat a creature or enemy as an actor unless the request establishes a statue, display model, static prop or modeling-only stage. State this assumption briefly and proceed.
- **Static or whole-object motion:** scenery, statues, display collectibles, projectiles and props moving only as a whole need no skeletal rig. A hinged door or mechanical turret may need pivots/joints without a skinned skeleton. Choose from the actual motion requirements, not the noun or art style.
- **Compatible Roblox characters:** use a standard R6 or R15 rig, built one of the two ways below, when anatomy and animation compatibility fit. Preserve a suitable existing rig. Do not require a standard rig for extra limbs, unusual proportions or organic deformation that it cannot support.
- **Custom anatomy:** follow [custom-creatures.md](custom-creatures.md), plus [modeling.md](../art/modeling.md). Plan skeleton, pivots, pose range, rigid pieces and deforming topology before final detailing and bakes.
- **Scope:** a working rig does not imply a finished animation set, combat system, navigation or AI. For a modeling request, include only the diagnostic poses/motion needed to prove the rig; deliver production clips or gameplay integration when requested. An explicitly modeling-only stage can remain unrigged; report that stage accurately.

## Standard R6/R15 characters: two builds

The remaining sections describe standard rigs, not arbitrary creature skeletons ([custom-creatures.md](custom-creatures.md)). A standard character is built one of two ways, and its Humanoid decides which: settle that first, and say which build you took.

1. **Does it keep its Humanoid?** The request and the project answer first: their words, the project's existing characters and its docs. Otherwise a player's character and anything on the keep list ([Without a Humanoid](#without-a-humanoid)) keep it, and a rig that only animates does not *(default)*: a Humanoid is costly.
2. **With a Humanoid, the look comes from the Marketplace catalog** *(default)*: body parts, classic Shirt and Pants, layered clothing, hair and accessories in a HumanoidDescription, plus a custom MeshPart only for a detail no item gives ([catalog.md](catalog.md)). Model the look instead, as in 3, only when the request, the project's requirements or the design's scope call for custom art.
3. **Without a Humanoid, you model the look** *(default)*. Classic clothing's textures show only with a Humanoid, so making the character look right is yours: a **skin** on the target R6 or R15 rig ([skins.md](skins.md)), even when catalog clothing comes close to the reference, and its gear ([gear.md](gear.md)). Hair is the exception: found before it is modeled ([hair.md](hair.md)).
   - **Blender unavailable** ([find_blender.py](../../scripts/find_blender.py) exits 1): build from audited Toolbox assets instead ([assets.md](../safety/assets.md), Safe intake): meshes dressed on as skin pieces (`RigSkin.apply`, `map` for their names), gear through `equip`. Say which parts came from the Toolbox.

## R15: generate it, never assemble it by hand

Describe the rig as a HumanoidDescription and let Roblox build it (Edit mode or server): the whole look on a catalog build ([catalog.md](catalog.md)), the base alone under a skin (hair, colors, scales; the skin is the look):

```lua
local desc = Instance.new("HumanoidDescription")
desc:SetAccessories({
	{ AssetId = hairId, AccessoryType = Enum.AccessoryType.Hair }, -- the asset's own type: many catalog hairs are Face
	{ AssetId = jacketId, AccessoryType = Enum.AccessoryType.Jacket, IsLayered = true, Order = 3 },
}, true)
desc.HeadColor = skin -- and TorsoColor, LeftArmColor, RightArmColor, LeftLegColor, RightLegColor
local model = Players:CreateHumanoidModelFromDescription(desc, Enum.HumanoidRigType.R15)
```

- **What a description can set:** body part ids (`Head`, `Torso`, ...), scales (`HeightScale`, `WidthScale`, `DepthScale`, `HeadScale`, `BodyTypeScale`, `ProportionScale`), classic `Shirt`/`Pants`, and per-accessory `Position`, `Rotation`, `Scale` and `Puffiness`.
- **Clothing follows the build.** With a Humanoid: [catalog.md](catalog.md). Without one, catalog clothing only when the request asks for it, and layered (jacket, shirt, pants, with `IsLayered` and an `Order`, higher worn outside), which reads better on 3D bodies and still wraps there; never classic 2D Shirt/Pants, which show only with a Humanoid.
- **Keep each look as data** (ids, colors, scales, adjustments), so the whole cast can be rebuilt in another place.
- **Give each accessory its asset's own type.** The generator silently drops an entry whose `AccessoryType` differs from the asset's, with no error. Read the type first (`MarketplaceService:GetProductInfo(id).AssetTypeId`: 8 Hat, 41 Hair, 42 Face, 43 Neck, 44 Shoulder, 45 Front, 46 Back, 47 Waist), then count the Accessories on the built rig.
  - An item that looks like hair can be another type: four black messy hairs found by keyword among all accessories were all type 42 (Face); declared as `Hair`, each left the rig bald.

**Then fix what the generator leaves** (`RigAudit.seat` and `RigAudit.clean` do 1-4):
1. **Seat every accessory.** Set each Handle's CFrame to where its joint holds it. The generator leaves handles where the catalog asset sat (seen 13 to 2,800 studs away), and only physics pulls them in. Anchored models, viewports and previews then show floating hair and clothes.
2. **Remove the generated scripts** (Animate, Health) when the project animates characters itself.
3. **Remove the default face under a face accessory:** the Head's Decal and the head MeshPart's TextureID (the default head texture is a face, which shows through as two dots). `clean` handles Face accessories; a hair or hat with a face built in needs the same by hand.
4. **Remove the handles' TouchInterests** unless the game listens for Touched on accessories. Catalog accessories arrive with one saved in, and it stays until removed.
5. **Finish the template:** name it, put metadata in attributes, keep the HumanoidRootPart as PrimaryPart, and store it in ReplicatedStorage only when clients show it (ServerStorage otherwise). A model with a PrimaryPart pivots by `PrimaryPart.PivotOffset`: setting `Model.WorldPivot` there was ignored (`GetPivot` unchanged; a monster stood facing backwards), and a template whose `WorldPivot` read back right cloned 180 degrees off.
6. **On a build without a Humanoid, swap it:** `RigAudit.controller(model)`, last, once accessories and the skin are on ([Without a Humanoid](#without-a-humanoid)). A catalog build keeps it.

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
- **Accessory:** a Handle holding one Attachment named like a body point, and a joint from the Handle to that body part that brings the two together.
  - The joint is a Weld named AccessoryWeld on R6, and a RigidConstraint named AccessoryRigidConstraint on R15.
  - `Humanoid:AddAccessory` makes it 12 to 18 frames after the call, in Workspace or out of it. Wait for it before `seat` or an audit; building one yourself in the meantime gives the handle two joints.
  - Layered clothing adds a WrapLayer on the Handle, which wraps the WrapTarget cage inside each body part.
- **Humanoid:** an Animator, the HumanoidDescription (the applied look), six scale NumberValues with AutomaticScalingEnabled, and HipHeight (2.19 at default scale; the floor sits at the root's bottom minus HipHeight).
- **Scaler records:** OriginalSize and OriginalPosition (Vector3Values on parts and attachments) and AvatarPartScaleType (a StringValue on handles). Resize through the description's scales, never by resizing parts.
- **Looks:** BodyColors (skin per part) and FaceControls (dynamic heads).

**Custom bodies** (the art is the 15 parts themselves) are the exception: use one only when the shape cannot fit a standard rig ([skins.md](skins.md)).
- Model on an R15 skeleton ([animation.md](../animation/animation.md)) and import with the 3D Importer as an R15 rig, so the 15 parts carry R15 names and rig attachments.
- Check with `BuildRigFromAttachments` and an AnimationInspector audit, which must show no `unmatched`.

## R6

- **Parts:** six plus the root: Head (2×1×1), Torso (2×2×1), Left/Right Arm and Left/Right Leg (1×2×1), and HumanoidRootPart (2×2×1).
- **Joints:** Motor6Ds: RootJoint in the root (to the Torso), and Neck, Left/Right Shoulder and Left/Right Hip in the Torso.
- **What it lacks:** rig attachments, layered clothing and scale values. HipHeight is 0, because the legs carry the height.
- **Accessories are welded onto the part they ride on,** an AccessoryWeld through the classic points. Custom art is a skin ([skins.md](skins.md)), not pieces welded and positioned by hand. The points:
  - Head: Hair, Hat, FaceFront, FaceCenter;
  - Torso: Neck, BodyFront, BodyBack, collars, waist points;
  - arms: Shoulder and Grip; legs: Foot.
- **A generated R6 makes the Head its PrimaryPart;** set it to the root (`clean`).
- **A recognisable R6 that keeps its Humanoid** is built from catalog parts, a classic Shirt and Pants under rigid accessories: [catalog.md](catalog.md#r6-the-common-format).

## Without a Humanoid

A Humanoid is costly; a rig that only animates plays the same clips through an AnimationController *(default)*, and its look is modeled. Build it with the Humanoid as above (the generator, `AddAccessory` and the scales need one), dress it, then in Studio `RigAudit.controller(model)` (`{ Anchored = false }` for a root held by movers) and audit (Check, below).

- **`controller`** moves the Animator to an AnimationController, anchors the root, removes the Animate and Health scripts, and records `RootHeight`: studs from the floor to the root's centre where the Humanoid stood it (3.19 on a blank generated R15, 3 on R6). It gives each textured body part an Overlay SurfaceAppearance: without a Humanoid a dynamic head showed its texture untinted, white whatever its Color. Game scripts cannot set that map, so convert in Studio.
- **Unchanged** (generated R6 and R15 in Play): parts, joints, attachments, cages, accessories, layered clothing (bending with the limbs), skins, gear, and every R6 or R15 clip, replicated to clients, with AnimationInspector findings equal to the Humanoid rig's.
- **Place the root at `RootHeight`:** unanchored and unheld it sank about 2 studs, legs through the floor (only the root, head and torso collide). Move an anchored root by CFrame, or hold an unanchored one with AlignPosition and AlignOrientation. Walking NPCs: [gameplay.md](../code/gameplay.md).
- **BodyColors no longer recolors the parts:** set their colors (`RigSkin.color` sets both).
- **Keep the Humanoid** (skip `controller`) only when the request or project asks for one or for a look built from catalog items, or for something that needs one: a player's character; `MoveTo`, walking physics, jumping, climbing, a Seat or a Tool (gear on a Motor6D works without); `Health`, `Died`, `BreakJointsOnDeath` or the name and health display; or `AddAccessory`, `ApplyDescription` or automatic scaling after the build. Its look then comes from the catalog ([catalog.md](catalog.md)). Without it classic Shirt and Pants stop showing, while layered clothing and skins still show: dress that rig with a skin.

## Check every standard R6/R15 model before use

These audits target standard Roblox rigs/skins. Custom creatures use the motion, weight and import checks in [custom-creatures.md](custom-creatures.md).

1. **Audit:** `return select(2, RigAudit.audit(model))` in Edit mode must report 0 errors ([scripts/RigAudit.luau](../../scripts/RigAudit.luau)).
   - The rules are `parts`, `joint`, `root`, `rig`, `anchored`, `unwelded`, `unseated`, `unmatched`, `layered`, `touch`, `default-face` and `script`, plus, with no Humanoid, `standing` (an unanchored root with no AlignPosition), `clothing` (classic Shirt or Pants) and `untinted` (a textured body part with no SurfaceAppearance).
   - `seat` and `clean` fix the generator's side effects, and `controller` fixes `untinted`. A `parts`, `joint` or `layered` error needs a rebuild.
2. **A skinned rig:** `return select(2, RigSkin.audit(rig))` must also report 0 errors.
   - The rules are `unwelded`, `unseated`, `astray` (a piece clear of its part, or a Bone outside it), `anchored`, `collision`, `mass`, `unbound`, `bare` (a part hidden with no skin over it), `hidden` (a warning for every hidden body part: fine only when the design replaces it), `stale` (weld attachments left by deleted pieces: dress again), `single-sided` (a MeshPart without `DoubleSided`) and `gear` (gear with no Motor6D to the rig). A held weapon is measured against the hand and its skin: `seat`, `fist`, `handle` and `facing` ([gear.md](gear.md)), `floor` (under the ground at rest), `budget` (a warning: off a weapon's triangle band) and `unread` (a mesh the place may not read; look at the hand from below instead).
   - Play-test one walk: the skin must stay on. A file holding `--@use RigSkin` and `return RigSkin.playtest({ workspace.MyRig })`, run with `python scripts/studio_mcp.py play FILE`, starts Play, walks the rig on the server, reports how far the limbs moved and the skin strayed, and stops Play.
3. **Look** at it front and side: nothing floats, it has a face, and the clothes sit on the body. Then look mid-walk from a three-quarter view, since a front or side walk sheet misses a bare inner side, and at a held weapon's hand from below.
