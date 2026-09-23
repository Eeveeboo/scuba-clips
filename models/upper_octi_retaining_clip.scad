// Upper octopus retaining clip: holds the 18.5 mm MP regulator fitting and one
// 12.5 mm MP hose on 50 x 3 mm shoulder webbing.
//
// Draft render: openscad -D MODEL_FN=36 -o out.stl models/upper_octi_retaining_clip.scad

use <../lib/octi_clip.scad>

MODEL_FN = 100;

upper_octi_clip(fn = MODEL_FN);
