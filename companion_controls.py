"""Compact in-game controls for optional companion overlays and voice volume."""
import json,time
from PyQt5.QtCore import Qt,QTimer,QEasingCurve,QVariantAnimation,QPointF,QRectF
from PyQt5.QtGui import QFont,QPainter,QPen,QColor,QPolygonF,QLinearGradient,QBrush
from PyQt5.QtWidgets import QWidget,QHBoxLayout,QVBoxLayout,QPushButton,QLabel,QFrame,QSlider
from tc_reminder.voice import RepeatingVoice
from tc_reminder import native
from ui_bits import StatusLightButton,SpeakerButton

class ChevronButton(QPushButton):
    """Little triangle on the divider line: red ▲ folds the controls away, green ▼ brings them back."""
    RED = QColor('#F87171')
    GREEN = QColor('#4ADE80')

    def __init__(self, parent=None):
        super().__init__(parent);self.progress=1.0;self.setFixedSize(30,16);self.setFlat(True)
    def sizeHint(self):return self.size()
    def minimumSizeHint(self):return self.size()
    def set_progress(self,value):
        self.progress=value;self.update()
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing)
        t=max(0.0,min(1.0,self.progress))  # 1 = open (red, up), 0 = closed (green, down)
        mix=lambda a,b:int(a*t+b*(1-t))
        color=QColor(mix(self.RED.red(),self.GREEN.red()),mix(self.RED.green(),self.GREEN.green()),mix(self.RED.blue(),self.GREEN.blue()))
        hover=self.underMouse()
        pill=QRectF(self.rect()).adjusted(1,1,-1,-1)
        p.setPen(QPen(QColor(color.red(),color.green(),color.blue(),160 if hover else 90),1))
        p.setBrush(QColor(color.red(),color.green(),color.blue(),55 if hover else 28))
        p.drawRoundedRect(pill,pill.height()/2,pill.height()/2)
        p.translate(self.width()/2,self.height()/2);p.rotate(180*(1-t))
        p.setPen(Qt.NoPen);p.setBrush(color)
        p.drawPolygon(QPolygonF([QPointF(-5.5,2.8),QPointF(5.5,2.8),QPointF(0,-3.6)]))

class Rule(QWidget):
    """One-pixel line that fades out towards its outer end."""
    def __init__(self,fade_left,parent=None):
        super().__init__(parent);self.fade_left=fade_left;self.setFixedHeight(16)
    def paintEvent(self,event):
        p=QPainter(self);w=self.width();g=QLinearGradient(0,0,w,0)
        near,far=QColor(255,255,255,95),QColor(255,255,255,0)
        g.setColorAt(0,far if self.fade_left else near);g.setColorAt(1,near if self.fade_left else far)
        p.setPen(QPen(QBrush(g),1));p.drawLine(0,self.height()//2,w,self.height()//2)

SLIDER_STYLE=('QSlider::groove:horizontal{height:4px;background:rgba(255,255,255,0.16);border-radius:2px;}'
 'QSlider::sub-page:horizontal{background:#A7F3D0;border-radius:2px;}'
 'QSlider::handle:horizontal{background:#EEF6FF;border:1px solid rgba(0,0,0,0.35);width:12px;height:12px;margin:-5px 0;border-radius:7px;}'
 'QSlider::handle:horizontal:hover{background:#FFFFFF;}')

class CompanionControls(QWidget):
 def __init__(self,main,build,tc):
  super().__init__(main);self.build=build;self.tc=tc;self.main=main;self.control_game=None
  self.setStyleSheet('QPushButton:disabled {color:#65717d;background:rgba(255,255,255,0.025);border:1px solid rgba(255,255,255,0.06);}')
  self.volume=max(0,min(100,int(tc.prefs.get('voice_volume',100))))
  RepeatingVoice.volume_percent=self.volume
  root=QVBoxLayout(self);root.setContentsMargins(0,0,0,0);root.setSpacing(2)
  # Header: a hairline with a small red/green triangle in the middle; it folds the controls away.
  self.header=QWidget();self.header.setObjectName('controlsHeader')
  head=QHBoxLayout(self.header);head.setContentsMargins(0,0,0,0);head.setSpacing(6)
  self.chevron=ChevronButton();self.chevron.setCursor(Qt.PointingHandCursor);self.chevron.setStyleSheet('border:none;background:transparent;')
  head.addWidget(Rule(True),1);head.addWidget(self.chevron);head.addWidget(Rule(False),1)
  self.chevron.clicked.connect(self.toggle_expanded)
  root.addWidget(self.header)
  self.body=QWidget();root.addWidget(self.body)
  layout=QVBoxLayout(self.body);layout.setContentsMargins(0,0,0,0);layout.setSpacing(5)
  self.expanded=bool(tc.prefs.get('controls_expanded',True));self._anim=None
  self.body.setVisible(self.expanded);self.chevron.set_progress(1.0 if self.expanded else 0.0)
  self._update_toggle_text()
  # Row 1: build-order picker on the left, then one status-light switch per in-game window.
  row=QHBoxLayout();row.setSpacing(5)
  self.select=QPushButton('Select build order');self.guide=StatusLightButton('Build Order');self.idle=StatusLightButton('Idle / Housed')
  row.addWidget(self.select,3);row.addWidget(self.guide,2);row.addWidget(self.idle,2)
  self.guide.pressed.connect(self.toggle_guide);self.idle.pressed.connect(self.toggle_idle)
  self.select.clicked.connect(lambda:QTimer.singleShot(0,build.select_dialog));self.select.setToolTip('Choose which build order to follow')
  layout.addLayout(row)
  # Voice volume lives in Settings: speaker (click to mute), slider and percentage.
  self.volume_row=QWidget();audio=QHBoxLayout(self.volume_row);audio.setSpacing(8);audio.setContentsMargins(0,0,0,0)
  self.speaker=SpeakerButton();self.speaker.clicked.connect(self.toggle_mute)
  self.slider=QSlider(Qt.Horizontal);self.slider.setRange(0,100);self.slider.setSingleStep(5);self.slider.setPageStep(10);self.slider.setValue(self.volume)
  self.slider.setFocusPolicy(Qt.NoFocus);self.slider.setStyleSheet(SLIDER_STYLE)
  self.slider.setToolTip('Voice volume for build orders and reminders');self.speaker.setToolTip('Click to mute / unmute all reminder voices')
  self.level=QLabel();self.level.setAlignment(Qt.AlignRight|Qt.AlignVCenter);self.level.setStyleSheet('color:#9FB3C8;')
  audio.addWidget(self.speaker);audio.addWidget(self.slider,1);audio.addWidget(self.level)
  self.level.setFixedWidth(44)
  self.save_timer=QTimer(self);self.save_timer.setSingleShot(True);self.save_timer.setInterval(250);self.save_timer.timeout.connect(self.save_volume)
  self.slider.valueChanged.connect(self.set_volume);self.tc.mute.toggled.connect(self.refresh_labels)
  for b in self.findChildren(QPushButton):b.setFocusPolicy(Qt.NoFocus);b.setCursor(Qt.PointingHandCursor)
  main.scale_changed.connect(self.set_scale);self.set_scale(main.scale_factor);self.refresh()
  self.availability_timer=QTimer(self);self.availability_timer.timeout.connect(self.refresh);self.availability_timer.start(150)
  tc.enabled.toggled.connect(self.refresh)
  if build.enabled_checkbox:build.enabled_checkbox.toggled.connect(self.refresh)
  # Controls must not take keyboard focus away from the game.
  main.setAttribute(Qt.WA_ShowWithoutActivating)
  for button in main.findChildren(QPushButton):button.setFocusPolicy(Qt.NoFocus)
 def _update_toggle_text(self):
  self.chevron.setToolTip('Hide build order and voice controls' if self.expanded else 'Show build order and voice controls')
 def toggle_expanded(self):
  self.expanded=not self.expanded
  self.tc.prefs['controls_expanded']=self.expanded
  try:self.tc.settings_path.write_text(json.dumps(self.tc.prefs))
  except Exception:pass
  self._update_toggle_text()
  if self._anim:self._anim.stop()
  body=self.body;body.setMaximumHeight(16777215);body.setVisible(True)
  self.layout().activate();full=body.sizeHint().height()
  anim=QVariantAnimation(self);anim.setDuration(200);anim.setEasingCurve(QEasingCurve.InOutCubic)
  anim.setStartValue(0 if self.expanded else min(body.height(),full) or full);anim.setEndValue(full if self.expanded else 0)
  start=self.chevron.progress;end=1.0 if self.expanded else 0.0
  def step(value):
   body.setMaximumHeight(int(value));self.chevron.set_progress(start+(end-start)*(anim.currentTime()/max(1,anim.duration())))
   self.main.adjustSize()
  def done():
   self.chevron.set_progress(end)
   if self.expanded:body.setMaximumHeight(16777215)
   else:body.hide()
   self.main.adjustSize()
  anim.valueChanged.connect(step);anim.finished.connect(done);self._anim=anim;anim.start()
 def set_scale(self,scale):
  self.setFont(QFont('Segoe UI',max(8,round(9*scale))))
  self.chevron.setFixedSize(round(30*scale),round(16*scale))
  self.guide.updateGeometry();self.idle.updateGeometry();self.main.adjustSize()
 def refresh(self,*args):
  game=native.foreground_game()
  if game:self.control_game=game
  guide_available=bool(game and self.tc.owns_capture and self.build.enabled and self.build.in_match and self.build.session==game[1])
  idle_available=bool(game and self.tc.owns_capture and self.tc.enabled.isChecked() and self.tc.match_session==game[1] and self.tc.latest_state.get('context') in ('gameplay','pause','menu'))
  for button,available,name,shown in [(self.guide,guide_available,'build-order guide',self.build.enabled and self.build.view_visible),(self.idle,idle_available,'Idle / Housed window',self.tc.enabled.isChecked() and self.tc.view_visible)]:
   if not button.isDown():button.setEnabled(available)
   button.setCursor(Qt.PointingHandCursor if available else Qt.ArrowCursor)
   button.setToolTip(('Green = showing. Click to '+('hide' if shown else 'show')+' the '+name+'. Audio keeps playing.') if available else 'The '+name+' is unavailable outside a detected game or while its feature is disabled.')
  self.refresh_labels()
 def refresh_labels(self,*args):
  self.guide.set_light(self.build.enabled and self.build.view_visible)
  self.idle.set_light(self.tc.enabled.isChecked() and self.tc.view_visible)
  self.level.setText(str(self.volume)+'%')
  self.speaker.set_state(self.tc.mute.isChecked(),self.volume)
 def toggle_guide(self):
  # A press on an enabled control is an explicit choice. Focus may change
  # before release; never re-check capture availability and discard that choice.
  if not self.guide.isEnabled():return
  self.build.set_view_visible(not self.build.view_visible,game=self.control_game)
  self.refresh_labels();self.repaint()
 def toggle_idle(self):
  if not self.idle.isEnabled():return
  self.tc.set_view_visible(not self.tc.view_visible,game=self.control_game)
  self.refresh_labels();self.repaint()
 def set_volume(self,value):
  self.volume=max(0,min(100,int(value)));RepeatingVoice.volume_percent=self.volume
  self.tc.prefs['voice_volume']=self.volume;self.refresh_labels();self.save_timer.start()
 def save_volume(self):
  try:self.tc.settings_path.write_text(json.dumps(self.tc.prefs))
  except OSError:pass
 def toggle_mute(self):self.tc.mute.toggle()
