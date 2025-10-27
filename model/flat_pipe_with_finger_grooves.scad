// Flat pipe with four finger grooves
// Designed for hand-held grip using OpenSCAD

$fn = 64; // smoothness for cylinders

// Overall dimensions (in millimeters)
pipe_length = 120;
pipe_width = 32;
pipe_thickness = 22;
wall_thickness = 3;
corner_radius = 8;

// Finger groove settings
finger_count = 4;
finger_radius = 11;
finger_depth = 7;
finger_margin = 18;

module rounded_prism(length, width, height, radius) {
    // Create a rectangular prism with rounded edges using hull of cylinders
    hull() {
        for (x = [-length/2 + radius, length/2 - radius])
            for (y = [-width/2 + radius, width/2 - radius])
                translate([x, y, 0])
                    cylinder(r = radius, h = height, center = true);
    }
}

module flat_pipe() {
    difference() {
        // Outer shell
        rounded_prism(pipe_length, pipe_width, pipe_thickness, corner_radius);

        // Hollow interior
        translate([0, 0, 0])
            rounded_prism(pipe_length - 2 * wall_thickness,
                          pipe_width - 2 * wall_thickness,
                          pipe_thickness - 2 * wall_thickness,
                          max(corner_radius - wall_thickness, 1));

        // Finger grooves along the top surface
        groove_spacing = (pipe_length - 2 * finger_margin) / (finger_count - 1);
        for (i = [0 : finger_count - 1]) {
            x_pos = -pipe_length/2 + finger_margin + i * groove_spacing;
            translate([x_pos, 0, pipe_thickness/2 - finger_depth + finger_radius])
                rotate([0, 90, 0])
                    cylinder(r = finger_radius, h = pipe_width + 2, center = true);
        }
    }
}

flat_pipe();
