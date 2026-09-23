// Lower octopus retaining clip: holds two 12.5 mm MP hoses on 37.5 x 5 mm hip
// webbing.
//
// Draft render: openscad -D MODEL_FN=36 -o out.stl models/lower_octi_retaining_clip.scad

use <../lib/octi_clip.scad>

MODEL_FN = 100;

lower_octi_clip(fn = MODEL_FN);
