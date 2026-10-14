"""One-shot cues are acknowledged only after uninterrupted playback completes."""
import winsound
import wave
import hashlib,tempfile
from pathlib import Path
import numpy as np

def volume_file(path,percent):
    if percent==100:return str(path)
    source=Path(path)
    key=hashlib.sha256((str(source.resolve())+str(source.stat().st_mtime_ns)+str(percent)).encode()).hexdigest()
    folder=Path(tempfile.gettempdir())/'AgeOfDuck-voice-volume';folder.mkdir(exist_ok=True)
    target=folder/(key+'.wav')
    if not target.exists():
        with wave.open(str(source),'rb') as f:params=f.getparams();raw=f.readframes(f.getnframes())
        if params.sampwidth!=2:raise ValueError('Expected 16-bit PCM voice')
        samples=np.frombuffer(raw,dtype='<i2');scaled=np.rint(samples.astype(np.float64)*(percent/100)).astype('<i2').tobytes()
        with wave.open(str(target),'wb') as f:f.setparams(params);f.writeframes(scaled)
    return str(target)

class RepeatingVoice:
    volume_percent=100
    def __init__(self,path,play=None):
        self.path=str(path);self.play=play or winsound.PlaySound
        self.next_due=None;self.active=False;self.last_event=None
        self.pending_event=None;self.finishes=None
    def advance(self,now):
        if self.pending_event is not None and self.finishes is not None and now>=self.finishes:
            self.last_event=self.pending_event;self.pending_event=None
    def update(self,active,now,event=None):
        self.advance(now)
        if not active:
            self.stop();return
        if event is not None and (event==self.last_event or event==self.pending_event):return
        if event is not None or self.next_due is None or now>=self.next_due:
            try:
                with wave.open(self.path,'rb') as clip:duration=clip.getnframes()/clip.getframerate()
            except (OSError,wave.Error):duration=1.0
            self.play(volume_file(self.path,RepeatingVoice.volume_percent),winsound.SND_FILENAME|winsound.SND_ASYNC|winsound.SND_NODEFAULT)
            self.pending_event=event;self.finishes=now+duration
            self.next_due=now+max(1.0,duration+.1)
        self.active=True
    def stop(self):
        if self.active:self.play(None,0)
        self.active=False;self.next_due=None;self.pending_event=None;self.finishes=None

    def reset(self):
        """Start a new cue session; ordinary pauses must keep acknowledged events."""
        self.stop()
        self.last_event=None


def choose_cue(voice,housing,idle,event,now):
    voice.advance(now)
    if housing=='Housed':return 'housed.wav',None,True
    if housing=='Build House' and event!=voice.last_event:
        return 'build-house.wav',event,True
    return 'idle.wav',None,idle

