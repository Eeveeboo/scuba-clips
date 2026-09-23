// Shared constants and dimension functions for the clip library.
//
// `use <params.scad>` imports the functions below but NOT the constants, because
// `use` imports modules and functions only. A lib file that needs DEFAULT_FN in
// a default argument must `include <params.scad>` instead; see ARCHITECTURE.md,
// "Constants and how lib/ files get them".
//
// This file holds assignments and functions only, so an include of it executes
// nothing but definitions.

DEFAULT_FN = 100; // the old global $fn = 100, so tessellation is unchanged
EPS = 0.01;

// Clip wall sizes. One source of truth for the old file-level globals t_inner,
// w_gap and t_outer, so a model that tunes them and a standoff clip that uses
// them cannot disagree. Functions, because `use` exports functions only.
function default_t_inner() = 2;
function default_w_gap() = 2;
function default_t_outer() = 3;

// Hose clip envelope. `d_hose` is the hose diameter, `t_inner` the flexible
// cantilever wall, `w_gap` the radial gap, `t_outer` the structural outer wall.
function clip_total_diameter(d_hose, t_outer, w_gap, t_inner) =
    d_hose + t_inner / 2 + w_gap + t_outer; // old `total_diameter`
function clip_base_diameter(d_hose, t_inner) = d_hose + t_inner / 2; // old `base_diameter`

// Hose and webbing specs. One function each replaces the old trailing globals.
function hose_inflator_tube_dia() = 27; // thick inflator tube from the BCD
function hose_lpi_dia() = 12.5; // LPI hose, first stage to the inflator
function hose_hp_spg_dia() = 8; // HP hose, first stage to the SPG
function hose_reg_fitting_dia() = 18.5; // MP hose fitting on the regulator
function hose_mp_dia() = 12.5; // MP hose, first stage to the regulator
function webbing_shoulder_size() = [50, 3]; // [width, thickness]
function webbing_hip_size() = [37.5, 5]; // [width, thickness]
