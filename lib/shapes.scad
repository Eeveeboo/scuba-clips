// Reusable solid shapes for the clip library.
//
// No module here positions anything: each one builds centred on the origin and
// the caller applies translate/rotate.
//
// The `include` is deliberate. Default argument values are evaluated in this
// file's scope, and `use` does not export variables, so it would hide
// DEFAULT_FN. params.scad holds definitions only, so the include has no effect
// other than making DEFAULT_FN visible.

include <params.scad>

// Solid box with selected edges rounded, upstream `roundedcube` semantics.
//
// `apply_to` selects which edges are rounded:
//   "all"                 every edge
//   "xmin" ... "zmax"     the four edges of that face
//   "x" / "y" / "z"       the four edges parallel to that axis
//
// The body is the hull of one sphere per selected corner and one cylinder per
// remaining corner. The cylinders point along the axis that `apply_to` names,
// so the selected edges are the only rounded ones.
//
// Keep the three separate `for` statements. A single multi-range
// `for (xi = ..., yi = ..., zi = ...)` iterates the same eight corners in the
// same order, but manifold's hull triangulates the two child trees differently,
// and the resulting mesh then differs from the pre-refactor mesh at some sizes
// (measured: size 5 / radius 0.5 gives 10548 facets against the original 10530,
// size [56,9,50] / radius 1.5 gives 10532 against 10520, and the downstream
// unions then jitter between renders). The nested form reproduces the original
// mesh and stays stable. The solid is the same either way.
//
// The upstream file began with a file-wide `$fs = 0.01`. It is gone: `use`
// drops top-level assignments from the caller's scope, so it never reached any
// caller. Resolution comes from `fn` alone, and dropping it changes no
// geometry.
module rounded_cube(size = [1, 1, 1], radius = 0.5, center = false,
                    apply_to = "all", fn = DEFAULT_FN) {
  $fn = fn;
  s = is_num(size) ? [size, size, size] : size;
  assert(len(s) == 3, "rounded_cube: size must be a number or a 3-element vector");
  assert(radius >= 0, "rounded_cube: radius must not be negative");
  assert(2 * radius <= s[0] && 2 * radius <= s[1] && 2 * radius <= s[2],
         "rounded_cube: radius must not exceed half of any size axis");
  // A typo here would silently round the wrong edges, so check the name.
  assert(apply_to == "all" || apply_to == "xmin" || apply_to == "xmax"
         || apply_to == "ymin" || apply_to == "ymax"
         || apply_to == "zmin" || apply_to == "zmax"
         || apply_to == "x" || apply_to == "y" || apply_to == "z",
         "rounded_cube: apply_to must be all, xmin, xmax, ymin, ymax, zmin, zmax, x, y, or z");

  // Corner centres: radius in from each face.
  lo = [radius, radius, radius];
  hi = [s[0] - radius, s[1] - radius, s[2] - radius];
  diameter = 2 * radius;
  // Rotation that puts a cylinder's axis on the axis `apply_to` names.
  axis_rotate = (apply_to == "xmin" || apply_to == "xmax" || apply_to == "x") ? [0, 90, 0] :
                (apply_to == "ymin" || apply_to == "ymax" || apply_to == "y") ? [90, 90, 0] :
                [0, 0, 0];

  translate(center ? [-s[0] / 2, -s[1] / 2, -s[2] / 2] : [0, 0, 0])
    hull()
      for (xi = [0, 1])
        for (yi = [0, 1])
          for (zi = [0, 1])
            translate(_corner(lo, hi, xi, yi, zi))
              if (_corner_is_rounded(xi, yi, zi, apply_to))
                sphere(r = radius);
              else
                rotate(axis_rotate)
                  cylinder(h = diameter, r = radius, center = true);
}

// Corner position on one axis: side 0 is the low end of the axis, 1 the high end.
function _corner(lo, hi, xi, yi, zi) = [
  xi == 0 ? lo[0] : hi[0],
  yi == 0 ? lo[1] : hi[1],
  zi == 0 ? lo[2] : hi[2],
];

// True when this corner sits on the face that `apply_to` names. Those corners
// get a sphere, so the edges of that face are rounded. "all" rounds every
// corner.
function _corner_is_rounded(xi, yi, zi, apply_to) =
  let (faces = [["xmin", "xmax"], ["ymin", "ymax"], ["zmin", "zmax"]])
  apply_to == "all"
  || apply_to == faces[0][xi]
  || apply_to == faces[1][yi]
  || apply_to == faces[2][zi];

// Solid wedge of `angle` degrees, symmetric about +X, centred on Z.
// The clip uses it to open a C.
module pie_wedge(radius, angle, height, fn = DEFAULT_FN) {
  $fn = fn;
  assert(radius > 0, "pie_wedge: radius must be positive");
  assert(angle > 0 && angle <= 360, "pie_wedge: angle must be in (0, 360]");
  assert(height > 0, "pie_wedge: height must be positive");

  translate([0, 0, height / -2])
    rotate([0, 0, angle / -2])
      rotate_extrude(angle = angle)
        square([radius, height]);
}

// Straight arm of `height` that joins a point on the `r_inner` circle at angle
// `a_inner` to a point on the `r_outer` circle at angle `a_outer`. The section
// across each end is set by `w_inner` and `w_outer`; the arms therefore taper.
module tapered_arm(a_inner, r_inner, w_inner, a_outer, r_outer, w_outer, height,
                   fn = DEFAULT_FN) {
  $fn = fn;
  assert(height > 0, "tapered_arm: height must be positive");

  p1 = [r_inner * cos(a_inner), r_inner * sin(a_inner)];
  p2 = [r_outer * cos(a_outer), r_outer * sin(a_outer)];
  dir = p2 - p1;
  assert(norm(dir) > EPS, "tapered_arm: inner and outer points must be distinct");
  n = [-dir[1], dir[0]] / norm(dir); // unit perpendicular to the arm

  linear_extrude(height = height, center = true)
    polygon(
      points = [
        p1 + n * (w_inner),
        p1 + n * (-w_inner / 4),
        p2 + n * (-w_outer / 4),
        p2 + n * (w_outer / 4),
      ]
    );
}
