"""Render the saved scene; PNG frames keep an interrupted run recoverable."""
import bpy
import json
import os
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'inline_four_ignition.blend'))
scene=bpy.context.scene
frames=ROOT/'frames';frames.mkdir(exist_ok=True)
scene.render.resolution_percentage=100
start=time.time()
first=int(os.environ.get('IGNITION_FIRST','1'))
last=int(os.environ.get('IGNITION_LAST','240'))
for frame in range(first,last+1):
    output=frames/f'{frame:04d}.png'
    if output.exists():continue
    scene.frame_set(frame);scene.render.filepath=str(output)
    bpy.ops.render.render(write_still=True)
    (ROOT/'render_progress.json').write_text(json.dumps({'last_frame':frame,'total':240,'elapsed_seconds':time.time()-start}))
print('RENDER_COMPLETE',first,last,time.time()-start)
