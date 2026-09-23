// Fit-test matrix for the C-clip: print a grid of clips across hose diameters
// and gap widths, each on a grip block with an engraved label, and test how
// they feel on the hose.
//
// This is a dev tool and it renders many clips at once, so MODEL_FN is
// overridable for a draft:
//   openscad -D MODEL_FN=36 -o /tmp/print_tests.stl dev/print_tests.scad

use <../lib/params.scad>
use <../lib/c_clip.scad>

MODEL_FN = 100;

// Matrix axes: every hose diameter against every gap width.
hose_diameters = [18, 19, 20, 27];  // mm; the last is the BCD inflator tube
w_gap_values = [2, 3];              // mm; relief gap between the C walls
t_inner = 2;                        // mm; clip inner wall thickness
t_outer = 3;                        // mm; clip outer wall thickness

// Grip block behind each clip (old literals: 25 x 12 x 10 at x = -9).
grip_x = -9;      // X centre of the block, so it sticks out as a grip
grip_len = 25;    // X length of the block
grip_h = 12;      // Y height of the block
grip_depth = 10;  // Z depth of the block, and the clip length

// Grid layout and label placement (old literals: 40, +-2.5, 4.5, size 5).
pitch = 40;        // mm between matrix cells
label_size = 5;    // mm
label_x = 1;       // X anchor of the right-aligned label
label_y = 2.5;     // Y offset of each of the two label lines
label_h = 1;       // extrusion height of the label
label_sink = 0.5;  // how far the label starts inside the block, so the union
                   // joins by overlap and not by face contact

module clip_test(d_hose, t_inner, w_gap, t_outer, fn) {
  $fn = fn;
  d = clip_total_diameter(d_hose, t_outer, w_gap, t_inner);

  // One placement for the clip and its keep-out volume, so the part and the
  // cut that shapes it cannot drift apart.
  module placed() {
    translate([d / 2, 0, 0]) children();
  }

  // The grip block, with the hose kept out of it.
  difference() {
    translate([grip_x, 0, 0])
      cube([grip_len, grip_h, grip_depth], center=true);
    placed()
      hose_clip_socket(d_hose=d_hose, t_inner=t_inner, w_gap=w_gap,
                       t_outer=t_outer, h=grip_depth, fn=fn);
  }

  // The clip itself, centred on its own outside diameter.
  placed()
    hose_clip(d_hose=d_hose, t_inner=t_inner, w_gap=w_gap, t_outer=t_outer,
              h=grip_depth, fn=fn);
}

// Engraved label on the top face of the grip block. It starts inside the block
// so that the label and the block join by overlap.
module clip_label(text_str, y, fn) {
  $fn = fn;
  translate([label_x, y, grip_depth / 2 - label_sink])
    linear_extrude(height=label_h)
      text(text_str, size=label_size, font="Liberation Sans",
           halign="right", valign="center");
}

for (i = [0 : len(hose_diameters) - 1])
  for (j = [0 : len(w_gap_values) - 1])
    translate([j * pitch, i * pitch, 0]) {
      clip_test(d_hose=hose_diameters[i], t_inner=t_inner,
                w_gap=w_gap_values[j], t_outer=t_outer, fn=MODEL_FN);
      clip_label(str(hose_diameters[i], ", ", t_inner), label_y, fn=MODEL_FN);
      clip_label(str(w_gap_values[j], ", ", t_outer), -label_y, fn=MODEL_FN);
    }
