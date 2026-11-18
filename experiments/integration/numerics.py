"""Fixed-protocol DC mesh and linearity checks on actual reimported CAD."""
from pathlib import Path
import argparse
import json
import sys
import time
import traceback
import numpy as np
import mph

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT))
from experiments.paths import run_data, resolve_record_paths, input_path
from ion_trap_chip.verification.comsol import interpolate
from ion_trap_chip.verification.records import write_json,file_hash
from ion_trap_chip.verification.checks import numerical_response
DATA=run_data()

def tighten(j):
    s=j.sol('sol1').feature('s1');s.set('control','user');s.set('stol','1e-8')

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser();parser.add_argument('--linearity-only',action='store_true');args=parser.parse_args()
    out=DATA/'numerics';out.mkdir(exist_ok=True)
    report={'cores':2,'stationary_relative_tolerance':1e-8,'profile_threshold_V':5e-5,'linearity_threshold_V':1e-6,'cases':[],'status':'running'}
    client=mph.start(cores=2,version='6.3')
    y=np.linspace(-1.65,-.70,381);coords=np.vstack([np.full_like(y,1.3),y,np.full_like(y,13.2)])
    paths={'reference':input_path('model'),'modified':DATA/'reimport_AB/model.mph'}
    for case,path in paths.items():
        if case=='reference':
            if args.linearity_only:continue
            for level,suffix in enumerate(['','_fine','_finer']):
                source=input_path('reference_profiles', directory=True)/('comsol_profile_reference'+suffix+'_tight.npz')
                saved=np.load(source)
                if not np.array_equal(saved['coords_mm'],coords):raise ValueError('Reference coordinates differ')
                np.savez_compressed(out/f'reference_{level}.npz',potential_V=saved['dc'][0],coords_mm=coords)
                report['cases'].append({'case':'reference','level':level,'status':'reused_verified_reference','source':str(source),'source_sha256':file_hash(source),'protocol':'same reference model, refinement factors, coordinates and 1e-8 solver tolerance'})
            write_json(out/'report.json',report)
            continue
        model=client.load(str(path));j=model.java
        try:
            for level in range(1 if args.linearity_only else 3):
                entry={'case':case,'level':level,'source_sha256':file_hash(path)}
                print('START',case,level,flush=True)
                if level:
                    mesh=j.mesh('mesh1');factor=.7 if level==1 else .8
                    for tag in ['map1','ftet1','ftet2','ftet3']:
                        f=mesh.feature(tag).feature('size1')
                        for prop in ['hmax','hmin']:f.set(prop,f'{factor}*({f.getString(prop)})')
                    for tag,count in ([('swe1',150),('swe2',60)] if level==1 else [('swe1',190),('swe2',75)]):mesh.feature(tag).feature('dis1').set('numelem',str(count))
                    start=time.perf_counter();mesh.run();entry['mesh_seconds']=time.perf_counter()-start
                tighten(j);start=time.perf_counter();j.sol('sol1').runAll();entry['dc_seconds']=time.perf_counter()-start
                values=interpolate(j,coords)
                entry['mesh']={'vertices':int(j.mesh('mesh1').getNumVertex()),'elements':int(j.mesh('mesh1').getNumElem())}
                entry['potential_range_V']=[float(values.min()),float(values.max())]
                np.savez_compressed(out/f'{case}_{level}.npz',potential_V=values,coords_mm=coords)
                model.save(str(out/f'{case}_{level}.mph'))
                if case=='modified' and level==0:
                    features=[j.physics('es').feature(t) for t in j.physics('es').feature().tags() if str(j.physics('es').feature(t).getType())=='ElectricPotential']
                    original=[str(f.getString('V0')) for f in features]
                    for f,v in zip(features,original):f.set('V0','2*('+v+')')
                    start=time.perf_counter();j.sol('sol1').runAll();entry['linearity_solve_seconds']=time.perf_counter()-start
                    doubled=interpolate(j,coords)
                    error=float(np.max(abs(doubled-2*values)))
                    report['linearity']={'max_absolute_error_V':error,'threshold_V':1e-6,'passed':error<=1e-6,'scope':'same-mesh linear DC operator consistency'}
                    np.savez_compressed(out/'linearity.npz',baseline_V=values,doubled_V=doubled,coords_mm=coords)
                    for f,v in zip(features,original):f.set('V0',v)
                entry['status']='solved';report['cases'].append(entry)
                write_json(out/'report.json',report)
                print('DONE',case,level,entry['mesh'],round(entry['dc_seconds'],2),flush=True)
        except Exception as exc:
            report['status']='failed';report['error']=str(exc);traceback.print_exc();write_json(out/'report.json',report)
            client.remove(model);raise
        client.remove(model)
    if not args.linearity_only:
        responses=[np.load(out/f'modified_{k}.npz')['potential_V']-np.load(out/f'reference_{k}.npz')['potential_V'] for k in range(3)]
        report['response']=numerical_response(responses)
        report['response']['maximum_absolute_response_mV']=[float(np.max(abs(a))*1000) for a in responses]
    report['status']='complete';write_json(out/'report.json',report)
    print('COMPLETE',json.dumps({k:v for k,v in report.items() if k!='cases'}),flush=True)

if __name__=='__main__':main()
