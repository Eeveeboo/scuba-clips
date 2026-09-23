// Standoff clip: one hose C-clip plus a block that reaches out to the webbing
// or strap it is mounted against. Shared by the octi clips and the webbing
// side clip.
//
// The clip walls take the library's fit defaults and accept named overrides, so
// a caller that tunes the fit gets a standoff clip that matches it. The values
// live in params.scad, one function each.

include <params.scad>
use <c_clip.scad>

module standoff_clip(h, tube_d, standoff_h, t_inner = default_t_inner(),
                     w_gap = default_w_gap(), t_outer = default_t_outer(),
                     fn = DEFAULT_FN) {
  $fn = fn;
  assert(h > 0, "standoff_clip: h must be positive");
  assert(tube_d > 0, "standoff_clip: tube_d must be positive");
  assert(standoff_h >= 0, "standoff_clip: standoff_h must not be negative");

  // Outside diameter of the hose clip; also the width of the standoff arm.
  d = clip_total_diameter(tube_d, t_outer, w_gap, t_inner);

  // One placement for the clip and its keep-out volume, so the part and the
  // cut that shapes it can never drift apart (old origin="bottom" inside
  // rotate([0, 0, 90])).
  module placed() {
    rotate([0, 0, 90])
      translate([d / 2, 0, 0])
        children();
  }

  union() {
    placed()
      hose_clip(d_hose=tube_d, t_outer=t_outer, w_gap=w_gap, t_inner=t_inner,
                h=h, fn=fn);

    difference() {
      union() {
        // Round boss at the far end of the standoff.
        translate([0, -standoff_h + d / 2, h / -2])
          cylinder(h=h, r=d / 2, center=false);
        // Flat arm from the clip out to the boss.
        translate([0, d / 2 - standoff_h / 2, 0])
          cube([d, standoff_h, h], center=true);
      }
      placed()
        hose_clip_socket(d_hose=tube_d, t_outer=t_outer, w_gap=w_gap,
                         t_inner=t_inner, h=h, fn=fn);
    }
  }
}
