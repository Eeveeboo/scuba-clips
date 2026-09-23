// Webbing side clip: a flat block that slides onto webbing, with one hose
// standoff clip on each side of the webbing.

include <params.scad>
use <shapes.scad>
use <standoff.scad>

module webbing_clip(wall_t, webbing_t, webbing_w, h, gap, tube_d = 12,
                    fn = DEFAULT_FN) {
  $fn = fn;
  assert(wall_t > 0, "webbing_clip: wall_t must be positive");
  assert(webbing_t > 0, "webbing_clip: webbing_t must be positive");
  assert(webbing_w > 0, "webbing_clip: webbing_w must be positive");
  assert(h > 0, "webbing_clip: h must be positive");
  assert(gap >= 0, "webbing_clip: gap must not be negative");

  tt = wall_t * 2 + webbing_t;  // block thickness across the webbing
  tw = wall_t * 2 + webbing_w;  // block width along the webbing
  clip_h = 10;         // height (clip axis) of both hose clips
  standoff_span = tt;  // distance from the webbing to the standoff end

  difference() {
    union() {
      // Rounded block that carries the webbing.
      rounded_cube(size=[tw, tt, h], center=true, radius=wall_t / 2,
                   apply_to="all", fn=fn);
      // One standoff clip on each side, on the block's lower face: they span
      // -h / 2 .. -h / 2 + clip_h, they are not centred in Z. The clip wall
      // follows the block wall, so a tuned wall_t tunes both.
      translate([tw / 2, tt / 2, -h / 2 + clip_h / 2])
        standoff_clip(h=clip_h, tube_d=tube_d, standoff_h=standoff_span,
                      t_outer=wall_t, fn=fn);
      translate([tw / -2, tt / 2, -h / 2 + clip_h / 2])
        standoff_clip(h=clip_h, tube_d=tube_d, standoff_h=standoff_span,
                      t_outer=wall_t, fn=fn);
    }
    union() {
      // Webbing passage through the block.
      cube(size=[webbing_w, webbing_t, h + 1], center=true);
      // Clearance slot, so the webbing slides in from one end.
      translate([tw / -2, 0, 0])
        cube(size=[tw, gap, h + 1], center=true);
    }
  }
}
