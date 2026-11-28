param(
    [switch] $SkipWordPressRuntime,
    [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9_-]*$')]
    [string] $DistSubdirectory
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonExe = "D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe"
$SpecPath = Join-Path $ProjectRoot "regex-pad.spec"

# PyInstallerで生成された onedir 版の EXE 名。
# dist 配下にこのフォルダが作られている前提です。
$AppDistName = "regex-pad"
$ProjectDistRoot = Join-Path $ProjectRoot "dist"
$DistRoot = $ProjectDistRoot
if ($DistSubdirectory) {
    $DistRoot = Join-Path $DistRoot $DistSubdirectory
}
foreach ($OutputPath in @($ProjectDistRoot, $DistRoot, (Join-Path $DistRoot $AppDistName))) {
    if ((Test-Path -LiteralPath $OutputPath) -and
        ((Get-Item -LiteralPath $OutputPath).Attributes -band [System.IO.FileAttributes]::ReparsePoint)) {
        throw "Refusing to build into a linked distribution directory: $OutputPath"
    }
}

# アプリ実行時に読み込む外部リソース。
# PyInstallerのspec側で同梱していない場合でも、ビルド後に確実にコピーします。
$ResourceSourcePath = Join-Path $ProjectRoot "resources"
$DictionarySourcePath = Join-Path $ProjectRoot "dictionaries"
$AssetSourcePath = Join-Path $ProjectRoot "assets"
$WordPressRuntimePath = Join-Path $ProjectRoot "runtime\wordpress-preview"
$DeletionListSourcePath = Join-Path $ProjectRoot "DELET_ITEMS_LIST.md"
$ConfigSourcePath = Join-Path $ProjectRoot "config.json"
$ColorPresetsSourcePath = Join-Path $ProjectRoot "color_presets.json"
$ExistingDistAppPath = Join-Path $DistRoot $AppDistName
$PortableFiles = @("config.json", "color_presets.json", "shortcutkey_ref.json")
$PortableFolders = @("user_dictionaries", "macro\preset_json_files")
$ExistingRecoveryFolders = @("_internal\autosave", "_internal\backup")
$PreservedPortableDataPath = $null
$BuildCompleted = $false

function Assert-DistributionNotRunning {
    param([Parameter(Mandatory = $true)][string] $AppDirectory)

    $running = @(Get-Process -Name "regex-pad", "module_cleaner" -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Path -and [string]::Equals(
                [System.IO.Path]::GetDirectoryName($_.Path),
                $AppDirectory,
                [System.StringComparison]::OrdinalIgnoreCase
            )
        })
    if ($running.Count -gt 0) {
        $processList = ($running | ForEach-Object { "$($_.ProcessName).exe (PID $($_.Id))" }) -join ", "
        throw "Build output is in use: $AppDirectory ($processList). Save your edits, close these processes, and rerun the build, or use -DistSubdirectory."
    }
}

function Copy-DirectoryFresh {
    param(
        [Parameter(Mandatory = $true)]
        [string] $SourcePath,

        [Parameter(Mandatory = $true)]
        [string] $DestinationPath
    )

    if (-not (Test-Path -LiteralPath $SourcePath)) {
        throw "Source directory was not found: $SourcePath"
    }

    if (Test-Path -LiteralPath $DestinationPath) {
        $ResolvedDestination = (Resolve-Path -LiteralPath $DestinationPath).Path
        $ExpectedDistRoot = [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot "dist"))
        if (-not $ResolvedDestination.StartsWith($ExpectedDistRoot + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing to replace a directory outside project dist: $ResolvedDestination"
        }
        Remove-Item -LiteralPath $ResolvedDestination -Recurse -Force
    }

    $DestinationParent = Split-Path -Parent $DestinationPath
    if (-not (Test-Path -LiteralPath $DestinationParent)) {
        New-Item -ItemType Directory -Path $DestinationParent -Force | Out-Null
    }

    Copy-Item -LiteralPath $SourcePath -Destination $DestinationPath -Recurse -Force
}

function Copy-ReleaseDocumentation {
    param(
        [Parameter(Mandatory = $true)]
        [string] $SourceRoot,

        [Parameter(Mandatory = $true)]
        [string] $DestinationRoot
    )

    $DocumentFiles = @(
        "readme.txt", "readme_jp.txt", "LICENSE", "LICENSE.txt", "SOURCE_CODE.md",
        "README.md", "README_jp.md", "SCRIPT_STEPS.md", "THIRD_PARTY_NOTICES.md"
    )
    $DocumentFolders = @("docs", "docs_jp", "LICENSES")

    $RequiredLicenseFiles = @(
        "qt-for-python\LGPL-3.0-only.txt", "qt-for-python\GPL-3.0-only.txt",
        "qt-for-python\GPL-2.0-only.txt", "qt-for-python\LicenseRef-Qt-Commercial.txt",
        "qt-for-python\SOURCES.md", "qt-virtual-keyboard\OpenWnn-NOTICE.txt",
        "qt-virtual-keyboard\PinyinIME-NOTICE.txt", "qt-virtual-keyboard\TCIME-COPYING.txt",
        "qt-virtual-keyboard\SOURCES.md"
    )

    # Validate the complete set before copying; the license notice is not generated.
    foreach ($Name in $DocumentFiles) {
        $SourcePath = Join-Path $SourceRoot $Name
        if (-not (Test-Path -LiteralPath $SourcePath -PathType Leaf)) {
            throw "Required release document was not found: $SourcePath"
        }
    }
    foreach ($Name in $DocumentFolders) {
        $SourcePath = Join-Path $SourceRoot $Name
        if (-not (Test-Path -LiteralPath $SourcePath -PathType Container)) {
            throw "Required release documentation folder was not found: $SourcePath"
        }
    }

    foreach ($Name in $RequiredLicenseFiles) {
        $SourcePath = Join-Path (Join-Path $SourceRoot "LICENSES") $Name
        if (-not (Test-Path -LiteralPath $SourcePath -PathType Leaf)) {
            throw "Required upstream license document was not found: $SourcePath"
        }
    }
    foreach ($Name in $DocumentFiles) {
        Copy-Item -LiteralPath (Join-Path $SourceRoot $Name) `
            -Destination (Join-Path $DestinationRoot $Name) -Force
    }
    foreach ($Name in $DocumentFolders) {
        $DestinationFolder = Join-Path $DestinationRoot $Name
        New-Item -ItemType Directory -Path $DestinationFolder -Force | Out-Null
        Get-ChildItem -LiteralPath (Join-Path $SourceRoot $Name) -Force | ForEach-Object {
            Copy-Item -LiteralPath $_.FullName -Destination $DestinationFolder -Recurse -Force
        }
    }
}

function Assert-JsonFilesCopied {
    param(
        [Parameter(Mandatory = $true)]
        [string] $SourcePath,

        [Parameter(Mandatory = $true)]
        [string] $DestinationPath
    )

    Get-ChildItem -LiteralPath $SourcePath -Recurse -File -Filter "*.json" | ForEach-Object {
        $RelativePath = [System.IO.Path]::GetRelativePath($SourcePath, $_.FullName)
        $CopiedPath = Join-Path $DestinationPath $RelativePath
        if (-not (Test-Path -LiteralPath $CopiedPath -PathType Leaf)) {
            throw "Required JSON was not copied: $CopiedPath"
        }
        if ((Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash -ne (Get-FileHash -LiteralPath $CopiedPath -Algorithm SHA256).Hash) {
            throw "Copied JSON does not match its source: $CopiedPath"
        }
    }
}

function Assert-ProjectJsonFilesBundled {
    param(
        [Parameter(Mandatory = $true)]
        [string] $SourceRoot,

        [Parameter(Mandatory = $true)]
        [string] $DestinationRoot
    )

    # Keep this filter aligned with _project_json_datas() in regex-pad.spec.
    $IgnoredParts = @(
        "build", "dist", "_internal", ".git", ".vscode", "runtime",
        "Temp", "install_records", "logs", "cache", "modules", "data",
        "user_dictionaries", "preset_json_files", ".deleted_presets"
    )
    $IgnoredNames = @("pyrightconfig.json")
    $PortableRootJson = @("config.json", "color_presets.json", "shortcutkey_ref.json")

    Get-ChildItem -LiteralPath $SourceRoot -Recurse -File -Filter "*.json" | ForEach-Object {
        $RelativePath = [System.IO.Path]::GetRelativePath($SourceRoot, $_.FullName)
        $RelativeParts = $RelativePath -split "[\\/]"
        if ($IgnoredNames -contains $_.Name) {
            return
        }
        if ($RelativeParts.Count -eq 1 -and $PortableRootJson -contains $RelativePath) {
            return
        }
        if (@($RelativeParts | Where-Object { $IgnoredParts -contains $_ }).Count -gt 0) {
            return
        }

        $BundledPath = Join-Path $DestinationRoot $RelativePath
        if (-not (Test-Path -LiteralPath $BundledPath -PathType Leaf)) {
            throw "Required project JSON was not bundled: $BundledPath"
        }
        if ((Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash -ne (Get-FileHash -LiteralPath $BundledPath -Algorithm SHA256).Hash) {
            throw "Bundled project JSON does not match its source: $BundledPath"
        }
    }
}

function Copy-PortableEntry {
    param(
        [Parameter(Mandatory = $true)] [string] $SourcePath,
        [Parameter(Mandatory = $true)] [string] $DestinationPath
    )

    if (Test-Path -LiteralPath $SourcePath -PathType Leaf) {
        New-Item -ItemType Directory -Path (Split-Path -Parent $DestinationPath) -Force | Out-Null
        Copy-Item -LiteralPath $SourcePath -Destination $DestinationPath -Force
        if ((Get-FileHash -LiteralPath $SourcePath -Algorithm SHA256).Hash -ne
            (Get-FileHash -LiteralPath $DestinationPath -Algorithm SHA256).Hash) {
            throw "Portable file copy differs from source: $DestinationPath"
        }
        return
    }

    if (Test-Path -LiteralPath $SourcePath -PathType Container) {
        New-Item -ItemType Directory -Path $DestinationPath -Force | Out-Null
        Get-ChildItem -LiteralPath $SourcePath -Recurse -File | ForEach-Object {
            $RelativePath = [System.IO.Path]::GetRelativePath($SourcePath, $_.FullName)
            $CopiedPath = Join-Path $DestinationPath $RelativePath
            New-Item -ItemType Directory -Path (Split-Path -Parent $CopiedPath) -Force | Out-Null
            Copy-Item -LiteralPath $_.FullName -Destination $CopiedPath -Force
            if ((Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash -ne
                (Get-FileHash -LiteralPath $CopiedPath -Algorithm SHA256).Hash) {
                throw "Portable folder copy differs from source: $CopiedPath"
            }
        }
    }
}

function Set-PortableProjectPaths {
    param(
        [Parameter(Mandatory = $true)] [string] $ConfigPath,
        [Parameter(Mandatory = $true)] [string] $SourceRoot
    )

    $Settings = Get-Content -LiteralPath $ConfigPath -Raw -Encoding utf8 | ConvertFrom-Json
    $Changed = $false
    $SourcePresetFolder = [System.IO.Path]::GetFullPath((Join-Path $SourceRoot "macro\preset_json_files"))
    $SourceUserDictionaryFolder = [System.IO.Path]::GetFullPath((Join-Path $SourceRoot "user_dictionaries"))
    if ($Settings.macro_folder -and
        [System.IO.Path]::GetFullPath($Settings.macro_folder) -eq $SourcePresetFolder) {
        $Settings.macro_folder = ""
        $Changed = $true
    }
    if ($Settings.user_dictionary_folder -and
        [System.IO.Path]::GetFullPath($Settings.user_dictionary_folder) -eq $SourceUserDictionaryFolder) {
        $Settings.user_dictionary_folder = "user_dictionaries"
        $Changed = $true
    }
    if ($Changed) {
        $Settings | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $ConfigPath -Encoding utf8
    }
}

function Test-FrozenQtImports {
    param([Parameter(Mandatory = $true)] [string] $AppDirectory)

    $InternalPath = Join-Path $AppDirectory "_internal"
    $ProbeCode = @'
import ctypes
import os
from pathlib import Path
import sys

internal = Path(sys.argv[1])
handles = [os.add_dll_directory(str(internal / name)) for name in (".", "PySide6", "shiboken6")]
ctypes.WinDLL(str(internal / "PySide6" / "Qt6Core.dll"))
ctypes.WinDLL(str(internal / "PySide6" / "QtCore.pyd"))
ctypes.WinDLL(str(internal / "PySide6" / "Qt6Gui.dll"))
ctypes.WinDLL(str(internal / "PySide6" / "QtGui.pyd"))
ctypes.WinDLL(str(internal / "PySide6" / "Qt6Widgets.dll"))
ctypes.WinDLL(str(internal / "PySide6" / "QtWidgets.pyd"))
ctypes.WinDLL(str(internal / "PySide6" / "plugins" / "platforms" / "qwindows.dll"))
print("Bundled Qt DLL load: OK")
'@
    & $PythonExe -c $ProbeCode $InternalPath
    if ($LASTEXITCODE -ne 0) {
        throw "Bundled Qt DLL load failed: $AppDirectory"
    }
}

Assert-DistributionNotRunning -AppDirectory $ExistingDistAppPath

if (-not (Test-Path -LiteralPath $PythonExe)) {
    throw "Python interpreter was not found: $PythonExe"
}

if (-not (Test-Path -LiteralPath $SpecPath)) {
    throw "PyInstaller spec file was not found: $SpecPath"
}

if (-not (Test-Path -LiteralPath $ResourceSourcePath)) {
    throw "resources directory was not found: $ResourceSourcePath"
}

if (-not (Test-Path -LiteralPath $DictionarySourcePath)) {
    throw "dictionaries directory was not found: $DictionarySourcePath"
}

if (-not (Test-Path -LiteralPath $ConfigSourcePath -PathType Leaf)) {
    throw "config.json was not found: $ConfigSourcePath"
}

if (-not (Test-Path -LiteralPath $ColorPresetsSourcePath -PathType Leaf)) {
    throw "color_presets.json was not found: $ColorPresetsSourcePath"
}

Push-Location $ProjectRoot
try {
    foreach ($PortableName in @($PortableFiles) + @($PortableFolders) + @($ExistingRecoveryFolders)) {
        $ExistingPath = Join-Path $ExistingDistAppPath $PortableName
        if (Test-Path -LiteralPath $ExistingPath) {
            if ($null -eq $PreservedPortableDataPath) {
                $PreservedPortableDataPath = Join-Path ([System.IO.Path]::GetTempPath()) `
                    ("regexpad-build-" + [guid]::NewGuid().ToString("N"))
            }
            Copy-PortableEntry -SourcePath $ExistingPath `
                -DestinationPath (Join-Path $PreservedPortableDataPath $PortableName)
        }
    }

    $OriginalPath = $env:Path
    $OriginalSkipWordPressRuntime = $env:REGEXPAD_SKIP_WORDPRESS_RUNTIME
    $env:Path = (($OriginalPath -split ";") | Where-Object {
            $_ -notmatch "\\\.cache\\codex-runtimes" -and
            $_ -notmatch "\\\.codex\\tmp" -and
            $_ -notmatch "[\\/]WindowsApps[\\/]OpenAI\.CodexPrimaryRuntime\."
        }) -join ";"

    if ($SkipWordPressRuntime) {
        $env:REGEXPAD_SKIP_WORDPRESS_RUNTIME = "1"
    }
    else {
        $env:REGEXPAD_SKIP_WORDPRESS_RUNTIME = "0"
        & $PythonExe -m preview.package_runtime --runtime-root $WordPressRuntimePath
        if ($LASTEXITCODE -ne 0) {
            throw "WordPress runtime preparation failed with exit code $LASTEXITCODE"
        }
    }

    Assert-DistributionNotRunning -AppDirectory $ExistingDistAppPath
    & $PythonExe -m PyInstaller --noconfirm --clean --distpath $DistRoot $SpecPath
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed with exit code $LASTEXITCODE"
    }

    $DistAppPath = Join-Path $DistRoot $AppDistName
    if (-not (Test-Path -LiteralPath $DistAppPath)) {
        throw "PyInstaller dist directory was not found: $DistAppPath"
    }

    $InternalPath = Join-Path $DistAppPath "_internal"
    if (-not (Test-Path -LiteralPath $InternalPath)) {
        throw "PyInstaller _internal directory was not found: $InternalPath"
    }
    Copy-Item -LiteralPath $DeletionListSourcePath -Destination (Join-Path $InternalPath "DELET_ITEMS_LIST.md") -Force

    # Translator が実行時に読む JSON を _internal\resources に配置します。
    Copy-DirectoryFresh `
        -SourcePath $ResourceSourcePath `
        -DestinationPath (Join-Path $InternalPath "resources")

    # Tag insertion and Linter dictionaries are runtime data under _internal.
    Copy-DirectoryFresh `
        -SourcePath $DictionarySourcePath `
        -DestinationPath (Join-Path $InternalPath "dictionaries")

    Assert-JsonFilesCopied `
        -SourcePath $ResourceSourcePath `
        -DestinationPath (Join-Path $InternalPath "resources")
    Assert-JsonFilesCopied `
        -SourcePath $DictionarySourcePath `
        -DestinationPath (Join-Path $InternalPath "dictionaries")

    # Verify every JSON selected by regex-pad.spec, including pseudo-macro,
    # WordPress Linter references and root-level verification records.
    Assert-ProjectJsonFilesBundled `
        -SourceRoot $ProjectRoot `
        -DestinationRoot $InternalPath

    # Existing dist data wins. On a first build, copy local portable data.
    foreach ($PortableName in @($PortableFiles) + @($PortableFolders)) {
        $SourcePath = Join-Path $ProjectRoot $PortableName
        if ($null -ne $PreservedPortableDataPath) {
            $PreservedPath = Join-Path $PreservedPortableDataPath $PortableName
            if (Test-Path -LiteralPath $PreservedPath) {
                $SourcePath = $PreservedPath
            }
        }
        Copy-PortableEntry -SourcePath $SourcePath `
            -DestinationPath (Join-Path $DistAppPath $PortableName)
        if ($PortableName -eq "config.json") {
            Set-PortableProjectPaths -ConfigPath (Join-Path $DistAppPath "config.json") `
                -SourceRoot $ProjectRoot
        }
    }
    foreach ($PortableFileName in @("config.json", "color_presets.json")) {
        $PortableFilePath = Join-Path $DistAppPath $PortableFileName
        if (-not (Test-Path -LiteralPath $PortableFilePath -PathType Leaf)) {
            throw "Portable settings file was not copied beside regex-pad.exe: $PortableFilePath"
        }
    }
    if ($null -ne $PreservedPortableDataPath) {
        foreach ($RecoveryFolder in $ExistingRecoveryFolders) {
            Copy-PortableEntry -SourcePath (Join-Path $PreservedPortableDataPath $RecoveryFolder) `
                -DestinationPath (Join-Path $DistAppPath $RecoveryFolder)
        }
    }

    # Runtime logs are user-owned output. Create an empty portable destination
    # beside the EXE; never copy development logs into a release.
    $LogOutputPath = Join-Path $DistAppPath "logs"
    New-Item -ItemType Directory -Path $LogOutputPath -Force | Out-Null
    if (-not (Test-Path -LiteralPath $LogOutputPath -PathType Container)) {
        throw "Portable log output directory could not be created: $LogOutputPath"
    }

    # 実行時にQIcon等で assets を参照する場合に備えて、assetsも同梱します。
    # assets が無い構成でもビルドを止めないよう、存在する場合だけコピーします。
    if (Test-Path -LiteralPath $AssetSourcePath) {
        Copy-DirectoryFresh `
            -SourcePath $AssetSourcePath `
            -DestinationPath (Join-Path $InternalPath "assets")
    }

    $RequiredTextFile = Join-Path $InternalPath "resources\app_text_en.json"
    if (-not (Test-Path -LiteralPath $RequiredTextFile)) {
        throw "Required resource was not copied: $RequiredTextFile"
    }

    $RequiredBridge = Join-Path $InternalPath "resources\wordpress_preview\bridge.mjs"
    if (-not (Test-Path -LiteralPath $RequiredBridge)) {
        throw "Required WordPress preview bridge was not copied: $RequiredBridge"
    }
    if (-not $SkipWordPressRuntime) {
        $BundledRuntimePath = Join-Path $InternalPath "runtime\wordpress-preview"
        & $PythonExe -m preview.package_runtime --verify --runtime-root $BundledRuntimePath
        if ($LASTEXITCODE -ne 0) {
            throw "Bundled WordPress verification failed with exit code $LASTEXITCODE"
        }
        Write-Host "WordPress preview runtime bundled at: $BundledRuntimePath"
    }

    Copy-ReleaseDocumentation -SourceRoot $ProjectRoot -DestinationRoot $DistAppPath

    Test-FrozenQtImports -AppDirectory $DistAppPath

    Write-Host "Build completed."
    Write-Host "Copied resources to: $(Join-Path $InternalPath 'resources')"
    Write-Host "Copied dictionaries to: $(Join-Path $InternalPath 'dictionaries')"
    Write-Host "Portable settings are beside regex-pad.exe: $DistAppPath"
    Write-Host "Portable logs will be written to: $LogOutputPath"
    Write-Host "Copied release documentation beside regex-pad.exe: $DistAppPath"
    $BuildCompleted = $true

}
finally {
    if ($null -ne $OriginalPath) {
        $env:Path = $OriginalPath
    }
    $env:REGEXPAD_SKIP_WORDPRESS_RUNTIME = $OriginalSkipWordPressRuntime
    if ($null -ne $PreservedPortableDataPath -and (Test-Path -LiteralPath $PreservedPortableDataPath)) {
        $ResolvedPreservedPath = (Resolve-Path -LiteralPath $PreservedPortableDataPath).Path
        $ExpectedTempRoot = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
        if (-not $ResolvedPreservedPath.StartsWith($ExpectedTempRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Unexpected portable backup path: $ResolvedPreservedPath"
        }
        if ($BuildCompleted) {
            Remove-Item -LiteralPath $ResolvedPreservedPath -Recurse -Force
        }
        else {
            Write-Warning "Build did not complete. Portable data backup remains at: $ResolvedPreservedPath"
        }
    }
    Pop-Location
}
