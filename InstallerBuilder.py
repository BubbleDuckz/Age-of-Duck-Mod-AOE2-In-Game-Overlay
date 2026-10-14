import argparse
import ctypes
import os
import subprocess
import sys


APP_ID = "{{8B9A41A8-897B-48DA-967F-D6E4A1F6BB47}"


def show_message(title, message, error=False, quiet=False):
    if quiet:
        print(f"{title}: {message}")
        return
    flags = 0x10 if error else 0x40
    ctypes.windll.user32.MessageBoxW(None, message, title, flags)


def find_inno_compiler():
    candidates = [
        os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Inno Setup 6", "ISCC.exe"),
        os.path.join(os.environ.get("ProgramFiles", ""), "Inno Setup 6", "ISCC.exe"),
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    return None


def release_directory(override=None):
    if override:
        return os.path.abspath(override)
    if getattr(sys, "frozen", False):
        builder_dir = os.path.dirname(sys.executable)
    else:
        builder_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(builder_dir)


def inno_path(path):
    return os.path.abspath(path).replace('"', '""')


def make_script(release_dir, builder_dir):
    version_folder = os.path.basename(os.path.normpath(release_dir))
    version = version_folder[1:] if version_folder.lower().startswith("v") else version_folder
    numeric_version = ".".join((version.split(".") + ["0"] * 4)[:4])
    app_source = os.path.join(release_dir, "AgeOfDuck")
    app_exe = os.path.join(app_source, "AgeOfDuck.exe")
    if not os.path.isfile(app_exe):
        raise FileNotFoundError(f"AgeOfDuck.exe was not found in:\n{app_source}")

    output_dir = os.path.join(builder_dir, "output")
    os.makedirs(output_dir, exist_ok=True)
    script_path = os.path.join(builder_dir, "AgeOfDuckInstaller.iss")
    output_name = f"AgeOfDuck-Setup-v{version}"
    script = f'''#define MyAppName "Age of Duck"
#define MyAppVersion "{version}"
#define MyAppPublisher "BubbleDuckz"
#define MyAppExeName "AgeOfDuck.exe"

[Setup]
AppId={APP_ID}
AppName={{#MyAppName}}
AppVersion={{#MyAppVersion}}
AppPublisher={{#MyAppPublisher}}
DefaultDirName={{autopf}}\\Age of Duck
DefaultGroupName=Age of Duck
DisableProgramGroupPage=yes
OutputDir={inno_path(output_dir)}
OutputBaseFilename={output_name}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile={inno_path(os.path.join(release_dir, "source", "duck.ico"))}
UninstallDisplayIcon={{app}}\\{{#MyAppExeName}}
PrivilegesRequired=admin
VersionInfoVersion={numeric_version}
VersionInfoProductName={{#MyAppName}}
VersionInfoProductVersion={{#MyAppVersion}}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
Source: "{inno_path(app_source)}\\*"; DestDir: "{{app}}"; Excludes: "tc-live-status.json,*.log"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{{autoprograms}}\\Age of Duck"; Filename: "{{app}}\\{{#MyAppExeName}}"
Name: "{{autodesktop}}\\Age of Duck"; Filename: "{{app}}\\{{#MyAppExeName}}"; Tasks: desktopicon

[Run]
Filename: "{{app}}\\{{#MyAppExeName}}"; Description: "Launch Age of Duck"; Flags: nowait postinstall skipifsilent
'''
    with open(script_path, "w", encoding="utf-8") as handle:
        handle.write(script)
    return script_path, os.path.join(output_dir, output_name + ".exe")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-dir")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    quiet = args.quiet
    try:
        compiler = find_inno_compiler()
        if not compiler:
            raise FileNotFoundError(
                "Inno Setup 6 was not found. Install it from jrsoftware.org, then run this builder again."
            )
        release_dir = release_directory(args.release_dir)
        builder_dir = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.getcwd()
        script_path, installer_path = make_script(release_dir, builder_dir)
        result = subprocess.run(
            [compiler, script_path], capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        if result.returncode != 0 or not os.path.isfile(installer_path):
            details = (result.stdout + "\n" + result.stderr).strip()
            raise RuntimeError("Installer compilation failed.\n\n" + details[-3000:])
        show_message(
            "Age of Duck Installer Builder",
            f"Installer created successfully:\n\n{installer_path}\n\nThis setup EXE is ready to upload to GitHub.",
            quiet=quiet,
        )
        return 0
    except Exception as exc:
        show_message("Age of Duck Installer Builder", str(exc), error=True, quiet=quiet)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
