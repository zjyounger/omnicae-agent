"""Native CAD counterweight design from existing rod mass and first moments."""
import json,math,sys,hashlib
from pathlib import Path
import FreeCAD as App
import Part
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent))
import model
V=App.Vector
RHO=7800e-9
L=143.

def local(o):
    s=o.Shape.copy();s.Placement=App.Placement();return s

def moments(shape):
    # Accumulate over solids; a cut/compound need not expose CenterOfMass.
    vol=sum(s.Volume for s in shape.Solids)
    c=sum((s.CenterOfMass*s.Volume for s in shape.Solids),V())/vol
    return vol,c

def profile(radius,sign=1):
    def t(y,z):return (y,sign*z)
    p=[t(-27,43),t(27,43),t(27.5,0),t(radius,0),t(-radius,0),t(-27.5,0)]
    return [model.arc(p[0],t(0,70),p[1]),
            Part.LineSegment(model.point(p[1]),model.point(p[2])),
            Part.LineSegment(model.point(p[2]),model.point(p[3])),
            model.arc(p[3],t(0,-radius),p[4]),
            Part.LineSegment(model.point(p[4]),model.point(p[5])),
            Part.LineSegment(model.point(p[5]),model.point(p[0]))]

def cell(radius):
    # One local cell along X=0..96, with crankpin at X=48, Z=43.
    f=Part.Face(Part.Wire([g.toShape() for g in profile(radius)]))
    f.Placement=App.Placement(V(14,0,0),model.YZ)
    front=f.extrude(V(20,0,0));rear=front.copy();rear.translate(V(48,0,0))
    pin=Part.makeCylinder(24,28,V(34,0,43),V(1,0,0))
    a=Part.makeCylinder(27.5,14,V(),V(1,0,0))
    b=Part.makeCylinder(27.5,14,V(82,0,0),V(1,0,0))
    return a.fuse(front).fuse(pin).fuse(rear).fuse(b).removeSplitter()

def mass_properties(doc):
    rows=[]
    names=['Rod1','RodCap1','CapBolt1_0','CapBolt1_1','BigEndBearing1_0','BigEndBearing1_1','SmallEndBush1']
    mass=0.;first=0.;inertia_origin=0.
    for name in names:
        s=local(doc.getObject(name));v,c=moments(s)
        rho=8800e-9 if name.startswith('SmallEndBush') else RHO
        m=v*rho
        # Shape inertia is centroidal; translate it to the big-end origin.
        Ixx=sum(sol.MatrixOfInertia.A11 for sol in s.Solids)*rho
        rows.append({'name':name,'mass_kg':m,'density_kg_m3':rho*1e9,
                     'cg_mm':[c.x,c.y,c.z],'Ixx_cg_kgmm2':Ixx})
        mass+=m;first+=m*c.z;inertia_origin+=Ixx+m*(c.y*c.y+c.z*c.z)
    zcg=first/mass
    big=mass-first/L;small=first/L
    actual=inertia_origin-mass*zcg*zcg
    equiv=big*zcg*zcg+small*(L-zcg)**2
    return {'components':rows,'rod_assembly_mass_kg':mass,'rod_assembly_cg_from_big_end_mm':zcg,
            'equivalent_big_end_kg':big,'equivalent_small_end_kg':small,
            'actual_rod_Ixx_cg_kgmm2':actual,'two_end_Ixx_cg_kgmm2':equiv,
            'two_end_inertia_error_percent':100*(equiv/actual-1)}

def design():
    doc=App.openDocument(str(ROOT.parent/'inline_four_short_block.FCStd'))
    report=mass_properties(doc)
    target=report['equivalent_big_end_kg']*43
    def residual(r):
        v,c=moments(cell(r));return RHO*v*c.z+target
    report['bracket']={str(r):residual(r) for r in (55,74)}
    assert residual(55)>0 and residual(74)<0,report['bracket']
    lo,hi=55.,74.
    for _ in range(36):
        mid=(lo+hi)/2
        if residual(mid)>0:lo=mid
        else:hi=mid
    exact=(lo+hi)/2;rounded=round(exact,2)
    original=local(doc.Crankshaft)
    oldcell=original.common(Part.makeBox(96,220,220,V(-192,-110,-110)))
    v,c=moments(oldcell)
    report.update({'material':'42CrMo4 +QT','density_kg_m3':7800,
        'balance_target':'100 percent equivalent rotating, zero reciprocating',
        'target_rod_moment_kgmm':target,'radius_exact_mm':exact,'radius_mm':rounded,
        'predicted_residual_kgmm':residual(rounded),'original_residual_kgmm':RHO*v*c.z+target,
        'original_shaft_mass_kg':original.Volume*RHO,
        'source_sha256':hashlib.sha256((ROOT.parent/'inline_four_short_block.FCStd').read_bytes()).hexdigest()})
    (ROOT/'design_parameters.json').write_text(json.dumps(report,indent=2))
    print('DESIGN',json.dumps(report),flush=True)
    App.closeDocument(doc.Name)
    return report

if __name__=='__main__':design()
