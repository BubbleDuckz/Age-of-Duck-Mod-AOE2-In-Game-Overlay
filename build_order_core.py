"""Build-order schema and villager-count progression; no game input."""
import json,re
from collections import deque
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Step:
 id:str
 villagers:int
 text:str

@dataclass(frozen=True)
class Order:
 name:str
 description:str
 steps:tuple

def load_order(path):
 path=Path(path)
 if path.stat().st_size>1_000_000:raise ValueError('Build order exceeds 1 MB.')
 data=json.loads(path.read_text(encoding='utf-8-sig'))
 if not isinstance(data,dict) or data.get('version')!=1:raise ValueError('Expected an object with version: 1.')
 name=data.get('name');rows=data.get('steps')
 if not isinstance(name,str) or not name.strip() or len(name)>100:raise ValueError('Name must contain 1–100 characters.')
 if not isinstance(rows,list) or not 1<=len(rows)<=500:raise ValueError('Expected 1–500 steps.')
 parsed=[];keys=set()
 for row in rows:
  if not isinstance(row,dict):raise ValueError('Each step must be an object.')
  value=row.get('step')
  if isinstance(value,bool) or not isinstance(value,(str,int)):raise ValueError('Write step IDs as strings, such as "19.1".')
  match=re.fullmatch(r'([1-9]\d{0,2})(?:\.([1-9]\d{0,2}))?',str(value))
  if not match:raise ValueError('Invalid step ID: '+str(value))
  count=int(match[1]);sub=int(match[2] or 0);key=(count,sub)
  if count>250 or key in keys:raise ValueError('Duplicate step or villager count above 250.')
  keys.add(key)
  unit=row.get('unit','');task=row.get('task','');building=row.get('building','');custom=row.get('text','');say=row.get('say','')
  if any(not isinstance(v,str) or len(v)>500 for v in (unit,task,building,custom,say)):raise ValueError('Step text fields must be strings of at most 500 characters.')
  if unit=='Custom':text=custom
  elif unit=='Villager':
   if task=='Build':
    if not building:raise ValueError('A Build step needs a building.')
    text=f'Villager {count}: build {building}.'
   elif task:text=f'Villager {count}: {task}.'
   else:raise ValueError('A Villager step needs a task.')
  elif unit in ('FeudalAge','CastleAge','ImperialAge'):text='Click up to '+{'FeudalAge':'Feudal Age','CastleAge':'Castle Age','ImperialAge':'Imperial Age'}[unit]+'.'
  elif unit=='Loom':text='Research Loom.'
  else:raise ValueError('Unknown unit type: '+unit)
  text=say.strip() or text.strip()
  if not text:raise ValueError('A Custom step needs text.')
  parsed.append((key,Step(str(value),count,text)))
 for key,_ in parsed:
  if key[1] and (key[0],0) not in keys:raise ValueError('Decimal steps need their whole-number parent step.')
 parsed.sort(key=lambda v:v[0])
 description=data.get('description','')
 if not isinstance(description,str) or len(description)>1000:raise ValueError('Description must be text, up to 1000 characters.')
 return Order(name.strip(),description,tuple(v for _,v in parsed))

class Progress:
 def __init__(self,order):self.order=order;self.reset()
 def reset(self):
  self.high=None;self.candidate=None;self.seen=0;self.pending=deque();self.current=None;self.last=None
 def observe(self,count,safe):
  if not safe or count is None:self.candidate=None;self.seen=0;return
  self.seen=self.seen+1 if count==self.candidate else 1;self.candidate=count
  # Villagers normally appear one or two at a time. A larger jump is more likely a misread digit
  # (for example 8 read as 18) than real, so it needs more agreeing frames before cues are queued.
  need=2
  if self.high is not None:
   jump=count-self.high
   need=4 if jump>=5 else 3 if jump>=3 else 2   # two at once happens with two Town Centres
  if self.seen<need:return
  if self.high is None:
   self.high=count
   self.pending.extend(s for s in self.order.steps if s.villagers==count)
  elif count>self.high:
   self.pending.extend(s for s in self.order.steps if self.high<s.villagers<=count)
   self.high=count
 def begin(self):
  if self.current is None and self.pending:self.current=self.pending.popleft()
  return self.current
 def complete(self):self.last=self.current;self.current=None
 def next_step(self):
  if self.pending:return self.pending[0]
  return next((s for s in self.order.steps if s.villagers>(self.high or 0)),None)
