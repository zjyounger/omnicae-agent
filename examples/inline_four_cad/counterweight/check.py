"""Reopen saved shaft/assembly; measure mass moments, clearances and STEP."""
import sys,json,math,hashlib,time,traceback
from pathlib import Path
import FreeCAD as App
import Part
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import design
V=App.Vector
start=time.time()
report={'passed':False,'motion':[]}
def save():
    report['elapsed_seconds']=time.time()-start
    (ROOT/'verification.json').write_text(json.dumps(report,indent=2))
def world(o):
    s=o.Shape.copy();s.Placement=o.getGlobalPlacement();return s
try:
    cfg=json.loads((ROOT/'design_parameters.json').read_text())
    doc=App.openDocument(str(ROOT/'short_block.FCStd'))
    doc.Mechanism.CrankAngle=0;doc.recompute()
    crank=design.local(doc.Crankshaft);v,c=design.moments(crank)
    assert crank.isValid() and len(crank.Solids)==1
    report['shaft_mass_kg']=v*design.RHO
    report['shaft_cg_mm']=[c.x,c.y,c.z]
    I=crank.Solids[0].MatrixOfInertia
    report['shaft_inertia_cg_kgmm2']=[[getattr(I,'A'+str(i)+str(j))*design.RHO for j in (1,2,3)] for i in (1,2,3)]
    report['rod_mass_properties']=design.mass_properties(doc)
    report['cells']=[]
    target=report['rod_mass_properties']['equivalent_big_end_kg']*43
    for i,(x,sgn) in enumerate(zip((-144,-48,48,144),(1,-1,-1,1)),1):
        cell=crank.common(Part.makeBox(96,200,200,V(x-48,-100,-100)))
        cv,cc=design.moments(cell)
        residual=design.RHO*cv*cc.z+sgn*target
        assert abs(residual)/target<.001,(i,residual)
        report['cells'].append({'cylinder':i,'shaft_cell_mass_kg':cv*design.RHO,
          'shaft_cell_moment_kgmm':cv*design.RHO*cc.z,'rod_rotating_moment_kgmm':sgn*target,
          'residual_kgmm':residual,'relative_residual_percent':abs(residual)/target*100})
    # Independent 2D integral: upper trapezoid plus top semicircle minus
    # lower semicircle. Symmetric main-journal halves add zero first moment.
    R=cfg['radius_mm']
    upper_moment=43**2*(55+2*54)/6+43*math.pi*27**2/2+2*27**3/3
    analytic=design.RHO*(40*(upper_moment-2*R**3/3)+math.pi*24**2*28*43)
    measured=report['cells'][0]['shaft_cell_moment_kgmm']
    assert abs(analytic-measured)<1e-6,(analytic,measured)
    report['analytic_cell_moment_kgmm']=analytic
    report['independent_integral_difference_kgmm']=analytic-measured
    report['lower_half_counterweight_regions']=[]
    for i,(x,sgn) in enumerate(zip((-144,-48,48,144),(1,-1,-1,1)),1):
        for side,xx in enumerate((x-34,x+14)):
            region=crank.common(Part.makeBox(20,180,90,V(xx,-90,-90 if sgn==1 else 0)))
            rv,rc=design.moments(region)
            report['lower_half_counterweight_regions'].append({'cylinder':i,'side':side,
                'mass_kg':rv*design.RHO,'cg_mm':[rc.x,rc.y,rc.z]})
    # These global checks supplement rather than replace the per-cell criterion.
    report['bare_shaft_radial_first_moment_kgmm']=[v*design.RHO*c.y,v*design.RHO*c.z]
    report['bare_shaft_rotating_couple_kgmm2']=[-I.A12*design.RHO+v*design.RHO*c.x*c.y,
                                              -I.A13*design.RHO+v*design.RHO*c.x*c.z]
    assert max(abs(x) for x in report['bare_shaft_radial_first_moment_kgmm'])<1e-5
    assert max(abs(x) for x in report['bare_shaft_rotating_couple_kgmm2'])<1e-3
    # The entire new shaft is within radius R. At BDC the lowest piston skirt
    # is 75 mm above the crank axis: this gives a continuous rigid envelope bound.
    cylinder=Part.makeCylinder(R+1e-6,550,V(-275,0,0),V(1,0,0))
    outside=crank.cut(cylinder).Volume
    assert outside<1e-5
    report['shaft_outside_design_radius_mm3']=outside
    report['continuous_piston_vertical_clearance_lower_bound_mm']=75-R
    assert 75-R>=1
    others=[o for o in doc.Objects if o.TypeId=='PartDesign::Body' and o.Name!='Crankshaft']
    assert len(others)==82
    min_piston=(1e9,None);min_block=(1e9,None)
    for angle in range(0,360,5):
        doc.Mechanism.CrankAngle=angle;doc.recompute()
        shaft=world(doc.Crankshaft)
        compound=Part.makeCompound([world(o) for o in others])
        overlap=shaft.common(compound).Volume
        db=shaft.distToShape(world(doc.CylinderBlock))[0]
        dp=min(shaft.distToShape(world(doc.getObject(f'Piston{i}')))[0] for i in range(1,5))
        if dp<min_piston[0]:min_piston=(dp,angle)
        if db<min_block[0]:min_block=(db,angle)
        report['motion'].append({'angle_deg':angle,'shaft_other_overlap_mm3':overlap,
                                 'piston_clearance_mm':dp,'block_clearance_mm':db})
        if overlap>1e-5:
            report['collisions']=[{'object':o.Name,'volume':shaft.common(world(o)).Volume} for o in others if shaft.common(world(o)).Volume>1e-5]
        assert overlap<1e-5 and dp>=1 and db>=1,(angle,overlap,dp,db)
        if angle%30==0:save()
    report['sampled_min_piston_clearance_mm_and_angle']=min_piston
    report['sampled_min_block_clearance_mm_and_angle']=min_block
    native=App.openDocument(str(ROOT/'crankshaft.FCStd'))
    body=next(o for o in native.Objects if o.TypeId=='PartDesign::Body')
    native_shape=design.local(body)
    exported=Part.Shape();exported.read(str(ROOT/'crankshaft.step'))
    a=crank.cut(native_shape).Volume+native_shape.cut(crank).Volume
    b=crank.cut(exported).Volume+exported.cut(crank).Volume
    assert a<1e-5 and b<1e-5 and exported.isValid()
    report['native_reopen_two_way_difference_mm3']=a
    report['step_two_way_difference_mm3']=b
    report['source_unchanged']=hashlib.sha256((ROOT.parent/'inline_four_short_block.FCStd').read_bytes()).hexdigest()==cfg['source_sha256']
    assert report['source_unchanged']
    # All nonshaft source solids must be unchanged in their own local coordinates.
    source=App.openDocument(str(ROOT.parent/'inline_four_short_block.FCStd'))
    changed=[]
    for o in others:
        a=design.local(o);b=design.local(source.getObject(o.Name))
        if a.cut(b).Volume+b.cut(a).Volume>1e-5:changed.append(o.Name)
    report['changed_nonshaft_components']=changed;assert not changed
    report['passed']=True
except Exception:
    report['error']=traceback.format_exc();traceback.print_exc()
finally:save()
print('COUNTERWEIGHT_VERIFICATION',report['passed'],flush=True)
