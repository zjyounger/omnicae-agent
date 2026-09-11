"""Freeze named boundaries on the original 83-body CAD; run with FreeCADCmd."""
from pathlib import Path
from collections import defaultdict
import csv, hashlib, json, math, re
import FreeCAD as App
import Part
ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / 'inline_four_short_block.FCStd'
OUTPUT = ROOT / 'inline_four_2l_short_block_named_v1.FCStd'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def xyz(v):
    return [float(x) for x in v]

def signature(f):
    b = f.optimalBoundingBox(False, False)
    s = f.Surface
    result = dict(type=type(s).__name__, area_mm2=f.Area,
                  centroid_mm=xyz(f.CenterOfMass),
                  bounds_mm=[b.XMin,b.YMin,b.ZMin,b.XMax,b.YMax,b.ZMax])
    if isinstance(s, Part.Cylinder):
        result.update(radius_mm=s.Radius, axis=xyz(s.Axis), axis_point_mm=xyz(s.Center))
    if isinstance(s, Part.Plane):
        result['normal'] = xyz(f.normalAt(*[sum(f.ParameterRange[i:i+2])/2 for i in (0,2)]))
    return result

def near(a,b): return abs(a-b)<1e-5

def station(x, values):
    matches=[i for i,v in enumerate(values,1) if near(x,v)]
    assert len(matches)==1, (x,values)
    return matches[0]

CYL=(-144,-48,48,144)
MAIN=(-192,-96,0,96,192)

def role(name,f):
    s=f.Surface;c=f.CenterOfMass
    cylinder=isinstance(s,Part.Cylinder)
    plane=isinstance(s,Part.Plane)
    zplane=plane and abs(s.Axis.z)>0.999999
    if name=='CylinderBlock':
        if zplane and near(c.z,218):return 'deck_gasket_face'
        if zplane and near(c.z,-90):return 'oil_pan_gasket_face'
        if cylinder and abs(s.Axis.z)>.999999:
            if near(s.Radius,43):return 'cylinder_%02d_bore_wall'%station(s.Center.x,CYL)
            if near(s.Radius,47):return 'cylinder_%02d_coolant_barrel_wall'%station(s.Center.x,CYL)
            if near(s.Radius,3):return 'deck_coolant_passage_walls'
            if near(s.Radius,3.25):return 'oil_pan_bolt_hole_walls'
            if near(s.Radius,5.25):
                if near(abs(s.Center.y),66):return 'head_bolt_hole_walls'
                if near(abs(s.Center.y),48):return 'main_cap_bolt_hole_walls'
        if cylinder and abs(s.Axis.x)>.999999 and near(s.Radius,30.025):
            if any(near(c.x,x) for x in MAIN):return 'main_%02d_upper_housing_seat'%station(c.x,MAIN)
    if name=='Crankshaft' and cylinder and abs(s.Axis.x)>.999999:
        if near(s.Radius,27.5):return 'main_%02d_journal'%station(c.x,MAIN)
        if near(s.Radius,24):return 'cylinder_%02d_crankpin'%station(c.x,CYL)
    if re.fullmatch(r'Piston[1-4]',name):
        if zplane and near(c.z,31):return 'crown_top_land'
        if zplane and near(c.z,29.5):return 'crown_bowl_floor'
        if cylinder and near(s.Radius,25) and abs(s.Axis.z)>.999999:return 'crown_bowl_wall'
        if cylinder and near(s.Radius,11.025):return 'wrist_pin_bore'
        if cylinder and near(s.Radius,42.96):return 'outer_lands_and_skirt'
    if name.startswith('MainBearing') and cylinder:
        if near(s.Radius,27.53):return 'journal_running_surface'
        if near(s.Radius,29.98):return 'housing_contact_surface'
    return None

source_hash=sha(SOURCE)
doc=App.openDocument(str(SOURCE));doc.Mechanism.CrankAngle=0;doc.recompute()
doc.Label='Inline-four 2.0 L | short-block CAD reference v1 | named surfaces'
bodies=[o for o in doc.Objects if o.TypeId=='PartDesign::Body'];assert len(bodies)==83
registry=doc.addObject('App::DocumentObjectGroup','NamedSurfaces')
registry.Label='Named surfaces | geometric selections, no BC values assigned'
entries=[];groups=defaultdict(list);original={}
for body in bodies:
    local=body.Shape.copy();local.Placement=App.Placement();original[body.Name]=local
    part_id=re.sub(r'(?<!^)(?=[A-Z])','_',body.Name).lower()
    names=[]
    for index,face in enumerate(local.Faces,1):
        semantic=role(body.Name,face)
        kind=type(face.Surface).__name__.lower()
        name=f'{part_id}__{semantic or kind}__f{index:03d}'
        names.append(name)
        world=face.copy();world.Placement=body.getGlobalPlacement()
        entries.append(dict(name=name,part=body.Name,part_label=body.Label,
                            subelement=f'Face{index}',semantic_group=f'{part_id}__{semantic}' if semantic else None,
                            local=signature(face),world_at_zero_deg=signature(world)))
        if semantic:groups[(body.Name,f'{part_id}__{semantic}')].append(f'Face{index}')
    body.addProperty('App::PropertyStringList','SurfaceNames','Surface archive',
                     'Entry N names FaceN in this frozen version. Revalidate after geometry edits.')
    body.SurfaceNames=names;body.setEditorMode('SurfaceNames',1)
for (part,name),refs in groups.items():
    obj=doc.addObject('App::FeaturePython','Surface_'+name)
    obj.Label=name
    obj.addProperty('App::PropertyLinkSubGlobal','References','Boundary selection')
    obj.References=(doc.getObject(part),refs)
    obj.addProperty('App::PropertyString','Purpose','Boundary selection')
    obj.Purpose='Geometric selection only; assign physics and mesh sets in the analysis case.'
    registry.addObject(obj)
doc.recompute();doc.saveAs(str(OUTPUT));App.closeDocument(doc.Name)
# Read actual persisted names, references and geometry back.
check=App.openDocument(str(OUTPUT));assert len(check.NamedSurfaces.Group)==len(groups)
max_difference=0
for name,old in original.items():
    body=check.getObject(name);new=body.Shape.copy();new.Placement=App.Placement()
    assert new.isValid() and len(new.Solids)==1
    assert len(new.Faces)==len(body.SurfaceNames)==len(old.Faces)
    difference=old.cut(new).Volume+new.cut(old).Volume
    max_difference=max(max_difference,difference);assert difference<1e-5
    for i,face in enumerate(new.Faces):
        assert near(face.Area,old.Faces[i].Area)
        assert (face.CenterOfMass-old.Faces[i].CenterOfMass).Length<1e-6
for obj in check.NamedSurfaces.Group:
    body,refs=obj.References
    assert refs and all(body.Shape.getElement(ref).Area>0 for ref in refs)
assert len({e['name'] for e in entries})==len(entries)
# Independent nominal-area checks catch selection of an end face or missing crown bowl.
area_checks={}
for (part,name),refs in groups.items():
    total=sum(check.getObject(part).Shape.getElement(r).Area for r in refs)
    expected=None
    if part=='Crankshaft' and name.endswith('_journal'):expected=2*math.pi*27.5*28
    if part=='Crankshaft' and name.endswith('_crankpin'):expected=2*math.pi*24*28
    if part.startswith('Piston') and name.endswith('crown_bowl_floor'):expected=math.pi*25**2
    if expected is not None:
        assert abs(total-expected)<1e-5,(name,total,expected)
        area_checks[name]={'measured_mm2':total,'nominal_mm2':expected}
assert len(area_checks)==13
assert sum('cylinder_' in name and name.endswith('_bore_wall') for _,name in groups)==4
assert sha(SOURCE)==source_hash
catalog=dict(example='inline_four_2l_short_block_named_v1',units='mm',crank_angle_deg=0,
             source='../'+SOURCE.name,source_sha256=source_hash,native_sha256=sha(OUTPUT),
             policy='Frozen-version names. Face indices and signatures must be revalidated after CAD edits, STEP import or meshing. Generic names describe geometry only.',
             faces=entries,
             groups=[dict(name=name,part=part,subelements=refs) for (part,name),refs in groups.items()])
(ROOT/'surface_catalog.json').write_text(json.dumps(catalog,indent=2)+'\n')
with (ROOT/'surface_catalog.csv').open('w') as stream:
    writer=csv.writer(stream);writer.writerow(['surface_name','part','face','semantic_group','type','area_mm2','local_cx_mm','local_cy_mm','local_cz_mm'])
    for e in entries:writer.writerow([e['name'],e['part'],e['subelement'],e['semantic_group'] or '',e['local']['type'],e['local']['area_mm2'],*e['local']['centroid_mm']])
report=dict(passed=True,body_count=len(bodies),named_face_count=len(entries),semantic_group_count=len(groups),
            semantically_grouped_face_count=sum(len(r) for r in groups.values()),
            max_body_two_way_difference_mm3=max_difference,source_unchanged=True,
            saved_reopened_references_valid=True,nominal_area_checks=area_checks)
(ROOT/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print('NAMED_SURFACES',json.dumps({k:v for k,v in report.items() if k!='nominal_area_checks'}),flush=True)
