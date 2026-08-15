SetFactory("OpenCASCADE");
Merge "joint.step";
v() = Volume{:};
Printf("=== volumes: %g ===", #v[]);
For i In {0:#v[]-1}
  bb() = BoundingBox Volume{v(i)};
  Printf("V%g  x[%g,%g] y[%g,%g] z[%g,%g]", v(i), bb(0),bb(3), bb(1),bb(4), bb(2),bb(5));
EndFor
s() = Surface{:};
Printf("=== surfaces: %g ===", #s[]);
For i In {0:#s[]-1}
  bb() = BoundingBox Surface{s(i)};
  Printf("S%g  x[%g,%g] y[%g,%g] z[%g,%g]", s(i), bb(0),bb(3), bb(1),bb(4), bb(2),bb(5));
EndFor
