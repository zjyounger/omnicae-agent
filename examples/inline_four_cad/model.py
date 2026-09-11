"""Original inline-four mechanism, generated with native FreeCAD features.

Run build.FCMacro in FreeCAD. The resulting file needs no Python proxy to
reopen, inspect, edit its feature tree, or change the mechanism angle.
"""
import json
import math
import os
import time
from pathlib import Path

import FreeCAD as App
import Part
import Sketcher

V = App.Vector
YZ = App.Rotation(V(1, 1, 1), 120)  # sketch x->Y, y->Z, normal->X
XY = App.Rotation()
P = dict(bore=86.0, piston_diameter=85.92, stroke=86.0, pitch=96.0,
         rod_length=143.0, main_diameter=55.0, crankpin_diameter=48.0,
         wristpin_diameter=22.0, angle=35.0)
COLORS = {'crank': (0.29, 0.34, 0.40), 'piston': (0.81, 0.84, 0.88),
          'rod': (0.68, 0.72, 0.78), 'cap': (0.49, 0.54, 0.61),
          'bearing': (0.81, 0.61, 0.30), 'ring': (0.20, 0.24, 0.29),
          'pin': (0.72, 0.77, 0.83), 'bolt': (0.22, 0.25, 0.29)}


def point(p):
    return V(p[0], p[1], 0)


def polygon(points):
    return [Part.LineSegment(point(a), point(b))
            for a, b in zip(points, points[1:] + points[:1])]


def rectangle(x0, y0, x1, y1):
    return polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])


def circles(*specs):
    return [Part.Circle(V(x, y, 0), V(0, 0, 1), r) for x, y, r in specs]


def arc(a, m, b):
    return Part.Arc(point(a), point(m), point(b))


def body(doc, name, label, color, parent=None):
    obj = doc.addObject('PartDesign::Body', name)
    obj.Label = label
    if parent:
        parent.addObject(obj)
    obj.addProperty('App::PropertyString', 'ComponentRole', 'Identification')
    obj.ComponentRole = color
    obj.ViewObject.ShapeColor = COLORS[color]
    obj.ViewObject.LineColor = (0.10, 0.12, 0.15)
    obj.ViewObject.DisplayMode = 'Flat Lines'
    obj.ViewObject.Deviation = 0.12
    return obj


def feature(obj, label, geometry, origin, rotation, length, pocket=False, reversed=False):
    doc = obj.Document
    previous = obj.Tip
    sk = doc.addObject('Sketcher::SketchObject', obj.Name + '_Profile')
    obj.addObject(sk)
    sk.Label = label + ' — profile'
    sk.Placement = App.Placement(V(*origin), rotation)
    sk.addGeometry(geometry, False)
    doc.recompute()
    f = obj.newObject('PartDesign::Pocket' if pocket else 'PartDesign::Pad',
                      obj.Name + ('_Pocket' if pocket else '_Pad'))
    f.Label = label
    f.Profile = sk
    f.Length = length
    f.Reversed = reversed
    f.Refine = True
    doc.recompute()
    if f.Shape.isNull() or not f.Shape.isValid() or len(f.Shape.Solids) != 1:
        raise RuntimeError('Invalid feature: ' + obj.Label + ' / ' + label + ' / ' + str(f.State))
    sk.Visibility = False
    if previous and previous != sk:
        previous.Visibility = False
    f.ViewObject.ShapeColor = COLORS[obj.ComponentRole]
    f.ViewObject.LineColor = (0.10, 0.12, 0.15)
    return f


def section_pad(obj, label, geometry, x, width):
    return feature(obj, label, geometry, (x, 0, 0), YZ, width)


def section_pocket(obj, label, geometry, x, depth, reverse=False):
    return feature(obj, label, geometry, (x, 0, 0), YZ, depth, True, reverse)


def half_ring(outer, inner, sign=1):
    return [arc((outer, 0), (0, sign * outer), (-outer, 0)),
            Part.LineSegment(V(-outer, 0, 0), V(-inner, 0, 0)),
            arc((-inner, 0), (0, sign * inner), (inner, 0)),
            Part.LineSegment(V(inner, 0, 0), V(outer, 0, 0))]


def web_profile(sign):
    r = P['stroke'] / 2
    def t(p):
        return (p[0], p[1] * sign)
    a, b = (-27, r), (27, r)
    pts = [b, (35, 10), (46, -26)]
    result = [arc(t(a), t((0, r + 27)), t(b))]
    result += [Part.LineSegment(point(t(u)), point(t(v))) for u, v in zip(pts, pts[1:])]
    result += [arc(t((46, -26)), t((0, -72)), t((-46, -26)))]
    result += [Part.LineSegment(point(t(u)), point(t(v)))
               for u, v in zip([(-46, -26), (-35, 10), a], [(-35, 10), a])]
    return result


def crankshaft(doc):
    b = body(doc, 'Crankshaft', '01 · Crankshaft / five mains / four throws', 'crank')
    p = P['pitch']
    mains = [(i - 2) * p for i in range(5)]
    cs = [(i - 1.5) * p for i in range(4)]
    main_r = P['main_diameter'] / 2
    section_pad(b, 'Main journal 1', circles((0, 0, main_r)), mains[0] - 14, 28)
    for i, (cx, s) in enumerate(zip(cs, (1, -1, -1, 1))):
        section_pad(b, f'Throw {i+1} / front web and counterweight', web_profile(s), cx - 34, 20)
        section_pad(b, f'Throw {i+1} / crankpin', circles((0, s*P['stroke']/2, 24)), cx-14, 28)
        section_pad(b, f'Throw {i+1} / rear web and counterweight', web_profile(s), cx+14, 20)
        section_pad(b, f'Main journal {i+2}', circles((0, 0, main_r)), mains[i+1]-14, 28)
    section_pad(b, 'Front seal journal', circles((0, 0, 23)), mains[0]-35, 21)
    section_pad(b, 'Pulley nose', circles((0, 0, 17)), mains[0]-65, 30)
    section_pad(b, 'Rear seal journal', circles((0, 0, 32)), mains[-1]+14, 20)
    section_pad(b, 'Flywheel mounting flange', circles((0, 0, 48)), mains[-1]+34, 12)
    section_pocket(b, 'Pilot bearing seat', circles((0, 0, 12)), mains[-1]+46, 18)
    holes = [(36*math.cos(a*math.pi/3), 36*math.sin(a*math.pi/3), 4.2) for a in range(6)]
    section_pocket(b, 'Six flywheel bolt bores', circles(*holes), mains[-1]+46, 12)
    b.setExpression('Placement.Rotation.Angle', 'Mechanism.CrankAngle')
    return b


def rod_profile():
    rb, rs, length = 32, 18, P['rod_length']
    alpha = math.asin((rb-rs)/length)
    br = (rb*math.cos(alpha), rb*math.sin(alpha))
    sr = (rs*math.cos(alpha), length+rs*math.sin(alpha))
    bl, sl = (-br[0], br[1]), (-sr[0], sr[1])
    return [arc(br, (0,-rb), bl), Part.LineSegment(point(bl), point(sl)),
            arc(sl, (0,length+rs), sr), Part.LineSegment(point(sr), point(br))]


def connecting_rod(doc, parent, index):
    length = P['rod_length']
    b = body(doc, f'Rod{index}', f'{index} · Connecting rod / recessed beam', 'rod', parent)
    section_pad(b, 'Forging outline', rod_profile(), -12, 24)
    section_pad(b, 'Cap bolt shoulders', rectangle(-39, -12, -25, 18)+rectangle(25,-12,39,18), -12, 24)
    section_pocket(b, 'Big and small end bores', circles((0,0,26.05),(0,length,14.525)), 12, 24)
    recess = polygon([(-15,36),(15,36),(10,length-25),(-10,length-25)])
    section_pocket(b, 'Front beam relief', recess, 12, 7)
    section_pocket(b, 'Rear beam relief', recess, -12, 7, True)
    feature(b, 'Cap split plane', rectangle(-30,-50,30,50), (0,0,0.15), XY, 50, True)
    feature(b, 'Two cap bolt bores', circles((0,-33,4.2),(0,33,4.2)), (0,0,19), XY, 22, True)
    cap = body(doc, f'RodCap{index}', f'{index} · Separate connecting-rod cap', 'cap', parent)
    section_pad(cap, 'Big end annulus', circles((0,0,32),(0,0,26.05)), -12, 24)
    section_pad(cap, 'Bolt seats', rectangle(-39,-16,-25,0)+rectangle(25,-16,39,0), -12, 24)
    section_pocket(cap, 'Finish bearing bore through bolt seats', circles((0,0,26.05)), 12, 24)
    feature(cap, 'Split face', rectangle(-30,-50,30,50), (0,0,-0.15), XY, 70, True, True)
    feature(cap, 'Bolt clearance bores', circles((0,-33,4.2),(0,33,4.2)), (0,0,1), XY, 30, True)
    for j, s in enumerate((1,-1)):
        shell = body(doc,f'BigEndBearing{index}_{j}',f'{index} · Big-end bearing / half {j+1}','bearing',parent)
        section_pad(shell, 'Bearing half', half_ring(26.00,24.03,s), -11.5,23)
    bush = body(doc,f'SmallEndBush{index}',f'{index} · Small-end bronze bush','bearing',parent)
    section_pad(bush,'Small-end bush',circles((0,length,14.50),(0,length,11.03)),-12,24)
    for j,y in enumerate((-33,33)):
        bolt=body(doc,f'CapBolt{index}_{j}',f'{index} · Cap bolt {j+1} / threads omitted','bolt',parent)
        feature(bolt,'Bolt shank',circles((0,y,4)),(0,0,-16),XY,33)
        feature(bolt,'Bolt head',polygon([(5.7*math.cos(k*math.pi/3),y+5.7*math.sin(k*math.pi/3)) for k in range(6)]),(0,0,-22),XY,6)
    return b,cap


def piston(doc,parent,index):
    radius=P['piston_diameter']/2
    b=body(doc,f'Piston{index}',f'{index} · Piston / hollow skirt / pin bosses','piston',parent)
    feature(b,'Crown and skirt blank',circles((0,0,radius)),(0,0,-25),XY,56)
    feature(b,'Open underside / crown thickness 8',circles((0,0,35)),(0,0,-25),XY,48,True,True)
    section_pad(b,'Left wrist-pin boss',circles((0,0,17)),-38,22)
    section_pad(b,'Right wrist-pin boss',circles((0,0,17)),16,22)
    section_pocket(b,'Wrist-pin through bore',circles((0,0,11.025)),44,88)
    feature(b,'Shallow crown dish',circles((0,0,25)),(0,0,31),XY,1.5,True)
    grooves=[(25,1.3,40.3),(21,1.5,40.3),(15,2.7,39.8)]
    for j,(z,h,root) in enumerate(grooves):
        feature(b,f'Ring groove {j+1}',circles((0,0,44),(0,0,root)),(0,0,z+h),XY,h,True)
    pin=body(doc,f'WristPin{index}',f'{index} · Hollow wrist pin','pin',parent)
    section_pad(pin,'Hollow pin',circles((0,0,11),(0,0,7.2)),-32,64)
    for j,(z,h,root) in enumerate(grooves):
        ring=body(doc,f'PistonRing{index}_{j}',f'{index} · Split piston ring {j+1}','ring',parent)
        feature(ring,'Ring section',circles((0,0,42.99),(0,0,root+0.15)),(0,0,z+0.15),XY,h-0.3)
        feature(ring,'Visible end gap',rectangle(-0.3,-45,0.3,-38),(0,0,z+h),XY,h+1,True)
    return b


def mechanism_groups(doc):
    crank=crankshaft(doc)
    crank.Placement.Rotation.Axis=V(1,0,0)
    groups=[]
    for i,s in enumerate((1,-1,-1,1),1):
        rg=doc.addObject('App::Part',f'RodAssembly{i}')
        rg.Label=f'{i+1:02d} · Cylinder {i} / rod and bearings'
        pg=doc.addObject('App::Part',f'PistonAssembly{i}')
        pg.Label=f'{i+5:02d} · Cylinder {i} / piston and rings'
        x=(i-2.5)*P['pitch']
        for g in (rg,pg):
            g.Placement.Base.x=x
        rg.Placement.Rotation.Axis=V(1,0,0)
        rg.setExpression('Placement.Base.y',f'-{s} * Mechanism.CrankRadius * sin(Mechanism.CrankAngle)')
        rg.setExpression('Placement.Base.z',f'{s} * Mechanism.CrankRadius * cos(Mechanism.CrankAngle)')
        rg.setExpression('Placement.Rotation.Angle',f'-asin({s} * Mechanism.CrankRadius * sin(Mechanism.CrankAngle) / Mechanism.RodLength)')
        pg.setExpression('Placement.Base.z',f'{s} * Mechanism.CrankRadius * cos(Mechanism.CrankAngle) + sqrt(Mechanism.RodLength^2 - (Mechanism.CrankRadius * sin(Mechanism.CrankAngle))^2)')
        connecting_rod(doc,rg,i)
        piston(doc,pg,i)
        groups.extend([rg,pg])
        print('CYLINDER_COMPLETE',i,flush=True)
    return crank,groups


def world_shape(obj):
    shape=obj.Shape.copy()
    shape.Placement=obj.getGlobalPlacement()
    return shape


def validate(doc,root):
    components=[o for o in doc.Objects if o.TypeId=='PartDesign::Body']
    data={'parameters':P,'freecad_version':App.Version(),'components':[]}
    for o in components:
        data['components'].append(dict(name=o.Name,label=o.Label,valid=o.Shape.isValid(),
            solids=len(o.Shape.Solids),volume_mm3=o.Shape.Volume))
    assert all(c['valid'] and c['solids']==1 and c['volume_mm3']>0 for c in data['components'])
    data['motion_samples']=[]
    for angle in range(0,361,15):
        doc.Mechanism.CrankAngle=angle
        doc.recompute()
        heights=[]
        errors=[]
        for i in range(1,5):
            rp=doc.getObject(f'RodAssembly{i}').Placement
            pp=doc.getObject(f'PistonAssembly{i}').Placement
            rodtop=rp.multVec(V(0,0,P['rod_length']))
            errors.append((rodtop-pp.Base).Length)
            heights.append(pp.Base.z)
        assert max(errors)<1e-7,(angle,errors)
        assert abs(heights[0]-heights[3])<1e-9 and abs(heights[1]-heights[2])<1e-9
        data['motion_samples'].append(dict(angle_deg=angle,pin_z_mm=heights,closure_error_mm=max(errors)))
    data['measured_strokes_mm']=[max(s['pin_z_mm'][i] for s in data['motion_samples'])-min(s['pin_z_mm'][i] for s in data['motion_samples']) for i in range(4)]
    assert all(abs(x-P['stroke'])<1e-8 for x in data['measured_strokes_mm'])
    doc.Mechanism.CrankAngle=P['angle']
    doc.recompute()
    (root/'verification.json').write_text(json.dumps(data,indent=2))
    return components,data


def build(directory):
    root=Path(directory)
    started=time.time()
    try:
        doc=App.newDocument('InlineFourRotatingAssembly')
        params=doc.addObject('App::FeaturePython','Mechanism')
        params.Label='00 · Mechanism / edit CrankAngle'
        params.addProperty('App::PropertyAngle','CrankAngle','Motion')
        params.CrankAngle=P['angle']
        for name,val in [('CrankRadius',P['stroke']/2),('RodLength',P['rod_length']),('Bore',P['bore']),('CylinderPitch',P['pitch'])]:
            params.addProperty('App::PropertyLength',name,'Design dimensions')
            setattr(params,name,val)
            params.setEditorMode(name,1)
        mechanism_groups(doc)
        components,data=validate(doc,root)
        import FreeCADGui as Gui
        Gui.activeDocument().activeView().viewAxonometric()
        Gui.activeDocument().activeView().fitAll()
        Gui.activeDocument().activeView().setAnimationEnabled(False) if hasattr(Gui.activeDocument().activeView(),'setAnimationEnabled') else None
        doc.recompute()
        doc.saveAs(str(root/'inline_four_rotating_assembly.FCStd'))
        # Export the actually placed individual solids; avoid exporting hidden feature history.
        exports=[]
        for o in components:
            f=doc.addObject('Part::Feature','Export_'+o.Name)
            f.Label=o.Label
            f.Shape=world_shape(o)
            exports.append(f)
        import Import
        Import.export(exports,str(root/'inline_four_rotating_assembly.step'))
        for f in exports:
            doc.removeObject(f.Name)
        doc.recompute()
        for o in components:
            o.Visibility=True
        Gui.activeDocument().activeView().fitAll()
        Gui.updateGui()
        Gui.activeDocument().activeView().saveImage(str(root/'assembly.png'),1800,1200,'White')
        data['build_seconds']=time.time()-started
        data['feature_count']=sum(o.TypeId in ('PartDesign::Pad','PartDesign::Pocket') for o in doc.Objects)
        data['sketch_count']=sum(o.TypeId=='Sketcher::SketchObject' for o in doc.Objects)
        (root/'verification.json').write_text(json.dumps(data,indent=2))
        (root/'build_complete.json').write_text(json.dumps({'ok':True,'components':len(components),'seconds':data['build_seconds']}))
        print('BUILD_COMPLETE',json.dumps({'components':len(components),'seconds':data['build_seconds']}),flush=True)
    except Exception:
        import traceback
        (root/'build_error.txt').write_text(traceback.format_exc())
        traceback.print_exc()
