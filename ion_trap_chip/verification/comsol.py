"""Explicit COMSOL adapter: replace CAD, resolve selections, then solve."""
import time
import numpy as np
import jpype

def ids(selection):
    return [int(x) for x in selection.entities()]

def entity_boxes(g, dimension, entities):
    measure = g.measureFinal(); measure.selection().geom('geom1', dimension)
    result = {}
    for entity in entities:
        measure.selection().set([int(entity)])
        result[int(entity)] = [float(x) for x in measure.getBoundingBox()]
    return result

def resolve_boxes(before, after, tolerance_mm=2e-6):
    """Return unique matches. Refuse ambiguous, absent, or reused entities."""
    target_ids = list(after)
    target_boxes = np.asarray([after[k] for k in target_ids])
    mapping = {}; failures = []
    for source, box in before.items():
        candidates = np.flatnonzero(np.max(abs(target_boxes-np.asarray(box)), axis=1) <= tolerance_mm)
        if len(candidates) != 1:
            failures.append({'entity': source, 'candidates': [target_ids[k] for k in candidates], 'bbox': box})
        else:
            mapping[source] = target_ids[candidates[0]]
    reverse = {}
    for old, new in mapping.items(): reverse.setdefault(new, []).append(old)
    for new, old in reverse.items():
        if len(old) > 1: failures.append({'duplicate_target': new, 'sources': old})
    return mapping, failures

def adjacent_domains(g, boundaries):
    return {int(b): [int(d) for d in g.getAdj(2, 3, int(b)) if int(d)>0] for b in boundaries}

def complete_by_adjacency(mapping, failures, domain_map, before_adjacency, after_adjacency):
    """Resolve remaining virtual faces only by a unique unused incidence match."""
    unresolved = []; recovered = []
    used = set(mapping.values())
    for failure in failures:
        old = failure.get('entity')
        if old is None:
            unresolved.append(failure);continue
        expected = {domain_map[d] for d in before_adjacency[old]}
        candidates = [b for b,domains in after_adjacency.items() if b not in used and set(domains)==expected]
        if len(candidates)==1:
            mapping[old]=candidates[0];used.add(candidates[0])
            recovered.append({'source':old,'target':candidates[0],'adjacent_domains':sorted(expected),'method':'unique_unmatched_domain_incidence'})
        else:
            unresolved.append({**failure,'adjacency_candidates':candidates})
    return unresolved,recovered

def replace_cad(g, records, object_names, order):
    delete = g.feature().createAfter('ifq_delete', 'Delete', 'imp1')
    delete.selection('input').init()
    delete.selection('input').set([object_names[k] for k in records])
    previous = 'ifq_delete'
    for label in order:
        tag = 'ifq_' + label.lower()
        feature = g.feature().createAfter(tag, 'Import', previous)
        feature.set('filename', records[label]['step'])
        feature.set('selresult', 'on'); feature.set('selresultshow', 'all')
        feature.importData()
        previous = tag
    g.run()

def transformed_boxes(boxes, records, tolerance_mm=2e-6):
    result = {}; changed = []
    for entity, box in boxes.items():
        value = np.array(box, float)
        for record in records.values():
            bounds = np.array(record['before']['bbox_mm'])
            contained = np.all(value[::2] >= bounds[::2]-tolerance_mm) and np.all(value[1::2] <= bounds[1::2]+tolerance_mm)
            if contained:
                lo, hi = bounds[2:4]
                factor = (hi-lo+record['delta_y_mm'])/(hi-lo)
                value[2:4] = lo + (value[2:4]-lo)*factor
                changed.append(entity)
                break
        result[entity] = value.tolist()
    return result, changed

def interpolate(j, coords, tag='ifq_sample'):
    f = j.result().numerical().create(tag, 'Interp')
    try:
        f.set('data', 'dset1'); f.set('expr', ['V'])
        f.set('coord', jpype.JArray(jpype.JDouble, 2)(np.asarray(coords, float)))
        raw = np.asarray(f.getData(), float)
        if raw.size != np.asarray(coords).shape[1]:
            raise ValueError(f'Unexpected solution channels: {raw.shape}')
        if not np.isfinite(raw).all(): raise ValueError('Nonfinite sampled potential')
        return raw.reshape(-1)
    finally:
        j.result().numerical().remove(tag)
