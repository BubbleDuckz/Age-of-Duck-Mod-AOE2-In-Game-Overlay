"""Keep network work off the GUI thread; dialogs and elevation stay on it."""
import ctypes
from ctypes import wintypes
from PyQt5.QtCore import QObject,pyqtSignal,pyqtSlot
from PyQt5.QtWidgets import QMessageBox,QSystemTrayIcon
from update_io import fetch_update,download_installer,launch_installer,start_background

class UpdateController(QObject):
    checked=pyqtSignal(object)
    downloaded=pyqtSignal(str)
    failed=pyqtSignal(str)
    def __init__(self,app,tray,action,parent_window,url,current_version,marker):
        super().__init__(app)
        self.tray=tray;self.action=action;self.parent_window=parent_window
        self.url=url;self.current_version=current_version;self.marker=marker
        self.busy=False;self.closed=False;self.version=None
        self.checked.connect(self.on_checked);self.downloaded.connect(self.on_downloaded);self.failed.connect(self.on_failed)
        app.aboutToQuit.connect(self.close)
    def close(self):self.closed=True
    def background(self,work,signal):
        return start_background(work,signal.emit,self.failed.emit,lambda:self.closed)
    def finish(self):self.busy=False;self.action.setEnabled(True)
    def check(self):
        if self.busy or self.closed:return
        self.busy=True;self.action.setEnabled(False)
        self.background(lambda:fetch_update(self.url,self.current_version),self.checked)
    @pyqtSlot(object)
    def on_checked(self,result):
        version,url=result
        if version is None:
            self.finish();QMessageBox.information(self.parent_window(),'No Update','You have the latest version.');return
        answer=QMessageBox.question(self.parent_window(),'Update Available',f'Version {version} is available. Install now?')
        if answer!=QMessageBox.Yes:self.finish();return
        self.version=version
        self.tray.showMessage('Updating','Downloading installer...',QSystemTrayIcon.Information)
        self.background(lambda:download_installer(url),self.downloaded)
    @pyqtSlot(str)
    def on_downloaded(self,path):
        execute=ctypes.windll.shell32.ShellExecuteW
        execute.argtypes=[wintypes.HWND,wintypes.LPCWSTR,wintypes.LPCWSTR,wintypes.LPCWSTR,wintypes.LPCWSTR,ctypes.c_int]
        execute.restype=ctypes.c_void_p
        try:launch_installer(path,self.version,self.marker,execute)
        except Exception as exc:self.on_failed(str(exc));return
        self.finish()
        self.tray.showMessage('Updating','Installer started. Complete its prompts to update Age of Duck.',QSystemTrayIcon.Information)
    @pyqtSlot(str)
    def on_failed(self,message):
        self.finish();self.tray.showMessage('Update Error',message,QSystemTrayIcon.Critical)
