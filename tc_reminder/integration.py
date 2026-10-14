"""Optional TC/housing panel owned by the Age of Duck application."""
import json
import logging
import time
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from PyQt5.QtCore import Qt,QTimer,QObject,pyqtSignal
from PyQt5.QtWidgets import QWidget,QLabel,QVBoxLayout,QAction
from . import native
from .paths import ROOT
from .vision import Detector
from .selection import SelectionFinder
from .core import Reminder,Observation
from .runtime import SelectionEvidence,MatchContinuity,frame_is_current
from .population import StableHousingReminder,BuildHouseEvents
from .voice import RepeatingVoice,choose_cue

from .panel import TCPanel
from preference_io import read_object

class TCController(QObject):
    frame_observed=pyqtSignal(object,object,float)
    panel_scale_changed=pyqtSignal(float)
    def __init__(self,app,menu,settings_path,main_overlay=None):
        super().__init__(app)
        self.observer_enabled=False;self.build_orders=None
        from villager_reader import VillagerReader
        self.villager_reader=VillagerReader()
        self.settings_path=Path(settings_path)
        self.diagnostics=Path(sys.executable).parent/'tc-live-status.json' if getattr(sys,'frozen',False) else ROOT/'tc-live-status.json'
        self.last_diagnostic=0
        self.latest_state={}
        self.error=''
        self.prefs=read_object(self.settings_path)
        self.view_visible=bool(self.prefs.get('view_visible',True))
        self.panel=TCPanel();self.panel.offset=self.prefs.get('position');self.main_overlay=main_overlay
        self.panel.position_changed.connect(self.save_position)
        # Idle / Housed and the build-order window share one size; the main overlay keeps its own.
        fallback=main_overlay.scale_factor if main_overlay is not None else 1.0
        try:self.panel_scale=min(1.8,max(.75,float(self.prefs.get('panel_scale',fallback))))
        except (TypeError,ValueError):self.panel_scale=fallback
        self.panel.set_scale(self.panel_scale)
        self.panel_scale_changed.connect(self.panel.set_scale)
        self.panel.scale_requested.connect(self.change_panel_scale)
        self.detector=Detector();self.reminder=Reminder()
        # Counts selected Town Centres at any resolution / interface size (bell + tile search).
        self.selection_finder=SelectionFinder()
        # Optional user-drawn HUD areas replace the built-in screen layout.
        from hud_regions import HudRegions
        self.regions=HudRegions(self.settings_path.parent/'hud_regions.json');self.detector.regions=self.regions
        try:self.manual_tcs=max(0,min(20,int(self.prefs.get('manual_tcs',0))))
        except (TypeError,ValueError):self.manual_tcs=0
        self.selection=SelectionEvidence();self.continuity=MatchContinuity();self.match_session=None;self.match_generation=0;self.housing=StableHousingReminder()
        self.voice=RepeatingVoice(ROOT/'idle.wav');self.voice_active=False
        self.build_events=BuildHouseEvents();self.voice_event=None
        self.housing_state="";self.idle_alert=False;self.blocked_since=None;self.blocked_last=0;self.last_villager_read=object()
        self.executor=ThreadPoolExecutor(max_workers=1);self.future=None;self.epoch=0
        self.last_frame=0;self.last_good=0;self.outside_since=None;self.closed=False;self.was_game=False
        self.owns_capture=native.single_instance()
        self.enabled=QAction('TC / housing reminders',self);self.enabled.setCheckable(True)
        self.enabled.setChecked(self.prefs.get('enabled',True));self.enabled.setEnabled(self.owns_capture)
        if not self.owns_capture:self.enabled.setText('TC reminders: close standalone app and restart Age of Duck')
        self.mute=QAction('Mute all reminder voices',self);self.mute.setCheckable(True);self.mute.setChecked(self.prefs.get('mute',False))
        self.enabled.toggled.connect(self.changed);self.mute.toggled.connect(self.changed)
        self.panel.mute_requested.connect(self.mute.trigger)
        menu.addSeparator();menu.addAction(self.enabled);menu.addAction(self.mute)
        self.timer=QTimer(self);self.timer.timeout.connect(self.tick);self.timer.start(50)
        app.aboutToQuit.connect(self.close)
    def changed(self):
        self.prefs.update(enabled=self.enabled.isChecked(),mute=self.mute.isChecked())
        try:self.settings_path.write_text(json.dumps(self.prefs))
        except OSError:logging.exception('Cannot save TC preferences')
        self.invalidate()
    def log_villagers(self,now,read,step):
        """Rolling record of villager-counter reads (changes only), for diagnosing mis-cues."""
        if read==self.last_villager_read:return
        self.last_villager_read=read
        path=self.settings_path.parent/'villager_reads.log'
        try:
            if path.exists() and path.stat().st_size>200_000:
                path.write_text(''.join(path.read_text(encoding='utf-8').splitlines(True)[-500:]),encoding='utf-8')
            with path.open('a',encoding='utf-8') as handle:
                handle.write(f"{time.strftime('%H:%M:%S')} read={read} step={step}\n")
        except OSError:pass
    def reload_regions(self):
        self.regions.load();self.detector.flash.reset();self.invalidate()
    def set_manual_tcs(self,value):
        self.manual_tcs=max(0,min(20,int(value)));self.prefs['manual_tcs']=self.manual_tcs
        try:self.settings_path.write_text(json.dumps(self.prefs))
        except OSError:logging.exception('Cannot save TC count')
        if self.manual_tcs:self.reminder.total=self.manual_tcs
        else:self.reminder.total=None
    def queue_blocked(self,blocked,now):
        """'Housed' once queue icons have shown a housed block for 1 s, bridging 2 s of flicker."""
        if blocked:
            if self.blocked_since is None:self.blocked_since=now
            self.blocked_last=now
        elif self.blocked_since is not None and now-self.blocked_last>2.0:self.blocked_since=None
        if self.blocked_since is not None and now-self.blocked_last<=2.0 and now-self.blocked_since>=1.0:return 'Housed'
        return ''
    def change_panel_scale(self,direction):
        value=self.panel_scale*1.1 if direction>0 else self.panel_scale/1.1
        self.panel_scale=min(1.8,max(.75,round(value,3)));self.prefs['panel_scale']=self.panel_scale
        try:self.settings_path.write_text(json.dumps(self.prefs))
        except OSError:logging.exception('Cannot save panel size')
        self.panel_scale_changed.emit(self.panel_scale)
    def set_view_visible(self,value,game=None):
        self.view_visible=bool(value);self.prefs['view_visible']=self.view_visible
        self.settings_path.write_text(json.dumps(self.prefs))
        self.sync_view(game or native.foreground_game(),self.enabled.isChecked() and self.owns_capture)
    def sync_view(self,game,enabled):
        """Keep this panel independent of capture latency and the guide window."""
        visible=bool(game and enabled and self.view_visible and self.match_session==game[1]
                     and self.latest_state.get("context") in ("gameplay","pause","menu"))
        if visible:
            self.panel.game=game
            self.panel.show()
            self.panel.place()
        else:self.panel.hide()
    def save_position(self,position):
        self.prefs['position']=position
        try:self.settings_path.write_text(json.dumps(self.prefs))
        except OSError:logging.exception('Cannot save TC position')
    def invalidate(self):
        self.epoch+=1;self.voice_active=False;self.housing_state="";self.idle_alert=False;self.blocked_since=None;self.voice.stop();self.panel.hide()
        self.reminder.shortfall_since=None;self.selection=SelectionEvidence();self.housing=StableHousingReminder()
    def capture_frame(self,game,epoch):
        captured_at=time.monotonic();raw=native.capture(game)
        image=raw
        # Read the selection from the untouched frame: it works on any size, and user-drawn
        # HUD areas (which only remap the top-left readouts) do not hide it.
        selected=self.selection_finder.read(raw,captured_at) if raw is not None else None
        if image is not None:image=self.detector.normalize_frame(image)
        result=self.detector.analyze(image,.86,captured_at) if image is not None else None
        if result is not None and result.get('gameplay'):
            result['selected_tcs']=selected
        if result is not None and image is not None and self.observer_enabled:result["villagers"]=self.villager_reader.read(image)
        return game,epoch,captured_at,result
    def tick(self):
        if self.closed:return
        try:self._tick()
        except Exception:
            logging.exception('TC reminder failed safely');self.error=__import__('traceback').format_exc();self.invalidate()
    def _tick(self):
        now=time.monotonic();game=native.foreground_game()
        enabled=self.enabled.isChecked() and self.owns_capture
        capture_enabled=(self.enabled.isChecked() or self.observer_enabled) and self.owns_capture
        if game and native.companion_focused():
            # Settings/selector windows must not erase the last gameplay view.
            # Do not capture through dialogs or announce stale game observations.
            self.voice.stop()
            self.sync_view(game,enabled)
            return
        if not game or not capture_enabled:
            if self.was_game:self.invalidate()
            self.was_game=False;self.voice.stop();self.panel.hide()
        else:self.was_game=True
        if now-self.last_good>1.25:
            self.voice_active=False;self.voice.stop();self.reminder.shortfall_since=None
        if self.future is not None and self.future.done():
            future=self.future;self.future=None
            captured,epoch,stamp,r=future.result()
            if capture_enabled and r is not None and frame_is_current(epoch,self.epoch,stamp,now,captured,game):
                self.last_good=now
                if r['context']=='unknown' and not r['gameplay']:
                    if self.outside_since is None:self.outside_since=now
                    # Temporary HUD occlusion/menu transitions suppress alerts, not TC memory.
                    # Process changes and confirmed match-clock rewinds still reset the count.
                else:self.outside_since=None
                process_changed=self.match_session is not None and self.match_session!=game[1]
                if process_changed:self.continuity=MatchContinuity()
                self.match_session=game[1]
                clock_restarted=self.continuity.observe(r.get('clock_seconds'))
                r['new_match']=process_changed or clock_restarted
                if r['new_match']:self.match_generation+=1
                # Persistent identity lets a disabled add-on catch up on re-enable.
                r['match_id']=(game[1],self.match_generation)
                r['match_pending']=self.continuity.pending is not None
                if r['new_match']:
                    self.reminder.forget();self.selection=SelectionEvidence();self.housing=StableHousingReminder()
                if self.continuity.pending is not None:r['confident']=False
                self.frame_observed.emit(game,r,stamp)
                if self.observer_enabled:
                    step=self.build_orders.progress.current.id if self.build_orders and self.build_orders.progress and self.build_orders.progress.current else None
                    self.log_villagers(now,r.get('villagers'),step)
                verified=self.selection.observe(r['selected_tcs'],stamp,r['context']=='pause' or (r['gameplay'] and r['advancing']))
                obs=Observation(busy=r['busy_upper_bound'],selected_tcs=r['selected_tcs'],selection_verified=verified,
                    foreground=True,gameplay=r['gameplay'],paused=r['context']=='pause',advancing=r['advancing'],
                    confident=r['confident'],housed=bool(r['housed']),session=game[1],reason=r['reason'])
                if self.manual_tcs:self.reminder.total=self.manual_tcs
                text,_,reason=self.reminder.step(obs,now,validated=self.detector.alerts_validated)
                if self.manual_tcs:self.reminder.total=self.manual_tcs
                housing=self.housing.update(r.get('population'),r['gameplay'] and r['advancing'] and self.continuity.pending is None,now)
                self.build_events.update(r.get('population'),housing,self.housing.seen>=2)
                self.voice_event=self.build_events.event if housing=='Build House' else None
                # The population counter is not always readable (other UI scales, the flashing
                # red/yellow box). The blocked queue icons are independent evidence, so a Town
                # Centre that has been blocked for a second still triggers the Housed warning.
                housing=housing or self.queue_blocked(text=='Population blocked' or bool(r.get('pop_flash')),now)
                self.housing_state=housing;self.idle_alert=text=='Check TC queues'
                self.latest_state=dict(match_id=r["match_id"],new_match=r["new_match"],villagers=r.get("villagers"),build_orders_enabled=self.observer_enabled,population=r.get('population'),housing=housing,tc_alert=text,reason=reason,context=r['context'],advancing=r['advancing'],confident=r['confident'],remembered_tcs=self.reminder.total,active=r['busy_upper_bound'],voice_event=self.voice_event)
                total=self.reminder.total;active=r['busy_upper_bound'];idle='?' if total is None else str(max(0,total-active))
                pop=r.get('population');population='?' if pop is None else f'{pop[0]}/{pop[1]}'
                state=housing or text or ('Paused' if r['context']=='pause' else reason)
                if not self.detector.alerts_validated:state='Recognition validation unavailable - voice off'
                if enabled and self.view_visible and r['context'] in ('gameplay','pause','menu'):
                    # Build House / Housed and an idle Town Centre can be active together; name both.
                    names=[]
                    if housing:names.append(housing)
                    if text=='Check TC queues':names.append('Idle TC' if housing else 'Idle Town Centre')
                    label=' · '.join(names) or ('Housed' if text=='Population blocked' else 'Select your Town Centres' if total is None else 'Town Centres active' if active>=total else state)
                    self.panel.present(game,total,idle,label,self.mute.isChecked(),bool(names) or text=='Population blocked')
                else:self.panel.hide()
        self.sync_view(game,enabled)
        # Build-order cues own the shared Windows sound channel, including queued
        # decimal instructions. Leave one-shot housing events unacknowledged so
        # current reminders resume after the guide has finished.
        if self.build_orders and self.build_orders.speech_priority:
            self.voice.stop()
        else:
            clip,event,active=choose_cue(self.voice,self.housing_state,self.idle_alert,self.voice_event,now)
            if self.voice.path!=str(ROOT/clip):self.voice.stop();self.voice.path=str(ROOT/clip)
            self.voice_active=active
            self.voice.update(bool(enabled and game and self.voice_active and not self.mute.isChecked()
                                   and self.detector.alerts_validated and now-self.last_good<=1.25),now,event=event)
        if now-self.last_diagnostic>=1:
            try:self.diagnostics.write_text(json.dumps(dict(self.latest_state,foreground=bool(game),tc_view_requested=self.view_visible,tc_panel_visible=self.panel.isVisible(),build_view_requested=self.build_orders.view_visible if self.build_orders else None,enabled=enabled,owns_capture=self.owns_capture,mute=self.mute.isChecked(),validated=self.detector.alerts_validated,voice_active=self.voice_active,clip=self.voice.path,build_order_step=self.build_orders.progress.current.id if self.build_orders and self.build_orders.progress and self.build_orders.progress.current else None,build_order_pending=[s.id for s in self.build_orders.progress.pending] if self.build_orders and self.build_orders.progress else [],error=self.error),indent=2))
            except OSError:pass
            self.last_diagnostic=now
        if capture_enabled and game and self.future is None and now-self.last_frame>=.5:
            self.last_frame=now;self.future=self.executor.submit(self.capture_frame,game,self.epoch)
    def close(self):
        self.closed=True;self.timer.stop();self.invalidate();self.executor.shutdown(wait=False,cancel_futures=True);self.panel.close()

