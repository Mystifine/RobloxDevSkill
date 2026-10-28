# Character models (R15 and R6)

For NPCs, enemies, vendors, collectibles and any character template. A character that could read as female also follows [characters.md](characters.md); animating one is [animation.md](animation.md).

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
4. **Remove the handles' TouchInterests** unless the game listens for Touched on accessories.
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

**Custom bodies** that are not built from catalog parts:
- Model on an R15 skeleton ([animation.md](animation.md)) and import with the 3D Importer as an R15 rig, so the 15 parts carry R15 names and rig attachments.
- Check with `BuildRigFromAttachments` and an AnimationInspector audit, which must show no `unmatched`.

## R6

- **Parts:** six plus the root: Head (2×1×1), Torso (2×2×1), Left/Right Arm and Left/Right Leg (1×2×1), and HumanoidRootPart (2×2×1).
- **Joints:** Motor6Ds: RootJoint in the root (to the Torso), and Neck, Left/Right Shoulder and Left/Right Hip in the Torso.
- **What it lacks:** rig attachments, layered clothing and scale values. HipHeight is 0, because the legs carry the height.
- **Accessories and custom pieces are welded onto the part they ride on and positioned by hand.** Either an AccessoryWeld through the classic points, or a Weld or WeldConstraint for a custom mesh. The points:
  - Head: Hair, Hat, FaceFront, FaceCenter;
  - Torso: Neck, BodyFront, BodyBack, collars, waist points;
  - arms: Shoulder and Grip; legs: Foot.
- **A generated R6 makes the Head its PrimaryPart;** set it to the root (`clean`).

## Check every character model before use

1. **Audit:** `return select(2, RigAudit.audit(model))` in Edit mode must report 0 errors ([scripts/RigAudit.luau](../scripts/RigAudit.luau)).
   - The rules are `parts`, `joint`, `root`, `rig`, `anchored`, `unwelded`, `unseated`, `unmatched`, `layered`, `touch`, `default-face` and `script`.
   - `seat` and `clean` fix the generator's side effects. A `parts`, `joint` or `layered` error needs a rebuild.
2. **Look** at it front and side: nothing floats, it has a face, and the clothes sit on the body.
