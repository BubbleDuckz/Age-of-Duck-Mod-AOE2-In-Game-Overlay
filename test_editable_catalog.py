import copy
import unittest
from editable_catalog import apply_catalog_edits

class EditableCatalogTests(unittest.TestCase):
    def setUp(self):
        self.catalog={'civs':{'Britons':{'civTeamBonus':'Current bonus','unitsAvailable':{'Archery Range':{'Archer':True}}}},
                      'units':{'Archer':{'id':4,'source':'aoe2techtree.net','unitDescription':'Current description'}}}
        self.civs={'Britons':{'civTeamBonus':'Legacy bonus','unitsAvailable':{'Archery':{'Archer':True}}}}
        self.units={'Archer':{'unitDescription':'Legacy description','strong_vs':[],'countered_by':[]}}

    def apply(self,civs=None,units=None):
        return apply_catalog_edits(self.catalog,self.civs,civs if civs is not None else self.civs,
                                   self.units,units if units is not None else self.units)

    def test_unchanged_seed_does_not_replace_current_catalog(self):
        self.assertEqual(self.apply(),self.catalog)

    def test_text_edits_preserve_current_ids_and_other_fields(self):
        civs=copy.deepcopy(self.civs);units=copy.deepcopy(self.units)
        civs['Britons']['civTeamBonus']='My bonus';units['Archer']['unitDescription']='My description'
        result=self.apply(civs,units)
        self.assertEqual(result['civs']['Britons']['civTeamBonus'],'My bonus')
        self.assertEqual(result['units']['Archer']['unitDescription'],'My description')
        self.assertEqual(result['units']['Archer']['id'],4)

    def test_legacy_category_edits_update_the_current_building(self):
        civs=copy.deepcopy(self.civs);civs['Britons']['unitsAvailable']['Archery']['Archer']=False
        result=self.apply(civs)
        self.assertFalse(result['civs']['Britons']['unitsAvailable']['Archery Range']['Archer'])
        self.assertNotIn('Archery',result['civs']['Britons']['unitsAvailable'])

    def test_custom_counter_edits_use_the_existing_manual_counter_path(self):
        units=copy.deepcopy(self.units);units['Archer']['countered_by']=[{'unit':'Skirmisher'}]
        result=self.apply(units=units)
        self.assertEqual(result['units']['Archer']['source'],'custom')
        self.assertEqual(result['units']['Archer']['countered_by'],[{'unit':'Skirmisher'}])

    def test_inputs_are_not_modified_and_bad_preferences_are_ignored(self):
        original=copy.deepcopy(self.catalog)
        result=apply_catalog_edits(self.catalog,self.civs,[],self.units,None)
        self.assertEqual(result,original);self.assertEqual(self.catalog,original)

    def test_missing_or_partial_legacy_files_do_not_remove_current_units(self):
        result=self.apply(civs={},units={})
        self.assertEqual(result,self.catalog)

if __name__=='__main__':unittest.main()
