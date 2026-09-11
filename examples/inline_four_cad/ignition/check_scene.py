"""Reopen the deliverable and compare evaluated Blender state to native CAD."""
import bpy
import json
import math
import hashlib
from pathlib import Path
from mathutils import Quaternion,Vector

ROOT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'inline_four_ignition.blend'))
scene=bpy.context.scene
ctrl=bpy.data.objects['ENGINE CONTROLS']
data=json.loads((ROOT/'cad_scene.json').read_text())
report={'passed':False,'samples':241,'checks':{}}
try:
    err=0.;rot_err=0.;travel={i:[] for i in range(1,5)};rod_error=0.
    for row in data['motion']:
        scene.frame_set(row['frame']);graph=bpy.context.evaluated_depsgraph_get()
        for name,expected in row['objects'].items():
            o=bpy.data.objects[name].evaluated_get(graph)
            delta=math.dist(list(o.matrix_world.translation),expected['p'])
            if delta>err:
                report['worst_translation']={'object':name,'frame':row['frame'],'expected':expected['p'],'actual':list(o.matrix_world.translation)}
            err=max(err,delta)
            q=o.matrix_world.to_quaternion();qe=Quaternion(expected['q'])
            dq=min((q-qe).magnitude,(q+qe).magnitude)
            if dq>rot_err:report['worst_rotation']={'object':name,'frame':row['frame'],'expected':list(qe),'actual':list(q)}
            rot_err=max(rot_err,dq)
        for i in range(1,5):
            p=bpy.data.objects[f'Piston{i}'].evaluated_get(graph).matrix_world.translation
            r=bpy.data.objects[f'Rod{i}'].evaluated_get(graph).matrix_world.translation
            travel[i].append(p.z)
            rod_error=max(rod_error,abs((p-r).length-.143))
            vol=bpy.data.objects[f'Flame volume {i}'].evaluated_get(graph)
            bottom=vol.location.z-vol.scale.z/2
            top=vol.location.z+vol.scale.z/2
            assert bottom>=p.z+.03135,(i,row['frame'],bottom,p.z)
            assert abs(top-.2295)<1e-7
    report['checks']['max_native_translation_error_mm']=err*1000
    report['checks']['max_native_quaternion_error']=rot_err
    report['checks']['piston_stroke_mm']={str(i):(max(v)-min(v))*1000 for i,v in travel.items()}
    report['checks']['max_rod_pin_distance_error_mm']=rod_error*1000
    assert err<2e-7 and rot_err<2e-6 and rod_error<2e-7
    assert all(abs(max(v)-min(v)-.086)<2e-7 for v in travel.values())
    active={i:[] for i in range(1,5)}
    for angle in range(720):
        scene.frame_set(angle//3+1,subframe=(angle%3)/3)
        graph=bpy.context.evaluated_depsgraph_get()
        now=[]
        for i in range(1,5):
            o=bpy.data.objects[f'Spark {i}'].evaluated_get(graph)
            if o.scale.x>.5:active[i].append(angle);now.append(i)
        assert len(now)<=1,(angle,now)
    expected={1:708,3:168,4:348,2:528}
    for i,start in expected.items():assert active[i]==list(range(start,start+7)),(i,active[i])
    report['checks']['spark_active_degrees']=active
    report['checks']['cyclic_firing_order']=[1,3,4,2]
    # Inspect driver validity after dependency-graph evaluation, including
    # materials and node trees; no external handler is required on reopening.
    bad=[];nonsimple=[];count=0
    ids=list(bpy.data.objects)+list(bpy.data.lights)
    ids += [m.node_tree for m in bpy.data.materials if m.node_tree]
    for obj in ids:
        ad=obj.animation_data
        if not ad:continue
        for fc in ad.drivers:
            count+=1
            if not fc.driver.is_valid:bad.append((obj.name,fc.data_path))
            if not fc.driver.is_simple_expression:nonsimple.append((obj.name,fc.data_path))
    assert not bad,bad
    report['checks']['valid_drivers']=count;report['checks']['invalid_drivers']=bad
    report['checks']['non_simple_expressions']=nonsimple
    assert not nonsimple,nonsimple
    ctrl['Spark advance']=20;ctrl.update_tag()
    scene.frame_set(234,subframe=1/3)  # 700 degrees = cylinder 1 at 20 BTDC
    graph=bpy.context.evaluated_depsgraph_get()
    assert bpy.data.objects['Spark 1'].evaluated_get(graph).scale.x>.5
    assert bpy.data.objects['Advance value 20'].evaluated_get(graph).scale.x>.5
    assert bpy.data.objects['Advance value 12'].evaluated_get(graph).scale.x<.5
    report['checks']['advance_change_20_deg_and_label']=True
    ctrl['Spark advance']=12
    source=ROOT.parent/data['source']
    assert hashlib.sha256(source.read_bytes()).hexdigest()==data['source_sha256']
    report['checks']['source_CAD_unchanged']=True
    assert scene.frame_end-scene.frame_start+1==240 and scene.render.fps==24
    report['passed']=True
finally:
    (ROOT/'scene_inspection.json').write_text(json.dumps(report,indent=2))
print('INSPECTION',report['passed'],report['checks'])
