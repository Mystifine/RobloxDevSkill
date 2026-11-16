<#
Installs, updates, checks or removes the roblox-dev skill, keeping a single source of truth. INSTALL.md has the steps.

  install.ps1               install, or update an existing install
  install.ps1 -Update       update an existing install (fails when there is none)
  install.ps1 -Status       where it is installed and at which version (exit 1 when it is not)
  install.ps1 -Uninstall    remove it and Claude's link to it; -Purge also deletes its learning notes and Codex handoff state

  Global (default):  base = your home folder.      -Local: base = the project folder (-Project, default current).

  1. If <base>\.agents exists          -> install to <base>\.agents\skills\roblox-dev
     and, if <base>\.claude also exists -> junction <base>\.claude\skills\roblox-dev to that folder (never a second copy).
  2. Else if <base>\.claude exists     -> install to <base>\.claude\skills\roblox-dev.
  3. Else                              -> create <base>\.agents\skills and install there.

Global installs keep their git history (update by re-running). Local installs drop .git so the project can commit them;
-Update replaces such a copy. Installed checkouts exclude the repository's development-only .mcp.json.
An existing install is updated, an existing foreign link is left untouched, and -Force reinstalls a non-git copy.
-Uninstall removes only this skill: a folder whose SKILL.md is named roblox-dev, or a link to one, which goes alone and
never takes the folder it points to. A global uninstall also takes the Codex handoff's permission rules out of Claude's
settings (with Node), and keeps the learning notes and Codex handoff state unless -Purge. -Force removes anything else
found at the skill's two paths.
#>
param(
    [switch]$Local,
    [string]$Project = (Get-Location).Path,
    [switch]$Force,
    [switch]$Update,
    [switch]$Uninstall,
    [switch]$Purge,
    [switch]$Status,
    [string]$HomeDir = $HOME
)
$ErrorActionPreference = 'Stop'
$name = 'roblox-dev'
$repo = if ($env:ROBLOX_DEV_REPO) { $env:ROBLOX_DEV_REPO } else { 'https://github.com/Mystifine/RobloxDevSkill.git' }

if (([int][bool]$Update + [int][bool]$Uninstall + [int][bool]$Status) -gt 1) { throw 'Use one of -Update, -Uninstall and -Status.' }
if ($Purge -and -not $Uninstall) { throw '-Purge goes with -Uninstall.' }

function Invoke-Git {
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue' # git writes progress to stderr, which Windows PowerShell 5.1 treats as an error
    & git @args
    $code = $LASTEXITCODE
    $ErrorActionPreference = $previous
    if ($code -ne 0) { throw "git $($args -join ' ') failed with exit code $code" }
}

function Get-Entry([string]$Path) {
    # The item at a path itself, a dangling link included.
    return Get-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
}

function Resolve-LinkTarget([string]$Path) {
    $item = Get-Entry $Path
    if ($null -eq $item -or -not $item.LinkType) { return $null }
    $target = [string]@($item.Target)[0]
    if (-not [IO.Path]::IsPathRooted($target)) { $target = Join-Path (Split-Path -Parent $Path) $target }
    return [IO.Path]::GetFullPath($target).TrimEnd('\')
}

function Test-Skill([string]$Path) {
    # This skill, not another one: its SKILL.md is named roblox-dev.
    $file = Join-Path $Path 'SKILL.md'
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { return $false }
    return [bool](Select-String -LiteralPath $file -Pattern '^name:\s*roblox-dev\s*$' -Quiet)
}

function Get-Version([string]$Path) {
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) { return '' }
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $line = & git -C $Path log -1 '--format=%h %cs' 2>$null
    $ErrorActionPreference = $previous
    return [string]$line
}

function Remove-Link([string]$Path) {
    # The link alone: a recursive delete through a junction can empty the folder it points to.
    [IO.Directory]::Delete($Path)
}

$base = if ($Local) { (Resolve-Path -LiteralPath $Project).Path } else { $HomeDir }
$agents = Join-Path $base '.agents'
$claude = Join-Path $base '.claude'
$agentsSkill = Join-Path (Join-Path $agents 'skills') $name
$claudeSkill = Join-Path (Join-Path $claude 'skills') $name

if ($Status) {
    $found = $false
    foreach ($path in @($agentsSkill, $claudeSkill)) {
        $item = Get-Entry $path
        if ($null -eq $item) { continue }
        $found = $true
        $what = 'a copy without git history'
        if ($item.LinkType) {
            $what = "a link to $(Resolve-LinkTarget $path)"
        } elseif (Test-Path -LiteralPath (Join-Path $path '.git')) {
            $what = "a git checkout at $(Get-Version $path)".TrimEnd()
        }
        if (-not (Test-Skill $path)) { $what += ' (no SKILL.md named roblox-dev: not this skill)' }
        Write-Output "${path}: $what"
    }
    if (-not $found) {
        Write-Output "roblox-dev is not installed under $base."
        exit 1
    }
    exit 0
}

if ($Uninstall) {
    Set-Location -LiteralPath $base # never stand inside a folder being removed
    $configDir = if ($env:CLAUDE_CONFIG_DIR -and -not $Local) { $env:CLAUDE_CONFIG_DIR } else { $claude }
    if (-not $Local) {
        # The Codex handoff's permission rules name this skill's wrapper: take them out while its installer is still here.
        $settings = Join-Path $configDir 'settings.json'
        if ((Test-Path -LiteralPath $settings) -and (Select-String -LiteralPath $settings -SimpleMatch 'roblox-dev/scripts/codex/handoff.sh' -Quiet)) {
            $mjs = @($agentsSkill, $claudeSkill) | ForEach-Object { Join-Path $_ 'scripts\codex\install.mjs' } |
                Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
            $removedRules = $false
            if ($mjs -and (Get-Command node -ErrorAction SilentlyContinue)) {
                $saved = $env:CLAUDE_CONFIG_DIR
                try {
                    $env:CLAUDE_CONFIG_DIR = $configDir
                    & node $mjs --uninstall
                    $removedRules = $LASTEXITCODE -eq 0
                } finally {
                    $env:CLAUDE_CONFIG_DIR = $saved
                }
            }
            if (-not $removedRules) {
                Write-Warning "$settings still allows the roblox-dev Codex handoff wrapper. Delete its permissions.allow entry naming roblox-dev/scripts/codex/handoff.sh and the autoMode.allow rule starting 'Running the roblox-dev Codex handoff wrapper'."
            }
        }
    }
    $removed = 0
    $agentsFull = [IO.Path]::GetFullPath($agentsSkill).TrimEnd('\')
    # Claude's entry first: it may be a link to the .agents copy, judged before that copy goes.
    foreach ($path in @($claudeSkill, $agentsSkill)) {
        $item = Get-Entry $path
        if ($null -eq $item) { continue }
        if ($item.LinkType) {
            $to = Resolve-LinkTarget $path
            $ours = (-not $to) -or ($to -ieq $agentsFull) -or -not (Test-Path -LiteralPath $to) -or (Test-Skill $to)
            if ($ours -or $Force) {
                Remove-Link $path
                if ($to -ieq $agentsFull) { Write-Output "Removed Claude's link $path" }
                else { Write-Output "Removed the link $path -> $to (the folder it points to was not touched)" }
                $removed++
            } else {
                Write-Warning "$path links to $to, which is not the roblox-dev skill; left untouched. -Force removes the link."
            }
        } elseif ((Test-Skill $path) -or $Force) {
            Remove-Item -LiteralPath $path -Recurse -Force
            Write-Output "Removed $path"
            $removed++
        } else {
            Write-Warning "$path is not the roblox-dev skill (no SKILL.md named roblox-dev); left untouched. -Force removes it."
        }
    }
    if (-not $Local) {
        $learning = if ($env:ROBLOX_DEV_LEARNING_HOME) { $env:ROBLOX_DEV_LEARNING_HOME } else { Join-Path $HomeDir '.roblox-dev\learning' }
        $handoffs = if ($env:CODEX_HANDOFF_HOME) { $env:CODEX_HANDOFF_HOME } else { Join-Path $configDir 'codex-handoffs' }
        foreach ($data in @(@($learning, 'learning notes'), @($handoffs, 'Codex handoff state'))) {
            if (-not (Test-Path -LiteralPath $data[0])) { continue }
            if ($Purge) {
                Remove-Item -LiteralPath $data[0] -Recurse -Force
                Write-Output "Removed the $($data[1]) in $($data[0])"
            } else {
                Write-Output "Kept the $($data[1]) in $($data[0]) (-Purge deletes them)."
            }
        }
        $notesHome = Join-Path $HomeDir '.roblox-dev'
        if ($Purge -and (Test-Path -LiteralPath $notesHome) -and -not (Get-ChildItem -LiteralPath $notesHome -Force)) {
            Remove-Item -LiteralPath $notesHome -Force
        }
    }
    if ($removed -eq 0) {
        Write-Output "roblox-dev was not installed under $base."
    } else {
        Write-Output 'Start a new agent session so its skill list no longer shows roblox-dev.'
    }
    exit 0
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'git is required.' }
$hasAgents = Test-Path -LiteralPath $agents -PathType Container
$hasClaude = Test-Path -LiteralPath $claude -PathType Container

$primary = if (-not $hasAgents -and $hasClaude) { $claude } else { $agents }
$target = Join-Path (Join-Path $primary 'skills') $name

if ($Update -and $null -eq (Get-Entry $target)) {
    $claudeItem = Get-Entry $claudeSkill
    if ($null -ne $claudeItem -and -not $claudeItem.LinkType) {
        # An install from before .agents existed: update it where it is.
        $primary = $claude
        $target = $claudeSkill
    } else {
        throw "roblox-dev is not installed at $target; run without -Update to install it."
    }
}

if (Test-Path -LiteralPath $target) {
    $linkedTo = Resolve-LinkTarget $target
    if ($linkedTo) {
        Write-Output "Already installed: $target is a link to $linkedTo (left untouched; update that checkout itself)."
    } elseif (Test-Path -LiteralPath (Join-Path $target '.git')) {
        $old = Get-Version $target
        Invoke-Git -C $target sparse-checkout set --no-cone '/*' '!/.mcp.json'
        Invoke-Git -C $target pull --ff-only --quiet
        $new = Get-Version $target
        if ($old -eq $new) { Write-Output "Up to date: $target at $new" } else { Write-Output "Updated ${target}: $old -> $new" }
    } elseif ($Force -or ($Update -and (Test-Skill $target))) {
        Write-Output "Replacing the copy at $target"
        Remove-Item -LiteralPath $target -Recurse -Force
    } else {
        throw "$target exists and is not a git checkout. Re-run with -Force to replace it."
    }
}
if (-not (Test-Path -LiteralPath $target)) {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
    Invoke-Git clone --depth 1 --no-checkout --quiet $repo $target
    Invoke-Git -C $target sparse-checkout set --no-cone '/*' '!/.mcp.json'
    Invoke-Git -C $target checkout --quiet
    if ($Local) { Remove-Item -LiteralPath (Join-Path $target '.git') -Recurse -Force }
    Write-Output "Installed $target"
}

# Claude points at the single copy instead of holding its own.
if ($primary -eq $agents -and $hasClaude) {
    $link = $claudeSkill
    $resolvedTarget = [IO.Path]::GetFullPath($target).TrimEnd('\')
    if (Test-Path -LiteralPath $link) {
        $current = Resolve-LinkTarget $link
        if ($current -ieq $resolvedTarget) {
            Write-Output "Claude link OK: $link"
        } else {
            Write-Warning "$link already exists and does not point to $resolvedTarget; left untouched."
        }
    } else {
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $link) | Out-Null
        New-Item -ItemType Junction -Path $link -Target $resolvedTarget | Out-Null
        Write-Output "Linked $link -> $resolvedTarget"
    }
}
