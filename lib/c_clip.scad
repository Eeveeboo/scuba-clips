// C-shaped hose clips.
//
// Structure of `hose_clip`, from the inside out:
//   * `_inner_cantilever_c` the flexible tongue the hose presses against
//   * `_gap_c`              the ring in the radial gap `w_gap`
//   * `_inner_relief_cut`   clears the front of that ring, so the tongue can flex
//   * `_outer_structural_c` the stiff backbone
//   * `_tapered_arms`       two arms that join the tongue tips to the backbone
//
// Every module builds centred on the origin. The caller translates.
//
// The `include` is deliberate: default argument values are evaluated in this
// file's scope and `use` does not export variables, so it would hide
// DEFAULT_FN. params.scad holds definitions only, so the include has no effect
// other than making the constants visible.

include <params.scad>
use <shapes.scad>

// Private helper: one rounded lip at the end of a C opening.
// `angle` is the half opening of the C, `radius` the lip centreline, and
// `diameter` the head of the lip (the old code halved it again, so the lip is
// half as thick as the ring wall). The old name was `rounded_tip`.
module _rounded_tip(angle, radius, diameter, height, fn = DEFAULT_FN) {
  $fn = fn;
  rotate([0, 0, angle])
    translate([radius, 0, 0])
      cylinder(d = diameter / 2, h = height, center = true);
}

// Ring from `id` to `od` with one sharp opening of `angle` degrees, centred on
// +X. Old `make_c_sharp`.
module c_clip(id, od, angle, height, fn = DEFAULT_FN) {
  $fn = fn;
  assert(id > 0 && od > id, "c_clip: need 0 < id < od");
  assert(angle > 0 && angle < 360, "c_clip: angle must be in (0, 360)");
  assert(height > 0, "c_clip: height must be positive");

  difference() {
    difference() {
      cylinder(d = od, h = height, center = true);
      cylinder(d = id, h = height + 1, center = true);
    }
    pie_wedge(od, angle, height + 1, fn = fn);
  }
}

// `c_clip` with both lips rounded. Old `make_c_round`.
module c_clip_rounded(id, od, angle, height, fn = DEFAULT_FN) {
  $fn = fn;
  c_clip(id, od, angle, height, fn = fn);
  _rounded_tip(angle / 2, (id + od) / 4, od - id, height, fn = fn);
  _rounded_tip(-angle / 2, (id + od) / 4, od - id, height, fn = fn);
}

// Ring from `id` to `od` with two openings and four rounded lips: `angle_a`
// opens at the front (+X) and `angle_b` at the back (-X). Old
// `make_dual_c_round`.
module dual_c_clip_rounded(id, od, angle_a, angle_b, height, fn = DEFAULT_FN) {
  $fn = fn;
  assert(id > 0 && od > id, "dual_c_clip_rounded: need 0 < id < od");
  assert(angle_a > 0 && angle_a < 360, "dual_c_clip_rounded: angle_a must be in (0, 360)");
  assert(angle_b > 0 && angle_b < 360, "dual_c_clip_rounded: angle_b must be in (0, 360)");
  assert(height > 0, "dual_c_clip_rounded: height must be positive");

  union() {
    difference() {
      difference() {
        cylinder(d = od, h = height, center = true);
        cylinder(d = id, h = height + 1, center = true);
      }
      pie_wedge(od, angle_a, height + 1, fn = fn);
      rotate([0, 0, 180])
        pie_wedge(od, angle_b, height + 1, fn = fn);
    }
    _rounded_tip(angle_a / 2, (id + od) / 4, od - id, height, fn = fn);
    _rounded_tip(-angle_a / 2, (id + od) / 4, od - id, height, fn = fn);
    rotate([0, 0, 180]) {
      _rounded_tip(angle_b / 2, (id + od) / 4, od - id, height, fn = fn);
      _rounded_tip(-angle_b / 2, (id + od) / 4, od - id, height, fn = fn);
    }
  }
}

// --- The parts of `hose_clip` ---

// Flexible tongue: the inner C, from `base_diameter - t_inner` to
// `base_diameter`.
module _inner_cantilever_c(base_diameter, t_inner, a_inner_front, a_inner_back,
                           height, fn = DEFAULT_FN) {
  $fn = fn;
  dual_c_clip_rounded(base_diameter - t_inner, base_diameter, a_inner_front,
                      a_inner_back, height, fn = fn);
}

// The ring in the radial gap: from `base_diameter` to `base_diameter + w_gap`.
// The relief cut below thins it, so it does not bridge tongue and backbone.
module _gap_c(base_diameter, w_gap, a_inner_front, a_inner_back, height,
              fn = DEFAULT_FN) {
  $fn = fn;
  dual_c_clip_rounded(base_diameter, base_diameter + w_gap, a_inner_front,
                      a_inner_back, height, fn = fn);
}

// Stiff backbone: one rounded C from `base_diameter + w_gap` outward.
module _outer_structural_c(base_diameter, t_outer, w_gap, a_outer_front, height,
                           fn = DEFAULT_FN) {
  $fn = fn;
  c_clip_rounded(base_diameter + w_gap, base_diameter + w_gap + t_outer,
                 a_outer_front, height, fn = fn);
}

// Two mirror-symmetric arms that join the tongue tips to the backbone.
module _tapered_arms(base_diameter, t_inner, t_outer, w_gap, a_inner_front,
                     a_outer_front, height, fn = DEFAULT_FN) {
  $fn = fn;
  r_tongue = (base_diameter - t_inner / 2) / 2; // mid-wall of the tongue
  r_backbone = (base_diameter + w_gap + t_outer / 2) / 2; // mid-wall of the backbone

  tapered_arm(a_inner = a_inner_front / 2, r_inner = r_tongue, w_inner = t_inner,
              a_outer = a_outer_front / 2, r_outer = r_backbone, w_outer = t_outer,
              height = height, fn = fn);
  mirror([0, 1, 0])
    tapered_arm(a_inner = a_inner_front / 2, r_inner = r_tongue, w_inner = t_inner,
                a_outer = a_outer_front / 2, r_outer = r_backbone, w_outer = t_outer,
                height = height, fn = fn);
}

// Relief cut: a rounded C from `base_diameter` to `base_diameter + w_gap` at the
// front arc `a_inner_front + a_offset`, one unit taller than the part. It
// removes the front of the gap ring over an arc wider than the opening of the
// tongue, so only the arms hold the tongue and it can flex open for the hose.
// The old code called `make_c_round` with these arguments inside `make_clip`.
module _inner_relief_cut(base_diameter, w_gap, a_inner_front, a_offset, height,
                         fn = DEFAULT_FN) {
  $fn = fn;
  c_clip_rounded(base_diameter, base_diameter + w_gap, a_inner_front + a_offset,
                 height + 1, fn = fn);
}

// One hose clip, centred on the origin.
//
//   d_hose         hose outer diameter
//   t_outer        structural outer wall thickness
//   w_gap          radial gap between tongue and backbone
//   t_inner        tongue thickness
//   a_inner_back   opening of the tongue at the back (-X)
//   a_outer_front  opening of the backbone at the front (+X)
//   a_offset       extra front opening of the tongue, and of the relief cut
//   h              part height
//
// Old placement switch: origin="center" is this module as it stands;
// origin="bottom" is `translate([clip_total_diameter(...) / 2, 0, 0])` around
// it. Old `make_scuba_clip`, part="main".
module hose_clip(d_hose = 12, t_outer = 3, w_gap = 3, t_inner = 1.5,
                 a_inner_back = 60, a_outer_front = 90, a_offset = 15,
                 h = 10, fn = DEFAULT_FN) {
  $fn = fn;
  assert(d_hose > 0 && t_outer > 0 && w_gap > 0 && t_inner > 0 && h > 0,
         "hose_clip: d_hose, t_outer, w_gap, t_inner and h must be positive");
  assert(a_outer_front > 0 && a_outer_front < 360,
         "hose_clip: a_outer_front must be in (0, 360)");
  assert(a_inner_back > 0 && a_inner_back < 360,
         "hose_clip: a_inner_back must be in (0, 360)");
  assert(a_offset >= 0, "hose_clip: a_offset must not be negative");
  assert(a_outer_front + a_offset + a_inner_back < 360,
         "hose_clip: the front and back openings must leave material");

  base_diameter = clip_base_diameter(d_hose, t_inner);
  a_inner_front = a_outer_front + a_offset;

  difference() {
    union() {
      _inner_cantilever_c(base_diameter = base_diameter, t_inner = t_inner,
                          a_inner_front = a_inner_front, a_inner_back = a_inner_back,
                          height = h, fn = fn);
      _gap_c(base_diameter = base_diameter, w_gap = w_gap,
             a_inner_front = a_inner_front, a_inner_back = a_inner_back,
             height = h, fn = fn);
      _outer_structural_c(base_diameter = base_diameter, t_outer = t_outer,
                          w_gap = w_gap, a_outer_front = a_outer_front,
                          height = h, fn = fn);
      _tapered_arms(base_diameter = base_diameter, t_inner = t_inner,
                    t_outer = t_outer, w_gap = w_gap,
                    a_inner_front = a_inner_front, a_outer_front = a_outer_front,
                    height = h, fn = fn);
    }
    _inner_relief_cut(base_diameter = base_diameter, w_gap = w_gap,
                      a_inner_front = a_inner_front, a_offset = a_offset,
                      height = h, fn = fn);
  }
}

// Keep-out volume for one hose clip: the full envelope cylinder plus a front
// wedge of `a_outer_front` degrees. Old `make_reserved_clip_space`,
// part="cutter".
//
// `a_inner_back` and `a_offset` are accepted for symmetry with `hose_clip` and
// are unused here: a caller passes one argument list to both a part and its
// keep-out volume, so the two cannot drift apart. They do not change this
// volume.
module hose_clip_socket(d_hose = 12, t_outer = 3, w_gap = 3, t_inner = 1.5,
                        a_inner_back = 60, a_outer_front = 90, a_offset = 15,
                        h = 10, fn = DEFAULT_FN) {
  $fn = fn;
  assert(d_hose > 0 && t_outer > 0 && w_gap > 0 && t_inner > 0 && h > 0,
         "hose_clip_socket: d_hose, t_outer, w_gap, t_inner and h must be positive");
  assert(a_outer_front > 0 && a_outer_front < 360,
         "hose_clip_socket: a_outer_front must be in (0, 360)");

  total_diameter = clip_total_diameter(d_hose, t_outer, w_gap, t_inner);

  cylinder(h = h + 1, r = total_diameter / 2, center = true);
  pie_wedge(total_diameter, a_outer_front, h + 1, fn = fn);
}
