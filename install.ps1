# 4diac Trainings-Installer - Bootstrap (Windows PowerShell 5.1, siehe KONZEPT.md 3.1)
#
# Laedt NUR Python. Alles andere erledigt der Python-Hauptinstaller (trainings_installer).
#   - legt C:\ms\sl an und prueft das Schreibrecht
#   - uebernimmt ein per Selbst-Update vorbereitetes installer.neu
#   - kopiert sich nach C:\ms\sl\installer (wenn von woanders gestartet, z. B. aus dem ZIP)
#   - prueft tools\python\.ms-sl-version gegen manifest.json, laedt Python nur bei Abweichung
#   - startet ohne Argumente die GUI (pythonw), mit Argumenten die Konsole (python)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'   # Fortschrittsanzeige von 5.1 bremst Downloads stark
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$Root      = if ($env:MS_SL_ROOT) { $env:MS_SL_ROOT } else { 'C:\ms\sl' }
$Here      = $PSScriptRoot
$Installer = Join-Path $Root 'installer'
$Neu       = Join-Path $Root 'installer.neu'
$PyDir     = Join-Path $Root 'tools\python'
$Tar       = Join-Path $env:SystemRoot 'System32\tar.exe'   # nicht das tar aus Git

# SHA256 direkt ueber .NET (Get-FileHash fehlt, wenn PowerShell 5.1 aus PowerShell 7 gestartet wird)
function Get-Sha256([string]$path) {
    $stream = [IO.File]::OpenRead($path)
    try { $hash = [Security.Cryptography.SHA256]::Create().ComputeHash($stream) } finally { $stream.Close() }
    return (($hash | ForEach-Object { $_.ToString('x2') }) -join '')
}

function Fail([string]$msg) {
    Write-Host ''
    Write-Host "FEHLER: $msg" -ForegroundColor Red
    exit 1
}

try {
    # 1. Grundordner + Schreibprobe
    foreach ($d in @('', 'tools', 'downloads', 'logs')) {
        New-Item -ItemType Directory -Force -Path (Join-Path $Root $d) | Out-Null
    }
    $probe = Join-Path $Root '.schreibprobe'
    Set-Content -Path $probe -Value 'x' -Encoding ASCII
    Remove-Item $probe -Force
} catch {
    Fail "Kann nicht in $Root schreiben: $($_.Exception.Message)"
}

# Internet-Markierung (Mark of the Web) bei den eigenen Dateien entfernen
try { Get-ChildItem -Path $Here -Recurse -File | Unblock-File } catch { }

Set-Location $Root   # nie im Ordner stehen, der gleich ersetzt wird

# 2. Selbst-Update abschliessen: installer.neu -> installer
if (Test-Path (Join-Path $Neu 'version.txt')) {
    Write-Host 'Neue Installer-Version wird uebernommen ...'
    if (Test-Path $Installer) { Remove-Item $Installer -Recurse -Force }
    Rename-Item -Path $Neu -NewName 'installer'
}

# 3. Sich selbst nach C:\ms\sl\installer kopieren (beim Start aus dem ZIP / vom USB-Stick)
$hereFull = (Resolve-Path $Here).Path.TrimEnd('\')
$instFull = [IO.Path]::GetFullPath($Installer).TrimEnd('\')
if ($hereFull -ne $instFull) {
    $tmp = Join-Path $Root 'installer.tmp'
    if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
    New-Item -ItemType Directory -Path $tmp | Out-Null
    foreach ($item in @('install.cmd', 'Neues Projekt.cmd', 'install.ps1', 'manifest.json', 'version.txt', 'LIESMICH.txt', 'trainings_installer')) {
        $src = Join-Path $Here $item
        if (Test-Path $src) { Copy-Item -Path $src -Destination $tmp -Recurse -Force }
    }
    Get-ChildItem -Path $tmp -Recurse -Directory -Filter '__pycache__' | Remove-Item -Recurse -Force
    if (Test-Path $Installer) { Remove-Item $Installer -Recurse -Force }
    Rename-Item -Path $tmp -NewName 'installer'
}

# 4. Python pruefen bzw. laden
try {
    $manifest = Get-Content -Raw -Encoding UTF8 (Join-Path $Installer 'manifest.json') | ConvertFrom-Json
} catch {
    Fail "manifest.json nicht lesbar: $($_.Exception.Message)"
}
$py = $manifest.python
$verFile = Join-Path $PyDir '.ms-sl-version'
$have = if (Test-Path $verFile) { (Get-Content $verFile -Raw).Trim() } else { '' }

if ($have -ne $py.version -or -not (Test-Path (Join-Path $PyDir 'python.exe'))) {
    Write-Host "Python $($py.version) wird installiert ..."
    try {
        $file = [IO.Path]::GetFileName(([Uri]$py.url).AbsolutePath)
        $dst  = Join-Path $Root "downloads\$file"
        $ok   = (Test-Path $dst) -and ((Get-Sha256 $dst) -eq $py.sha256)
        if (-not $ok) {
            $tmp = "$dst.tmp"
            Invoke-WebRequest -Uri $py.url -OutFile $tmp -UseBasicParsing
            if ((Get-Sha256 $tmp) -ne $py.sha256) {
                Remove-Item $tmp -Force
                throw "SHA256 stimmt nicht: $file"
            }
            Move-Item -Path $tmp -Destination $dst -Force
        }
        if (Test-Path $PyDir) { Remove-Item $PyDir -Recurse -Force }
        New-Item -ItemType Directory -Path $PyDir | Out-Null
        & $Tar -xf $dst -C $PyDir
        if ($LASTEXITCODE -ne 0) { throw "Entpacken fehlgeschlagen ($file)" }
        & (Join-Path $PyDir 'python.exe') -m pip --version | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Funktionsprobe python -m pip --version fehlgeschlagen' }
        Set-Content -Path $verFile -Value $py.version -Encoding ASCII
    } catch {
        Fail "Python konnte nicht installiert werden: $($_.Exception.Message)"
    }
}

# 5. Hauptinstaller starten (Arbeitsverzeichnis = installer, dort liegt das Paket)
if ($args.Count -eq 0) {
    Start-Process -FilePath (Join-Path $PyDir 'pythonw.exe') -ArgumentList @('-m', 'trainings_installer') -WorkingDirectory $Installer
    exit 0
}
Set-Location $Installer
& (Join-Path $PyDir 'python.exe') -m trainings_installer @args
exit $LASTEXITCODE
