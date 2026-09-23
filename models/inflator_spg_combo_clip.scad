// Inflator + SPG combo clip: bundles the three left-side hoses of a rig.
// Fits the 27 mm BCD inflator tube, the 12.5 mm LPI hose and the 8 mm HP/SPG
// hose.
//
// Draft render: openscad -D MODEL_FN=36 -o out.stl models/inflator_spg_combo_clip.scad

use <../lib/params.scad>
use <../lib/c_clip.scad>

MODEL_FN = 100;

// Clip walls and clip length (old file-level t_inner / t_outer / w_gap and the
// default clip height).
t_inner = 2;
t_outer = 3;
w_gap = 2;
clip_h = 10;

// Hoses this clip fits.
inflator_tube_d = hose_inflator_tube_dia();  // BCD inflator tube
lpi_hose_d = hose_lpi_dia();                 // LPI hose, first stage to inflator
hp_spg_hose_d = hose_hp_spg_dia();           // HP hose, first stage to the SPG

// Position of the HP/SPG clip around the inflator clip.
hp_spg_angle = 30;      // degrees, from the inflator clip's axis
hp_spg_radius = 22.5;   // distance from the inflator clip's centre
hp_spg_block_x = -14.5; // X centre of the block between the two clips
hp_spg_block_len = 29;  // X length of that block

// Position of the LPI clip around the inflator clip.
lpi_angle = -22;      // degrees, from the inflator clip's axis
lpi_radius = 30;      // distance from the inflator clip's centre
lpi_block_x = -14.5;  // X centre of the blocks between the two clips
lpi_block_len = 29;   // X length of those blocks
lpi_block_angle = 12; // degrees, tilt of the block on each side

module inflator_spg_combo_clip(fn = MODEL_FN) {
  $fn = fn;

  // Each hose position is written once, and both the clip and its keep-out
  // socket go through it, so the part and the cut cannot drift apart.
  module at_inflator_clip() {
    rotate([0, 0, 180]) children();
  }

  module at_hp_spg_clip() {
    rotate([0, 0, hp_spg_angle]) translate([hp_spg_radius, 0, 0]) children();
  }

  module at_lpi_clip() {
    rotate([0, 0, lpi_angle]) translate([lpi_radius, 0, 0]) children();
  }

  module bundle(blocks = false) {
    union() {
      // BCD inflator tube, clip opening away from the other two.
      at_inflator_clip()
        hose_clip(d_hose=inflator_tube_d, t_inner=t_inner, w_gap=w_gap,
                  t_outer=t_outer, h=clip_h, fn=fn);

      // HP/SPG hose.
      at_hp_spg_clip() {
        hose_clip(d_hose=hp_spg_hose_d, t_inner=t_inner, w_gap=w_gap,
                  t_outer=t_outer, h=clip_h, fn=fn);
        if (blocks)
          translate([hp_spg_block_x, 0, 0])
            cube([hp_spg_block_len,
                  clip_total_diameter(hp_spg_hose_d, t_outer, w_gap, t_inner),
                  clip_h], center=true);
      }

      // LPI hose, with a block on each side.
      at_lpi_clip() {
        hose_clip(d_hose=lpi_hose_d, t_inner=t_inner, w_gap=w_gap,
                  t_outer=t_outer, h=clip_h, fn=fn);
        if (blocks) {
          rotate([0, 0, -lpi_block_angle])
            translate([lpi_block_x, 0, 0])
              cube([lpi_block_len,
                    clip_total_diameter(lpi_hose_d, t_outer, w_gap, t_inner),
                    clip_h], center=true);
          rotate([0, 0, lpi_block_angle])
            translate([lpi_block_x, 0, 0])
              cube([lpi_block_len,
                    clip_total_diameter(lpi_hose_d, t_outer, w_gap, t_inner),
                    clip_h], center=true);
        }
      }
    }
  }

  // Keep-out volumes for the three hoses, through the same placements.
  module sockets() {
    union() {
      at_inflator_clip()
        hose_clip_socket(d_hose=inflator_tube_d, t_inner=t_inner, w_gap=w_gap,
                         t_outer=t_outer, h=clip_h, fn=fn);
      at_hp_spg_clip()
        hose_clip_socket(d_hose=hp_spg_hose_d, t_inner=t_inner, w_gap=w_gap,
                         t_outer=t_outer, h=clip_h, fn=fn);
      at_lpi_clip()
        hose_clip_socket(d_hose=lpi_hose_d, t_inner=t_inner, w_gap=w_gap,
                         t_outer=t_outer, h=clip_h, fn=fn);
    }
  }

  union() {
    bundle();
    difference() {
      bundle(blocks=true);
      sockets();
    }
  }
}

inflator_spg_combo_clip(fn = MODEL_FN);
