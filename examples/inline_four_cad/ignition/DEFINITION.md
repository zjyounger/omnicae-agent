# Ignition cutaway animation

Purpose: show the existing inline-four CAD assembly moving with correctly phased
spark and illustrative flame propagation. This is an animation, not a combustion
or thermodynamic calculation. Original CAD files remain unchanged.

The 86 mm bore, 86 mm stroke and 143 mm rod geometry comes from the saved
FreeCAD assembly. Tessellate each displayed component in its local coordinates,
then export its actual global placement at 3-degree intervals through two turns,
wrapping FreeCAD's mechanical angle at 360 degrees. Blender uses metres and
native drivers; compare their evaluated placements with these CAD samples.
Check piston travel and rod pin distances after reopening the saved Blender file.

Cylinder numbering follows X=-144,-48,48,144 mm. Compression TDC is assigned at
0,540,180,360 degrees for cylinders 1,2,3,4, respectively: order 1-3-4-2.
Each cylinder fires once per 720 degrees. The visual spark advance defaults to
12 degrees BTDC and is an illustrative adjustable setting, not a tuned value.
Render 240 unique frames at 24 fps: two crank turns over ten seconds. The
additional frame 241 stores the seamless 720-degree endpoint.

A supplemental display head has four cylindrical combustion recesses, a cut
front half and four simplified spark plugs. It has no valve gear or gas ports;
stroke labels describe assigned cycle phases, not simulated breathing. This
head is display geometry, not a completed CAD cylinder-head design.

Flame emission starts at the plug, expands inside a mask bounded by the bore,
chamber roof and moving piston crown, then fades during expansion. Neither
its colour nor its brightness represents a measured temperature or pressure.
The flat piston-crown bound intentionally excludes the piston bowl volume.

Evidence: original CAD hashes, per-component tessellation and placement export,
reopened Blender measurements, per-cylinder ignition-event count and order,
sampled flame-mask bounds, still renders and an encoded full-cycle video.
