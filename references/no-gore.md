# Blood and gore (uploads strict, existing assets trusted)

**Where the risk is.** Roblox's automated moderation screens everything new you submit: images, decals, textures, flipbooks, meshes and their maps, audio, video, saved models and packages, and the text that goes with them. It applies its own rules to uploads whatever the experience's label ([content maturity](https://create.roblox.com/docs/production/promotion/content-maturity), checked 2026-10-28), it can misfire (a red splash meant as paint or magic can be read as blood), and a rejection can strike the uploading account ([characters.md](characters.md)). What is already on Roblox has passed that screen: particles, textures and models used by their ids rarely get taken down, and using them uploads nothing.

| Zone | Rule |
|---|---|
| **Uploading** anything new | strict, with a margin for false positives |
| **Using** what is already on Roblox | trusted: use it by id, never re-upload it |
| **What players see** | within the experience's maturity label, stylized by default |

This is the skill's default bar, stricter than Roblox's for uploads. The project's own rules or the user's instructions replace it ([SKILL.md](../SKILL.md)); when they ask for something looser than Roblox's own rules, say once that moderation will act on it.

## Uploads: strict, with a margin

Never upload:
- blood in any color or style (realistic, cartoon or "unrealistic"), wounds, gore (severed parts, exposed flesh or organs, bone through flesh), corpses, blood stains on weapons, claws or mouths, or gore sounds (squelching, flesh tearing, bone snapping);
- anything a classifier could take for them, even when it is something else: a red, dark red or maroon liquid splat, drip, spray or pool (paint, juice, sauce, red slime), red smears on a figure or a weapon, dark, matte red droplets or spatter on transparency. Glow is not spatter: a bright red aura, haze or sparkle field around an energy effect reads as power and is fine;
- gore words in what you submit: name uploads plainly ("ImpactSparks_01", not "BloodSplat").

Keep the look, lose the risk:
- **Reuse before you upload:** the project's own assets and packs, the Toolbox and Creator Store, Roblox's own library. Every reuse is an upload you never make.
- **Upload VFX textures neutral and tint them in Roblox:** white or grey on transparency, colored by `ParticleEmitter.Color`, `Beam.Color`, `Trail.Color`, `ImageLabel.ImageColor3`, `Decal.Color3` or `Texture.Color3`. One upload then serves every color, and the file carries no red to misread. What players see must still fit the label and the maturity questionnaire: tinting is for reuse and false positives, never a way to slip past moderation what the label does not allow.
- **Let red read as an object:** an apple, a cape, a ruby blade, a flame with its glow; never a lone red blob on transparency.
- **Generated art:** lead the prompt with the look ("a burst of white and gold impact sparks with a small dust puff"). Keep blood and gore words out of it, even as "no blood", and put them in the negative prompt when the generator has one. Describe a name with blood in it instead of quoting it: "a huge glowing crimson moon in a dark red sky", not "Blood Moon". Generators add blood unasked (blades, claws, mouths, battle scenes, horror), so review every try, and on a retry name the exact failure and its fix: "red drips run down the sword: make the blade polished steel with a white glint".
- **Saving a model, package or plugin is an upload** under your account, even when everything inside already exists: screen what it shows.

Screen every file at full size and at 128 px (play a flipbook through) and fix what fails by recoloring to neutral, reshaping or cropping. Then send it through the upload gate in [assets.md](assets.md): one of a new kind first, wait for approval, never test moderation.

## Existing assets: trusted

- Use what is already on Roblox by its id (the project's approved uploads, VFX packs, Toolbox and Creator Store particles, textures and models) without auditing it against this page.
- Never download and re-upload one: that is a new upload under your account (and may breach its creator's rights). Recolor, resize and retime it through properties instead.
- Keep every id in the project's asset tables, so the rare one taken down later is a one-line swap.
- The project's own exclusions win (for example a rule never to play a pack's blood textures), and Toolbox code stays banned ([assets.md](assets.md)).

## What players see: within the label, stylized by default

The experience's label is the ceiling. Minimal allows occasional mild violence and light unrealistic blood; Mild, repeated mild violence and heavy unrealistic blood; Moderate, non-graphic realistic violence and light realistic blood; Restricted, heavy realistic blood, dismemberment, severed parts and organs. Extreme gore is never allowed. Only Minimal and Mild are open to Roblox Kids (ages 5-8), and Restricted only to age-verified adults, so design to the label the project declares (Minimal when unknown) and answer the maturity questionnaire for what players actually see, existing assets included.

Stylized effects are the default: they keep the label low, read on phones, and come from neutral textures that are safe to upload.

| Moment | Show |
|---|---|
| A hit lands | a white or gold flash on the impact frame, sharp sparks or stars, a shockwave ring, a dust puff for heavy hits; the target flashes white for about 0.1 s, squashes or is knocked back; damage numbers; a thud or whoosh |
| Elemental hits | the element on the target: embers and flame, ice shards and frost, lightning sparks, green poison bubbles and smoke, purple wisps, light motes |
| Slashes | a crescent of light or wind along the weapon's arc, sparks where it connects |
| Projectiles | impact sparks, dust or a puff, a ricochet glint |
| Low health, damage over time | a soft pulsing screen-edge glow, a heartbeat, a flashing health bar; each effect as an icon and a tinted aura (orange embers for burn, green bubbles for poison, purple wisps for drain) |
| Defeat, knockout, death | dizzy stars or a "KO" pop; the body falls, ragdolls or breaks into blocky pieces, then fades, dissolves into light or sparkles, or vanishes in a smoke puff; loot bursts out; respawn with a glow |
| Enemies and creatures | whole and stylized: zombies with green or grey skin and torn clothes; slime and jelly burst into blobs of their own color, robots into sparks, smoke and bolts |
| Vampires, life drain | fangs and capes; feeding or draining is a stream of glowing energy motes |
| Horror | darkness, sound, silhouettes, chases and timing; claw marks, scratches and glowing runes |
| Hurt characters in art | dust, soot, torn clothes, a plaster or a clean bandage, a sweat drop, swirl eyes |
| Sounds | thuds, whooshes, pops, cracks of stone or armor, cartoon boings |

The white flash: a `Highlight` (white fill fading out) or a quick tint of the target's parts. A client draws at most 31 Highlights at once, so in crowded fights reuse one per target or tint instead.

Always fine, so never strip it to play safe:
- action and death as game states: weapons, knockouts, eliminations, respawn, and the words kill, die, dead and defeat;
- Roblox's blocky break-apart on death (`Humanoid.BreakJointsOnDeath`), and robots, toys, statues or golems coming apart;
- slapstick: bumps with circling stars, soot, X or swirl eyes, plasters, tears, sweat drops;
- liquids that plainly are something else: water, mud, slime, paint, ink, potions, lava, poison dripping from a blade (uploaded neutral, tinted in game);
- red as a color or as energy: red weapons, teams, glows, flames, crystals, night skies;
- spooky staples, whole and clean: skeletons, skulls and crossbones, ghosts, mummies, cartoon zombies, vampires with fangs, werewolves;
- "blood" as an established term (Blood Moon, bloodline, blood magic), and healed scars or cartoon stitches as closed lines.

Removing more than the rules need is not safer; it only makes the game blander.

## Existing content

What a project already ships, and assets already on Roblox, are likely safe: leave them. Raise only what breaks Roblox's rules for the experience's label, with a proposed fix, and change it once the user agrees.
