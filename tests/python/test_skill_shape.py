"""The skill's shape: what a task pays for stays within budget, every link resolves, and every reference can be reached from the route.
docs/developing.md says why. Over a budget? Move rare detail out or split the file; raise a limit only when every task on that route needs it."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
SKILL_MD = 3000  # heavy agent fan-outs sharing the plan's usage limit, Blender-only background agents beside Studio work, a cleanup route row, backslashes kept out of inline scripts with their signs, pipeline intermediates, the monetization row, review output kept out of the project with its evidence, the top bar checked in a user's Play, the rules read as production experience, long scripts kept in files
DESCRIPTION = 450  # characters: read in every session, Roblox or not
REFERENCE = 10000  # the maintainer's limit for one reference; routing still comes first, so a file splits when its routes mostly need only a part of it
EXCEPTIONS = {}
# What a typical task loads, SKILL.md included.
ROUTES = {
    'luau code': (['code/coding'], 7400),
    'streaming': (['code/coding', 'code/streaming'], 8450),  # streamed models, binders and travel: split from coding
    'economy': (['design/game-economy'], 8850),  # currencies, pacing models, ladders, live ops
    'studio testing': (['code/coding', 'code/studio-testing'], 12000),
    'performance': (['code/coding', 'code/performance'], 8500),  # measurement in its own file
    'hud': (['art/visual-style', 'ui/ui'], 10000),  # lists, grids and tabs moved to ui/lists
    'ui lists': (['art/visual-style', 'ui/ui', 'ui/lists'], 11150),  # scrolling lists, grids, tab strips, drop-downs
    'icons': (['art/visual-style', 'ui/icons', 'safety/assets', 'safety/no-gore', 'safety/uploading'], 13200),  # upload sizing, portraits
    'vfx': (['art/visual-style', 'art/vfx', 'safety/no-gore', 'safety/uploading'], 13100),
    'hit vfx': (['art/visual-style', 'art/vfx', 'art/hit-vfx', 'safety/no-gore', 'safety/uploading'], 14300),  # attacks in their own file
    'bake': (['art/visual-style', 'art/modeling', 'art/baking'], 9650),
    'weapon': (['art/visual-style', 'art/modeling', 'rigs/gear', 'safety/no-gore', 'safety/uploading'], 14150),  # the weapon's own joint
    'character skin': (['art/visual-style', 'art/modeling', 'rigs/rigs', 'rigs/skins', 'safety/characters', 'safety/no-gore', 'safety/uploading'], 24300),  # bare skin is the colored body, not a shell
    'catalog character': (['rigs/rigs', 'rigs/catalog', 'rigs/hair'], 11800),  # a look from Marketplace items, with a Humanoid
    'r6-like clip': (['animation/r6-on-r15', 'animation/animation'], 11150),
    'r6-like weapon clip': (['animation/r6-on-r15', 'animation/animation', 'animation/r6-weapons'], 12650),  # weapon clips in their own file  # the weapon's own joint; R6 walks in their own file
    'blender clip': (['animation/animation', 'animation/blender'], 9950),  # was 18,700 with animate-roblox-characters loaded
    'r6-like clip in blender': (['animation/r6-on-r15', 'animation/animation', 'animation/blender'], 14350),
    'default r6 clips': (['animation/r6-default-set'], 4700),
    'funnels': (['design/analytics'], 7150),
    'journeys': (['design/analytics', 'design/journeys'], 8400),
    'monetization': (['design/monetization'], 6500),  # products, shop, offers, gifts; split from game-economy
    'maps': (['art/visual-style', 'art/modeling', 'art/maps'], 10350),  # maps, bases and buildings: their own file beside modeling
    'ui windows': (['art/visual-style', 'ui/ui', 'ui/windows'], 10850),  # windows, modals and sheets
    'vfx pack': (['art/visual-style', 'art/vfx', 'art/vfx-packs', 'safety/no-gore', 'safety/uploading'], 13550),  # effects from a supplied pack
    'audio': (['art/audio', 'safety/assets'], 7050),
    'video': (['art/video', 'art/visual-style'], 6050),
    'cutscene': (['art/cutscenes', 'art/vfx', 'art/visual-style'], 13700),
    'studio captures': (['code/coding', 'code/studio-testing', 'code/captures'], 13050),  # what captures show and miss, catching short moments
    'project cleanup': (['code/coding', 'code/cleanup'], 8350),  # retired systems, old-save code, status docs
    'hud feedback': (['art/visual-style', 'ui/ui', 'ui/hud'], 11450),  # gains, stat readouts, notifications
    'fight controls': (['art/visual-style', 'ui/ui', 'ui/controls'], 11400),  # touch ring, PC tiles, gamepad
    'character vfx': (['art/visual-style', 'art/vfx', 'art/character-fx', 'safety/no-gore', 'safety/uploading'], 15100),  # auras, transformations, payoffs, camera kicks
    'editable mesh': (['art/visual-style', 'art/modeling', 'art/editable-mesh', 'safety/uploading'], 12500),  # meshes built and published in Studio
    'play input': (['code/coding', 'code/studio-testing', 'code/play-input'], 14850),  # clicks, prompts, camera, touch: split from studio testing
    'product setup': (['design/monetization', 'design/product-setup'], 7650),  # Open Cloud creates, updates and retries
    'offers': (['design/monetization', 'design/offers'], 8900),  # shop, offers and the popup queue: split from monetization
    'chatgpt images': (['art/visual-style', 'ui/icons', 'ui/chatgpt-images', 'safety/assets', 'safety/no-gore', 'safety/uploading'], 13750),  # icon sheets through ChatGPT in the user's Chrome
    'cutscene captions': (['art/cutscenes', 'art/captions', 'art/vfx', 'art/visual-style'], 14000),  # spoken lines: split from cutscenes
}
LINK = re.compile(r'\[[^\]]*\]\(([^)\s]+)\)')


def tokens(path):
    return len(path.read_text(encoding='utf-8')) // 4


def docs():
    roots = [ROOT / 'SKILL.md', ROOT / 'README.md', ROOT / 'INSTALL.md']
    return roots + sorted((ROOT / 'references').rglob('*.md')) + sorted((ROOT / 'docs').rglob('*.md'))


def links(path):
    # Code fences and code spans show examples, not links.
    text = re.sub(r'```.*?```', '', path.read_text(encoding='utf-8'), flags=re.S)
    text = re.sub(r'`[^`\n]*`', '', text)
    return [t for t in LINK.findall(text) if not re.match(r'[a-z]+:', t)]


def route_paths():
    text = (ROOT / 'SKILL.md').read_text(encoding='utf-8')
    return re.findall(r'`([\w/-]+\.md)`', text[text.index('## Route'):text.index('## Scripts')])


def anchors(path):
    found = set()
    for line in path.read_text(encoding='utf-8').splitlines():
        m = re.match(r'#{1,6} (.+)', line)
        if m:
            slug = re.sub(r'[^\w\- ]', '', m.group(1).lower()).strip().replace(' ', '-')
            found.add(slug)
    return found


class Budgets(unittest.TestCase):
    def test_skill_md_is_within_budget(self):
        self.assertLessEqual(tokens(ROOT / 'SKILL.md'), SKILL_MD, 'SKILL.md is read on every task: move detail to its reference')

    def test_description_is_within_budget(self):
        text = (ROOT / 'SKILL.md').read_text(encoding='utf-8')
        self.assertLessEqual(len(re.search(r'^description: (.*)$', text, re.M).group(1)), DESCRIPTION)

    def test_references_are_within_budget(self):
        over = {}
        for path in (ROOT / 'references').rglob('*.md'):
            name = path.relative_to(ROOT).as_posix()
            if tokens(path) > EXCEPTIONS.get(name, REFERENCE):
                over[name] = tokens(path)
        self.assertEqual(over, {}, 'split the file along its routes')

    def test_typical_tasks_are_within_budget(self):
        over = {}
        for task, (files, limit) in ROUTES.items():
            total = tokens(ROOT / 'SKILL.md') + sum(tokens(ROOT / 'references' / f'{f}.md') for f in files)
            if total > limit:
                over[task] = (total, limit)
        self.assertEqual(over, {})


class Frontmatter(unittest.TestCase):
    def test_the_description_is_valid_yaml(self):
        # Its colon is invalid YAML unquoted, and an agent then shows the skill with no description: seen on a CRLF checkout, which Windows installs get.
        text = (ROOT / 'SKILL.md').read_text(encoding='utf-8')
        self.assertRegex(text, r"(?m)^description: '[^']+'$")


class Links(unittest.TestCase):
    def test_every_relative_link_and_anchor_resolves(self):
        broken = []
        for path in docs():
            for target in links(path):
                file, _, anchor = target.partition('#')
                resolved = (path.parent / file).resolve() if file else path
                name = path.relative_to(ROOT).as_posix()
                if not resolved.exists():
                    broken.append(f'{name}: {target}')
                elif anchor and resolved.suffix == '.md' and anchor not in anchors(resolved):
                    broken.append(f'{name}: {target} (no such heading)')
        self.assertEqual(broken, [])

    def test_paths_named_in_code_exist(self):
        broken = []
        for folder in ('scripts', 'tests'):
            for path in (ROOT / folder).rglob('*'):
                if path.suffix not in {'.py', '.luau', '.mjs', '.sh'} or '__pycache__' in path.parts or path.name == Path(__file__).name:
                    continue
                for named in re.findall(r'references/[\w/-]+\.md', path.read_text(encoding='utf-8', errors='replace')):
                    if not (ROOT / named).exists():
                        broken.append(f'{path.relative_to(ROOT).as_posix()}: {named}')
        self.assertEqual(broken, [])

    def test_codex_prompts_name_files_that_exist(self):
        source = (ROOT / 'scripts/codex/handoff.mjs').read_text(encoding='utf-8')
        for parts in re.findall(r"path\.join\(skillRoot, ((?:'[^']+'(?:, )?)+)\)", source):
            self.assertTrue(ROOT.joinpath(*re.findall(r"'([^']+)'", parts)).exists(), parts)

    def test_every_path_in_the_route_exists(self):
        missing = [p for p in route_paths() if not (ROOT / 'references' / p).exists()]
        self.assertEqual(missing, [])

    def test_every_reference_can_be_reached_from_the_route(self):
        seen = {(ROOT / 'references' / p).resolve() for p in route_paths()}
        queue = [*seen, ROOT / 'SKILL.md']
        while queue:
            path = queue.pop()
            for target in links(path):
                file = target.partition('#')[0]
                resolved = (path.parent / file).resolve() if file else path
                if resolved.suffix == '.md' and resolved.exists() and resolved not in seen and resolved.is_relative_to(ROOT / 'references'):
                    seen.add(resolved)
                    queue.append(resolved)
        orphans = [p.relative_to(ROOT).as_posix() for p in (ROOT / 'references').rglob('*.md') if p.resolve() not in seen]
        self.assertEqual(orphans, [])


if __name__ == '__main__':
    unittest.main()
