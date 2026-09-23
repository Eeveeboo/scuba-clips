// Octopus (octi) retaining clips: hose standoff clips mounted on a strap block
// that grips webbing.
//   upper_octi_clip() holds the regulator fitting and one MP hose on the
//   shoulder webbing; lower_octi_clip() holds two MP hoses on the hip webbing.
//
// Both bodies share `_octi_clip_at`: one octi clip with its lower face at a
// given z. Callers mirror it where the part needs a pair.

include <params.scad>
use <shapes.scad>
use <standoff.scad>

// One octi standoff clip, lower face at `z` (Z is the clip's axis).
module _octi_clip_at(h, tube_d, standoff_h, w_strap, t_strap, offset, z,
                     fn = DEFAULT_FN) {
  $fn = fn;
  translate([0, 0, z])
    octi_clip_part(h=h, tube_d=tube_d, standoff_h=standoff_h, w_strap=w_strap,
                   t_strap=t_strap, offset=offset, fn=fn);
}

module octi_clip_part(h, tube_d, standoff_h, w_strap, t_strap, offset = 0,
                      fn = DEFAULT_FN) {
  $fn = fn;
  assert(h > 0, "octi_clip_part: h must be positive");
  assert(tube_d > 0, "octi_clip_part: tube_d must be positive");
  assert(standoff_h >= 0, "octi_clip_part: standoff_h must not be negative");
  assert(w_strap > 0, "octi_clip_part: w_strap must be positive");
  assert(t_strap > 0, "octi_clip_part: t_strap must be positive");

  t_outer = default_t_outer();  // standoff wall thickness; the strap block's side wall
  tt = t_strap + t_outer * 2;  // strap block thickness
  tw = w_strap + t_outer * 2;  // strap block width

  // `offset` is a displacement in millimetres along +X, applied to the standoff
  // that otherwise hangs off the strap block's left edge at x = -tw / 2.
  // offset = 0 is the old alignment = "outer"; the old alignment = -6 is
  // offset = +6.
  translate([tw / -2 + offset, standoff_h, 0])
    standoff_clip(h=h, tube_d=tube_d, standoff_h=standoff_h + tt, fn=fn);

  // The strap block itself; the webbing opening is cut by the caller.
  translate([0, tt / -2, 0])
    rounded_cube(size=[tw, tt, h], center=true, radius=t_outer / 2,
                 apply_to="all", fn=fn);
}

// Flared slit cutter: a slot in the XZ plane (X = slit width, Z = slit length)
// that is `inner_half_width` wide where the webbing rests and flares to
// `outer_half_width` at both ends, so the webbing can be pushed through.
// `flare_start` is the Z distance from the centre where the flare begins,
// `thickness` is the Y thickness of the cutter, and `angle` / `y_offset` tilt
// and lift it for the caller. Private: only upper_octi_clip uses it.
module _flared_angle_cut(length, inner_half_width, outer_half_width,
                         flare_start, thickness, angle, y_offset,
                         fn = DEFAULT_FN) {
  $fn = fn;
  pts = [
    [-outer_half_width, -length / 2],  // bottom-left flare
    [inner_half_width, -length / 2],   // bottom-right inner edge
    [inner_half_width, -flare_start],
    [inner_half_width, flare_start],
    [outer_half_width, length / 2],    // top-right flare
    [-inner_half_width, length / 2],   // top-left inner edge
    [-inner_half_width, flare_start],
    [-inner_half_width, -flare_start],
  ];

  translate([0, y_offset, 0])
    rotate([0, angle, 0])
      rotate([90, 0, 0])
        linear_extrude(height=thickness, center=true)
          polygon(pts);
}

module upper_octi_clip(fn = DEFAULT_FN) {
  $fn = fn;

  t_outer = default_t_outer();  // side wall of the strap block; its corners round at t_outer / 2
  strap = webbing_shoulder_size();  // [width, thickness] of the shoulder webbing
  w_strap = strap[0];
  t_strap = strap[1];
  tt = t_strap + t_outer * 2;  // strap block thickness
  tw = w_strap + t_outer * 2;  // strap block width

  clip_bottom_z = -31;     // z of the lower face of both octi clips
  reg_clip_h = 15;         // height of the regulator-fitting clip
  reg_clip_standoff = 18;  // regulator-fitting clip distance from the webbing
  hose_clip_h = 10;        // height of the MP-hose clip
  hose_clip_standoff = 0;  // MP-hose clip rests on the webbing
  strap_block_h = 50;      // height of the webbing strap block
  webbing_slot_h = 63;     // vertical slot the webbing passes through
  slit_inner_half = t_strap * 1.25;  // slit half width at the webbing
  slit_outer_half = t_strap * 8;     // slit half width at the flared ends
  slit_flare_start = 5;              // z where the slit starts to flare
  slit_angle = -25;                  // tilt of the slit cutter
  slit_thickness = t_outer + 1;      // Y thickness of the slit cutter
  slit_y_offset = t_strap + 0.5;     // lift, so the slit cuts the near wall
  slit_length = 100;                 // Z length of the slit cutter

  // The regulator-fitting clip sits on one side only; the MP-hose clip is
  // mirrored, and both standoffs shift 6 mm in +X (the old alignment = -6).
  offset = 6;

  difference() {
    union() {
      _octi_clip_at(h=reg_clip_h, tube_d=hose_reg_fitting_dia(),
                    standoff_h=reg_clip_standoff, w_strap=w_strap,
                    t_strap=t_strap, offset=offset,
                    z=clip_bottom_z + reg_clip_h / 2, fn=fn);
      mirror([1, 0, 0])
        _octi_clip_at(h=hose_clip_h, tube_d=hose_mp_dia(),
                      standoff_h=hose_clip_standoff, w_strap=w_strap,
                      t_strap=t_strap, offset=offset,
                      z=clip_bottom_z + hose_clip_h / 2, fn=fn);
      translate([0, tt / -2, 0])
        rounded_cube(size=[tw, tt, strap_block_h], center=true,
                     radius=t_outer / 2, apply_to="all", fn=fn);
    }
    union() {
      translate([0, tt / -2, 0]) {
        // Webbing passage through the whole strap block.
        cube([w_strap, t_strap, webbing_slot_h], center=true);
        // Flared slit, so the webbing can be pushed in from the side.
        _flared_angle_cut(length=slit_length, inner_half_width=slit_inner_half,
                          outer_half_width=slit_outer_half,
                          flare_start=slit_flare_start,
                          thickness=slit_thickness, angle=slit_angle,
                          y_offset=slit_y_offset, fn=fn);
      }
    }
  }
}

module lower_octi_clip(fn = DEFAULT_FN) {
  $fn = fn;

  t_outer = default_t_outer();  // side wall of the strap block; its corners round at t_outer / 2
  strap = webbing_hip_size();  // [width, thickness] of the hip webbing
  w_strap = strap[0];
  t_strap = strap[1];
  tt = t_strap + t_outer * 2;  // strap block thickness
  tw = w_strap + t_outer * 2;  // strap block width

  clip_h = 10;                   // height of each MP-hose clip
  webbing_slot_h = 51;           // vertical slot the webbing passes through
  slit_angle = 30;               // tilt of the angled insertion slit
  slit_width = t_strap * 2.5;    // X width of the insertion slit
  slit_clearance = t_outer + 2;  // Y thickness of the insertion slit
  slit_length = 100;             // Z length of the insertion slit

  difference() {
    union() {
      _octi_clip_at(h=clip_h, tube_d=hose_mp_dia(), standoff_h=0,
                    w_strap=w_strap, t_strap=t_strap, offset=0,
                    z=0, fn=fn);
      mirror([1, 0, 0])
        _octi_clip_at(h=clip_h, tube_d=hose_mp_dia(), standoff_h=0,
                      w_strap=w_strap, t_strap=t_strap, offset=0,
                      z=0, fn=fn);
    }
    union() {
      translate([0, tt / -2, 0]) {
        // Webbing passage through the whole strap block.
        cube([w_strap, t_strap, webbing_slot_h], center=true);
        // Angled slit, so the webbing can be pushed in from the side.
        translate([0, t_strap, 0])
          rotate([0, slit_angle, 0])
            cube([slit_width, slit_clearance, slit_length], center=true);
      }
    }
  }
}
