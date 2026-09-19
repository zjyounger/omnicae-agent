"""Run with FreeCADCmd. Export source BReps and actual native motion to Blender."""
import hashlib
import json
import math
import traceback
from pathlib import Path
import FreeCAD as App
import Part

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parent/'short_block_cutaway.FCStd'

def placement(o):
    p=o.getGlobalPlacement()
    return {'p':[p.Base.x/1000,p.Base.y/1000,p.Base.z/1000],
            'q':[p.Rotation.Q[3],*p.Rotation.Q[:3]]}

def main():
    doc=App.openDocument(str(SOURCE))
    doc.Mechanism.CrankAngle=0;doc.recompute()
    objects=[o for o in doc.Objects if o.TypeId in ('PartDesign::Body','Part::Cut') and o.Visibility]
    records=[]
    for o in objects:
        s=o.Shape.copy();s.Placement=App.Placement()
        verts,tri=s.tessellate(0.12)
        records.append({'name':o.Name,'label':o.Label,
                        'verts':[[v.x/1000,v.y/1000,v.z/1000] for v in verts],
                        'faces':tri,'placement':placement(o)})
    motion=[]
    for frame in range(241):
        # App::PropertyAngle clamps values above 360 in this document. Keep
        # the four-stroke cycle angle separate from the native mechanical angle.
        mechanical_angle=(frame*3)%360
        doc.Mechanism.CrankAngle=mechanical_angle;doc.recompute()
        assert abs(doc.Mechanism.CrankAngle.Value-mechanical_angle)<1e-8
        motion.append({'frame':frame+1,'angle_deg':frame*3,
                       'objects':{o.Name:placement(o) for o in objects}})
    # Supplemental head and plugs are display BReps, distinct from source CAD.
    head=Part.makeBox(432,152,35,App.Vector(-216,-76,218))
    for x in (-144,-48,48,144):
        head=head.cut(Part.makeCylinder(38,12,App.Vector(x,0,218)))
        head=head.cut(Part.makeCylinder(6,30,App.Vector(x,0,230)))
    for x in (-192,-96,0,96,192):
        for y in (-66,66):
            head=head.cut(Part.makeCylinder(5.25,36,App.Vector(x,y,218)))
    front=Part.makeBox(600,150,100,App.Vector(-300,-150,210))
    head=head.cut(front)
    supplements=[('DisplayHead',head)]
    for i,x in enumerate((-144,-48,48,144),1):
        shell=Part.makeCylinder(5.9,18,App.Vector(x,0,231))
        shell=shell.cut(Part.makeCylinder(3.3,19,App.Vector(x,0,230.5)))
        insulator=Part.makeCylinder(3.2,34,App.Vector(x,0,228))
        for z in (251,254,257,260):
            insulator=insulator.fuse(Part.makeCylinder(4.1,1.2,App.Vector(x,0,z)))
        terminal=Part.makeCylinder(2.3,6,App.Vector(x,0,262))
        electrode=Part.makeCylinder(0.7,3,App.Vector(x,0,225))
        ground=Part.makeBox(1.3,1.3,6.5,App.Vector(x+3.4,-0.65,224.5))
        ground=ground.fuse(Part.makeBox(3.4,1.3,1,App.Vector(x+0.4,-0.65,224.5)))
        supplements.extend([(f'PlugShell{i}',shell),(f'PlugCeramic{i}',insulator),
                            (f'PlugTerminal{i}',terminal),(f'PlugElectrode{i}',electrode),
                            (f'PlugGround{i}',ground)])
    for name,s in supplements:
        assert s.isValid() and s.Volume>0,name
        verts,tri=s.tessellate(0.08)
        records.append({'name':name,'label':name,'verts':[[v.x/1000,v.y/1000,v.z/1000] for v in verts],
                        'faces':tri,'placement':{'p':[0,0,0],'q':[1,0,0,0]},'supplemental':True})
    data={'source':SOURCE.name,'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
          'units':'metres','components':records,'motion':motion}
    (ROOT/'cad_scene.json').write_text(json.dumps(data,separators=(',',':')))
    (ROOT/'cad_export_report.json').write_text(json.dumps({
        'source_sha256':data['source_sha256'],'cad_components':len(objects),
        'display_components':len(supplements),'frames':len(motion),
        'triangles':sum(len(r['faces']) for r in records)},indent=2))
    print('EXPORT_COMPLETE',len(records),flush=True)

try:main()
except Exception:
    (ROOT/'cad_export_error.txt').write_text(traceback.format_exc());raise
