"""
Blade Chip Base Shapes Utility Module

Provides general 3D shape generation capabilities for component builders.
"""

import math

try:
    from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder
    from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakePolygon
    from OCC.Core.BRepOffsetAPI import BRepOffsetAPI_ThruSections
    from OCC.Core.gp import gp_Pnt, gp_Dir, gp_Ax2
    OCC_AVAILABLE = True
except ImportError:
    OCC_AVAILABLE = False


class BladeShapeGenerator:
    """Blade Chip General Shape Generator"""
    
    def __init__(self, params=None):
        self.params = params
    
    def create_box(self, center_x, center_y, z_start, length, width, height):
        """Create a rectangular box"""
        if not OCC_AVAILABLE:
            return None
        
        box_maker = BRepPrimAPI_MakeBox(
            gp_Pnt(center_x - length/2, center_y - width/2, z_start),
            length, width, height
        )
        return box_maker.Shape()
    
    def create_cylinder(self, center_x, center_y, z_start, radius, height, direction='z'):
        """Create a cylinder"""
        if not OCC_AVAILABLE:
            return None
        
        if direction == 'z':
            axis = gp_Ax2(gp_Pnt(center_x, center_y, z_start), gp_Dir(0, 0, 1))
        elif direction == 'x':
            axis = gp_Ax2(gp_Pnt(center_x, center_y, z_start), gp_Dir(1, 0, 0))
        elif direction == 'y':
            axis = gp_Ax2(gp_Pnt(center_x, center_y, z_start), gp_Dir(0, 1, 0))
        else:
            axis = gp_Ax2(gp_Pnt(center_x, center_y, z_start), gp_Dir(0, 0, 1))
        
        cylinder_maker = BRepPrimAPI_MakeCylinder(axis, radius, height)
        return cylinder_maker.Shape()
    
    def create_tapered_pyramid_slot(self, length, width_outer, width_inner,
                                    center_x=0, center_y=0, z_start=0, z_end=0,
                                    is_vertical=False):
        """Create a tapered pyramid slot"""
        if not OCC_AVAILABLE:
            return None
        
        thickness = abs(z_end - z_start)
        
        if is_vertical:
            outer_corners = [
                gp_Pnt(center_x - width_outer/2, center_y - length/2, z_start),
                gp_Pnt(center_x + width_outer/2, center_y - length/2, z_start),
                gp_Pnt(center_x + width_outer/2, center_y + length/2, z_start),
                gp_Pnt(center_x - width_outer/2, center_y + length/2, z_start)
            ]
            inner_corners = [
                gp_Pnt(center_x - width_inner/2, center_y - length/2, z_end),
                gp_Pnt(center_x + width_inner/2, center_y - length/2, z_end),
                gp_Pnt(center_x + width_inner/2, center_y + length/2, z_end),
                gp_Pnt(center_x - width_inner/2, center_y + length/2, z_end)
            ]
        else:
            outer_corners = [
                gp_Pnt(center_x - length/2, center_y - width_outer/2, z_start),
                gp_Pnt(center_x + length/2, center_y - width_outer/2, z_start),
                gp_Pnt(center_x + length/2, center_y + width_outer/2, z_start),
                gp_Pnt(center_x - length/2, center_y + width_outer/2, z_start)
            ]
            inner_corners = [
                gp_Pnt(center_x - length/2, center_y - width_inner/2, z_end),
                gp_Pnt(center_x + length/2, center_y - width_inner/2, z_end),
                gp_Pnt(center_x + length/2, center_y + width_inner/2, z_end),
                gp_Pnt(center_x - length/2, center_y + width_inner/2, z_end)
            ]
        
        outer_polygon = BRepBuilderAPI_MakePolygon()
        for corner in outer_corners:
            outer_polygon.Add(corner)
        outer_polygon.Close()
        outer_wire = outer_polygon.Wire()
        
        inner_polygon = BRepBuilderAPI_MakePolygon()
        for corner in inner_corners:
            inner_polygon.Add(corner)
        inner_polygon.Close()
        inner_wire = inner_polygon.Wire()
        
        loft_maker = BRepOffsetAPI_ThruSections(True)
        loft_maker.AddWire(outer_wire)
        loft_maker.AddWire(inner_wire)
        loft_maker.Build()
        
        return loft_maker.Shape()
