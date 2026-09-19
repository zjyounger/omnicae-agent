"""Blender 4.5: original CAD cutaway with native drivers and procedural ignition."""
import bpy
import ast
import json
import math
import os
import re
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.unit_settings.system='METRIC'
scene.render.engine='BLENDER_EEVEE_NEXT'
scene.render.resolution_x=1440;scene.render.resolution_y=900
scene.render.resolution_percentage=100
scene.render.fps=24;scene.frame_start=1;scene.frame_end=240
scene.eevee.taa_render_samples=64
scene.eevee.volumetric_samples=48
scene.eevee.volumetric_tile_size='8'
scene.eevee.use_gtao=True
scene.eevee.gtao_distance=0.035
scene.eevee.use_raytracing=False
scene.render.image_settings.file_format='PNG'
scene.view_settings.view_transform='AgX'
scene.world=bpy.data.worlds.new('Midnight studio')
scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(0.009,0.017,0.028,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=0.35

def collection(name):
    c=bpy.data.collections.new(name);scene.collection.children.link(c);return c
CAD=collection('01 • FreeCAD components')
HEAD=collection('02 • Display head and spark plugs')
FX=collection('03 • Ignition effects')
UI=collection('04 • Cycle diagram')
STUDIO=collection('05 • Studio')

def move_collection(o,c):
    for old in list(o.users_collection):old.objects.unlink(o)
    c.objects.link(o)

def mat(name,color,metal=0,rough=.4,emission=0):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough
    if emission:
        e=m.node_tree.nodes.new('ShaderNodeEmission')
        e.inputs['Color'].default_value=(*color,1)
        e.inputs['Strength'].default_value=emission
        m.node_tree.links.new(e.outputs[0],m.node_tree.nodes.get('Material Output').inputs['Surface'])
    return m

blockmat=mat('Cast block • deep petrol',(.045,.19,.24),.65,.32)
headmat=mat('Head • satin aluminium',(.25,.39,.43),.72,.3)
steel=mat('Forged steel',(.20,.25,.31),.83,.24)
silver=mat('Pistons • machined aluminium',(.61,.69,.77),.78,.26)
rodmat=mat('Rods • brushed steel',(.40,.47,.52),.8,.27)
gold=mat('Bearing alloy',(.56,.32,.10),.74,.27)
dark=mat('Rings and bolts',(.045,.063,.083),.75,.25)
ceramic=mat('Spark plug porcelain',(.8,.86,.87),.05,.2)
paper=mat('Type • ice',(.66,.79,.87),emission=.8)
muted=mat('Type • muted',(.19,.31,.41),emission=.7)
accent=mat('Type • amber',(1,.42,.075),emission=1.2)
panelmat=mat('Panel',(.008,.02,.035),rough=1,emission=.5)
colors=[(1,.28,.025),(.38,.22,.12),(.03,.52,.78),(.59,.32,.94)]
phase_mats=[mat(n,c,emission=.8) for n,c in zip(['POWER','EXHAUST','INTAKE','COMPRESSION'],colors)]

ctrl=bpy.data.objects.new('ENGINE CONTROLS',None);CAD.objects.link(ctrl)
ctrl['Crank angle']=0.;ctrl['Spark advance']=12
ctrl.id_properties_ui('Crank angle').update(min=0,max=720,description='Degrees; animate two turns per four-stroke cycle')
ctrl.id_properties_ui('Spark advance').update(min=0,max=35,description='Illustrative degrees before compression TDC')
ctrl['Crank angle']=0.;ctrl.keyframe_insert(data_path='["Crank angle"]',frame=1)
ctrl['Crank angle']=720.;ctrl.keyframe_insert(data_path='["Crank angle"]',frame=241)
for fc in ctrl.animation_data.action.fcurves:
    for k in fc.keyframe_points:k.interpolation='LINEAR'

def drive(owner,path,expr,index=None,variables=None):
    f=owner.driver_add(path) if index is None else owner.driver_add(path,index)
    # Blender's safe native expression evaluator supports pow()/floor(), but
    # not Python ** or %. Preserve Python's nonnegative modulo semantics.
    class SimpleArithmetic(ast.NodeTransformer):
        def visit_BinOp(self,node):
            self.generic_visit(node)
            if isinstance(node.op,ast.Pow):
                return ast.Call(func=ast.Name(id='pow',ctx=ast.Load()),args=[node.left,node.right],keywords=[])
            if isinstance(node.op,ast.Mod):
                quotient=ast.BinOp(left=node.left,op=ast.Div(),right=node.right)
                floor=ast.Call(func=ast.Name(id='floor',ctx=ast.Load()),args=[quotient],keywords=[])
                return ast.BinOp(left=node.left,op=ast.Sub(),right=ast.BinOp(left=floor,op=ast.Mult(),right=node.right))
            return node
    expr=ast.unparse(SimpleArithmetic().visit(ast.parse(expr,mode='eval')))
    d=f.driver;d.type='SCRIPTED';d.expression=expr
    for name,prop in (variables or {'a':'Crank angle','v':'Spark advance'}).items():
        var=d.variables.new();var.name=name;var.type='SINGLE_PROP'
        var.targets[0].id=ctrl;var.targets[0].data_path='["'+prop+'"]'
    return f

def mesh_object(name,vertices,faces,c,m):
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.update()
    o=bpy.data.objects.new(name,mesh);c.objects.link(o);o.data.materials.append(m)
    return o

data=json.loads((ROOT/'cad_scene.json').read_text())
for r in data['components']:
    n=r['name'];supp=r.get('supplemental',False)
    material=steel
    if 'CylinderBlock' in n:material=blockmat
    elif n=='DisplayHead':material=headmat
    elif n.startswith('PlugCeramic'):material=ceramic
    elif n.startswith(('PistonRing','CapBolt','MainBolt')):material=dark
    elif n.startswith(('Piston','WristPin')):material=silver
    elif 'Bearing' in n or 'Bush' in n:material=gold
    elif n.startswith('Rod'):material=rodmat
    elif 'MainCap' in n or n.startswith('CorePlug'):material=blockmat
    o=mesh_object(n,r['verts'],r['faces'],HEAD if supp else CAD,material)
    o.location=r['placement']['p'];o.rotation_mode='QUATERNION';o.rotation_quaternion=r['placement']['q']
    o['Source']=r['label'];o['Supplemental display geometry']=supp
    # Imported face normals stay flat at CAD feature boundaries; small bevels
    # catch the studio lights without editing the CAD BRep.
    if not n.startswith(('PistonRing','Plug')):
        bevel=o.modifiers.new('Render edge highlight','BEVEL');bevel.width=.00035
        bevel.segments=2;bevel.limit_method='ANGLE';bevel.angle_limit=.52
        normal=o.modifiers.new('Weighted normals','WEIGHTED_NORMAL');normal.keep_sharp=True
    if supp or n.startswith(('Section_','MainBolt','CorePlug')):continue
    o.rotation_mode='XYZ'
    if n=='Crankshaft':drive(o,'rotation_euler','a*pi/180',0);continue
    z=r['placement']['p'][2]
    s=1 if r['placement']['p'][0] in (-.144,.144) else -1
    if abs(abs(z)-.043)<1e-7:
        drive(o,'location',f'-{s}*.043*sin(a*pi/180)',1)
        drive(o,'location',f'{s}*.043*cos(a*pi/180)',2)
        drive(o,'rotation_euler',f'-asin({s}*.043*sin(a*pi/180)/.143)',0)
    elif abs(z-.186)<1e-7 or abs(z-.1)<1e-7:
        drive(o,'location',f'{s}*.043*cos(a*pi/180)+sqrt(.143**2-(.043*sin(a*pi/180))**2)',2)
    else:raise ValueError(('Unclassified moving component',n,z))

def node_math(nodes,links,op,*args):
    n=nodes.new('ShaderNodeMath');n.operation=op
    for i,arg in enumerate(args):
        if isinstance(arg,(float,int)):n.inputs[i].default_value=arg
        else:links.new(arg,n.inputs[i])
    return n.outputs[0]

TDC=[0,540,180,360]
for i,(x,tdc) in enumerate(zip((-.144,-.048,.048,.144),TDC),1):
    s=1 if i in (1,4) else -1
    crown=f'({s}*.043*cos(a*pi/180)+sqrt(.143**2-(.043*sin(a*pi/180))**2)+.0314)'
    age=f'((a-{tdc}+v)%720)'
    bpy.ops.mesh.primitive_cylinder_add(vertices=96,radius=.0425,depth=1,location=(x,0,0))
    o=bpy.context.object;o.name=f'Flame volume {i}';move_collection(o,FX)
    drive(o,'location',f'(.2295+{crown})/2',2)
    drive(o,'scale',f'.2295-{crown}',2)
    o['Cylinder']=i;o['Compression TDC']=tdc
    m=bpy.data.materials.new(f'Flame {i} • bounded propagation');m.use_nodes=True
    o.data.materials.append(m);nodes=m.node_tree.nodes;links=m.node_tree.links;nodes.clear()
    output=nodes.new('ShaderNodeOutputMaterial')
    volume=nodes.new('ShaderNodeVolumePrincipled');links.new(volume.outputs['Volume'],output.inputs['Volume'])
    volume.inputs['Color'].default_value=(.4,.12,.012,1)
    volume.inputs['Emission Color'].default_value=(1,.19,.015,1)
    volume.inputs['Anisotropy'].default_value=.1
    pos=nodes.new('ShaderNodeNewGeometry').outputs['Position']
    xyz=nodes.new('ShaderNodeSeparateXYZ');links.new(pos,xyz.inputs[0])
    dx=node_math(nodes,links,'SUBTRACT',xyz.outputs['X'],x)
    xx=node_math(nodes,links,'MULTIPLY',dx,dx)
    yy=node_math(nodes,links,'MULTIPLY',xyz.outputs['Y'],xyz.outputs['Y'])
    radial=node_math(nodes,links,'SQRT',node_math(nodes,links,'ADD',xx,yy))
    dz=node_math(nodes,links,'SUBTRACT',xyz.outputs['Z'],.225)
    dist=node_math(nodes,links,'SQRT',node_math(nodes,links,'ADD',node_math(nodes,links,'ADD',xx,yy),node_math(nodes,links,'MULTIPLY',dz,dz)))
    # Above the deck the narrower recess bounds the chamber; below it the
    # cylinder mesh itself bounds the bore. Avoid glow leaking into the head.
    below=node_math(nodes,links,'LESS_THAN',xyz.outputs['Z'],.218)
    chamber=node_math(nodes,links,'LESS_THAN',radial,.0376)
    mask=node_math(nodes,links,'MAXIMUM',below,chamber)
    radius=nodes.new('ShaderNodeValue');radius.name='Flame front radius'
    drive(radius.outputs[0],'default_value',f'min(.19,{age}*.0016)')
    inside=node_math(nodes,links,'GREATER_THAN',radius.outputs[0],dist)
    noise=nodes.new('ShaderNodeTexNoise');noise.noise_dimensions='4D'
    noise.inputs['Scale'].default_value=210;noise.inputs['Detail'].default_value=3
    links.new(pos,noise.inputs['Vector']);drive(noise.inputs['W'],'default_value',f'{age}/35')
    texture=node_math(nodes,links,'MULTIPLY_ADD',noise.outputs['Fac'],.8,.2)
    strength=nodes.new('ShaderNodeValue');strength.name='Burn envelope'
    drive(strength.outputs[0],'default_value',f'90*min(1,{age}/8)*max(0,1-{age}/145)')
    field=node_math(nodes,links,'MULTIPLY',node_math(nodes,links,'MULTIPLY',mask,inside),texture)
    emission=node_math(nodes,links,'MULTIPLY',field,strength.outputs[0])
    links.new(emission,volume.inputs['Emission Strength'])
    links.new(node_math(nodes,links,'MULTIPLY',emission,.025),volume.inputs['Density'])
    # A magnified visible arc bridges the actual ground/central-electrode gap.
    arc=bpy.data.curves.new(f'Spark arc {i}','CURVE');arc.dimensions='3D';arc.bevel_depth=.00030;arc.bevel_resolution=3
    poly=arc.splines.new('POLY');poly.points.add(5)
    for p,co in zip(poly.points,[(x,0,.225),(x+.00035,-.0002,.2259),(x+.0007,.0002,.2255),
                               (x+.0010,-.0001,.2259),(x+.0014,0,.2256),(x+.0015,0,.2255)]):p.co=(*co,1)
    spark=bpy.data.objects.new(f'Spark {i}',arc);FX.objects.link(spark)
    sparkmat=mat(f'Spark blue-white {i}',(.35,.65,1),emission=1)
    arc.materials.append(sparkmat)
    emitter=sparkmat.node_tree.nodes.get('Emission')
    drive(emitter.inputs['Strength'],'default_value',f'65 if {age}<7 else 0')
    for axis in range(3):drive(spark,'scale',f'1 if {age}<7 else 0',axis)
    light=bpy.data.lights.new(f'Combustion light {i}','POINT');light.color=(1,.26,.045);light.shadow_soft_size=.015
    lo=bpy.data.objects.new(light.name,light);FX.objects.link(lo);lo.location=(x,-.005,.22)
    drive(light,'energy',f'3*min(1,{age}/8)*max(0,1-{age}/110)')

# Camera and broad studio lights.
bpy.ops.object.camera_add(location=(.32,-1.2,.50))
camera=bpy.context.object;camera.name='Cutaway camera';move_collection(camera,STUDIO)
target=Vector((.070,0,.113));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.type='ORTHO';camera.data.ortho_scale=.94;camera.data.lens=50;scene.camera=camera
camera.data.clip_start=.01;camera.data.clip_end=100
def area(name,pos,power,color,size):
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;d.color=color
    o=bpy.data.objects.new(name,d);STUDIO.objects.link(o);o.location=pos
    o.rotation_euler=(Vector((0,0,.1))-o.location).to_track_quat('-Z','Y').to_euler()
area('Key • softbox',(-.3,-.45,.65),11,(.71,.86,1),.55)
area('Rim • cool',(.25,.25,.5),12,(.23,.63,1),.4)
area('Fill • warm',(.5,-.2,.1),4,(1,.64,.35),.45)

# Camera-facing, editable labels and four-stroke indicator cards.
regular=bpy.data.fonts.load('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
bold=bpy.data.fonts.load('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')
def text(name,body,x,y,size,material=paper,boldface=False):
    c=bpy.data.curves.new(name,'FONT');c.body=body;c.size=size;c.font=bold if boldface else regular
    o=bpy.data.objects.new(name,c);UI.objects.link(o);o.parent=camera;o.location=(x,y,-.70)
    c.materials.append(material);return o
def rect(name,x,y,w,h,material,z=-.705):
    o=mesh_object(name,[(0,0,0),(w,0,0),(w,h,0),(0,h,0)],[(0,1,2,3)],UI,material)
    o.parent=camera;o.location=(x,y,z);return o
text('Title','INLINE FOUR',-.40,.213,.028,paper,True)
text('Subtitle','IGNITION / 720° FOUR-STROKE CYCLE',-.399,.190,.011,muted)
text('Header tag','CAD → BLENDER',.235,.226,.0085,accent,True)
text('Header note','86 mm bore × 86 mm stroke',.235,.208,.0073,muted)
rect('Header rule',-.40,.177,.80,.0007,muted)
rect('Timing panel',.219,-.134,.191,.275,panelmat)
text('Panel title','FIRING ORDER',.233,.120,.0085,muted,True)
text('Order','1   ›   3   ›   4   ›   2',.233,.097,.014,accent,True)
names=['POWER','EXHAUST','INTAKE','COMPRESSION']
for i,tdc in enumerate(TDC,1):
    y=.057-(i-1)*.042
    text(f'Cylinder label {i}',f'CYL {i:02d}',.233,y,.0095,paper,True)
    for phase,name in enumerate(names):
        label=text(f'Cylinder {i} / {name}',name,.289,y,.008,phase_mats[phase])
        for axis in range(3):drive(label,'scale',f'1 if floor(((a-{tdc})%720)/180)=={phase} else 0',axis)
    rect(f'Cylinder rule {i}',.233,y-.010,.161,.0004,muted)
text('Advance label','SPARK ADVANCE',.233,-.117,.007,muted)
for advance in range(36):
    value=text('Advance value '+str(advance),str(advance)+'° BTDC*',.331,-.117,.007,accent)
    for axis in range(3):drive(value,'scale',f'1 if v=={advance} else 0',axis)
text('Cycle caption','CYLINDER 01  /  CRANK ANGLE',-.398,-.175,.0075,muted,True)
for p,name in enumerate(names):
    x=-.397+p*.198
    rect('Cycle bar '+name,x,-.208,.193,.005,phase_mats[p])
    text('Cycle label '+name,name,x,-.197,.008,phase_mats[p],True)
    text('Cycle angle '+name,str(p*180)+'°',x,-.222,.0065,muted)
text('Cycle end','720°',.374,-.222,.0065,muted)
cursor=rect('Crank angle cursor',-.397,-.211,.0015,.012,paper,z=-.690)
drive(cursor,'location','-.397+.787*(a%720)/720',0)
text('Footer','PROCEDURAL COMBUSTION VISUALIZATION  /  SIMPLIFIED HEAD',-.398,-.248,.0063,muted)
text('Footer advance','*Illustrative setting',.284,-.248,.0063,muted)
for o in UI.objects:
    if o.location.y < -.15:o.location.y-=.019

# Number the cylinders beside the plugs, projected into the same camera view.
from bpy_extras.object_utils import world_to_camera_view
bpy.context.view_layer.update()
for i,x in enumerate((-.144,-.048,.048,.144),1):
    co=world_to_camera_view(scene,camera,Vector((x,-.012,.282)))
    text(f'Engine cylinder number {i}',str(i),(co.x-.5)*.94-.003,(co.y-.5)*.94/1.6,.009,accent,True)

scene.use_nodes=True
nodes=scene.node_tree.nodes;nodes.clear()
rl=nodes.new('CompositorNodeRLayers')
glow=nodes.new('CompositorNodeGlare');glow.glare_type='FOG_GLOW';glow.quality='MEDIUM'
glow.inputs['Threshold'].default_value=2.5
glow.inputs['Strength'].default_value=.3
comp=nodes.new('CompositorNodeComposite')
scene.node_tree.links.new(rl.outputs['Image'],glow.inputs['Image'])
scene.node_tree.links.new(glow.outputs['Image'],comp.inputs[0])
for angle,cylinder in [(168,3),(348,4),(528,2),(708,1)]:
    scene.timeline_markers.new(f'SPARK • CYL {cylinder}',frame=1+angle//3)
scene['Description']='Native CAD cutaway with procedural illustrative combustion; not CFD.'
scene['CAD source SHA256']=data['source_sha256']
scene['Firing order']='1-3-4-2';scene['Cycle degrees']=720
scene.frame_set(13)
for o in bpy.context.selected_objects:o.select_set(False)
ctrl.select_set(True);bpy.context.view_layer.objects.active=ctrl
for screen in bpy.data.screens:
    for a in screen.areas:
        if a.type=='VIEW_3D':
            a.spaces.active.region_3d.view_perspective='CAMERA'
            a.spaces.active.shading.type='RENDERED'
            a.spaces.active.overlay.show_overlays=False
            a.spaces.active.region_3d.view_camera_zoom=0
readme=ROOT/'README.md'
if readme.exists():bpy.data.texts.load(str(readme))
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'inline_four_ignition.blend'))
(ROOT/'scene_build_report.json').write_text(json.dumps({'objects':len(bpy.data.objects),
    'cad_source_components':74,'display_head_components':21,'blender':bpy.app.version_string,
    'frame_count':240,'fps':24,'source_sha256':data['source_sha256']},indent=2))
scene.render.resolution_percentage=int(os.environ.get('IGNITION_PREVIEW_PERCENT','70'))
scene.render.filepath=str(ROOT/'preview.png')
bpy.ops.render.render(write_still=True)
