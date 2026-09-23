// Print plate: all four models, in the layout of the old scuba_hose_clip.scad.
//
// Draft render: openscad -D MODEL_FN=36 -o out.stl models/all.scad

use <../lib/params.scad>
use <../lib/octi_clip.scad>
use <../lib/webbing_clip.scad>
use <inflator_spg_combo_clip.scad>

MODEL_FN = 100;

wall_t = 3;   // wall thickness of the webbing side clip
clip_h = 20;  // height of its webbing block
gap = 0.5;    // clearance, so the webbing slides in
tube_d = 12;  // hose held by its standoff clips

hip = webbing_hip_size();  // [width, thickness] of the hip webbing
webbing_w = hip[0];        // width along the webbing
webbing_t = hip[1];        // thickness across the webbing

inflator_spg_combo_clip(fn = MODEL_FN);
translate([100, 0, 0])
  upper_octi_clip(fn = MODEL_FN);
translate([100, -50, 0])
  lower_octi_clip(fn = MODEL_FN);
translate([0, -50, 0])
  webbing_clip(wall_t=wall_t, webbing_t=webbing_t, webbing_w=webbing_w,
               h=clip_h, gap=gap, tube_d=tube_d, fn=MODEL_FN);
