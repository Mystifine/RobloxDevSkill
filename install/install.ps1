<#
Installs the roblox-dev skill with a single source of truth.

  Global (default):  base = your home folder.      -Local: base = the project folder (-Project, default current).

  1. If <base>\.agents exists          -> install to <base>\.agents\skills\roblox-dev
     and, if <base>\.claude also exists -> junction <base>\.claude\skills\roblox-dev to that folder (never a second copy).
  2. Else if <base>\.claude exists     -> install to <base>\.claude\skills\roblox-dev.
  3. Else                              -> create <base>\.agents\skills and install there.

Global installs keep their git history (update by re-running). Local installs drop .git so the project can commit them.
An existing install is updated, an existing foreign link is left untouched, and -Force reinstalls a non-git copy.
#>
param(
    [switch]$Local,
    [string]$Project = (Get-Location).Path,
    [switch]$Force,
    [string]$HomeDir = $HOME
)
$ErrorActionPreference = 'Stop'
$name = 'roblox-dev'
$repo = if ($env:ROBLOX_DEV_REPO) { $env:ROBLOX_DEV_REPO } else { 'https://github.com/Mystifine/RobloxDevSkill.git' }

function Invoke-Git {
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue' # git writes progress to stderr, which Windows PowerShell 5.1 treats as an error
    & git @args
    $code = $LASTEXITCODE
    $ErrorActionPreference = $previous
    if ($code -ne 0) { throw "git $($args -join ' ') failed with exit code $code" }
}

function Resolve-LinkTarget([string]$Path) {
    $item = Get-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
    if ($null -eq $item -or -not $item.LinkType) { return $null }
    $target = [string]@($item.Target)[0]
    if (-not [IO.Path]::IsPathRooted($target)) { $target = Join-Path (Split-Path -Parent $Path) $target }
    return [IO.Path]::GetFullPath($target).TrimEnd('\')
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'git is required.' }
$base = if ($Local) { (Resolve-Path -LiteralPath $Project).Path } else { $HomeDir }
$agents = Join-Path $base '.agents'
$claude = Join-Path $base '.claude'
$hasAgents = Test-Path -LiteralPath $agents -PathType Container
$hasClaude = Test-Path -LiteralPath $claude -PathType Container

$primary = if (-not $hasAgents -and $hasClaude) { $claude } else { $agents }
$target = Join-Path (Join-Path $primary 'skills') $name

if (Test-Path -LiteralPath $target) {
    $linkedTo = Resolve-LinkTarget $target
    if ($linkedTo) {
        Write-Output "Already installed: $target is a link to $linkedTo (left untouched)."
    } elseif (Test-Path -LiteralPath (Join-Path $target '.git')) {
        Invoke-Git -C $target pull --ff-only --quiet
        Write-Output "Updated $target"
    } elseif ($Force) {
        Remove-Item -LiteralPath $target -Recurse -Force
    } else {
        throw "$target exists and is not a git checkout. Re-run with -Force to replace it."
    }
}
if (-not (Test-Path -LiteralPath $target)) {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
    Invoke-Git clone --depth 1 --quiet $repo $target
    if ($Local) { Remove-Item -LiteralPath (Join-Path $target '.git') -Recurse -Force }
    Write-Output "Installed $target"
}

# Claude points at the single copy instead of holding its own.
if ($primary -eq $agents -and $hasClaude) {
    $link = Join-Path (Join-Path $claude 'skills') $name
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
