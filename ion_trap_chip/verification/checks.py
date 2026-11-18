"""Check electrical membership independently from voltage and entity counts."""
import numpy as np

def assignments(expected, actual):
    errors=[]
    expected_by_id={r['label']:r for r in expected}
    actual_by_id={r['label']:r for r in actual}
    if len(actual_by_id)!=len(actual): errors.append({'reason':'duplicate_logical_id'})
    if expected_by_id.keys()!=actual_by_id.keys(): errors.append({'reason':'electrode_set_mismatch'})
    owners={}
    for label,target in expected_by_id.items():
        row=actual_by_id.get(label)
        if row is None: continue
        members=row['entities']
        if not members or len(members)!=len(set(members)): errors.append({'label':label,'reason':'empty_or_duplicate_members'})
        if set(members)!=set(target['entities']): errors.append({'label':label,'reason':'geometric_membership_mismatch'})
        if row['voltage']!=target['voltage']: errors.append({'label':label,'reason':'voltage_mismatch'})
        for entity in set(members): owners.setdefault(entity,[]).append(label)
    for entity, labels in owners.items():
        if len(labels)>1: errors.append({'entity':entity,'labels':labels,'reason':'shared_boundary'})
    return {'passed':not errors,'errors':errors,'electrodes':len(actual),'unique_boundaries':len(owners)}

def numerical_response(profiles, max_difference_V=5e-5):
    arrays=[np.asarray(p,float) for p in profiles]
    if len(arrays)<3 or any(a.shape!=arrays[0].shape or not np.isfinite(a).all() for a in arrays):
        return {'passed':False,'reason':'need_three_finite_aligned_levels'}
    differences=[float(np.max(abs(b-a))) for a,b in zip(arrays,arrays[1:])]
    return {'passed':all(d<=max_difference_V for d in differences[-2:]),'max_adjacent_differences_V':differences,'threshold_V':max_difference_V,'interpretation':'empirical mesh consistency, not a certified error bound'}
