"""
Blade Chip Components Module

Contains three main component builders for blade chip:
1. BladeBaseBuilder - Base builder
2. BladeColumnBuilder - Column builder
3. BladeTrapezoidBuilder - Trapezoidal blade builder
"""

import math

try:
    from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse
    from OCC.Core.BRepBuilderAPI import (
        BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeFace,
        BRepBuilderAPI_GTransform, BRepBuilderAPI_Sewing, BRepBuilderAPI_MakeSolid
    )
    from OCC.Core.gp import gp_Pnt, gp_Dir, gp_Ax1, gp_Trsf, gp_GTrsf
    from OCC.Core.TopAbs import TopAbs_SHELL
    from OCC.Core.TopExp import TopExp_Explorer
    from OCC.Core.BRepCheck import BRepCheck_Analyzer
    from .base_shapes import BladeShapeGenerator
    OCC_AVAILABLE = True
except ImportError:
    OCC_AVAILABLE = False
    BladeShapeGenerator = None  # Define placeholder


class BladeBaseBuilder:
    """Base builder - Builds top and bottom bases with chamfers and center hole"""
    
    def __init__(self, params):
        self.params = params
        self.bp = params.base_params
        self.op = params.overall_params
        if OCC_AVAILABLE and BladeShapeGenerator is not None:
            self.shape_generator = BladeShapeGenerator(params)
        else:
            self.shape_generator = None
    
    def build(self, is_top=True):
        """Build base"""
        if not OCC_AVAILABLE:
            return None
        
        bp = self.bp
        op = self.op
        
        z_pos = op['total_height']/2 if is_top else -op['total_height']/2
        
        # Base body (chamfered rectangle)
        base_length = op['base_length']
        base_width = op['base_width']
        thickness = bp['thickness']
        
        # Main rectangle
        main_part = self.shape_generator.create_box(
            0, 0, z_pos - thickness/2,
            base_length, base_width, thickness
        )
        
        # Add extensions (for chamfer corners)
        ext_len = bp['extension_length']
        ext_wid = bp['extension_width']

        bottom_ext = self.shape_generator.create_box(
            0, base_width/2 - ext_wid/2, z_pos - thickness/2,
            ext_len, ext_wid, thickness
        )
        
        top_ext = self.shape_generator.create_box(
            0, -base_width/2 + ext_wid/2, z_pos - thickness/2,
            ext_len, ext_wid, thickness
        )

        right_ext = self.shape_generator.create_box(
            base_length/2 - ext_len/2, 0, z_pos - thickness/2,
            ext_len, ext_wid, thickness
        )

        left_ext = self.shape_generator.create_box(
            -base_length/2 + ext_len/2, 0, z_pos - thickness/2,
            ext_len, ext_wid, thickness
        )
        
        # Cut extensions to create chamfers
        base = BRepAlgoAPI_Cut(main_part, top_ext).Shape()
        base = BRepAlgoAPI_Cut(base, bottom_ext).Shape()
        base = BRepAlgoAPI_Cut(base, right_ext).Shape()
        base = BRepAlgoAPI_Cut(base, left_ext).Shape()
        
        # Create center hole (through)
        center_hole = self.shape_generator.create_cylinder(
            0, 0, z_pos - thickness/2 - 1,
            bp['center_hole_diameter']/2, thickness + 4
        )
        base = BRepAlgoAPI_Cut(base, center_hole).Shape()
        
        # Create mounting holes (through)
        for (hx, hy) in bp['mount_hole_positions']:
            hole = self.shape_generator.create_cylinder(
                hx, hy, z_pos - thickness/2 - 1,
                bp['mount_hole_diameter']/2, thickness + 4
            )
            base = BRepAlgoAPI_Cut(base, hole).Shape()
        
        return base


class BladeColumnBuilder:
    """Column builder - Builds X-shaped crossing columns"""
    
    def __init__(self, params):
        self.params = params
        self.cp = params.column_params
        self.bp = params.base_params
        self.op = params.overall_params
        self.shape_generator = BladeShapeGenerator(params)
    
    def build(self, column_index):
        """Build X-shaped crossing column (vertical, X-shaped in top view)"""
        if not OCC_AVAILABLE:
            return None
        
        cp = self.cp
        bp = self.bp
        op = self.op
        
        column_height = op['total_height'] - bp['thickness']
        offset = cp['corner_offset']
        
        diag_angle = math.pi / 4
        
        if column_index == 0:
            x_pos = -offset * math.cos(diag_angle)
            y_pos = offset * math.sin(diag_angle)
            rotation_angle = diag_angle
        elif column_index == 1:
            x_pos = offset * math.cos(diag_angle)
            y_pos = -offset * math.sin(diag_angle)
            rotation_angle = diag_angle
        elif column_index == 2:
            x_pos = offset * math.cos(diag_angle)
            y_pos = offset * math.sin(diag_angle)
            rotation_angle = -diag_angle
        else:
            x_pos = -offset * math.cos(diag_angle)
            y_pos = -offset * math.sin(diag_angle)
            rotation_angle = -diag_angle
        
        # Calculate column Z position
        bottom_z = -column_height / 2
        
        # Create vertical rectangular column
        column = self.shape_generator.create_box(
            x_pos, y_pos, bottom_z,
            cp['thickness'], cp['width'], column_height
        )
        
        # Drill holes before rotating the column
        num_holes = cp.get('num_holes_per_column', 4)
        hole_diameter = cp.get('hole_diameter', 1.0)
        hole_spacing = cp.get('hole_spacing', 8.0)
        hole_radial_offset = cp.get('hole_radial_offset', 0)
        
        if num_holes > 0 and hole_diameter > 0:
            if num_holes == 1:
                z_positions = [bottom_z + column_height / 2]
            else:
                total_length = (num_holes - 1) * hole_spacing
                start_z = bottom_z + (column_height - total_length) / 2
                z_positions = [start_z + i * hole_spacing for i in range(num_holes)]
            
            column_penetration = cp['thickness'] + 100
            
            dist_from_center = math.sqrt(x_pos**2 + y_pos**2)
            if dist_from_center > 0:
                outward_x = x_pos / dist_from_center
                outward_y = y_pos / dist_from_center
            else:
                outward_x = 0
                outward_y = 0
            
            for z in z_positions:
                hole_x = x_pos + hole_radial_offset * outward_x
                hole_y = y_pos + hole_radial_offset * outward_y
                cylinder_start_x = hole_x - column_penetration / 2
                
                cylinder = self.shape_generator.create_cylinder(
                    cylinder_start_x, hole_y, z,
                    hole_diameter / 2, column_penetration,
                    direction='x'
                )
                
                column = BRepAlgoAPI_Cut(column, cylinder).Shape()
        
        trsf = gp_Trsf()
        axis = gp_Ax1(gp_Pnt(x_pos, y_pos, bottom_z), gp_Dir(0, 0, 1))
        trsf.SetRotation(axis, rotation_angle)
        
        gtrsf = gp_GTrsf()
        gtrsf.SetTrsf(trsf)
        column = BRepBuilderAPI_GTransform(column, gtrsf, True).Shape()
        
        return column


class BladeTrapezoidBuilder:
    """Trapezoidal blade builder - Builds isosceles trapezoidal blades"""
    
    def __init__(self, params):
        self.params = params
        self.blp = params.blade_params
        self.cp = params.column_params
        self.bp = params.base_params
        self.op = params.overall_params
    
    def build(self, blade_index):
        """Build true prismatic blade (height and width taper from outside to inside)"""
        if not OCC_AVAILABLE:
            return None, []
        
        cp = self.cp
        bp = self.bp
        op = self.op
        blp = self.blp
        
        # Blade parameters
        blade_length = blp['length']
        blade_width_outer = blp['max_thickness']
        blade_width_inner = blp['min_thickness']
        
        # Blade height tapers from outside to inside
        column_height = op['total_height'] - bp['thickness']
        blade_height_outer = column_height * 0.8
        blade_height_inner = column_height * 0.3
        
        # Get blade offset parameter
        blade_offset = blp.get('offset', 18.0)
        
        # Define positions for four blades
        if blade_index == 0:
            x_pos = -blade_offset
            y_pos = blade_offset
        elif blade_index == 1:
            x_pos = blade_offset
            y_pos = -blade_offset
        elif blade_index == 2:
            x_pos = blade_offset
            y_pos = blade_offset
        else:
            x_pos = -blade_offset
            y_pos = -blade_offset
        
        # Calculate angle towards central axis
        extend_angle = math.atan2(-y_pos, -x_pos)
        
        # Calculate outer end Z positions
        outer_bottom_z = -column_height/2 + (column_height - blade_height_outer)/2
        outer_top_z = outer_bottom_z + blade_height_outer
        
        # Calculate inner end Z positions
        inner_bottom_z = -column_height/2 + (column_height - blade_height_inner)/2
        inner_top_z = inner_bottom_z + blade_height_inner
        
        # Calculate inner end X position
        inner_x = x_pos + blade_length
        
        # Create 8 vertices
        p1 = gp_Pnt(x_pos, y_pos - blade_width_outer/2, outer_bottom_z)
        p2 = gp_Pnt(x_pos, y_pos + blade_width_outer/2, outer_bottom_z)
        p3 = gp_Pnt(x_pos, y_pos + blade_width_outer/2, outer_top_z)
        p4 = gp_Pnt(x_pos, y_pos - blade_width_outer/2, outer_top_z)
        
        p5 = gp_Pnt(inner_x, y_pos - blade_width_inner/2, inner_bottom_z)
        p6 = gp_Pnt(inner_x, y_pos + blade_width_inner/2, inner_bottom_z)
        p7 = gp_Pnt(inner_x, y_pos + blade_width_inner/2, inner_top_z)
        p8 = gp_Pnt(inner_x, y_pos - blade_width_inner/2, inner_top_z)
        
        # Create 12 edges
        e1 = BRepBuilderAPI_MakeEdge(p1, p2).Edge()
        e2 = BRepBuilderAPI_MakeEdge(p2, p3).Edge()
        e3 = BRepBuilderAPI_MakeEdge(p3, p4).Edge()
        e4 = BRepBuilderAPI_MakeEdge(p4, p1).Edge()
        
        e5 = BRepBuilderAPI_MakeEdge(p5, p6).Edge()
        e6 = BRepBuilderAPI_MakeEdge(p6, p7).Edge()
        e7 = BRepBuilderAPI_MakeEdge(p7, p8).Edge()
        e8 = BRepBuilderAPI_MakeEdge(p8, p5).Edge()
        
        e9 = BRepBuilderAPI_MakeEdge(p1, p5).Edge()
        e10 = BRepBuilderAPI_MakeEdge(p2, p6).Edge()
        e11 = BRepBuilderAPI_MakeEdge(p3, p7).Edge()
        e12 = BRepBuilderAPI_MakeEdge(p4, p8).Edge()
        
        # Create wires for 6 faces
        w1 = BRepBuilderAPI_MakeWire(e1, e10, e5.Reversed(), e9.Reversed()).Wire()
        w2 = BRepBuilderAPI_MakeWire(e2, e11, e6.Reversed(), e10.Reversed()).Wire()
        w3 = BRepBuilderAPI_MakeWire(e3, e12, e7.Reversed(), e11.Reversed()).Wire()
        w4 = BRepBuilderAPI_MakeWire(e4, e9, e8.Reversed(), e12.Reversed()).Wire()
        w5 = BRepBuilderAPI_MakeWire(e1, e2, e3, e4).Wire()
        w6 = BRepBuilderAPI_MakeWire(e5, e6, e7, e8).Wire()
        
        # Create 6 faces
        f1 = BRepBuilderAPI_MakeFace(w1).Face()
        f2 = BRepBuilderAPI_MakeFace(w2).Face()
        f3 = BRepBuilderAPI_MakeFace(w3).Face()
        f4 = BRepBuilderAPI_MakeFace(w4).Face()
        f5 = BRepBuilderAPI_MakeFace(w5).Face()
        f6 = BRepBuilderAPI_MakeFace(w6).Face()
        
        # Sew all faces to form solid
        sewing = BRepBuilderAPI_Sewing()
        sewing.Add(f1)
        sewing.Add(f2)
        sewing.Add(f3)
        sewing.Add(f4)
        sewing.Add(f5)
        sewing.Add(f6)
        sewing.Perform()
        
        blade = sewing.SewedShape()
        
        # Ensure blade is a solid
        exp = TopExp_Explorer(blade, TopAbs_SHELL)
        if exp.More():
            shell = exp.Current()
            solid_maker = BRepBuilderAPI_MakeSolid(shell)
            if solid_maker.IsDone():
                blade = solid_maker.Shape()
                print(f"    Blade {blade_index}: Successfully converted to solid")
        
        # Validate shape validity
        analyzer = BRepCheck_Analyzer(blade)
        if not analyzer.IsValid():
            print(f"    Blade {blade_index}: Warning - Shape is not valid")
        
        # Drill holes before rotating the blade
        num_holes = blp.get('num_holes_per_blade', 3)
        hole_diameter = blp.get('hole_diameter', 0.8)
        hole_spacing = blp.get('hole_spacing', 6.0)
        hole_radial_offset = blp.get('hole_radial_offset', 0)
        
        hole_cylinders = []
        shape_generator = BladeShapeGenerator(self.params)
        
        if num_holes > 0 and hole_diameter > 0:
            blade_height = outer_top_z - outer_bottom_z
            if num_holes == 1:
                z_positions = [outer_bottom_z + blade_height / 2]
            else:
                total_length = (num_holes - 1) * hole_spacing
                start_z = outer_bottom_z + (blade_height - total_length) / 2
                z_positions = [start_z + i * hole_spacing for i in range(num_holes)]
            
            dist_from_center = math.sqrt(x_pos**2 + y_pos**2)
            if dist_from_center > 0:
                outward_x = x_pos / dist_from_center
                outward_y = y_pos / dist_from_center
            else:
                outward_x = 0
                outward_y = 0
            
            outward_direction_x = -1 if x_pos > 0 else 1
            outward_direction_y = -1 if y_pos > 0 else 1
            
            hole_x = x_pos + blade_length / 2 + hole_radial_offset * outward_x * outward_direction_x
            hole_y = y_pos + hole_radial_offset * outward_y * outward_direction_y
            
            print(f"    Blade {blade_index}: y_pos={y_pos}, hole_radial_offset={hole_radial_offset}, hole_y={hole_y}")
            
            blade_penetration = blade_width_outer + 100
            
            for z in z_positions:
                cylinder_start_y = hole_y - blade_penetration / 2
                
                cylinder = shape_generator.create_cylinder(
                    hole_x, cylinder_start_y, z,
                    hole_diameter / 2, blade_penetration,
                    direction='y'
                )
                
                hole_cylinders.append(cylinder)
                blade = BRepAlgoAPI_Cut(blade, cylinder).Shape()
        
        trsf = gp_Trsf()
        axis = gp_Ax1(gp_Pnt(x_pos, y_pos, outer_bottom_z), gp_Dir(0, 0, 1))
        trsf.SetRotation(axis, extend_angle)
        
        gtrsf = gp_GTrsf()
        gtrsf.SetTrsf(trsf)
        blade = BRepBuilderAPI_GTransform(blade, gtrsf, True).Shape()

        rotated_cylinders = []
        for cylinder in hole_cylinders:
            rotated_cylinder = BRepBuilderAPI_GTransform(cylinder, gtrsf, True).Shape()
            rotated_cylinders.append(rotated_cylinder)
        
        return blade, rotated_cylinders
