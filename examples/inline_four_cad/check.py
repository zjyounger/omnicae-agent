"""Independent reopening, joint-location and solid-intersection checks.

Run with FreeCADCmd check.py, using INLINE_FOUR_ROOT if relocated.
"""
import itertools
import json
import math
import os
import time
from pathlib import Path
import FreeCAD as App
import Part

root=Path(os.environ.get('INLINE_FOUR_ROOT',Path(__file__).resolve().parent))
started=time.time()
doc=App.openDocument(str(root/'inline_four_rotating_assembly.FCStd'))
doc.recompute()
components=[o for o in doc.Objects if o.TypeId=='PartDesign::Body']

def world(o):
    s=o.Shape.copy()
    s.Placement=o.getGlobalPlacement()
    return s

def overlap(a,b):
    aa,bb=a.BoundBox,b.BoundBox
    return (min(aa.XMax,bb.XMax)-max(aa.XMin,bb.XMin)>1e-6 and
            min(aa.YMax,bb.YMax)-max(aa.YMin,bb.YMin)>1e-6 and
            min(aa.ZMax,bb.ZMax)-max(aa.ZMin,bb.ZMin)>1e-6)

def assembly_name(o):
    p=o.getParentGeoFeatureGroup()
    return p.Name if p else o.Name

report={'reopened_native_components':len(components),
        'all_native_solids_valid':all(o.Shape.isValid() and len(o.Shape.Solids)==1 for o in components),
        'sample_interval_deg':15,'intersection_tolerance_mm3':1e-5,
        'collisions':[],'maximum_crankpin_alignment_error_mm':0.0,
        'boolean_pairs_checked':0,'poses':[]}
assert report['all_native_solids_valid']
for angle in range(0,360,15):
    doc.Mechanism.CrankAngle=angle
    doc.recompute()
    for i,sign in enumerate((1,-1,-1,1),1):
        # Check crank solid placement separately from rod/piston closure.
        cp=doc.Crankshaft.Placement.multVec(App.Vector((i-2.5)*96,0,sign*43))
        rp=doc.getObject(f'RodAssembly{i}').Placement.Base
        error=(cp-rp).Length
        report['maximum_crankpin_alignment_error_mm']=max(error,report['maximum_crankpin_alignment_error_mm'])
        assert error<1e-7,(angle,i,error)
    shapes={o.Name:world(o) for o in components}
    for a,b in itertools.combinations(components,2):
        # Relative positions inside a rigid subassembly are invariant: check once.
        if angle and assembly_name(a)==assembly_name(b):
            continue
        sa,sb=shapes[a.Name],shapes[b.Name]
        if not overlap(sa,sb):
            continue
        volume=sa.common(sb).Volume
        report['boolean_pairs_checked']+=1
        if volume>report['intersection_tolerance_mm3']:
            report['collisions'].append({'angle_deg':angle,'a':a.Name,'b':b.Name,'volume_mm3':volume})
    report['poses'].append({'angle_deg':angle,'piston_pin_z_mm':[doc.getObject(f'PistonAssembly{i}').Placement.Base.z for i in range(1,5)]})
    (root/'inspection_progress.json').write_text(json.dumps(report,indent=2))
    print('CHECKED',angle,'collisions',len(report['collisions']),flush=True)

step=Part.Shape()
step.read(str(root/'inline_four_rotating_assembly.step'))
report['step_reimport']={'valid':step.isValid(),'solids':len(step.Solids),'volume_mm3':step.Volume}
report['native_volume_mm3']=sum(o.Shape.Volume for o in components)
report['step_volume_relative_difference']=abs(step.Volume-report['native_volume_mm3'])/report['native_volume_mm3']
# Native/STEP mass-property integration can differ even when the BReps subtract
# to empty. Test spatial geometry directly, pairing by location AND volume:
# a wrist pin and its small-end bush have the same centroid.
doc.Mechanism.CrankAngle=35
doc.recompute()
remaining=list(step.Solids)
report['step_component_checks']=[]
for obj in components:
    native=world(obj)
    center=native.Solids[0].CenterOfMass
    imported=min(remaining,key=lambda s:(s.CenterOfMass-center).Length+
                 10*abs(s.Volume-native.Volume)/native.Volume)
    remaining.remove(imported)
    # Default boxes can include display triangulation approximations. Use
    # geometric optimal boxes for the export comparison.
    a,b=native.optimalBoundingBox(False,False),imported.optimalBoundingBox(False,False)
    bbox_error=max(abs(getattr(a,k)-getattr(b,k)) for k in
                   ('XMin','XMax','YMin','YMax','ZMin','ZMax'))
    report['step_component_checks'].append({'component':obj.Name,
        'native_volume_mm3':native.Volume,'step_volume_mm3':imported.Volume,
        'bbox_max_difference_mm':bbox_error,
        'native_minus_step_mm3':native.cut(imported).Volume,
        'step_minus_native_mm3':imported.cut(native).Volume})
report['step_geometry_passed']=all(c['bbox_max_difference_mm']<1e-6 and
    c['native_minus_step_mm3']<1e-5 and c['step_minus_native_mm3']<1e-5
    for c in report['step_component_checks'])
report['seconds']=time.time()-started
report['passed']=(not report['collisions'] and step.isValid() and len(step.Solids)==len(components)
                  and report['step_geometry_passed'])
(root/'inspection.json').write_text(json.dumps(report,indent=2))
print('INSPECTION_COMPLETE',report['passed'],report['seconds'],flush=True)
App.closeDocument(doc.Name)
