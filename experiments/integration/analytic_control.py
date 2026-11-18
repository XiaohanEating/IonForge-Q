"""Independent solver control: linear potential in a parallel-plate box."""
from pathlib import Path
import sys,time,json
import numpy as np
import mph
import jpype

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT))
from experiments.paths import run_data, resolve_record_paths
DATA=run_data()
from ion_trap_chip.verification.records import write_json
OUT=DATA/'analytic_control'

def main():
    sys.stdout.reconfigure(encoding='utf-8');OUT.mkdir(exist_ok=True)
    client=mph.start(cores=2,version='6.3');model=client.create('parallel_plate_control');j=model.java
    comp=j.component().create('comp1',True);g=comp.geom().create('geom1',3);g.lengthUnit('mm')
    g.create('blk1','Block');g.feature('blk1').set('size',[1.,1.,1.]);g.run()
    p=comp.physics().create('es','Electrostatics','geom1')
    material=comp.material().create('mat1','Common');material.propertyGroup('def').set('relpermittivity',['1','0','0','0','1','0','0','0','1'])
    measure=g.measureFinal();measure.selection().geom('geom1',2);plates={}
    for b in range(1,int(g.getNBoundaries())+1):
        measure.selection().set([b]);box=np.array(measure.getBoundingBox(),float)
        if abs(box[1]-box[0])<1e-8 and abs(box[0])<1e-8:plates['ground']=b
        if abs(box[1]-box[0])<1e-8 and abs(box[0]-1)<1e-8:plates['drive']=b
    if set(plates)!= {'ground','drive'}:raise ValueError('Analytic control plate identification failed')
    p.create('gnd1','Ground',2);p.feature('gnd1').selection().set([plates['ground']])
    p.create('pot1','ElectricPotential',2);p.feature('pot1').selection().set([plates['drive']]);p.feature('pot1').set('V0','1[V]')
    mesh=comp.mesh().create('mesh1');mesh.create('ftet1','FreeTet')
    study=j.study().create('std1');study.create('stat','Stationary')
    xx=np.linspace(.01,.99,101);coords=np.vstack([xx,np.full_like(xx,.37),np.full_like(xx,.61)])
    report={'geometry':'1 mm cube; x=0 at 0 V, x=1 mm at 1 V; other faces insulated','analytical_solution':'V=x/(1 mm) volts','threshold_V':1e-6,'scope':'analytic solver control, not device discretization validation','cases':[]}
    for size in [5,3]:
        mesh.feature('size').set('hauto',jpype.JInt(size));mesh.feature('size').set('custom','off')
        mesh.run();start=time.perf_counter();study.run()
        n=j.result().numerical().create('interp'+str(size),'Interp');n.set('expr',['V']);n.set('coord',jpype.JArray(jpype.JDouble,2)(coords));a=np.array(n.getData(),float).reshape(-1)
        if a.size!=len(xx):raise ValueError('Unexpected solution channels')
        error=float(np.max(abs(a-xx)));row={'auto_mesh_size':size,'elements':int(mesh.getNumElem()),'solve_seconds':time.perf_counter()-start,'max_error_V':error,'passed':error<=1e-6};report['cases'].append(row)
        np.savez_compressed(OUT/f'mesh_{size}.npz',coords_mm=coords,potential_V=a,exact_V=xx);print(row,flush=True)
    report['distinct_meshes']=len({r['elements'] for r in report['cases']})==2
    report['status']='ACCEPT' if report['distinct_meshes'] and all(r['passed'] for r in report['cases']) else 'UNRESOLVED'
    model.save(str(OUT/'model.mph'));write_json(OUT/'report.json',report);client.remove(model)

if __name__=='__main__':main()
