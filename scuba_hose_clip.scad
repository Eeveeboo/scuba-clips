use <roundedcube.scad>

$fn = 100;

module pie_wedge(radius, a, h = 1) {
  translate([0, 0, h / -2])
    rotate([0, 0, a / -2])
      rotate_extrude(angle=a)
        square([radius, h]);
}

module make_c_sharp(id, od, a, h) {
  difference() {
    difference() {
      cylinder(d=od, h=h, center=true);
      cylinder(d=id, h=h + 1, center=true);
    }
    pie_wedge(od, a, h + 1);
  }
}

module make_dual_c_sharp(id, od, a1, a2, h) {
  difference() {
    difference() {
      cylinder(d=od, h=h, center=true);
      cylinder(d=id, h=h + 1, center=true);
    }
    pie_wedge(od, a1, h + 1);
    rotate([0, 0, 180])
      pie_wedge(od, a2, h + 1);
  }
}

module rounded_tip(angle, radius, diameter, h) {
  rotate([0, 0, angle])
    translate([radius, 0, 0])
      cylinder(d=diameter / 2, h=h, center=true);
}

module make_c_round(id, od, a, h) {
  make_c_sharp(id, od, a, h);
  rounded_tip(a / 2, (id + od) / 4, od - id, h);
  rounded_tip(-a / 2, (id + od) / 4, od - id, h);
}

module make_dual_c_round(id, od, a1, a2, h) {
  make_dual_c_sharp(id, od, a1, a2, h);
  rounded_tip(a1 / 2, (id + od) / 4, od - id, h);
  rounded_tip(-a1 / 2, (id + od) / 4, od - id, h);
  rotate([0, 0, 180]) {
    rounded_tip(a2 / 2, (id + od) / 4, od - id, h);
    rounded_tip(-a2 / 2, (id + od) / 4, od - id, h);
  }
}

module tapered_arm(
  a_inner,
  r_inner,
  w_inner,
  a_outer,
  r_outer,
  w_outer,
  h
) {
  p1 = [r_inner * cos(a_inner), r_inner * sin(a_inner)];
  p2 = [r_outer * cos(a_outer), r_outer * sin(a_outer)];
  dir = p2 - p1;
  n = [-dir[1], dir[0]] / norm(dir); // unit perpendicular

  linear_extrude(height=h, center=true)
    polygon(
      points=[
        p1 + n * (w_inner),
        p1 + n * ( -w_inner / 4),
        p2 + n * ( -w_outer / 4),
        p2 + n * (w_outer / 4),
      ]
    );
}

module make_clip_base(
  base_diameter,
  outer_thickness,
  w_gap,
  inner_thickness,
  a_inner_back,
  a_inner_front,
  a_outer_front,
  height
) {

  // Innermost C (Canteliever)
  make_dual_c_round(
    base_diameter - inner_thickness,
    base_diameter,
    a_inner_front,
    a_inner_back,
    height
  );

  make_dual_c_round(
    base_diameter,
    base_diameter + w_gap,
    a_inner_front,
    a_inner_back,
    height
  );

  // Outer C (Structure)
  make_c_round(base_diameter + w_gap, base_diameter + w_gap + outer_thickness, a_outer_front, height);

  // Ajoining tapered arms from outer to inner
  tapered_arm(
    a_inner=a_inner_front / 2,
    r_inner=(base_diameter - inner_thickness / 2) / 2,
    w_inner=inner_thickness,
    a_outer=a_outer_front / 2,
    r_outer=(base_diameter + w_gap + outer_thickness / 2) / 2,
    w_outer=outer_thickness,
    h=height
  );

  mirror([0, 1, 0])
    tapered_arm(
      a_inner=a_inner_front / 2,
      r_inner=(base_diameter - inner_thickness / 2) / 2,
      w_inner=inner_thickness,
      a_outer=a_outer_front / 2,
      r_outer=(base_diameter + w_gap + outer_thickness / 2) / 2,
      w_outer=outer_thickness,
      h=height
    );
}

module make_scuba_clip(
  d_hose = 12,
  t_outer = 3,
  w_gap = 3,
  t_inner = 1.5,
  a_inner_back = 60,
  a_outer_front = 90,
  a_offset = 15,
  origin = "center", // center or bottom
  part = "main", // main or cutter
  h = 10
) {

  base_diameter = d_hose + t_inner / 2;
  total_diameter = base_diameter + w_gap + t_outer;
  x_offset = origin == "bottom" ? total_diameter / 2 : 0;

  module make_clip() {
    a_inner_front = a_outer_front + a_offset;

    translate([x_offset, 0, 0])
      difference() {
        make_clip_base(
          base_diameter,
          t_outer,
          w_gap,
          t_inner,
          a_inner_back,
          a_inner_front,
          a_outer_front,
          h
        );
        make_c_round(
          base_diameter,
          base_diameter + w_gap,
          a_inner_front + a_offset,
          h + 1
        );
      }
  }

  module make_reserved_clip_space() {
    translate([x_offset, 0, 0]) {
      cylinder(h=h + 1, r=total_diameter / 2, center=true);
      pie_wedge(total_diameter, a_outer_front, h + 1);
    }
  }

  if (part == "main") {
    make_clip();
  } else {
    make_reserved_clip_space();
  }
}
/*
// Print test clips to test feel
module _x(hose_diameter, t_inner, w_gap, t_outer) {
  difference() {
    translate([-9, 0, 0])
      cube([25, 12, 10], center=true);
    make_scuba_clip(
      d_hose=hose_diameter,
      t_inner=t_inner,
      w_gap=w_gap,
      t_outer=t_outer,
      origin="bottom",
      part="cutter"
    );
  }
  make_scuba_clip(
    d_hose=hose_diameter,
    t_inner=t_inner,
    w_gap=w_gap,
    t_outer=t_outer,
    origin="bottom"
  );
}

for (i = [0:3]) {
  for (j = [0:1]) {
    t_hose = i == 3 ? 27 : i + 18;
    t_outer = 3;
    t_inner = 2;
    w_gap = j + 2;
    translate([j * 40, i * 40, 0]) {
      _x(hose_diameter=t_hose, t_inner=t_inner, w_gap=w_gap, t_outer=t_outer);
      translate([1, 2.5, 4.5])
        linear_extrude(height=1) {
          text(str(t_hose, ", ", t_inner), size=5, font="Liberation Sans", halign="right", valign="center");
        }
      translate([1, -2.5, 4.5])
        linear_extrude(height=1) {
          text(str(w_gap, ", ", t_outer), size=5, font="Liberation Sans", halign="right", valign="center");
        }
    }
  }
}*/

// -- GLOBALS -- //
t_inner = 2;
t_outer = 3;
w_gap = 2;

// Used for Inflator+SPG combo clips
inflator_tube_d = 27; // Thick Inflator Tube Coming from the BCD
inflator_hose_d = 12.5; // LPI Hose from the first stage to the inflator
hp_spg_hose_d = 8; // HP Hose from the first stage to the SPG

// Used for octi organisation
reg_fitting_d = 18.5; // MP Hose fitting on the regulator
mp_reg_hose_d = 12.5; // MP Hose from the first stage to the regulator
shoulder_webbing_w = 50;
shoulder_webbing_t = 3;
hip_webbing_w = 37.5;
hip_webbing_t = 5;

module make_inflator_spg_combo_clip() {
  // Holds the three left-side suba hoses together in a nice bundle

  module _x(part, block = false) {
    union() {
      // BCD Inflator Tube
      rotate([0, 0, 180])
        make_scuba_clip(
          d_hose=inflator_tube_d,
          t_inner=t_inner,
          w_gap=w_gap,
          t_outer=t_outer,
          origin="center",
          part=part
        );

      // HP - SPG Hose
      rotate([0, 0, 30]) translate([22.5, 0, 0]) {
          rotate([0, 0, 0])
            make_scuba_clip(
              d_hose=hp_spg_hose_d,
              t_inner=t_inner,
              w_gap=w_gap,
              t_outer=t_outer,
              origin="center",
              part=part
            );
          if (block) {
            translate([-14.5, 0, 0])
              cube([29, hp_spg_hose_d + t_inner / 2 + t_outer + w_gap, 10], center=true);
          }
        }

      // LP - Inflator Hose
      rotate([0, 0, -22]) translate([30, 0, 0]) {
          rotate([0, 0, 0])
            make_scuba_clip(
              d_hose=inflator_hose_d,
              t_inner=t_inner,
              w_gap=w_gap,
              t_outer=t_outer,
              origin="center",
              part=part
            );
          if (block) {
            rotate([0, 0, -12]) translate([-14.5, 0, 0])
                cube([29, inflator_hose_d + t_inner / 2 + t_outer + w_gap, 10], center=true);
            rotate([0, 0, 12]) translate([-14.5, 0, 0])
                cube([29, inflator_hose_d + t_inner / 2 + t_outer + w_gap, 10], center=true);
          }
        }
    }
  }
  _x("main");
  difference() {
    _x("main", block=true);
    _x("cutter");
  }
}

module make_standoff_clip(h, tube_d, standoff_h) {
  rotate([0, 0, 90])
    make_scuba_clip(d_hose=tube_d, t_inner=t_inner, w_gap=w_gap, t_outer=t_outer, origin="bottom", part="main", h=h);

  d = tube_d + (w_gap + t_outer + t_inner / 2);
  difference() {
    union() {
      translate([0, -standoff_h + d / 2, h / -2]) cylinder(h=h, r=d / 2, center=false);
      translate([0, d / 2 - standoff_h / 2, 0]) cube([d, standoff_h, h], center=true);
    }

    rotate([0, 0, 90])
      make_scuba_clip(d_hose=tube_d, t_inner=t_inner, w_gap=w_gap, t_outer=t_outer, origin="bottom", part="cutter", h=h);
  }
}

module make_octi_retaining_clip_part(h, tube_d, standoff_h, w_strap, t_strap, alignment = "outer") {
  d = tube_d + (w_gap + t_outer + t_inner / 2);
  tt = t_strap + t_outer * 2;
  tw = w_strap + t_outer * 2;

  translate(alignment == "outer" ? [(tw / -2), standoff_h, 0] : [(tw / -2) - alignment, standoff_h, 0]) {
    make_standoff_clip(h, tube_d, standoff_h + tt);
  }
  translate([0, tt / -2, 0]) roundedcube(size=[tw, tt, h], center=true, radius=t_outer / 2, apply_to="all");
}

// ------------------------------------------------------------
// Flared, angled slot cutter
// ------------------------------------------------------------
module flared_angle_cut(
  length = 100,
  inner_left = -3.75,
  inner_right = 3.75,
  outer_top_left = -11.25,
  outer_top_right = 11.25,
  // Defaults mirror the top edges for the bottom
  outer_bottom_left = 11.25, // = -outer_top_right
  outer_bottom_right = -11.25, // = -outer_top_left
  flare_start = 20, // Z distance from centre where flare begins
  thickness = 4, // Y thickness of the cutter
  angle = 25,
  y_offset = 3.5
) {
  // 2D profile in the XZ plane (X = width, Z = length)
  pts = [
    [outer_bottom_left, -length / 2],
    [outer_bottom_right, -length / 2],
    [inner_right, -flare_start],
    [inner_right, flare_start],
    [outer_top_right, length / 2],
    [outer_top_left, length / 2],
    [inner_left, flare_start],
    [inner_left, -flare_start],
  ];

  translate([0, y_offset, 0])
    rotate([0, angle, 0])
      rotate([90, 0, 0])
        linear_extrude(height=thickness, center=true)
          polygon(pts);
}

module make_upper_octi_retaining_clip() {
  tt = shoulder_webbing_t + t_outer * 2;
  tw = shoulder_webbing_w + t_outer * 2;

  difference() {
    union() {
      translate([0, 0, -31 + (15 / 2)]) make_octi_retaining_clip_part(
          h=15,
          tube_d=reg_fitting_d,
          standoff_h=18,
          t_strap=shoulder_webbing_t,
          w_strap=shoulder_webbing_w,
          alignment=-6
        );
      mirror([1, 0, 0]) translate([0, 0, -31 + 10 / 2]) make_octi_retaining_clip_part(
            h=10,
            tube_d=mp_reg_hose_d,
            standoff_h=0,
            t_strap=shoulder_webbing_t,
            w_strap=shoulder_webbing_w,
            alignment=-6
          );
      /*translate([0, 0, -31 + (10 / 2)]) make_octi_retaining_clip_part(
          h=10,
          tube_d=mp_reg_hose_d,
          standoff_h=(reg_fitting_d - mp_reg_hose_d) / 2 + 15,
          t_strap=shoulder_webbing_t,
          w_strap=shoulder_webbing_w,
        );*/
      translate([0, tt / -2, 0]) roundedcube(size=[tw, tt, 50], center=true, radius=t_outer / 2, apply_to="all");
    }
    union() {
      translate([0, tt / -2, 0]) {
        // Space for the webbing to go through in general.
        cube([shoulder_webbing_w, shoulder_webbing_t, 63], center=true);
        // Flared angled slit for insertion
        flared_angle_cut(
          length=100,
          inner_left=-shoulder_webbing_t * 1.25,
          inner_right=shoulder_webbing_t * 1.25,
          outer_top_left=-shoulder_webbing_t * 1.25,
          outer_top_right=shoulder_webbing_t * 8,
          outer_bottom_left=-shoulder_webbing_t * 8,
          outer_bottom_right=shoulder_webbing_t * 1.25,
          flare_start=5,
          thickness=t_outer + 1,
          angle=-25,
          y_offset=shoulder_webbing_t + 0.5
        );
      }
    }
  }
}

module make_lower_octi_retaining_clip() {
  tt = hip_webbing_t + t_outer * 2;
  tw = hip_webbing_w + t_outer * 2;

  difference() {
    union() {

      make_octi_retaining_clip_part(
        h=10,
        tube_d=mp_reg_hose_d,
        standoff_h=0,
        t_strap=hip_webbing_t,
        w_strap=hip_webbing_w,
      );
      mirror([1, 0, 0]) make_octi_retaining_clip_part(
          h=10,
          tube_d=mp_reg_hose_d,
          standoff_h=0,
          t_strap=hip_webbing_t,
          w_strap=hip_webbing_w,
        );
    }

    union() {
      translate([0, tt / -2, 0]) {
        cube([hip_webbing_w, hip_webbing_t, 51], center=true);
        translate([0, hip_webbing_t, 0]) rotate([0, 30, 0]) cube([hip_webbing_t * 2.5, t_outer + 2, 100], center=true);
      }
    }
  }
}

make_inflator_spg_combo_clip();
translate([100, 0, 0]) make_upper_octi_retaining_clip();
translate([100, -50, 0]) make_lower_octi_retaining_clip();

module make_webbing_side_clip(wall_t, webbing_t, webbing_w, h, gap) {
  tt = wall_t * 2 + webbing_t;
  tw = wall_t * 2 + webbing_w;
  difference() {
    union() {
      roundedcube(size=[tw, tt, h], center=true, radius=wall_t / 2, apply_to="all");
      translate([tw / 2, tt / 2, h / -2 + 5]) make_standoff_clip(h=10, tube_d=12, standoff_h=tt);
      translate([tw / -2, tt / 2, h / -2 + 5]) make_standoff_clip(h=10, tube_d=12, standoff_h=tt);
    }
    union() {
      cube(size=[webbing_w, webbing_t, h + 1], center=true);
      translate([tw / -2, 0, 0]) cube(size=[tw, gap, h + 1], center=true);
    }
  }

  //translate([0, webbing_t / 2 + wall_t / 2, 0]) roundedcube(size=[tw, wall_t, h], center=true, radius=wall_t / 2, apply_to="all");
  //translate([0, webbing_t / -2 + wall_t / -2, 0]) roundedcube(size=[tw, wall_t, h], center=true, radius=wall_t / 2, apply_to="all");
  //translate([webbing_w / 2 + wall_t / 2, 0, 0]) roundedcube(size=[wall_t, tt, h], center=true, radius=wall_t / 2, apply_to="all");
  //translate([webbing_w / -2 + wall_t / -2, wall_t / 2 + gap / 2, 0]) roundedcube(size=[wall_t, tt - wall_t - gap, h], center=true, radius=wall_t / 2, apply_to="all");
}

translate([0, -50, 0]) make_webbing_side_clip(t_outer, hip_webbing_t, hip_webbing_w, 20, gap=.5);
