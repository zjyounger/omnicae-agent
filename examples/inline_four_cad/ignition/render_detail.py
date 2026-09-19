"""Render a close inspection of the actual spark arc and initial flame."""
import bpy
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'inline_four_ignition.blend'))
s=bpy.context.scene
bpy.data.collections['04 • Cycle diagram'].hide_render=True
camera=s.camera
camera.location=(-.124,-.19,.271)
camera.rotation_euler=(Vector((-.144,0,.234))-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.ortho_scale=.113
s.render.resolution_x=1400;s.render.resolution_y=1000
s.eevee.taa_render_samples=128
s.eevee.volumetric_tile_size='4';s.eevee.volumetric_samples=96
s.frame_set(238)  # 711 degrees; spark begins at 708 degrees
s.render.filepath=str(ROOT/'ignition_detail.png')
bpy.ops.render.render(write_still=True)
