"""Native PartDesign cylinder block matched to the original rotating assembly."""
import hashlib
import json
import math
import time
from pathlib import Path

import FreeCAD as App
import FreeCADGui as Gui
import Part
from PySide import QtCore

from model import body, feature, section_pad, section_pocket, circles, rectangle, polygon, half_ring, XY, YZ, COLORS, world_shape

V=App.Vector
XZ=App.Rotation(V(1,0,0),90)  # local x=X, y=Z, normal=-Y
CYLINDERS=(-144,-48,48,144)
MAINS=(-192,-96,0,96,192)
COLORS.update(block=(0.29,0.45,0.52),maincap=(0.34,0.42,0.47),plug=(0.66,0.70,0.74))


def block_body(doc):
    b=body(doc,'CylinderBlock','10 · Cylinder block / closed deck / deep skirt','block')
    outer=polygon([(-100,-90),(100,-90),(100,10),(76,100),(-76,100),(-100,10)])
    section_pad(b,'Crankcase outer casting envelope',outer,-222,444)
    feature(b,'Cylinder bank and deck blank',rectangle(-216,-76,216,76),(0,0,90),XY,128)
    frame=rectangle(-230,-112,230,112)+rectangle(-210,-88,210,88)
    feature(b,'Oil-pan mounting rail',frame,(0,0,-90),XY,8)
    core=polygon([(-88,-92),(88,-92),(88,8),(64,98),(-64,98),(-88,8)])
    section_pocket(b,'Open crankcase core',core,210,420)

    # Add the five upper bearing webs AFTER coring the crankcase.
    saddle=polygon([(-94,0),(94,0),(73,100),(-73,100)])
    for i,x in enumerate(MAINS,1):
        section_pad(b,f'Main bearing bulkhead {i}',saddle,x-12,24)
    section_pocket(b,'Line-bored main bearing tunnel',circles((0,0,30.025)),224,448)

    # A closed cavity, with four retained cylinder barrels. Adjacent barrel
    # outer diameters are 94 mm on a 96 mm pitch, so water can pass between.
    jacket=rectangle(-202,-56,202,56)+circles(*[(x,0,47) for x in CYLINDERS])
    feature(b,'Closed water-jacket core',jacket,(0,0,208),XY,90,True)
    feature(b,'Four cylinder bores / skirt relief into webs',circles(*[(x,0,43) for x in CYLINDERS]),(0,0,219),XY,149,True)
    relief=[]
    for x in CYLINDERS:
        relief += rectangle(x-16,-46,x+16,-39)+rectangle(x-16,39,x+16,46)
    feature(b,'Eight local connecting-rod mouth reliefs',relief,(0,0,106),XY,36,True)

    bolt_bosses=circles(*[(x,y,11) for x in MAINS for y in (-66,66)])
    feature(b,'Ten head-bolt columns',bolt_bosses,(0,0,168),XY,50)
    feature(b,'Ten head-bolt pilot bores',circles(*[(x,y,5.25) for x in MAINS for y in (-66,66)]),(0,0,219),XY,41,True)
    ports=[(x,y,3) for x in CYLINDERS for y in (-51,51)]+[(-197,0,3),(197,0,3)]
    feature(b,'Deck-to-head coolant passages',circles(*ports),(0,0,219),XY,14,True)

    side_ports=circles(*[(x,166,12.5) for x in CYLINDERS])
    feature(b,'Front-side coolant core openings',side_ports,(0,-78,0),XZ,27,True)
    feature(b,'Rear-side coolant core openings',side_ports,(0,78,0),XZ,27,True,True)

    front_rib=[(-106,-78),(-106,12),(-81,104),(-74,104),(-98,10),(-98,-78)]
    for i,x in enumerate(MAINS,1):
        for side in (-1,1):
            points=[(y*(-side),z) for y,z in front_rib]
            section_pad(b,f'External bulkhead rib {i} / side {side}',polygon(points),x-5,10)

    section_pad(b,'Front seal carrier boss',circles((0,0,42)),-230,10)
    section_pad(b,'Rear seal carrier boss',circles((0,0,46)),210,14)
    # Finish openings after additions so bosses/ribs cannot refill a passage.
    section_pocket(b,'Finish front seal opening',circles((0,0,30.025)),-206,26)
    section_pocket(b,'Finish rear seal opening',circles((0,0,34.025)),225,19)

    main_holes=circles(*[(x,y,5.25) for x in MAINS for y in (-48,48)])
    feature(b,'Main-cap fastener bores',main_holes,(0,0,0),XY,25,True,True)
    pan_holes=[(x,y,3.25) for x in (-210,-140,-70,0,70,140,210) for y in (-104,104)]
    pan_holes += [(x,y,3.25) for x in (-220,220) for y in (-60,0,60)]
    feature(b,'Twenty oil-pan flange holes',circles(*pan_holes),(0,0,-90),XY,14,True,True)
    return b


def main_components(doc):
    group=doc.addObject('App::Part','MainBearingAssembly')
    group.Label='11 · Main bearing caps / shells / fasteners'
    outline=polygon([(-65,-0.15),(65,-0.15),(65,-36),(35,-36),(25,-46),(-25,-46),(-35,-36),(-65,-36)])
    for i,x in enumerate(MAINS,1):
        cap=body(doc,f'MainCap{i}',f'Main cap {i} / removable','maincap',group)
        section_pad(cap,'Cap forging',outline,x-12,24)
        section_pocket(cap,'Lower half of main tunnel',circles((0,0,30.025)),x+12,24)
        feature(cap,'Cap bolt clearance',circles((x,-48,5.25),(x,48,5.25)),(0,0,1),XY,48,True)
        for j,sign in enumerate((1,-1)):
            shell=body(doc,f'MainBearing{i}_{j}',f'Main bearing {i} / half {j+1}','bearing',group)
            section_pad(shell,'Bearing shell',half_ring(29.98,27.53,sign),x-11.5,23)
        for j,y in enumerate((-48,48)):
            bolt=body(doc,f'MainBolt{i}_{j}',f'Main cap {i} / bolt {j+1} / no thread','bolt',group)
            feature(bolt,'M10 envelope shank',circles((x,y,5)),(0,0,-36),XY,56)
            hexagon=polygon([(x+8.5*math.cos(k*math.pi/3),y+8.5*math.sin(k*math.pi/3)) for k in range(6)])
            feature(bolt,'Hex head',hexagon,(0,0,-44),XY,8)
    return group


def coolant_plugs(doc):
    group=doc.addObject('App::Part','CorePlugs')
    group.Label='12 · Eight coolant core plugs'
    for i,x in enumerate(CYLINDERS,1):
        for side in (-1,1):
            plug=body(doc,f'CorePlug{i}_{"F" if side<0 else "R"}',f'Coolant core plug {i} / side {side}','plug',group)
            feature(plug,'Cup blank',circles((x,166,12.45)),(0,side*75,0),XZ,2,reversed=side>0)
            feature(plug,'Cup recess',circles((x,166,11.4)),(0,side*77,0),XZ,1,True,reversed=side>0)
    return group


def orient(view,eye=(0.8,-1.5,1.15)):
    z=V(*eye);z.normalize()
    x=V(0,0,1).cross(z);x.normalize()
    y=z.cross(x)
    view.setCameraOrientation(App.Rotation(x,y,z,'ZXY').Q)
    view.fitAll()
    Gui.updateGui()


def copy_views(doc,root):
    components=[o for o in doc.Objects if o.TypeId=='PartDesign::Body']
    # Native linked cuts keep the source Bodies and the mechanism's editable
    # angle in the cutaway file. The full, uncut document was already saved.
    doc.Label='Inline-four · movable short-block cutaway'
    tool=doc.addObject('Part::Box','SectionTool')
    tool.Label='Display section / remove front half'
    tool.Length=600;tool.Width=150;tool.Height=400
    tool.Placement.Base=V(-300,-150,-120)
    doc.recompute()
    for o in components:
        if (o.Name.startswith('CorePlug') and o.Name.endswith('_F')) or (o.Name.startswith('MainBolt') and o.Name.endswith('_0')):
            o.Visibility=False
            continue
        if o.Name=='CylinderBlock' or o.Name.startswith(('MainCap','MainBearing')):
            f=doc.addObject('Part::Cut','Section_'+o.Name)
            f.Label=o.Label+' / display section'
            f.Base=o;f.Tool=tool
            doc.recompute()
            assert f.Shape.isValid() and not f.Shape.isNull()
            o.Visibility=False
            f.ViewObject.ShapeColor=o.ViewObject.ShapeColor
            f.ViewObject.LineColor=(0.10,0.12,0.15)
            f.ViewObject.DisplayMode='Flat Lines'
    tool.Visibility=False
    doc.recompute()
    v=Gui.activeDocument().activeView();orient(v,(0.65,-2,0.8))
    v.saveImage(str(root/'short_block_cutaway.png'),1800,1250,'White')
    doc.saveAs(str(root/'short_block_cutaway.FCStd'))


def build(directory):
    root=Path(directory);started=time.time()
    try:
        src=root/'inline_four_rotating_assembly.FCStd'
        source_hash=hashlib.sha256(src.read_bytes()).hexdigest()
        doc=App.openDocument(str(src))
        doc.Label='Inline-four · cylinder block and rotating assembly'
        App.ParamGet('User parameter:BaseApp/Preferences/View').SetBool('UseNavigationAnimations',False)
        doc.Mechanism.CrankAngle=35;doc.recompute()
        block=block_body(doc)
        main_components(doc);coolant_plugs(doc)
        doc.recompute()
        objects=[o for o in doc.Objects if o.TypeId=='PartDesign::Body']
        report={'source_sha256':source_hash,'components':[],
                'block_feature_count':sum(o.TypeId in ('PartDesign::Pad','PartDesign::Pocket') for o in block.Group)}
        for o in objects:
            report['components'].append({'name':o.Name,'valid':o.Shape.isValid(),'solids':len(o.Shape.Solids),'volume_mm3':o.Shape.Volume})
        assert all(o['valid'] and o['solids']==1 and o['volume_mm3']>0 for o in report['components'])
        v=Gui.activeDocument().activeView();orient(v)
        doc.saveAs(str(root/'inline_four_short_block.FCStd'))
        v.saveImage(str(root/'short_block_assembly.png'),1800,1250,'White')

        export=[]
        for o in objects:
            f=doc.addObject('Part::Feature','Export_'+o.Name);f.Label=o.Label;f.Shape=world_shape(o);export.append(f)
        import Import
        Import.export(export,str(root/'inline_four_short_block.step'))
        Import.export([next(f for f in export if f.Name=='Export_CylinderBlock')],str(root/'cylinder_block.step'))
        for f in export:doc.removeObject(f.Name)
        doc.recompute()

        standalone=App.newDocument('CylinderBlockNative')
        copied=standalone.copyObject(block,True)
        standalone.recompute()
        assert copied.Shape.isValid() and len(copied.Shape.Solids)==1
        v=Gui.activeDocument().activeView();orient(v)
        standalone.saveAs(str(root/'cylinder_block.FCStd'))
        v.saveImage(str(root/'cylinder_block.png'),1800,1250,'White')
        orient(v,(0.9,-1.7,-1.1))
        v.saveImage(str(root/'cylinder_block_underside.png'),1800,1250,'White')
        App.closeDocument(standalone.Name)
        App.setActiveDocument(doc.Name)
        copy_views(doc,root)
        report['build_seconds']=time.time()-started
        report['source_unchanged']=hashlib.sha256(src.read_bytes()).hexdigest()==source_hash
        (root/'block_build.json').write_text(json.dumps(report,indent=2))
        for name in list(App.listDocuments()):App.closeDocument(name)
        QtCore.QTimer.singleShot(0,QtCore.QCoreApplication.quit)
    except Exception:
        import traceback
        (root/'block_error.txt').write_text(traceback.format_exc())
        traceback.print_exc()
