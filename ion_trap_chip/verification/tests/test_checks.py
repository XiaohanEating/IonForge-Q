from copy import deepcopy
import unittest
import numpy as np
from ion_trap_chip.verification.checks import assignments,numerical_response
from ion_trap_chip.verification.comsol import resolve_boxes,complete_by_adjacency
from ion_trap_chip.verification.records import Verification,invalidated,signature

class Checks(unittest.TestCase):
    def test_ambiguous_geometry_is_not_silently_chosen(self):
        mapping,failures=resolve_boxes({1:[0,1,0,1,0,1]}, {10:[0,1,0,1,0,1],11:[0,1,0,1,0,1]})
        self.assertEqual(mapping,{})
        self.assertEqual(len(failures),1)

    def test_two_sources_cannot_share_candidate(self):
        _,failures=resolve_boxes({1:[0,1,0,1,0,1],2:[0,1,0,1,0,1]}, {10:[0,1,0,1,0,1]})
        self.assertTrue(any('duplicate_target' in row for row in failures))

    def test_large_coordinates_do_not_relax_absolute_tolerance(self):
        _,failures=resolve_boxes({1:[100,101,0,1,0,1]}, {10:[100,101.0001,0,1,0,1]})
        self.assertTrue(failures)

    def test_adjacency_rejects_multiple_unused_faces(self):
        mapping={1:11}
        failures,recovered=complete_by_adjacency(mapping,[{'entity':2}],{4:8},{2:[4]},{11:[8],12:[8],13:[8]})
        self.assertTrue(failures);self.assertEqual(recovered,[])

    def test_same_voltage_and_count_do_not_hide_swap(self):
        original=[{'label':'A','voltage':'1','entities':[1,2]},{'label':'B','voltage':'1','entities':[3,4]}]
        corrupted=deepcopy(original);corrupted[0]['entities'],corrupted[1]['entities']=[3,4],[1,2]
        self.assertFalse(assignments(original,corrupted)['passed'])

    def test_missing_check_cannot_accept(self):
        self.assertEqual(Verification(True,True,True,None).status,'UNRESOLVED')
        self.assertEqual(Verification(True,False,True,True).status,'REJECT')

    def test_sample_change_preserves_field(self):
        state={k:k for k in ['geometry','roles','materials','drives','mesh_settings','solver','sampling']}
        self.assertEqual(invalidated(state,state|{'sampling':'different'}),['samples'])
        self.assertEqual(invalidated(state,state|{'drives':'different'}),['field','samples'])
        with self.assertRaises(KeyError):signature('field',{})

    def test_one_good_refinement_is_insufficient(self):
        self.assertFalse(numerical_response([np.array([0.]),np.array([.001]),np.array([.00101])])['passed'])
        self.assertFalse(numerical_response([np.array([0.]),np.array([0.])])['passed'])

if __name__=='__main__':unittest.main()
