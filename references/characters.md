# Characters (all-ages safety)

Applies to every character you generate, model, edit or upload that could read as female, humanoid or creature, in 2D (icons, portraits, thumbnails, and renders of any model, which are new uploads) and 3D (models, textures). Characters already on Roblox (catalog avatars, approved Toolbox models) are trusted like any existing asset ([no-gore.md](no-gore.md)), and in game they still sit within the experience's label. Moderation can deactivate the owner's account, not just remove the asset. This filter is the skill's default bar, set after a moderation action and stricter than Roblox's Community Standards. The project's own rules or the user's instructions replace it ([SKILL.md](../SKILL.md)); when they ask for something looser than Roblox's own standards, say once that moderation will act on it. Female designs are fine under it:

1. **Flat chest** in silhouette, outlines, contour lines, shading and highlights: the chest piece lies flat, with at most a slight curve, and has no bust bump, cleavage dip or shading that models breasts. Straight torso: its sides run straight and nearly parallel from the armpits to the hips (widen the waist, never the chest), with no pinched waist or hourglass.
2. **Covered, no cleavage.** Opaque armor or clothing covers the whole chest and at least 70% of the torso (by area of the front, from the shoulders to the hips, or to where a tail, stem or flower begins). Its top edge, or the point of a V-neck, sits on the upper chest above the bust, so no cleavage line or inner curve shows. The neck, shoulders and a strip of upper chest above the bust may stay bare, with no rounded forms in it.
3. **The chest piece cannot pass for skin:** a clearly different color (metal, bark, cloth) or a much darker or lighter value, with visible texture and edges. Never the skin's own color, and on human skin never a flesh tone. Other pieces may echo the body's palette when they read as material (scales, plates or leaves with edges or trim).
4. **Never:** bra or bikini tops (two cups), bare midriff, paired round shapes below the collarbone (a small bow or knot at the collar is fine; on the torso itself a bow is flat or angular), seductive poses or expressions (half-lidded eyes, pout, tongue out).

**See-through bodies** (slime, ghost, glass, water) on a character that reads as female read as nudity to classifiers even when fully covered: seen 2026-10-28, when an image tool blocked a covered slime-girl prompt as sexual. Give such a body an opaque core or a dense tint, or present the character as a creature or mascot, and never describe a see-through body together with a female figure in a prompt.

**No blood, wounds or gore on any character you generate or upload** ([no-gore.md](no-gore.md)): hurt shows as dust, torn clothes, a clean bandage or swirl eyes.

## Design the cover in character

**Change as little as the rules need**, so the character stays itself:
- **Build every piece from the character's own materials and palette,** shaped like armor or clothing it would wear: its jewelry metal as a breastplate, its scales, bark, leaves or petals as panels. It should look designed, not added.
- **Keep its outfit and the bare areas the rules allow** (neck, shoulders, arms, a strip of upper chest), and reshape only what fails:
  - two cups become one flat band or plate in the same material;
  - a bare midriff gets a fitted panel down to the hips, in the body's scales, bark or cloth in a darker shade, edged with trim;
  - a bust drawn on a creature body becomes a flat plate of its own material.
- **Prefer a chest plate plus a waist panel or belt** to one long dress, robe, cuirass or boxy tunic, and to colors foreign to the character. More cover than the rules need is not safer; it only changes who the character is.
- **Fix a pinched waist by straightening the sides,** not by lengthening the chest piece.

To fix existing art, make a precise edit of that image: change only the torso cover, and an expression that breaks rule 4. Keep the pose, identity, palette, line style and border; only the torso's silhouette may straighten. Generative edits drift, so when everything outside the torso must stay identical, composite the edited torso back into the original through a soft mask.

## 2D prompts

**Describe the outfit, never the body.** An image tool's input filter reacts to anatomy words even when they are negated, exactly as [no-gore.md](no-gore.md) says of blood: "no cleavage, no bust bump" beside a see-through body got a prompt blocked as sexual. Lead with the garment in positive terms and let the clothing give the torso its shape: "[Character] wears [its own material as armor, for example a single flat gold cuirass and a dark scale panel with gold trim] from the collarbone down to the [hips / tail / stem]: one smooth plane with straight, parallel sides." Keep out of the prompt: cleavage, bust, breast or breasts (say cuirass, plate, vest or tunic rather than "breastplate"), curvy, skin-tight, and see-through or transparent next to a body. Put avoid-terms only in a separate negative-prompt field when the tool has one. For an edit, add: "Change only the outfit [and the expression]; keep everything else, including the line style and border."

Generators often fail the first try (a "flat" plate drawn with two lobes, bare skin above the band, a pinched waist, a plate grown into a dress), so review each try. On a retry, name the failure in shape words and give the fix, for example: "the plate shows two lobes: make it one plane with straight top and bottom edges and a single flat sheen, starting at the collarbone".

## 3D

Model the chest flat: no bust geometry, and no bust shading in the normal or color maps. The chest piece is its own geometry or material. Renders of the model must pass the same rules.

## Review before any upload

View each image or render at full size and at 128 px. It fails if:
- the torso would read as nude or curvy with the body recolored to a human skin tone;
- the chest piece could pass for skin;
- a cleavage line, a bust bump or breast shading shows, or less than 70% of the torso is covered;
- blood, a wound or gore shows ([no-gore.md](no-gore.md));
- the cover looks pasted on (a foreign color, a bulky shape), or the outline differs from the rest of the set.

Fix the art first. Never upload to test moderation.
