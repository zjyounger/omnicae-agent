"""Configure the opened Blender window for inspecting the delivered scene."""
import bpy
import json
import os
from pathlib import Path
ROOT=Path(__file__).resolve().parent
scene=bpy.context.scene
scene.frame_set(25)
scene.eevee.taa_samples=16
scene.sync_mode='FRAME_DROP'
def ready():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type=='VIEW_3D':
                area.spaces.active.region_3d.view_perspective='CAMERA'
                area.spaces.active.shading.type='RENDERED'
                area.spaces.active.overlay.show_overlays=False
                area.spaces.active.region_3d.view_camera_zoom=8
            elif area.type=='PROPERTIES':area.spaces.active.context='OBJECT'
    (ROOT/'blender_window.json').write_text(json.dumps({'pid':os.getpid(),'file':bpy.data.filepath}))
    def capture():
        window=bpy.context.window_manager.windows[0]
        with bpy.context.temp_override(window=window):
            bpy.ops.screen.screenshot(filepath=str(ROOT/'blender_window.png'))
        return None
    bpy.app.timers.register(capture,first_interval=6)
    return None
bpy.app.timers.register(ready,first_interval=2)
