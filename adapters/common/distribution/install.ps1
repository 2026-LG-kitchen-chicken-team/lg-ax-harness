param(
    [ValidateSet('codex','claude')][string]$Engine = 'codex',
    [string]$Version = 'product-v0.16.1',
    [string]$Target,
    [ValidateSet('gh','public')][string]$Transport = 'gh',
    [switch]$DownloadOnly
)
$ErrorActionPreference = 'Stop'
$repo = '2026-LG-kitchen-chicken-team/lg-ax-agent'
$installerTag = 'installer-v0.1.0'
$coreSHA = '716599e7921665036f77ec2858eaa654bfb982c6093c607ab1208805e4d57cdc'
$tempRoot = [IO.Path]::GetTempPath()
$work = Join-Path $tempRoot ('lgax-installer-' + [Guid]::NewGuid().ToString('N'))
$null = New-Item -ItemType Directory -Path $work
$core = Join-Path $work 'install.py'
try {
    if ($Transport -eq 'gh') {
        if (-not (Get-Command gh -ErrorAction SilentlyContinue)) { throw 'Install GitHub CLI, then run gh auth login with repository read access.' }
        gh release download $installerTag --repo $repo --pattern install.py --output $core
        if ($LASTEXITCODE -ne 0) { throw 'Installer download failed. Check GitHub authentication and repository access.' }
    } else {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -UseBasicParsing -Uri "https://github.com/$repo/releases/download/$installerTag/install.py" -OutFile $core
    }
    $stream = [IO.File]::OpenRead($core)
    $hasher = [Security.Cryptography.SHA256]::Create()
    try { $actual = [BitConverter]::ToString($hasher.ComputeHash($stream)).Replace('-','').ToLowerInvariant() }
    finally { $stream.Dispose(); $hasher.Dispose() }
    if ($actual -ne $coreSHA) { throw 'Installer checksum mismatch.' }
    $uv = Get-Command uv -ErrorAction SilentlyContinue
    if (-not $uv) {
        $knownUV = Join-Path $env:USERPROFILE '.local/bin/uv.exe'
        if (Test-Path -LiteralPath $knownUV) { $uv = Get-Item -LiteralPath $knownUV }
    }
    if (-not $uv) {
        Write-Host 'uv prepares Python 3.12. Official installer: https://astral.sh/uv/install.ps1'
        $answer = Read-Host 'Install uv now? [y/N]'
        if ($answer -notin @('y','Y','yes')) { throw 'Stopped. Install uv and run this command again.' }
        & ([scriptblock]::Create((Invoke-RestMethod https://astral.sh/uv/install.ps1)))
        $knownUV = Join-Path $env:USERPROFILE '.local/bin/uv.exe'
        if (Test-Path -LiteralPath $knownUV) { $uv = Get-Item -LiteralPath $knownUV }
        else { $uv = Get-Command uv -ErrorAction SilentlyContinue }
        if (-not $uv) { throw 'uv was not found. Open a new terminal after installing uv.' }
    }
    $uvPath = if ($uv -is [IO.FileInfo]) { $uv.FullName } else { $uv.Source }
    $env:PATH = (Split-Path -Parent $uvPath) + [IO.Path]::PathSeparator + $env:PATH
    $arguments = @('run','--no-project','--python','3.12','python',$core,'--repo',$repo,'--version',$Version,'--engine',$Engine,'--transport',$Transport)
    if ($Target) { $arguments += @('--target',$Target) }
    if ($DownloadOnly) { $arguments += '--download-only' }
    & $uvPath @arguments
    if ($LASTEXITCODE -ne 0) { throw 'Installation stopped. Read the preceding error; existing work was not overwritten.' }
} finally {
    # Only the single downloaded file and this newly-created empty directory are removed.
    if (Test-Path -LiteralPath $core) { Remove-Item -LiteralPath $core }
    if (Test-Path -LiteralPath $work) { Remove-Item -LiteralPath $work }
}
