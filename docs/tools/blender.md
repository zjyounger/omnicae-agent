# Blender

Version exercised: 4.5.9 LTS, official Linux x64 portable archive installed in
`/home/linuxjun/.local/opt/`, launcher `/home/linuxjun/.local/bin/blender`.
The archive SHA-256 was checked against the official release checksum.

## Native scene work

The inline-four ignition example lives in `examples/inline_four_cad/ignition/`.
Run scripts through Blender's own `--python` CLI; native meshes, materials,
drivers, cameras and animation are saved in the `.blend` file. Reopen that file
for inspection rather than only checking the builder's in-memory state.

Use a separate collection for illustrative additions. The ignition study keeps
the original CAD components distinct from its simplified display head and plugs.
Combustion emission is a visual effect, not a thermodynamic prediction.

## Observed pitfalls

- Python `**` and `%` make otherwise elementary drivers fall outside Blender's
  simple-expression evaluator. Such drivers worked in the initial background
  run but failed the portability criterion. `pow()` and `x-floor(x/n)*n` retain
  the intended arithmetic and evaluate without enabling Python auto-execution.
  `check_scene.py` checks all 302 drivers with `--disable-autoexec`, as well as
  their actual motion and ignition events.
- In this environment the sandbox does not expose `/dev/dri`. EEVEE emitted
  EGL errors, then completed a preview using a much slower fallback. Host
  execution exposed the render devices and reduced cached full-frame rendering
  to roughly half a second. An EGL message alone did not establish total render
  failure; the saved image and render log did.
- In 4.5 the Glare compositor's threshold and strength should be set through
  its named input sockets. Setting the legacy `threshold` attribute emitted
  `RNA_float_set: NodeSocket.default_value not found` and left unintended glow.
- Imported tessellated CAD needs explicit material, normals and lighting QA.
  A legal mesh and matching transforms do not establish a readable render.

Evidence is in the example's build/render logs, `scene_inspection.json`, still
images, video and `blender_window.png`.
