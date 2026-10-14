"""Provider contract tests using fabricated profiles; no personal data or network calls."""
import copy,json,unittest
from pathlib import Path
from recs_provider import normalize_profile,profile_updates,RecsWorker
FIX=Path(__file__).parent/'fixtures'
class ProviderTests(unittest.TestCase):
 def setUp(self):self.packet=json.loads((FIX/'recs-live-synthetic.json').read_text())
 def test_synthetic_live_payload(self):
  match,players,mode,map_name=normalize_profile(self.packet['data'],'1001')
  self.assertEqual((mode,map_name),('RM 1v1','Arabian Desert'))
  self.assertEqual([(p['name'],p['civ'],p['rating']) for p in players],[('Test Player','Cumans',1500),('Test Opponent','Mongols',1400)])
  self.assertEqual(players[0]['peak'],1600);self.assertIsNone(players[1]['peak']);self.assertTrue(players[0]['is_self'])
 def test_profile_with_linked_accounts_matches_the_account_that_is_playing(self):
  # A synthetic profile combines accounts; the match lists a linked account.
  d=copy.deepcopy(self.packet['data'])
  d['player']['id']=2001;d['accounts']=[{'id':'2002'},{'id':'2003'},{'id':'2001'}]
  d['live']['players']=[dict(d['live']['players'][1],id=2004,name='Other Account'),dict(d['live']['players'][0],id=2003,name='Linked Account',civilization='Danes')]
  match,players,mode,map_name=normalize_profile(d,'2001')
  mine=[p for p in players if p['is_self']]
  self.assertEqual([(p['name'],p['civ']) for p in mine],[('Linked Account','Danes')])
  self.assertEqual(mine[0]['peak'],1600);self.assertFalse(any(p['is_self'] for p in players if p['name']=='Other Account'))
  d['accounts']=[{'id':'2002'}]   # no linked account is playing: still not live
  self.assertIsNone(normalize_profile(d,'2001'))
 def test_scenario_free_for_all_and_ai_player(self):
  d=copy.deepcopy(self.packet['data']);base=d['live']['players'][0]
  rows=[dict(base,id=n,name=f'P{n}',team=10+n) for n in range(1,6)]
  rows[0]['id']=1001;rows.append({'number':6,'civilization':'Bohemians','ai':True,'color':6,'color_hex':'#ea69e1','team':16})
  d['live'].update(players=rows,diplomacy='FFA',type='Scenario')
  match,players,mode,map_name=normalize_profile(d,'1001')
  self.assertTrue(match['ffa'])
  self.assertEqual([(p['name'],p['is_ai']) for p in players][-1],('AI',True))
  self.assertFalse(any(p['is_ai'] for p in players[:-1]))
  self.assertFalse(normalize_profile(self.packet['data'],'1001')[0]['ffa'])   # a 1v1 is not FFA
 def test_offline_does_not_use_history(self):
  p=json.loads((FIX/'recs-offline-synthetic.json').read_text())
  self.assertIsNone(normalize_profile(p['data'],'9001'))
 def test_lobby_finished_and_wrong_profile(self):
  for status in ['complete','lobby','cancelled']:
   d=copy.deepcopy(self.packet['data']);d['live']['status']=status;self.assertIsNone(normalize_profile(d,'1001'))
  self.assertIsNone(normalize_profile(self.packet['data'],'9001'))
 def test_batched_and_null_profile(self):
  self.assertEqual(list(profile_updates({'cls':3,'data':[{'cls':1,'data':{}},self.packet]})),[self.packet['data']])
  self.assertEqual(list(profile_updates({'cls':13,'data':None})),[None])
 def test_push_end_and_obsolete_response(self):
  worker=RecsWorker();self.addCleanup(worker.stop);worker.profile_id='1001';worker.generation=2
  updates=[];ended=[];worker.data_updated.connect(lambda *x:updates.append(x));worker.not_in_game.connect(lambda:ended.append(True))
  worker.accept(self.packet['data'],'1001',1);self.assertFalse(updates)
  worker.accept(self.packet['data'],'1001',2);worker.accept(self.packet['data'],'1001',2);self.assertEqual(len(updates),1)
  d=copy.deepcopy(self.packet['data']);d['live']=None;worker.accept(d,'1001',2);self.assertFalse(worker.live);self.assertTrue(ended)
 def test_disconnect_clears_and_resubscribe_emits(self):
  worker=RecsWorker();self.addCleanup(worker.stop);worker.profile_id='1001';updates=[];worker.data_updated.connect(lambda *x:updates.append(x))
  worker.accept(self.packet['data'],'1001',0);worker.clear();self.assertIsNone(worker.last_payload)
  worker.accept(self.packet['data'],'1001',0);self.assertEqual(len(updates),2)
 def test_missing_rating_is_not_zero(self):
  d=copy.deepcopy(self.packet['data']);d['live']['players'][1].pop('rating')
  self.assertIsNone(normalize_profile(d,'1001')[1][1]['rating'])
 def test_not_found_profile_is_not_live(self):
  d=copy.deepcopy(self.packet['data']);d['found']=False
  self.assertIsNone(normalize_profile(d,'1001'))
 def test_other_game_or_incomplete_live_match_is_not_live(self):
  for field,value in [('game','AoE4'),('started',None),('id',None)]:
   with self.subTest(field=field):
    d=copy.deepcopy(self.packet['data']);d['live'][field]=value
    self.assertIsNone(normalize_profile(d,'1001'))
class PeakTests(unittest.TestCase):
 def test_highest_across_modes_not_current_match(self):
  from recs_provider import highest_peak
  d=json.loads((FIX/'recs-live-synthetic.json').read_text())['data'];d['live']['leaderboard']='RM TG';d['live']['players'][0]['rating']=1300
  player=normalize_profile(d,'1001')[1][0]
  self.assertEqual((player['rating'],player['peak'],player['peak_mode']),(1300,1600,'1v1'))
  for ident,label in [(3,'1v1'),(4,'Teams'),(13,'EW 1v1'),(14,'EW Teams')]:
   self.assertEqual(highest_peak({'ladders':[{'id':ident,'highest':2200},{'id':29,'highest':9999}]}),(2200,label))
 def test_missing_peaks_and_cached_other_player(self):
  from recs_provider import highest_peak
  self.assertEqual(highest_peak({'ladders':[]}),(None,None))
  w=RecsWorker();self.addCleanup(w.stop);w.profile_id='1001';w.peak_cache['1002']=(__import__('time').monotonic(),(2800,'EW Teams'));seen=[]
  w.data_updated.connect(lambda *x:seen.append(x));w.accept(json.loads((FIX/'recs-live-synthetic.json').read_text())['data'],'1001',0)
  self.assertEqual((seen[0][1][1]['peak'],seen[0][1][1]['peak_mode']),(2800,'EW Teams'));w.stop()

