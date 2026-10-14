"""Optional build-order overlay and local Windows speech, driven by shared captures."""
import hashlib,json,os,shutil,subprocess,time,wave
from pathlib import Path
from PyQt5.QtCore import Qt,QTimer,QPoint,pyqtSignal
from PyQt5.QtGui import QCursor,QFont,QColor,QPainter,QPen,QLinearGradient
from PyQt5.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QDialog,QListWidget,QMessageBox,QCheckBox,QApplication,QGraphicsDropShadowEffect,QFrame
from build_order_core import load_order,Progress
from tc_reminder.voice import RepeatingVoice
from tc_reminder import native
from screen_placement import visible_position
from build_panel import BuildPanel

class SpokenPrompt(QWidget):
 """Large raid-style cue, visible only during speech; never accepts input."""
 def __init__(self,scale):
  super().__init__(None,Qt.Tool|Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint|Qt.WindowDoesNotAcceptFocus)
  self.setWindowTitle('Age of Duck — Spoken instruction')
  self.setAttribute(Qt.WA_ShowWithoutActivating);self.setAttribute(Qt.WA_TranslucentBackground);self.setAttribute(Qt.WA_TransparentForMouseEvents)
  layout=QVBoxLayout(self);layout.setContentsMargins(18,14,18,14)
  self.label=QLabel();self.label.setTextFormat(Qt.PlainText);self.label.setWordWrap(True);self.label.setAlignment(Qt.AlignCenter)
  self.label.setStyleSheet('color:#fff0bc;background:transparent;')
  shadow=QGraphicsDropShadowEffect(self.label);shadow.setBlurRadius(9);shadow.setOffset(0,2);shadow.setColor(QColor(0,0,0,245));self.label.setGraphicsEffect(shadow)
  layout.addWidget(self.label);self.set_scale(scale)
  self.hwnd=int(self.winId());native.u.SetWindowLongPtrW(self.hwnd,-20,native.u.GetWindowLongPtrW(self.hwnd,-20)|0x80000|0x20|0x80|0x08000000)
 def set_scale(self,scale):
  self.scale=scale;self.label.setFont(QFont('Segoe UI',max(18,round(30*scale)),QFont.Bold))
 def present(self,game,text):
  l,t,r,b=game[2];ratio=self.devicePixelRatioF()
  self.setFixedWidth(max(220,min(round(950*self.scale),round((r-l)*.64/ratio))))
  self.label.setText(text);self.adjustSize();self.show()
  ratio=self.devicePixelRatioF();w=round(self.width()*ratio);h=round(self.height()*ratio)
  native.show_overlay(self.hwnd,l+(r-l-w)//2,t+max(0,(b-t)//4-h//2),w,h)

class BuildOrders:
 def __init__(self,app,main,tc,app_data,assets):
  self.app=app;self.main=main;self.tc=tc;self.assets=Path(assets);self.folder=Path(app_data)/'Build Orders';self.folder.mkdir(parents=True,exist_ok=True)
  for p in (self.assets/'BuildOrders').glob('*'):
   if p.is_file() and not (self.folder/p.name).exists():shutil.copy2(p,self.folder/p.name)
  self.pref_file=Path(app_data)/'build_orders_settings.json'
  try:self.prefs=json.loads(self.pref_file.read_text())
  except (OSError,ValueError):self.prefs={}
  self.view_visible=bool(self.prefs.get('view_visible',True));self.enabled=bool(self.prefs.get('enabled',False));self.muted=tc.mute.isChecked();self.order=None;self.progress=None;self.process=None;self.audio_busy=False;self.current_audio=None;self.deadline=None;self.last_frame=0;self.in_match=False;self.safe=False;self.count=None;self.session=None;self.match_id=None;self.status='Select a build order';self.voice=RepeatingVoice('');self.cache=None
  if not self.prefs.get('flow_list_layout'):
   self.prefs.pop('position',None);self.prefs['flow_list_layout']=True;self.save()
  self.cue_text='';self.cue_until=0;self.focus_hold_until=0
  self.audio_checkbox=None;self.enabled_checkbox=None
  # The guide and the Idle / Housed window share their own size, independent of the main overlay.
  self.scale=getattr(tc,'panel_scale',main.scale_factor)
  self.panel=BuildPanel(self);self.spoken=SpokenPrompt(self.scale)
  (getattr(tc,'panel_scale_changed',None) or main.scale_changed).connect(self.apply_scale)
  self.tc.mute.toggled.connect(self.set_muted)
  self.tc.observer_enabled=self.enabled;self.tc.build_orders=self;self.tc.frame_observed.connect(self.observe)
  selected=self.prefs.get('selected','')
  if isinstance(selected,str) and Path(selected).name==selected and (self.folder/selected).is_file():
   try:self.load(self.folder/selected)
   except (ValueError,OSError):self.status='Saved build order cannot be loaded. Select another.'
  self.timer=QTimer();self.timer.timeout.connect(self.tick);self.timer.start(100);app.aboutToQuit.connect(self.close)
 def apply_scale(self,value):
  self.scale=value;self.panel.set_scale(value);self.spoken.set_scale(value)
 def change_panel_scale(self,direction):
  if hasattr(self.tc,'change_panel_scale'):self.tc.change_panel_scale(direction)
  elif direction>0:self.main.increase_scale()
  else:self.main.decrease_scale()
 def save(self):
  self.prefs.update(enabled=self.enabled,muted=self.muted);self.pref_file.write_text(json.dumps(self.prefs,indent=2))
 def set_enabled(self,value):
  self.enabled=bool(value);self.tc.observer_enabled=self.enabled;self.save()
  if not self.enabled:self.pause_audio();self.panel.hide()
 def set_view_visible(self,value,game=None):
  self.view_visible=bool(value);self.prefs['view_visible']=self.view_visible;self.save()
  if not self.view_visible:self.panel.hide();self.spoken.hide()
  elif self.enabled and self.in_match:
   game=game or native.foreground_game()
   if game and self.session==game[1]:
    self.panel.place();self.panel.show();self.panel.repaint()
 def toggle_mute(self):self.tc.mute.toggle()
 def set_muted(self,value):
  self.muted=bool(value);self.pause_audio();self.save()
  if self.audio_checkbox:
   self.audio_checkbox.blockSignals(True);self.audio_checkbox.setChecked(not self.muted);self.audio_checkbox.blockSignals(False)
 def tray_controls(self,menu):
  menu.addSeparator();menu.addAction('Select build order…',lambda:QTimer.singleShot(0,self.select_dialog))
  menu.addAction('Open build orders folder',self.open_folder)
 def open_folder(self):os.startfile(str(self.folder))
 def settings_controls(self,layout):
  label=QLabel('Interactive Build Orders');label.setStyleSheet('font-weight:600');layout.addWidget(label)
  enabled=QCheckBox('Enable build-order overlay and cues');self.enabled_checkbox=enabled;enabled.setChecked(self.enabled);enabled.toggled.connect(self.set_enabled);layout.addWidget(enabled)
  audio=QCheckBox('Enable audio for build orders and TC / housing reminders');self.audio_checkbox=audio;audio.setChecked(not self.muted)
  def change_audio(value):
   if value==self.muted:self.toggle_mute()
  audio.toggled.connect(change_audio);layout.addWidget(audio)
  row=QHBoxLayout();select=QPushButton('Select build order');folder=QPushButton('Open build orders folder');select.clicked.connect(self.select_dialog);folder.clicked.connect(self.open_folder);row.addWidget(select);row.addWidget(folder);layout.addLayout(row)
 def select_dialog(self):
  if getattr(self,'selector',None) is not None and self.selector.isVisible():
   self.selector.raise_();self.selector.activateWindow();return
  dialog=QDialog();self.selector=dialog;dialog.setWindowTitle('Select build order');dialog.setWindowFlags(dialog.windowFlags()|Qt.WindowStaysOnTopHint);dialog.resize(480,330)
  layout=QVBoxLayout(dialog);layout.addWidget(QLabel('Add .json files to your Build Orders folder, then reopen this list.'))
  listing=QListWidget();paths=[]
  for path in sorted(self.folder.glob('*.json')):
   try:order=load_order(path);text=order.name+' — '+path.name
   except (ValueError,OSError) as e:text=path.name+' — invalid: '+str(e)
   listing.addItem(text);paths.append(path)
  layout.addWidget(listing);buttons=QHBoxLayout();folder=QPushButton('Open folder');folder.clicked.connect(self.open_folder);use=QPushButton('Use build order');buttons.addWidget(folder);buttons.addWidget(use);layout.addLayout(buttons)
  def choose():
   if listing.currentRow()<0:return
   try:self.load(paths[listing.currentRow()])
   except (OSError,ValueError) as e:QMessageBox.warning(dialog,'Build order',str(e));return
   dialog.accept()
  use.clicked.connect(choose);listing.itemDoubleClicked.connect(lambda _item:choose());dialog.setWindowModality(Qt.NonModal);dialog.show();dialog.raise_();dialog.activateWindow()
 def load(self,path):
  order=load_order(path);self.pause_audio();self.voice.reset();self.order=order;self.progress=Progress(order);self.prefs['selected']=Path(path).name;self.save();self.status='Waiting for villager count'
  if self.process and self.process.poll() is None:self.process.kill()
  payload=[dict(index=i,text=s.text) for i,s in enumerate(order.steps)];key=hashlib.sha256(json.dumps(payload).encode()).hexdigest()[:24]
  self.cache=self.folder/'.voice-cache'/key;self.cache.mkdir(parents=True,exist_ok=True);manifest=self.cache/'speech.json';manifest.write_text(json.dumps(payload),encoding='utf-8')
  if not all((self.cache/f'{i}.wav').is_file() for i in range(len(payload))):
   script=(self.assets/'build_order_voice.ps1').read_text(encoding='utf-8-sig').split('\n',1)[1]
   command='$Manifest=$env:AGEOFDUCK_SPEECH_MANIFEST; $Output=$env:AGEOFDUCK_SPEECH_OUTPUT; '+script
   env=os.environ.copy();env.update(AGEOFDUCK_SPEECH_MANIFEST=str(manifest),AGEOFDUCK_SPEECH_OUTPUT=str(self.cache))
   with (self.cache/'generation.log').open('w') as log:
    self.process=subprocess.Popen(['powershell.exe','-NoProfile','-NonInteractive','-Command',command],env=env,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
  else:self.process=None
 def restart(self):
  self.pause_audio()
  self.voice.reset()
  if self.progress:self.progress.reset()
  self.status='New game — waiting for villager count'
 def pause_audio(self,clear_visual=True):
  self.voice.stop();self.current_audio=None;self.deadline=None;self.audio_busy=False
  if clear_visual:self.cue_text='';self.cue_until=0;self.spoken.hide()
 @property
 def speech_priority(self):
  # Reserve the shared sound channel before the next UI timer starts a cue.
  return bool(self.enabled and not self.muted and self.safe and time.monotonic()-self.last_frame<1.25 and self.progress and (self.progress.current or self.progress.pending))
 def observe(self,game,result,stamp):
  session=game[1] if game else None
  match_id=result.get('match_id') if result else None
  changed=(self.match_id is not None and match_id is not None and match_id!=self.match_id)
  process_changed=bool(session and self.session and session!=self.session)
  if changed or process_changed or (result and result.get('new_match')):self.restart()
  if match_id is not None:self.match_id=match_id
  if session:self.session=session
  if not self.enabled:return
  self.last_frame=stamp
  self.in_match=bool(game and result and ((result.get('gameplay') and (result.get('advancing') or time.monotonic()<self.focus_hold_until)) or result.get('context')=='pause'))
  if not self.in_match:self.panel.hide()
  self.safe=bool(game and result and result.get('gameplay') and result.get('advancing') and not result.get('match_pending'))
  self.count=result.get('villagers') if result else None
  if self.progress:self.progress.observe(self.count,self.safe and self.count is not None)
  if not self.safe:self.pause_audio()
 def tick(self):
  if not self.enabled:self.panel.hide();return
  game=native.foreground_game()
  if not game:self.pause_audio();self.panel.hide();return
  now=time.monotonic();companion=native.companion_focused()
  if companion:self.focus_hold_until=now+2.5
  if not self.in_match or game[1]!=self.session or (not companion and now-self.last_frame>=1.25 and now>=self.focus_hold_until):
   self.pause_audio();self.panel.hide();return
  safe=self.safe and not companion and now-self.last_frame<1.25
  if not safe:self.pause_audio()
  self.panel.place();self.panel.setVisible(self.view_visible)
  self.panel.title.setText(self.order.name if self.order else 'No build order selected')
  self.panel.count.setText('Villagers '+('?' if self.count is None else str(self.count)))
  if not self.progress:self.panel.instruction.setText('Choose a JSON build order to begin.');return
  if safe:
   if self.deadline is not None and now>=self.deadline:
    self.progress.complete();self.pause_audio(clear_visual=False)
   step=self.progress.begin()
   if step and self.deadline is None:
    index=self.order.steps.index(step);clip=self.cache/f'{index}.wav'
    if self.muted:self.deadline=now+(10 if '.' in step.id else 3)
    elif clip.exists() and (not self.process or self.process.poll() is not None):
     try:
      with wave.open(str(clip),'rb') as f:duration=f.getnframes()/f.getframerate()
      self.tc.voice.stop();self.audio_busy=True;self.voice.path=str(clip);self.voice.update(True,now,event=(self.prefs.get('selected'),step.id));self.deadline=now+max(duration+.08,10 if '.' in step.id else 0)
      self.cue_text=step.text;self.cue_until=now+duration+3
     except (OSError,wave.Error):self.status='Voice unavailable — use Mute for visual-only steps'
    elif self.process and self.process.poll() is None:self.status='Preparing voice…'
    else:self.status='Voice unavailable — use Mute for visual-only steps'
  self.panel.show_progress(self.progress,safe)
  step=self.progress.current
  speaking=bool(safe and not self.muted and self.audio_busy and step and self.voice.finishes is not None and now<self.voice.finishes)
  if self.view_visible and safe and not self.muted and self.cue_text and now<self.cue_until:self.spoken.present(game,self.cue_text)
  else:self.spoken.hide()
  extra=self.status if step and self.deadline is None and safe else ('Playing instruction' if speaking else 'Follow this instruction' if step else 'Waiting for villager '+str(self.progress.next_step().villagers) if self.progress.next_step() else 'Build order complete')
  if not safe:extra='Paused — waiting for running gameplay.'
  self.panel.next.setText(extra);self.panel.adjustSize()
 def close(self):
  self.timer.stop();self.pause_audio();self.panel.close();self.spoken.close()
  if getattr(self,'selector',None) is not None:self.selector.close()
  if self.process and self.process.poll() is None:self.process.kill()

