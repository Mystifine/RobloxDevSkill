# Blood and gore (uploads strict, existing assets trusted)

**Where the risk is.** Roblox's automated moderation screens everything new you submit: images, decals, textures, flipbooks, meshes and their maps, audio, video, saved models and packages, and the text that goes with them. It applies its own rules to uploads whatever the experience's label ([content maturity](https://create.roblox.com/docs/production/promotion/content-maturity)), it can misfire (a red splash meant as paint or magic can be read as blood), and a rejection can strike the uploading account ([characters.md](characters.md)). What is already on Roblox has passed that screen: particles, textures and models used by their ids rarely get taken down, and using them uploads nothing.

| Zone | Rule |
|---|---|
| **Uploading** anything new | strict, with a margin for false positives |
| **Using** what is already on Roblox | trusted: use it by id, never re-upload it |
| **What players see** | within the experience's maturity label, stylized by default: [stylized-violence.md](stylized-violence.md) |

This is the skill's default bar, stricter than Roblox's for uploads. The project's own rules or the user's instructions replace it ([SKILL.md](../../SKILL.md)); when they ask for something looser than Roblox's own rules, say once that moderation will act on it.

## Uploads: strict, with a margin

Never upload:
- blood in any color or style (realistic, cartoon or "unrealistic"), wounds, gore (severed parts, exposed flesh or organs, bone through flesh), corpses, blood stains on weapons, claws or mouths, or gore sounds (squelching, flesh tearing, bone snapping);
- anything a classifier could take for them, even when it is something else: a red, dark red or maroon liquid splat, drip, spray or pool (paint, juice, sauce, red slime), red smears on a figure or a weapon, dark, matte red droplets or spatter on transparency. Glow is not spatter: a bright red aura, haze or sparkle field around an energy effect reads as power and is fine;
- gore words in what you submit: name uploads plainly ("ImpactSparks_01", not "BloodSplat").

Keep the look, lose the risk:
- **Reuse before you upload:** the project's own assets and packs, the Toolbox and Creator Store, Roblox's own library. Every reuse is an upload you never make.
- **Upload VFX textures neutral and tint them in Roblox:** white or grey on transparency, colored by `ParticleEmitter.Color`, `Beam.Color`, `Trail.Color`, `ImageLabel.ImageColor3`, `Decal.Color3` or `Texture.Color3`. One upload then serves every color, and the file carries no red to misread. What players see must still fit the label and the maturity questionnaire: tinting is for reuse and false positives, never a way to slip past moderation what the label does not allow.
- **Let red read as an object:** an apple, a cape, a ruby blade, a flame with its glow; never a lone red blob on transparency. Keep saturated red off the floor in effects *(default)*: a red shockwave disc on the floor read as a pool in a Play recording; tint floor marks another colour (violet, black) and keep red to an effect's edges.
- **Generated art:** lead the prompt with the look ("a burst of white and gold impact sparks with a small dust puff"). Keep blood and gore words out of it, even as "no blood", and put them in the negative prompt when the generator has one. Describe a name with blood in it instead of quoting it: "a huge glowing crimson moon in a dark red sky", not "Blood Moon". Generators add blood unasked (blades, claws, mouths, battle scenes, horror), so review every try, and on a retry name the exact failure and its fix: "red drips run down the sword: make the blade polished steel with a white glint".
- **Saving a model, package or plugin is an upload** under your account, even when everything inside already exists: screen what it shows.

Screen every file at full size and at 128 px (play a flipbook through) and fix what fails by recoloring to neutral, reshaping or cropping. Then send it through the upload gate in [uploading.md](uploading.md): one of a new kind first, wait for approval, never test moderation.
- **A mark that shares colors with lit shading goes back as an image edit:** three hue and value masks for smudges caught lit folds and outlines and made the art worse. A local recolor only works on flat color.

## Existing assets: trusted

- Use what is already on Roblox by its id (the project's approved uploads, VFX packs, Toolbox and Creator Store particles, textures and models) without auditing it against this page.
- Never download and re-upload one: that is a new upload under your account (and may breach its creator's rights). Recolor, resize and retime it through properties instead.
- Keep every id in the project's asset tables, so the rare one taken down later is a one-line swap.
- The project's own exclusions win (for example a rule never to play a pack's blood textures), and Toolbox code stays banned ([assets.md](assets.md)).

