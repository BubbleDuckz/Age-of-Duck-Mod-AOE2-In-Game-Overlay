"""Public aoe2recs profile subscription; no login, scraping loop, or gameplay input."""
import json
import re
import threading
import time
import websocket
from concurrent.futures import ThreadPoolExecutor
from PyQt5.QtCore import QObject,pyqtSignal

URL='wss://aoe2recs.com/dashboard/api/'
LEADERBOARDS={'RM 1v1':3,'RM TG':4,'EW 1v1':13,'EW TG':14}
CIV_ALIASES={'Maya':'Mayans','Inca':'Incas','Aztec':'Aztecs'}
_CATALOG_CIVS=None

def _catalog_civs():
    global _CATALOG_CIVS
    if _CATALOG_CIVS is None:
        try:
            from pathlib import Path
            _CATALOG_CIVS=tuple(json.loads((Path(__file__).parent/'techtree_data.json').read_text(encoding='utf-8'))['civs'])
        except (OSError,ValueError,KeyError):_CATALOG_CIVS=()
    return _CATALOG_CIVS

def canonical_civ(name):
    """Map the provider's civilisation text onto the catalog's name (case, plural, small spelling differences)."""
    name=(name or '').strip()
    if not name:return ''
    if name in CIV_ALIASES:return CIV_ALIASES[name]
    civs=_catalog_civs()
    if name in civs:return name
    key=re.sub(r'[^a-z]','',name.lower())
    lookup={re.sub(r'[^a-z]','',c.lower()):c for c in civs}
    for variant in (key,key+'s',key[:-1] if key.endswith('s') else key,key+'es'):
        if variant in lookup:return lookup[variant]
    import difflib
    close=difflib.get_close_matches(key,list(lookup),n=1,cutoff=.86)
    return lookup[close[0]] if close else name

def profile_updates(message):
    if not isinstance(message,dict):return
    if message.get('cls')==3:
        for item in message.get('data',[]):yield from profile_updates(item)
    elif message.get('cls')==13:
        yield message.get('data')

PEAK_MODES={3:'1v1',4:'Teams',13:'EW 1v1',14:'EW Teams'}

def highest_peak(data):
    candidates=[]
    for ladder in data.get('ladders',[]):
        if not isinstance(ladder,dict):continue
        value=ladder.get('highest');mode=PEAK_MODES.get(ladder.get('id'))
        if mode and isinstance(value,(int,float)) and not isinstance(value,bool) and value>0:
            candidates.append((int(value),mode))
    return max(candidates,key=lambda item:item[0]) if candidates else (None,None)

def fetch_peak(profile_id):
    ws=websocket.create_connection(URL,origin='https://aoe2recs.com',timeout=8)
    try:
        ws.send(json.dumps({'profile_id':int(profile_id)}));ws.settimeout(1);deadline=time.monotonic()+12
        while time.monotonic()<deadline:
            try:raw=ws.recv()
            except websocket.WebSocketTimeoutException:continue
            if not raw:break
            for data in profile_updates(json.loads(raw)):
                if isinstance(data,dict) and str((data.get('player') or {}).get('id'))==str(profile_id):return highest_peak(data)
        raise TimeoutError('Peak profile unavailable')
    finally:ws.close()

def normalize_profile(data,profile_id):
    if not isinstance(data,dict) or not data.get('found'):return None
    owner=data.get('player') or {}
    if str(owner.get('id'))!=str(profile_id):return None
    live=data.get('live')
    if not isinstance(live,dict) or live.get('status')!='ongoing' or live.get('game')!='AoE2':return None
    if not live.get('started') or not live.get('id'):return None
    rows=live.get('players') or []
    # An aoe2recs profile can combine several in-game accounts (alt / smurf accounts). The live
    # match lists the account that is actually playing, which need not be the profile's own id.
    owned={str(profile_id)}
    for account in data.get('accounts') or []:
        if isinstance(account,dict) and account.get('id') is not None:owned.add(str(account['id']))
    if not any(str(p.get('id')) in owned for p in rows):return None
    leaderboard=LEADERBOARDS.get(live.get('leaderboard'))
    peak,peak_mode=highest_peak(data)
    players=[]
    for p in rows:
        color=p.get('color_hex','')
        if not isinstance(color,str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',color):color='#EAF2F9'
        team=p.get('team')
        if not isinstance(team,int):team=0
        civ=p.get('civilization') or ''
        is_ai=bool(p.get('ai')) or (not p.get('name') and p.get('id') is None)
        players.append(dict(name='AI' if is_ai else str(p.get('name') or ''),is_ai=is_ai,team=team,color=color,
            civ=canonical_civ(civ),country=p.get('country') or '',rating=p.get('rating'),
            peak=peak if str(p.get('id')) in owned else None,
            peak_mode=peak_mode if str(p.get('id')) in owned else None,
            profile_id=p.get('id'),is_self=str(p.get('id')) in owned))
    teams={p['team'] for p in players}
    # Free-for-all: the lobby says so, or every player is alone on their own team (more than two
    # players). Scenario lobbies report this even when the map plays as co-op / fixed teams.
    ffa=live.get('diplomacy')=='FFA' or (len(players)>2 and len(teams)==len(players))
    match=dict(matchId=live['id'],ffa=ffa,leaderboardId=leaderboard,leaderboardName=live.get('leaderboard') or live.get('type') or 'Live Match',mapName=live.get('rms') or 'Unknown map',started=live['started'],source='aoe2recs',teams=[])
    return match,players,match['leaderboardName'],match['mapName']

class RecsWorker(QObject):
    data_updated=pyqtSignal(dict,list,str,str)
    not_in_game=pyqtSignal()
    profile_error=pyqtSignal(str)
    in_game_signal=pyqtSignal(bool)
    provider_status=pyqtSignal(str)
    def __init__(self):
        super().__init__();self.running=True;self.profile_id=None;self.aoe2_running=False
        self.wake=threading.Event();self.socket=None;self.generation=0;self.last_payload=None;self.live=False;self._cleared=False
        self.peak_pool=ThreadPoolExecutor(max_workers=1);self.peak_tasks={};self.peak_cache={};self.current_data=None
    def _disconnect(self):
        ws=self.socket
        if ws is not None:
            try:ws.close()
            except Exception:pass
        self.wake.set()
    def set_game_running_state(self,running):
        self.aoe2_running=running
        if not running:self.generation+=1;self._disconnect()
        else:self.wake.set()
    def set_profile(self,profile_id):
        value=str(profile_id).strip()
        if not value.isdigit():self.profile_error.emit('Please enter a valid numeric profile ID.');return
        self.profile_id=value;self.generation+=1;self._disconnect()
    def stop(self):
        self.running=False;self._disconnect();self.peak_pool.shutdown(wait=False,cancel_futures=True)
    def clear(self):
        self.last_payload=None;self.current_data=None
        if self.live:self.in_game_signal.emit(False)
        self.live=False
        if not self._cleared:self.not_in_game.emit()
        self._cleared=True
    def accept(self,data,pid,generation):
        if generation!=self.generation or pid!=self.profile_id:return
        result=normalize_profile(data,pid)
        if result is None:self.clear();return
        self.current_data=data
        for player in result[1]:
            cached=self.peak_cache.get(str(player['profile_id']))
            if not player['is_self'] and cached and time.monotonic()-cached[0]<300:
                player['peak'],player['peak_mode']=cached[1]
        signature=json.dumps(result,sort_keys=True)
        if signature!=self.last_payload:
            self.data_updated.emit(*result);self.last_payload=signature
        if not self.live:self.in_game_signal.emit(True)
        self.live=True;self._cleared=False
    def enrich_peaks(self,pid,generation):
        changed=False
        for player_id,future in list(self.peak_tasks.items()):
            if future.done():
                del self.peak_tasks[player_id]
                try:value=future.result()
                except Exception:value=(None,None)
                self.peak_cache[player_id]=(time.monotonic(),value);changed=True
        if changed and self.current_data:self.accept(self.current_data,pid,generation)
        if not self.current_data:return
        for player in (self.current_data.get('live') or {}).get('players',[]):
            player_id=str(player.get('id'))
            if not player_id.isdigit() or player_id==pid or player_id in self.peak_tasks:continue
            cached=self.peak_cache.get(player_id)
            if cached and time.monotonic()-cached[0]<300:continue
            self.peak_tasks[player_id]=self.peak_pool.submit(fetch_peak,player_id)

    def poll_loop(self):
        delay=2
        while self.running:
            if not self.aoe2_running or not self.profile_id:
                self.clear();self.wake.wait(1);self.wake.clear();continue
            pid=self.profile_id;generation=self.generation;ws=None
            try:
                self.provider_status.emit('Connecting to aoe2recs…')
                ws=websocket.create_connection(URL,origin='https://aoe2recs.com',timeout=8)
                self.socket=ws
                if not self.running or generation!=self.generation:continue
                ws.send(json.dumps({'profile_id':int(pid)}));ws.settimeout(1)
                refreshed=time.monotonic();received=refreshed;confirmed=False
                while self.running and self.aoe2_running and generation==self.generation:
                    try:
                        raw=ws.recv()
                        if not raw:raise ConnectionError('Live feed closed')
                        for data in profile_updates(json.loads(raw)):
                            # Ignore late responses belonging to another profile.
                            if isinstance(data,dict) and data.get('found') and str((data.get('player') or {}).get('id'))!=pid:continue
                            self.accept(data,pid,generation);received=time.monotonic();confirmed=True;delay=2
                            self.provider_status.emit('aoe2recs live feed')
                    except websocket.WebSocketTimeoutException:pass
                    self.enrich_peaks(pid,generation)
                    now=time.monotonic()
                    # Refresh only the subscribed profile; never poll all matches/players.
                    if now-refreshed>=30:ws.send(json.dumps({'profile_id':int(pid)}));refreshed=now
                    if now-received>(75 if confirmed else 20):raise TimeoutError('Profile feed became stale')
            except Exception:
                self.clear();self.provider_status.emit('aoe2recs unavailable — reconnecting')
            finally:
                if ws is not None:
                    try:ws.close()
                    except Exception:pass
                if self.socket is ws:self.socket=None
            if self.running and generation==self.generation:
                self.wake.wait(delay);self.wake.clear();delay=min(30,delay*2)
