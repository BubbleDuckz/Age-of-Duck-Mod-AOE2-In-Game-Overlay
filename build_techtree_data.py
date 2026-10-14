"""Rebuild the bundled catalog from saved aoe2techtree.net source snapshots."""
import hashlib, html, json, re
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/'techtree_source'
def plain(text):
    text=re.sub(r'<br\s*/?>','\n',text,flags=re.I)
    text=re.sub(r'<[^>]+>','',text)
    return html.unescape(text).replace('\ufffd','').strip()
def build():
    data=json.loads((SOURCE/'data.json').read_text(encoding='utf-8'))
    strings=json.loads((SOURCE/'strings.json').read_text(encoding='utf-8'))
    civs={};units={}
    for civ,meta in data['civs'].items():
        tree=json.loads((SOURCE/'trees'/f'{civ}.json').read_text(encoding='utf-8'))
        buildings={b['building_id']:' '.join(plain(strings.get(str(b['name_string_id']),b['name'])).split()) for b in tree['buildings']}
        available={};details={}
        for node in tree['units_techs']:
            if node['use_type']!='Unit' or node['node_id'] not in meta['Unit'] or node['node_status']=='NotAvailable':continue
            name=' '.join(plain(strings.get(str(node['name_string_id']),node['name'])).split())
            building=buildings[node['building_id']]
            available.setdefault(building,{})[name]=True
            raw=strings.get(str(node['help_string_id']-79000),'')
            # First line is the Create/Upgrade heading; omit stats placeholders and upgrade instructions.
            description=re.split(r'<i>|\ufffdDEFAULT\ufffd',raw,flags=re.I)[0]
            description=re.split(r'<br\s*/?>',description,maxsplit=1,flags=re.I)
            description=plain(description[1] if len(description)>1 else description[0])
            stats=data['data']['Unit'].get(str(node['node_id']),{})
            unit=units.setdefault(name,{'id':node['node_id'],'unitDescription':description,'source':'aoe2techtree.net','buildings':[], 'cost':stats.get('Cost',{})})
            if building not in unit['buildings']:unit['buildings'].append(building)
            details.setdefault(name,[]).append({'building':building,'age':node['age_id'],'status':node['node_status'],'id':node['node_id']})
        description=plain(strings.get(str(meta['help_string_id']),''))
        team=re.split(r'Team Bonus:\s*',description,flags=re.I)
        civs[civ]={'civStrategy':description,'civTeamBonus':team[-1].strip() if len(team)>1 else 'Not listed','unitsAvailable':available,'unitDetails':details,'source':'https://aoe2techtree.net/#'+civ}
    result={'metadata':{'source':'https://aoe2techtree.net/','retrieved_utc':datetime.now(timezone.utc).isoformat(),'scope':'All civilizations in the main AoE2 DE tree (Chronicles and Return of Rome are separate trees).','data_sha256':hashlib.sha256((SOURCE/'data.json').read_bytes()).hexdigest(),'license':'techtree_source/LICENSE','attribution':'Siege Engineers / aoe2techtree; Age of Empires II © Microsoft Corporation.'},'civs':civs,'units':units}
    (ROOT/'techtree_data.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'{len(civs)} civilizations, {len(units)} units; missing descriptions: {[n for n,u in units.items() if not u["unitDescription"]]}')
if __name__=='__main__':build()
