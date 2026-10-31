# Characters (all-ages safety)

Applies to every character you generate, model, edit or upload that could read as female, humanoid or creature, in 2D (icons, portraits, thumbnails, and renders of any model, which are new uploads) and 3D (models, textures). Characters already on Roblox (catalog avatars, approved Toolbox models) are trusted like any existing asset ([no-gore.md](no-gore.md)), and in game they still sit within the experience's label. Moderation can deactivate the owner's account, not just remove the asset. This filter is the skill's default bar. Its chest rules follow Roblox's [Marketplace Policy](https://create.roblox.com/docs/marketplace/marketplace-policy) for avatar bodies, applied to every character you make; the rest stays stricter than Roblox's Community Standards, set after a moderation action. The project's own rules or the user's instructions replace it ([SKILL.md](../SKILL.md)); when they ask for something looser than Roblox's own standards, say once that moderation will act on it. Female designs are fine under it:

1. **A modest chest, fully covered.** The chest may follow a natural, modest curve under one continuous chest piece that covers it completely, as Roblox requires of avatar bodies: an opaque layer over the whole chest, in a color unlike the skin (flat, muscle-shaped pecs need none). Never exaggerated in size or made the focal point of the figure: soft shading of the form is fine, a strong highlight or deep shadow on it is not (Roblox bans "excessive highlighting or shadowing"). No cleavage line or dip, and no two separately shaped cups. A slight hourglass is fine: Roblox's rules have no waist limit, only size exaggerated until the chest, pelvis or buttocks become the focal point. What fails is a pinched waist that does that (as a guide, narrower than about 0.7 of the width of the cover across the hips, which should hang straight). A character that looks like a child stays flat, with chest and stomach covered.
2. **Covered, no cleavage.** Opaque armor or clothing covers the whole chest and at least 70% of the torso (by area of the front, from the shoulders to the hips, or to where a tail, stem or flower begins). Its top edge, or the point of a V-neck, sits on the upper chest above the bust, so no cleavage line or inner curve shows. The neck, shoulders and a strip of upper chest above the bust may stay bare, with no rounded forms in it.
3. **The chest piece cannot pass for skin:** a clearly different color (metal, bark, cloth) or a much darker or lighter value, with visible texture and edges. Never the skin's own color, and on human skin never a flesh tone. Other pieces may echo the body's palette when they read as material (scales, plates or leaves with edges or trim).
4. **Never:** bra or bikini tops (two cups), bare midriff, paired round shapes below the collarbone on the skin or set on the chest piece (two round gems, rosettes or shells; a small bow or knot at the collar is fine, and on the torso itself a bow is flat or angular), seductive poses or expressions (half-lidded eyes, pout, tongue out).

**See-through bodies** (slime, ghost, glass, water) on a character that reads as female read as nudity to classifiers even when fully covered: an image tool blocked a covered slime-girl prompt as sexual. Give such a body an opaque core or a dense tint, or present the character as a creature or mascot, and never describe a see-through body together with a female figure in a prompt.

**No blood, wounds or gore on any character you generate or upload** ([no-gore.md](no-gore.md)): hurt shows as dust, torn clothes, a clean bandage or swirl eyes.

## Design the cover in character

**Change as little as the rules need**, so the character stays itself:
- **Build every piece from the character's own materials and palette,** shaped like armor or clothing it would wear: its jewelry metal as a breastplate, its scales, bark, leaves or petals as panels. It should look designed, not added.
- **Keep its outfit and the bare areas the rules allow** (neck, shoulders, arms, a strip of upper chest), and reshape only what fails:
  - two cups become one continuous band or plate in the same material;
  - a bare midriff gets a fitted panel down to the hips, in the body's scales, bark or cloth in a darker shade, edged with trim;
  - a bust drawn bare on a creature body is covered by a plate of its own material, and reduced to a modest curve.
- **Break up the chest piece with a layer the character would wear** when its outline curves: a tabard or surcoat, a mantle, capelet or fin collar, a scarf, a broad gorget, pauldrons that reach onto the chest. It reads as design, and the chest stops being the focal point.
- **Prefer a chest plate plus a waist panel or belt** to one long dress, robe, cuirass or boxy tunic, and to colors foreign to the character. More cover than the rules need is not safer; it only changes who the character is.
- **Carry a layer past the hips** when the body's own outline shows below the belt: tassets, a tabard or coat hem, a fin or leaf skirt, or sash ends, hanging from the belt to mid-thigh.
  - The layer hangs straight down, no wider than the cover's sides above the belt. A flared skirt widens the hips and makes the waist look narrower.
  - The outline below the waist is then the garment's, not the hips'.
  - The knight's tabard and the ranger's vest hem passed. The siren's armor stopped at the hips, and below its waist panel her bare outline flared on both tries. Given a "slightly flared" skirt, the siren and a dryad both came back with flared skirts and waists at about 0.6 of the hem.
- **Fix a pinched waist by easing the sides into a natural waist** and carrying a layer past the hips, not by lengthening the chest piece.

To fix existing art, make a precise edit of that image: change only the torso cover, and an expression that breaks rule 4. Keep the pose, identity, palette, line style and border; only the torso's silhouette may change, toward modest. Generative edits drift, so when everything outside the torso must stay identical, composite the edited torso back into the original through a soft mask.

## 2D prompts

**Describe the outfit, never the body.** An image tool's input filter reacts to anatomy words even when they are negated, exactly as [no-gore.md](no-gore.md) says of blood: "no cleavage, no bust bump" beside a see-through body got a prompt blocked as sexual. Lead with the garment in positive terms and let the clothing give the torso its shape: "[Character] wears [its own material as armor, for example a sturdy, straight-cut matte gold cuirass with one broad, smooth front and a central ridge, and a dark scale panel with gold trim] from the collarbone down to the [hips / tail / stem], in one continuous piece whose sides run straight down from the armpits, with a wide belt at the waist." Keep out of the prompt: cleavage, bust, breast or breasts (say cuirass, plate, vest or tunic rather than "breastplate"), curvy, skin-tight, and see-through or transparent next to a body. Put avoid-terms only in a separate negative-prompt field when the tool has one. For an edit, add: "Change only the outfit [and the expression]; keep everything else, including the line style and border."

**Name the build and the layer from the first prompt.** In fantasy styles, generators draw "adult woman" curvier than these rules on every try (three test portraits, two tries each, under two wordings), and retries only soften it. Give the build in neutral words ("a sturdy, athletic build", "broad-shouldered", "practical adventurer proportions"), never words for the chest, waist or hips, and put the cover's layer (above) in the prompt. The waist resists longest (still pinched on two of three portraits after build words and layers fixed the chest): describe the cover's side outline ("its sides run straight down from the armpits to the hips"), put a wide sash, belt or waist panel at the waist itself, as broad as the chest piece above it, and hang a layer from it straight down to mid-thigh (tassets, a tabard or coat hem, a fin skirt), "falling straight, as wide as the armor above", so the outline below the belt is the garment's.

**Garment words shape the torso** (three test portraits under a looser wording):
- "Fitted", "form-fitting", "tight" and "corset" make the generator mold the cover around an hourglass: say straight-cut, sturdy, practical or layered.
- "Polished", "glossy" or "shiny" on the chest piece give it a separate highlight on each side, which models the chest even on one continuous plate: make the chest piece matte, satin or brushed (gloss elsewhere is fine). Scales and shell are drawn glossy even when called matte (a siren's scale armor came back with a highlight on each side): call them "dull, weathered, chalky matte", or cover them with a cloth or leather layer.
- A cloth layer over armor (a tabard, a sash, a short shoulder cape) softens the silhouette; at the waist, a wide sash, belt or waist panel keeps it from pinching, where a belt low on the hips leaves the waist free to narrow. A strap across the chest outlines it: run straps over one shoulder to the back, and check, because generators draw a quiver or bag strap diagonally across the chest anyway.
- Give the expression in positive words ("wide-open, alert eyes and a determined expression"); "eyes open" alone loses to a reference.

**Never attach a reference whose torso or expression breaks these rules:** generators copy both over the prompt (a siren concept's sweetheart neckline and half-lidded eyes came back on both tries). Attach a crop of only what it should contribute (the head with its fins, a palette swatch) and describe the rest in words.

Generators often fail the first try (a plate drawn as two separate cups, bare skin above the band, a pinched waist, a plate grown into a dress), so review each try. On a retry, name the failure in shape words and give the fix, for example: "the plate shows two separate cups with a dip between them: make it one continuous plate with a smooth front and a single sheen, starting at the collarbone", or "the cuirass is molded into two rounded shapes with a highlight on each: make it one broad, gently rounded matte front with a central ridge and one soft highlight".

## 3D

The same rules hold for meshes and their maps. The chest piece is its own geometry or material, one continuous shell over the chest: it may follow a modest curve of the body under it, but never as two separately shaped cups or with a dip between them, and no normal, color or roughness map shades or highlights the chest. A character that looks like a child is modeled flat. Renders of the model must pass the same rules.

Box cuirasses on three monsters and a tube from chest to thigh on a fourth read as pasted on, so the armor is built like this: on three monsters and a tube from chest to thigh on a fourth, which read as pasted on:
- **Armor follows the body.** Build the chest piece from the torso surface (shrinkwrap, or rays from the trunk out to the skin, plus 1 to 2 cm), then give it thickness and bevels, so it wraps the torso's rounded cross-section. Never a box or a tube around the body.
- **Split it like real armor:** a cuirass plus a belt, and tassets or a skirt below, not one piece from chest to thigh.
- **Top edge:** with bare shoulders, a straight edge across the chest reads as a strapless tube top. Run it in one convex line instead: up to the collar (a halter neck), over the shoulders (straps or pauldrons), or under a high collar. A point raised at the sternum leaves a rounded patch of skin on each side of it, two round shapes below the collarbone (rule 4); never put a concave dip beside a point.

## Review before any upload

View each image or render at full size and at 128 px. It fails if:
- with the chest piece recolored to the skin tone, the figure would read as nude, or the chest is the figure's focal point (its size, highlights or shading);
- the chest piece could pass for skin;
- a cleavage line, a dip between two separately shaped cups, or a pinched waist (narrower than about 0.7 of the hips' cover; a slight hourglass passes) shows, or less than 70% of the torso is covered;
- blood, a wound or gore shows ([no-gore.md](no-gore.md));
- the cover looks pasted on (a foreign color, a bulky shape), or the outline differs from the rest of the set.

Fix the art first. Never upload to test moderation.
