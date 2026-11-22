# Catalog characters: the look from Marketplace items

The default look for a standard R6 or R15 character that keeps its Humanoid ([rigs.md](rigs.md) settles that first): its body, clothes, hair and accessories are avatar items from the Marketplace catalog, worn through a HumanoidDescription. Classic Shirt and Pants show only with a Humanoid, so a character without one is modeled instead ([skins.md](skins.md)).

- **Catalog first** *(default)*: build the whole look from items, and model a piece only for a detail no item gives ([below](#a-detail-no-item-gives)).
- **Model the look instead** when the request, the project's requirements or the design's scope call for custom art: a skin dresses a Humanoid rig too ([skins.md](skins.md)).
- **The outfit is your choice.** The items are existing assets and trusted, but keep the character inside [characters.md](../safety/characters.md): every render of it is a new upload.
- **Matching a named character from catalog items is the user's call:** a project's own rule kept forms to an archetype, never a 1:1 copy of a named character, and its owner overrode it, reasoning that Marketplace items have already passed Roblox's moderation and that assembling them is common practice. Say the takedown risk once (a rights holder can still report the experience), then build it; [characters.md](../safety/characters.md) cover rules still hold, and 3 of 19 such characters needed their revealing source outfits covered.

## Find the items

Search in Studio by exact type (Studio MCP `search_asset` covers the Creator Store only):

```lua
local params = CatalogSearchParams.new()
params.SearchKeyword = "knight"
params.AssetTypes = { Enum.AvatarAssetType.Shirt, Enum.AvatarAssetType.Pants } -- or params.BundleTypes = { Enum.BundleType.BodyParts }
local page = game:GetService("AvatarEditorService"):SearchCatalog(params):GetCurrentPage() -- 30 rows: Id, Name, AssetType, CreatorName, Price
```

- **Types** (`Enum.AvatarAssetType`):
  - classic clothing: `Shirt`, `Pants`, `TShirt`;
  - rigid accessories: `Hat`, `HairAccessory`, `FaceAccessory`, `NeckAccessory`, `ShoulderAccessory`, `FrontAccessory`, `BackAccessory`, `WaistAccessory`;
  - layered clothing: `TShirtAccessory`, `ShirtAccessory`, `PantsAccessory`, `JacketAccessory`, `SweaterAccessory`, `ShortsAccessory`, `DressSkirtAccessory`, `LeftShoeAccessory`, `RightShoeAccessory`;
  - body: `Head`, `DynamicHead`, `Face`, `Torso`, `LeftArm`, `RightArm`, `LeftLeg`, `RightLeg`;
  - bundles (`Enum.BundleType`): `BodyParts`, `Shoes`, `DynamicHead`.
- **Retry an empty page:** in Edit, about 1 in 6 of 140 rapid searches returned an empty page until retried a few seconds later, so loop with a backoff when filling many slots.
- **A form meant to be recognised at a glance starts from its face item:** 30 evolution forms built from catalog items read as generic blocky avatars in row captures; most wore the default dot face, so a lich, a dragon lord and a royal knight differed only by hats and colours at gameplay distance. A search for face accessories ("anime eyes", "demon eyes", "fang", "slit eyes") gave 62 candidates on one contact sheet; one face item per form, chosen by the archetype's eye colour, with the default face removed ([rigs.md](rigs.md), step 3), made each head read as an anime character at once. Then place the signature pieces where the front view shows them, checked in a front capture: wings behind a body were invisible from the front until scaled 1.4x through `AccessoryDescription.Scale`, and a weapon worn on the back showed past the shoulder.
- **Search by a known character's name as well as its look,** as for hair ([hair.md](hair.md), found first on either build). Name first, filtered: `SearchCatalog` with the character's name per asset-type group, keeping only items whose name contains it, gave 1,383 hits; most popular characters had 15-30 named hairs, faces, outfits and props each, enough for a full look, while six minor characters had 0-2 and needed look words ("white tailcoat", "pink spider legs"). Filter inside the Studio call and return tab-separated lines: unfiltered pages overflowed the MCP reply at about 100 KB (truncated JSON).
- **Look before choosing:** thumbnails from `thumbnails.roblox.com/v1/assets?assetIds=<ids>&size=420x420&format=Png` (bundles: `/v1/bundles/thumbnails?bundleIds=<ids>`). Take a shirt and pants from one creator's set, so they match. Then try every pick on the target rig: a well-liked hair rendered dark blotches on an R6 head and a shirt left the torso blank (skin), both seen only on the rig. Find hair by its exact type here: the web catalog's accessory search returned hair filed as Shoulder, Face, Back or Hat items, most with a drawn face, while `AssetTypes` = `HairAccessory` listed clean hair first.
- **Read picked ids from the search data, never off a contact sheet:** two of about 95 ids typed off 120 px thumbnail labels were wrong by one or two digits (115011066726714 for 115011606672714), and each silently dropped its accessory (the build reported 4 of 5 accessories, no error). A script matching every pick back to the search results by name found both before the final build; count accessories after it.
- **Without Studio:** `catalog.roblox.com/v1/search/items/details?Category=<c>&Subcategory=<s>&Keyword=<words>&Limit=30` (v2 ignores `Subcategory` for clothing and accessories), with `c/s`: classic T-shirts 3/55, shirts 3/56, pants 3/57; layered shirts 3/59, pants 3/60, jackets 3/61, shoes 3/64; hats 11/54, face 11/21, neck 11/22, shoulder 11/23, front 11/24, back 11/25, every accessory 11/19. It answers 429 after about ten calls in a row: space them 5 s apart.

## Put the look in a HumanoidDescription

[rigs.md](rigs.md) has the generator call, the accessory entries and the fixes after it. A catalog build adds:
- **Classic clothing:** `Shirt`, `Pants` and `GraphicTShirt` take the catalog item's own asset id (types 11, 12 and 2); the generator finds its template image. They show on R6 and R15 alike.
- **Layered clothing** (R15 only): accessory entries with `IsLayered` and an `Order`, higher worn outside. It sits over classic clothing, which is painted on the body.
- **Body:** part ids in `Head`, `Torso`, `LeftArm`, `RightArm`, `LeftLeg` and `RightLeg`, the skin in the six colors, the size in the scales.
  - **A hooded or half-masked look colours the head near-black,** alone, and is checked close up: a pale forehead inside a hood over a lower-face mask read as a hole showing the sky, where a near-black head made the hood a void around its glowing eyes.
  - **A body bundle:** `AssetService:GetBundleDetailsAsync(bundleId).Items` lists its parts and two `UserOutfit`s. `Players:GetHumanoidDescriptionFromOutfitId` on the outfit named like the bundle gives the whole body with its scales; the one ending "- Face" holds only the head.
  - **`Face`** (a classic face) shows on R6 only: a generated R15 has a dynamic head, which ignored it. Its face comes from the head or a face accessory.
- **An avatar's look:** `Players:GetHumanoidDescriptionFromUserId(userId)`.
- **Build** a template with `Players:CreateHumanoidModelFromDescription` (about half a second), then `RigAudit.seat` and `clean`, and skip `controller`. On a character already in a running game: `Humanoid:ApplyDescription(description)` on the server.
- **Count what arrived:** the Shirt and Pants instances, and one Accessory per entry. A wrong `AccessoryType` drops its entry without an error ([rigs.md](rigs.md)). Map the search's `AssetType` to the `AccessoryType` mechanically: a white shawl found under a jacket search was a `ShirtAccessory`; written as `Jacket` it dropped silently, written as `Shirt` it loaded. Classic "shirtless" shirts differ too: one painted its own pale skin over a tan body (torso and arms visibly mismatched), another drew only muscle lines over transparency and matched any skin colour, so prefer line-only templates.
- **Type-check every id against its slot before calling a cast done:** an enemy's shirt slot held a pants item of the same theme and name style. Lint, specs and thumbnails passed; only the Play boot warned "Asset type does not match requested type". A `MarketplaceService:GetProductInfo` sweep in Edit of all 461 outfit ids, comparing each `AssetTypeId` with its slot (Shirt 11, Pants 12, the accessory types), found that one, and rebuilding the look with the old id as a control reproduced the warning. A thumbnail or a name does not tell.

## A cast as data

*(default)* How a cast of catalog looks (evolution forms, enemies, NPCs) is kept and built, so it can be rebuilt in any place and adjusted by eye; a cast of 30 forms and their enemies ran this way from spawn to re-dress.

- **One compact row per look, data only:** `{ skin = "RRGGBB", headSkin = "RRGGBB"?, scale = { Height, Width, Depth, Head, BodyType, Proportion }, shirt?, pants?, face?, head?, acc = { { assetId, "AccessoryType", layered = order?, p = { x, y, z }?, r = { x, y, z }?, s = { x, y, z }?, puff = n? } } }`, plus what the game reads beside the look (whether to drop the default face, aura colours). The type is the asset's own ([above](#put-the-look-in-a-humanoiddescription)).
- **A builder and a capture that mirror each other:** `Description(look)` sets the six body colours from `skin` (the head from `headSkin`, for a hooded void face), the six scales (defaults `{ 1, 1, 1, 1, 0, 0 }`), `Shirt`, `Pants`, `Face` and `Head`, and the accessories through `HumanoidDescription:SetAccessories(list, true)`: a layered row becomes `IsLayered`, `Order` and `Puffiness` (default 1), a rigid row `Position`, `Rotation` and `Scale`; an unknown type warns and is skipped. `Capture(description)` reads a description back through `GetAccessories(true)`, rounding to 0.001 and leaving out every value at its default, so a rig nobody adjusted captures to exactly its source row.
- **The loop:**
  1. **Search** per look and slot (hair, horns or hat, face, back, waist, shoulder, shirt, pants, a layered jacket), results written to a file, not printed.
  2. **Write the rows.**
  3. **Build** one rig per look into a Studio folder from the rows (`Players:CreateHumanoidModelFromDescriptionAsync`), audited with `RigAudit` (0 errors).
  4. **Adjust by eye:** edit a rig's HumanoidDescription (accessory position, rotation and scale; layered order and puffiness; colours; scales) and apply it with `Humanoid:ApplyDescriptionAsync`; flags such as "drop the default face" go on the rig as attributes.
  5. **Capture:** a script reads every rig back into rows and rewrites the data module, with a dry run that prints the diff first.

  Keep the rigs in ServerStorage (never loaded in game) and drag the folder into Workspace to edit; the capture reads either.
- **In game:** spawn with `Player:LoadCharacterWithHumanoidDescriptionAsync(description)`. When the look changes on a living character, the server calls `Humanoid:ApplyDescriptionAsync(description:Clone())` inside `pcall`, records which look the character wears once it worked, and warns on failure. Clear the default face after every dress ([rigs.md](rigs.md), step 3).
- **Pre-warm the next look:** building a look once per server with `Players:CreateHumanoidModelFromDescriptionAsync` fetches its items into the server's cache, so a later `ApplyDescriptionAsync` (a reveal in a cutscene) swaps the body at once instead of fetching then. Keep the built model inert (scripts removed, parts anchored) in a ReplicatedStorage folder so clients load its meshes and textures ahead too, with its descendant count in an attribute: a model reaches a client a piece at a time, and a client that copies it waits for all of them. Warm the player's current look and the next one they will reach.

## A detail no item gives

Model only that piece ([modeling.md](../art/modeling.md), then [the upload gate](../safety/uploading.md)) and put it on the way the catalog's own items go on:
- **An Accessory:** an `Accessory` holding a `Handle` (the MeshPart, `CanCollide` off, `Massless`) with one Attachment named like a body point ([rigs.md](rigs.md) lists them). `Humanoid:AddAccessory(accessory)` joins it there: an `AccessoryRigidConstraint` on R15 (0.000 studs from the point), an `AccessoryWeld` on R6. Place the piece by moving that Attachment inside the Handle, then `RigAudit.seat`.
  - It stays through `ApplyDescription` and goes with `ApplyDescriptionReset`: add it again after one.
- **Held or jointed gear** (a weapon, a shield): [gear.md](gear.md).
- **A piece shaped to a body part** (a pauldron, a mask): a skin piece on that part ([skins.md](skins.md)), beside the catalog clothes.

## R6: the common format

A recognisable R6 from catalog parts (studied on 98 built characters): `Players:CreateHumanoidModelFromDescription(description, Enum.HumanoidRigType.R6)` gives the plain rig (six Parts, a SpecialMesh head, BodyColors for the skin).
- **The outfit** is a classic Shirt and Pants (2D templates, 585 x 559, wrapped on the blocks). Layered clothing does not apply to R6, so a coat or armour is drawn into the template or made an accessory.
- **Everything with volume** is a rigid Accessory (a Part Handle with a SpecialMesh) on the R6 points: hair and hats (`HairAttachment`, `HatAttachment`), the face (`FaceFrontAttachment`, `FaceCenterAttachment`), back and waist items (weapons, capes, tails).
- **The face** is usually an accessory too: a shell over the head carrying the drawn face, sometimes with 3D parts (a nose) in the same mesh.
  - **No drawn faces:** clear the face accessory's texture and color its handle with the head's BodyColors, keeping its mesh; removing the accessory would remove its 3D parts too. Real 3D face items (blindfolds, masks, moustaches), found by looking at all the heads on one grid, stay.
- **Judge a template from a close capture of the torso front:** each torso face gets 128 x 128 pixels over 2 studs, so a template drawn small and scaled up shows blocks at gameplay zoom where a well-made one on the same rig reads clean. No rig or engine setting changes that, and a script cannot read another creator's template (`CreateEditableImageAsync` refuses without permission; assetdelivery answers 401 without a login, Open Cloud 403), but `thumbnails.roblox.com/v1/assets?assetIds=<template image id>&size=700x700&format=Png` returns the template itself to look at (585 x 559 scaled to 700 x 669). A catalog item's template image id comes from building it on a throwaway R6 (`Players:CreateHumanoidModelFromDescription`, then `Shirt.ShirtTemplate`).
  - **Judge resolution by eye** on contact sheets of the torso and leg fronts at 2x nearest-neighbour, then 4x for suspects, and compare candidates the same way before choosing: a sharpness score (a round-trip energy ratio: the mean squared error after a 2x downscale and upscale over the mean squared neighbour difference) scattered 183 templates between 0.30 and 0.6, the scaled-up and blurred ones among clean hard-edged art, while the sheets found the five at a glance. Hard-edged art drawn at the template's own size held up at 4x.

**Check** as every standard model ([rigs.md](rigs.md), Check): `RigAudit.audit` with the Humanoid kept, then a look from the front and side.
