"""Reopen and inspect the short block independently of its generator."""
import hashlib
import itertools
import json
import math
import os
import time
from pathlib import Path

import FreeCAD as App
import Part

root=Path(os.environ.get('INLINE_FOUR_ROOT',Path(__file__).resolve().parent))
start=time.time()
report={'passed':False,'collision_tolerance_mm3':1e-5,'sample_interval_deg':15,
        'static_collisions':[],'motion_samples':[],'step_components':[]}

def save():
    report['elapsed_seconds']=time.time()-start
    (root/'block_inspection.json').write_text(json.dumps(report,indent=2))

def world(o):
    s=o.Shape.copy();s.Placement=o.getGlobalPlacement();return s

def overlap(a,b):
    a,b=a.BoundBox,b.BoundBox
    return all(min(getattr(a,k+'Max'),getattr(b,k+'Max'))-
               max(getattr(a,k+'Min'),getattr(b,k+'Min'))>1e-6 for k in ('X','Y','Z'))

try:
    doc=App.openDocument(str(root/'inline_four_short_block.FCStd'));doc.recompute()
    objects=[o for o in doc.Objects if o.TypeId=='PartDesign::Body']
    fixed=[o for o in objects if o.Name=='CylinderBlock' or o.Name.startswith(('MainCap','MainBearing','MainBolt','CorePlug'))]
    moving=[o for o in objects if o not in fixed]
    report['native_component_count']=len(objects)
    report['new_stationary_components']=len(fixed)
    report['moving_components']=len(moving)
    report['all_components_valid']=all(o.Shape.isValid() and len(o.Shape.Solids)==1 and o.Shape.Volume>0 for o in objects)
    assert report['all_components_valid']

    b=doc.CylinderBlock.Shape
    cylinders=[];tunnel=[];barrels=[]
    for f in b.Faces:
        s=f.Surface
        if not isinstance(s,Part.Cylinder):continue
        box=f.optimalBoundingBox(False,False)
        row={'radius_mm':s.Radius,'axis':[s.Axis.x,s.Axis.y,s.Axis.z],
             'center':[s.Center.x,s.Center.y,s.Center.z],
             'z_range_mm':[box.ZMin,box.ZMax],'x_range_mm':[box.XMin,box.XMax]}
        if abs(s.Radius-43)<1e-7 and abs(s.Axis.z)>0.999999:cylinders.append(row)
        if abs(s.Radius-47)<1e-7 and abs(s.Axis.z)>0.999999:barrels.append(row)
        if abs(s.Radius-30.025)<1e-7 and abs(s.Axis.x)>0.999999:tunnel.append(row)
    report['measured_bore_surfaces']=cylinders
    report['measured_barrel_surfaces']=barrels
    report['measured_main_tunnel_surfaces']=tunnel
    centers=sorted(set(round(s['center'][0],6) for s in cylinders))
    assert centers==[-144,-48,48,144],centers
    assert len(barrels)>=4 and len(tunnel)>=5
    assert all(abs(s['center'][1])<1e-7 for s in cylinders)
    assert all(abs(s['center'][1])<1e-7 and abs(s['center'][2])<1e-7 for s in tunnel)
    report['point_probes']=[]
    # Explicit probes distinguish actual barrels, water spaces, deck and holes.
    probes=[('cylinder void',(-144,0,160),False),
            ('4 mm cylinder wall',(-144,45,160),True),
            ('side coolant space',(-144,52,160),False),
            ('inter-cylinder coolant space',(-96,0,160),False),
            ('closed deck above jacket',(-144,45,213),True),
            ('deck coolant passage',(-144,51,213),False),
            ('head bolt pilot',(-96,66,190),False),
            ('rod mouth notch',(-144,45,101),False),
            ('wall above rod notch',(-144,45,112),True),
            ('crankcase void',(-144,0,-70),False),
            ('main upper saddle',(0,0,40),True)]
    for name,point,expected in probes:
        actual=b.isInside(App.Vector(*point),1e-7,False)
        report['point_probes'].append({'name':name,'point_mm':point,'expected_material':expected,'material':actual})
        assert actual==expected,(name,actual)
    report['deck_z_mm']=b.optimalBoundingBox(False,False).ZMax
    assert abs(report['deck_z_mm']-218)<1e-7
    doc.Mechanism.CrankAngle=0;doc.recompute()
    piston=world(doc.Piston1)
    report['tdc_piston_deck_clearance_mm']=218-piston.optimalBoundingBox(False,False).ZMax
    report['piston_block_distance_at_tdc_mm']=b.distToShape(piston)[0]
    assert abs(report['tdc_piston_deck_clearance_mm']-1)<1e-7
    assert abs(report['piston_block_distance_at_tdc_mm']-0.04)<1e-6
    doc.Mechanism.CrankAngle=60;doc.recompute()
    report['rod_block_distance_at_60_deg_mm']=b.distToShape(world(doc.Rod1))[0]
    assert report['rod_block_distance_at_60_deg_mm']>0.1

    static={o.Name:world(o) for o in fixed}
    report['static_boolean_pairs']=0
    for a,c in itertools.combinations(fixed,2):
        sa,sc=static[a.Name],static[c.Name]
        if not overlap(sa,sc):continue
        v=sa.common(sc).Volume;report['static_boolean_pairs']+=1
        if v>1e-5:report['static_collisions'].append({'a':a.Name,'b':c.Name,'volume_mm3':v})
    save()
    fixed_shape=Part.makeCompound(list(static.values()))
    for angle in range(0,360,15):
        doc.Mechanism.CrankAngle=angle;doc.recompute()
        dynamic={o.Name:world(o) for o in moving}
        moving_shape=Part.makeCompound(list(dynamic.values()))
        common=moving_shape.common(fixed_shape)
        volume=common.Volume
        sample={'angle_deg':angle,'moving_fixed_overlap_mm3':volume,'collisions':[]}
        if volume>1e-5:
            for a in moving:
                for c in fixed:
                    if not overlap(dynamic[a.Name],static[c.Name]):continue
                    v=dynamic[a.Name].common(static[c.Name]).Volume
                    if v>1e-5:sample['collisions'].append({'moving':a.Name,'stationary':c.Name,'volume_mm3':v})
        report['motion_samples'].append(sample);save()
        print('BLOCK_MOTION',angle,'overlap',volume,flush=True)

    doc.Mechanism.CrankAngle=35;doc.recompute()
    step=Part.Shape();step.read(str(root/'inline_four_short_block.step'))
    report['step_solid_count']=len(step.Solids)
    assert step.isValid() and len(step.Solids)==len(objects)
    remaining=list(step.Solids)
    for o in objects:
        n=world(o);center=n.Solids[0].CenterOfMass
        s=min(remaining,key=lambda s:(s.CenterOfMass-center).Length+10*abs(s.Volume-n.Volume)/n.Volume)
        remaining.remove(s)
        a,c=n.optimalBoundingBox(False,False),s.optimalBoundingBox(False,False)
        row={'component':o.Name,'native_minus_step_mm3':n.cut(s).Volume,'step_minus_native_mm3':s.cut(n).Volume,
             'bbox_difference_mm':max(abs(getattr(a,k)-getattr(c,k)) for k in ('XMin','XMax','YMin','YMax','ZMin','ZMax'))}
        report['step_components'].append(row)
    standalone=App.openDocument(str(root/'cylinder_block.FCStd'))
    standalone.recompute()
    bodies=[o for o in standalone.Objects if o.TypeId=='PartDesign::Body']
    report['standalone_native_bodies']=len(bodies)
    assert len(bodies)==1 and bodies[0].Shape.isValid()
    s=Part.Shape();s.read(str(root/'cylinder_block.step'))
    report['standalone_step_valid']=s.isValid() and len(s.Solids)==1
    report['standalone_native_difference_mm3']=b.cut(bodies[0].Shape).Volume+bodies[0].Shape.cut(b).Volume
    report['standalone_step_difference_mm3']=b.cut(s).Volume+s.cut(b).Volume
    build=json.loads((root/'block_build.json').read_text())
    report['rotating_source_unchanged']=hashlib.sha256((root/'inline_four_rotating_assembly.FCStd').read_bytes()).hexdigest()==build['source_sha256']
    report['passed']=(not report['static_collisions'] and
        all(p['moving_fixed_overlap_mm3']<1e-5 for p in report['motion_samples']) and
        all(p['native_minus_step_mm3']<1e-5 and p['step_minus_native_mm3']<1e-5 and p['bbox_difference_mm']<1e-6 for p in report['step_components']) and
        report['standalone_step_valid'] and report['standalone_native_difference_mm3']<1e-5 and report['standalone_step_difference_mm3']<1e-5 and report['rotating_source_unchanged'])
    save()
    print('BLOCK_INSPECTION_COMPLETE',report['passed'],flush=True)
    App.closeDocument(standalone.Name);App.closeDocument(doc.Name)
except Exception:
    import traceback
    report['error']=traceback.format_exc();save();traceback.print_exc()
