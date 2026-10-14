"""Apply edits relative to the shipped legacy seed onto the current catalog."""
import copy

def merge_changes(target,seed,edited):
    result=copy.deepcopy(target)
    if not isinstance(seed,dict) or not isinstance(edited,dict):return result
    for key in seed.keys()-edited.keys():result.pop(key,None)
    for key,value in edited.items():
        if key in seed and value==seed[key]:continue
        if isinstance(value,dict) and isinstance(seed.get(key),dict) and isinstance(result.get(key),dict):
            result[key]=merge_changes(result[key],seed[key],value)
        else:result[key]=copy.deepcopy(value)
    return result

def merge_availability(target,seed,edited):
    result=copy.deepcopy(target)
    for category in set(seed)|set(edited):
        before=seed.get(category,{})
        after=edited.get(category,{})
        if not isinstance(before,dict) or not isinstance(after,dict):continue
        for unit in set(before)|set(after):
            if unit in before and unit in after and before[unit]==after[unit]:continue
            available=after.get(unit,False)
            groups=[values for values in result.values() if unit in values]
            if groups:
                for values in groups:values[unit]=available
            else:result.setdefault(category,{})[unit]=available
    return result

def apply_catalog_edits(catalog,seed_civs,edited_civs,seed_units,edited_units):
    result=copy.deepcopy(catalog)
    for section,seed,edited in [('civs',seed_civs,edited_civs),('units',seed_units,edited_units)]:
        if not isinstance(seed,dict) or not isinstance(edited,dict):continue
        # A missing legacy entry is not evidence that a newly added catalog unit was deleted.
        for name,value in edited.items():
            if not isinstance(value,dict):continue
            if name in result[section]:
                result[section][name]=merge_changes(result[section][name],seed.get(name,{}),value)
            elif name not in seed:
                result[section][name]=copy.deepcopy(value)
    if isinstance(seed_civs,dict) and isinstance(edited_civs,dict):
        for civ,edited in edited_civs.items():
            if civ not in catalog['civs'] or not isinstance(edited,dict):continue
            seed=seed_civs.get(civ,{})
            if not isinstance(seed,dict):continue
            result['civs'][civ]['unitsAvailable']=merge_availability(
                catalog['civs'][civ].get('unitsAvailable',{}),
                seed.get('unitsAvailable',{}),edited.get('unitsAvailable',{}))
    if isinstance(seed_units,dict) and isinstance(edited_units,dict):
        for name,unit in edited_units.items():
            if not isinstance(unit,dict):continue
            seed=seed_units.get(name,{})
            if not isinstance(seed,dict):continue
            if any(key in unit and unit[key]!=seed.get(key) for key in ('strong_vs','countered_by')):
                result['units'][name]['source']='custom'
    return result
