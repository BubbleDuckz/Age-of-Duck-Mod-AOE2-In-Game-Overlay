"""Update I/O and Windows launch bookkeeping, independent of Qt."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
from packaging.version import Version
from update_release import select_update

def start_background(work,success,failure,is_closed=lambda:False):
    def run():
        try:result=work()
        except Exception as exc:
            if not is_closed():failure(str(exc))
        else:
            if not is_closed():success(result)
    thread=threading.Thread(target=run,daemon=True)
    thread.start()
    return thread

def startup_command(frozen, executable, script):
    return subprocess.list2cmdline([executable] if frozen else [executable,str(script)])

def fetch_update(url,current_version,get=None):
    if get is None:
        import requests
        get=requests.get
    response=get(url,timeout=8)
    response.raise_for_status()
    release=response.json()
    result=select_update(release,current_version)
    latest=(release.get('tag_name') or '').removeprefix('v')
    if (not result[0] and latest and not release.get('draft') and not release.get('prerelease')
            and Version(latest)>Version(current_version)):
        raise ValueError('The newer release has no downloadable Windows installer.')
    return result

def download_installer(url,get=None):
    if get is None:
        import requests
        get=requests.get
    handle,path=tempfile.mkstemp(prefix='AgeOfDuckInstaller-',suffix='.exe')
    os.close(handle)
    try:
        with get(url,stream=True,timeout=60) as response:
            response.raise_for_status()
            with open(path,'wb') as output:
                for chunk in response.iter_content(8192):
                    if chunk:output.write(chunk)
        return path
    except Exception:
        Path(path).unlink(missing_ok=True)
        raise

def launch_installer(path,version,marker,shell_execute):
    log=Path(tempfile.gettempdir())/'AgeOfDuck_Install.log'
    params=f'/LOG="{log}" /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS'
    result=shell_execute(None,'runas',str(path),params,None,1)
    if not result or int(result)<=32:
        raise OSError(f'Windows could not start the installer (ShellExecute error {result}).')
    # Launch success is not installation success; the next startup verifies the version.
    try:Path(marker).write_text(json.dumps({'version':version}),encoding='utf-8')
    except OSError:pass

def consume_completed_update(marker,current_version):
    path=Path(marker)
    try:
        data=json.loads(path.read_text(encoding='utf-8'))
        expected=Version(data['version'])
    except (OSError,ValueError,KeyError,TypeError):
        try:path.unlink(missing_ok=True)
        except OSError:pass
        return False
    if Version(current_version)<expected:return False
    try:path.unlink(missing_ok=True)
    except OSError:pass
    return True
