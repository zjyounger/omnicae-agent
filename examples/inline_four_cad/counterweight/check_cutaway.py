import sys,json
from pathlib import Path
import FreeCAD as App
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import design
a=App.openDocument(str(ROOT/'short_block.FCStd'))
b=App.openDocument(str(ROOT/'short_block_cutaway.FCStd'))
r=[]
for angle in (0,35,90,180,270,355):
    a.Mechanism.CrankAngle=angle;b.Mechanism.CrankAngle=angle
    a.recompute();b.recompute()
    sa=a.Crankshaft.Shape.copy();sa.Placement=a.Crankshaft.getGlobalPlacement()
    sb=b.Crankshaft.Shape.copy();sb.Placement=b.Crankshaft.getGlobalPlacement()
    diff=sa.cut(sb).Volume+sb.cut(sa).Volume
    assert diff<1e-5,(angle,diff)
    r.append({'angle':angle,'uncut_vs_cutaway_shaft_difference_mm3':diff})
(ROOT/'cutaway_verification.json').write_text(json.dumps({'passed':True,'samples':r},indent=2))
