// Webbing side clip: slides onto 37.5 x 5 mm hip webbing and holds one 12 mm
// hose on each side.
//
// Draft render: openscad -D MODEL_FN=36 -o out.stl models/webbing_side_clip.scad

use <../lib/params.scad>
use <../lib/webbing_clip.scad>

MODEL_FN = 100;

wall_t = 3;      // wall thickness of the block and of the hose clips
clip_h = 20;     // height of the webbing block
gap = 0.5;       // clearance, so the webbing slides in
tube_d = 12;     // hose held by the two standoff clips

hip = webbing_hip_size();  // [width, thickness] of the hip webbing
webbing_w = hip[0];
webbing_t = hip[1];

webbing_clip(wall_t=wall_t, webbing_t=webbing_t, webbing_w=webbing_w,
             h=clip_h, gap=gap, tube_d=tube_d, fn=MODEL_FN);
