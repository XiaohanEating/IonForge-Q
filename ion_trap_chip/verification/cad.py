"""External STEP edits in millimeters, preserving explicit logical identity."""
from pathlib import Path
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRepBndLib import brepbndlib
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_GTransform
from OCC.Core.BRepCheck import BRepCheck_Analyzer
from OCC.Core.BRepGProp import brepgprop
from OCC.Core.GProp import GProp_GProps
from OCC.Core.gp import gp_GTrsf
from OCC.Core.STEPControl import STEPControl_Reader, STEPControl_Writer, STEPControl_AsIs
from OCC.Core.IFSelect import IFSelect_RetDone
from OCC.Core.TopAbs import TopAbs_SOLID, TopAbs_FACE
from OCC.Core.TopExp import TopExp_Explorer
from .records import file_hash, write_json

def read_step(path: Path):
    reader = STEPControl_Reader()
    if reader.ReadFile(str(path)) != IFSelect_RetDone:
        raise ValueError(f'Cannot read STEP: {path}')
    reader.TransferRoots()
    return reader.OneShape()

def describe(shape) -> dict:
    box = Bnd_Box(); box.SetGap(0.0)
    brepbndlib.AddOptimal(shape, box, False, False)
    x0,y0,z0,x1,y1,z1 = box.Get()
    props = GProp_GProps(); brepgprop.VolumeProperties(shape, props)
    counts = {}
    for name, kind in [('solids', TopAbs_SOLID), ('faces', TopAbs_FACE)]:
        exp = TopExp_Explorer(shape, kind); n = 0
        while exp.More(): n += 1; exp.Next()
        counts[name] = n
    return {'bbox_mm': [x0,x1,y0,y1,z0,z1], 'volume_mm3': props.Mass(), 'valid': bool(BRepCheck_Analyzer(shape).IsValid()), **counts}

def extend_y(source: Path, destination: Path, logical_id: str, delta_mm: float) -> dict:
    shape = read_step(source); before = describe(shape)
    low, high = before['bbox_mm'][2:4]
    if high <= low or high - low + delta_mm <= 0:
        raise ValueError('Requested y extent is nonpositive')
    factor = (high - low + delta_mm)/(high-low)
    transform = gp_GTrsf()
    transform.SetValue(2, 2, factor)
    transform.SetValue(2, 4, low * (1.0-factor))
    modified = BRepBuilderAPI_GTransform(shape, transform, True).Shape()
    after = describe(modified)
    if not before['valid'] or not after['valid'] or after['solids'] != 1 or after['volume_mm3']<=0:
        raise ValueError('Electrode edit produced invalid or non-single-solid CAD')
    destination.parent.mkdir(parents=True, exist_ok=True)
    writer = STEPControl_Writer(); writer.Transfer(modified, STEPControl_AsIs)
    if writer.Write(str(destination)) != IFSelect_RetDone:
        raise RuntimeError('STEP export failed')
    readback = describe(read_step(destination))
    if not readback['valid'] or max(abs(a-b) for a,b in zip(after['bbox_mm'], readback['bbox_mm'])) > 1e-6:
        raise ValueError('STEP read-back geometry mismatch')
    record = {'logical_id': logical_id, 'units': 'mm', 'source': str(source), 'source_sha256': file_hash(source), 'step': str(destination), 'step_sha256': file_hash(destination), 'delta_y_mm': delta_mm, 'anchor_y_mm': low, 'before': before, 'after': readback}
    write_json(destination.with_suffix('.json'), record)
    return record
