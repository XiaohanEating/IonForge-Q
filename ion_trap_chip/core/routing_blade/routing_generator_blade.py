"""
Blade Ion Trap Routing Groove Generation Module
Routing grooves connect electrodes to inner end midpoint
"""
import math

try:
    from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox
    from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Fuse
    from OCC.Core.gp import gp_Pnt, gp_Dir, gp_Trsf, gp_Ax1, gp_Ax2, gp_GTrsf, gp_Vec
    from OCC.Core.BRepBuilderAPI import (
        BRepBuilderAPI_GTransform,
        BRepBuilderAPI_MakeWire,
        BRepBuilderAPI_MakeEdge,
        BRepBuilderAPI_MakeFace,
        BRepBuilderAPI_Sewing,
        BRepBuilderAPI_MakeSolid
    )
    OCC_AVAILABLE = True
except ImportError as e:
    print(f"OCC import failed in blade_routing_generator: {e}")
    OCC_AVAILABLE = False


class BladeRoutingGenerator:
    """Blade Ion Trap Routing Groove Generator"""
    
    def __init__(self, params):
        self.params = params
        self.routing_params = params.routing_params
        self.blade_params = params.blade_params
        self.overall_params = params.overall_params
        self.base_params = params.base_params
        
        self.grooves = []
        self.groove_geometries = None
    
    def calculate_routing_paths(self, electrode_endpoints):
        """Calculate routing paths
        
        Connect from short electrode near blade tip to blade tip, supports routing spacing parameter.
        
        Parameter description:
        - groove_spacing: Controls distance between connection points at blade tip
        - groove_spacing = 0: All electrodes connect to the same point (blade tip)
        - groove_spacing > 0: Electrodes connect to different points near blade tip, with groove_spacing between points
        """
        # Group electrode endpoints by blade and side
        endpoints_by_blade_side = {}
        for endpoint in electrode_endpoints:
            blade_index = endpoint['blade_index']
            side = endpoint['electrode_key'][2]  # 0 or 1, indicating left/right side
            key = (blade_index, side)
            if key not in endpoints_by_blade_side:
                endpoints_by_blade_side[key] = []
            endpoints_by_blade_side[key].append(endpoint)
        
        paths = []
        
        for (blade_index, side), endpoints in endpoints_by_blade_side.items():
            if not endpoints:
                continue
            
            # Get blade tip position (use X,Y coordinates, Z coordinate uses blade center Z=0)
            # If inner_point is None, use blade_inner_x and blade_inner_y
            if endpoints[0]['inner_point'] is not None:
                inner_x, inner_y, _ = endpoints[0]['inner_point']
            else:
                inner_x = endpoints[0]['blade_inner_x']
                inner_y = endpoints[0]['blade_inner_y']
            inner_z = 0.0  # Blade tip Z coordinate should be at blade center position
            direction_angle = endpoints[0]['direction_angle']
            
            # Get blade outer end position
            blade_x = endpoints[0]['blade_x']
            blade_y = endpoints[0]['blade_y']
            blade_inner_x = endpoints[0]['blade_inner_x']
            blade_inner_y = endpoints[0]['blade_inner_y']
            
            # Get routing parameters (from individual blade parameters in electrode params)
            electrode_blade_params = self.params.electrode_params.get('blade_params', {})
            blade_electrode_params = electrode_blade_params.get(blade_index, {})
            groove_spacing = blade_electrode_params.get('groove_spacing', self.routing_params.get('groove_spacing', 0.0))
            groove_width = blade_electrode_params.get('groove_width', self.routing_params.get('groove_width', 1.0))
            num_electrodes = len(endpoints)
            
            # Sort electrodes by Z coordinate (ensure routing order matches electrode positions)
            endpoints_sorted = sorted(endpoints, key=lambda e: e['z'])
            
            for i, endpoint in enumerate(endpoints_sorted):
                electrode_key = endpoint['electrode_key']
                
                # Calculate endpoint position of short electrode near blade tip
                # Short electrode extends towards blade tip
                dx_to_tip = inner_x - endpoint['x']
                dy_to_tip = inner_y - endpoint['y']
                dist_to_tip = math.sqrt(dx_to_tip ** 2 + dy_to_tip ** 2)
                
                # Take the end of short electrode near blade tip as routing start point
                tip_length = self.params.electrode_params['short_electrode_length']
                if dist_to_tip > 0:
                    ratio = tip_length / 2 / dist_to_tip
                    start_x = endpoint['x'] + dx_to_tip * ratio
                    start_y = endpoint['y'] + dy_to_tip * ratio
                else:
                    start_x = endpoint['x']
                    start_y = endpoint['y']
                start_z = endpoint['z']
                
                # Calculate routing end position (point near blade tip)
                # Multiple points evenly distributed along Z-axis with groove_spacing
                if num_electrodes > 1 and groove_spacing > 0:
                    offset_factor = (i - (num_electrodes - 1) / 2)
                    end_z = inner_z + offset_factor * groove_spacing
                else:
                    end_z = inner_z
                
                end_x = inner_x
                end_y = inner_y
                
                path_points = [
                    (start_x, start_y, start_z),
                    (end_x, end_y, end_z)
                ]
                
                paths.append({
                    'electrode_key': electrode_key,
                    'blade_index': blade_index,
                    'electrode_index': electrode_key[1],
                    'side': side,
                    'points': path_points,
                    'direction_angle': direction_angle,
                    'blade_width_inner': self.blade_params['min_thickness'] * 2 * 0.3,
                    'groove_width': groove_width,
                    'blade_x': blade_x,
                    'blade_y': blade_y,
                    'blade_inner_x': blade_inner_x,
                    'blade_inner_y': blade_inner_y,
                })
        
        self.grooves = paths
        return paths
    
    def create_groove_segment(self, p1, p2, width, depth, direction_angle, side, blade_width_inner, 
                              blade_x, blade_y, blade_inner_x, blade_inner_y):
        """Create single routing groove segment (using sweep method)
        
        Args:
            p1, p2: Two endpoints of the segment (from short electrode to blade tip, p1 at outer end, p2 at blade tip)
            width: Routing groove width (perpendicular to routing direction, within blade surface)
            depth: Routing groove etching depth (inward perpendicular to blade surface)
            direction_angle: Blade direction angle
            side: Blade side (0 or 1)
            blade_width_inner: Blade inner end width
            blade_x, blade_y: Blade outer end coordinates
            blade_inner_x, blade_inner_y: Blade inner end coordinates
        """
        if not OCC_AVAILABLE:
            return None
        
        x1, y1, z1 = p1
        x2, y2, z2 = p2
        
        # Calculate blade normal direction (refer to electrode implementation)
        # Vector from outer end to inner end is the blade tangent direction
        dx = blade_inner_x - blade_x
        dy = blade_inner_y - blade_y
        length_norm = math.sqrt(dx * dx + dy * dy)
        
        if length_norm > 0:
            # Normal direction = perpendicular to tangent, pointing outward from blade
            normal_x = -dy / length_norm
            normal_y = dx / length_norm
        else:
            normal_x = 0
            normal_y = 0
        
        # 1. Create diagonal path (edge)
        path_edge = BRepBuilderAPI_MakeEdge(gp_Pnt(x1, y1, z1), gp_Pnt(x2, y2, z2)).Edge()
        
        # Convert edge to wire (MakePipe requires Wire)
        path_wire = BRepBuilderAPI_MakeWire(path_edge).Wire()
        
        # 2. Create cross-section: width x depth rectangle
        # Cross-section in plane perpendicular to path
        # - Width direction: Z-axis (blade thickness direction)
        # - Depth direction: perpendicular to blade surface (inward normal direction)
        half_width = width / 2
        
        # Create four corner points of cross-section
        # Based on electrode position, left electrode is in positive normal direction, right in negative
        # Etching direction needs adjustment based on side
        if side == 0:
            # Left electrode, inward etching = subtract normal direction
            etched_x = x1 - normal_x * depth
            etched_y = y1 - normal_y * depth
        else:
            # Right electrode, inward etching = add normal direction
            etched_x = x1 + normal_x * depth
            etched_y = y1 + normal_y * depth
        
        sec_p1 = gp_Pnt(etched_x, etched_y, z1 - half_width)
        sec_p2 = gp_Pnt(etched_x, etched_y, z1 + half_width)
        sec_p3 = gp_Pnt(x1, y1, z1 + half_width)
        sec_p4 = gp_Pnt(x1, y1, z1 - half_width)
        
        # Create four edges of cross-section
        sec_edge1 = BRepBuilderAPI_MakeEdge(sec_p1, sec_p2).Edge()
        sec_edge2 = BRepBuilderAPI_MakeEdge(sec_p2, sec_p3).Edge()
        sec_edge3 = BRepBuilderAPI_MakeEdge(sec_p3, sec_p4).Edge()
        sec_edge4 = BRepBuilderAPI_MakeEdge(sec_p4, sec_p1).Edge()
        
        # Create cross-section wire
        sec_wire = BRepBuilderAPI_MakeWire()
        sec_wire.Add(sec_edge1)
        sec_wire.Add(sec_edge2)
        sec_wire.Add(sec_edge3)
        sec_wire.Add(sec_edge4)
        
        # Create cross-section face
        section = BRepBuilderAPI_MakeFace(sec_wire.Wire()).Face()
        
        # 3. Sweep along path to generate solid
        from OCC.Core.BRepOffsetAPI import BRepOffsetAPI_MakePipe
        pipe = BRepOffsetAPI_MakePipe(path_wire, section)
        
        return pipe.Shape()
    
    def create_all_routing_grooves(self, electrode_endpoints):
        """Create all routing grooves"""
        if not OCC_AVAILABLE:
            return None
        
        if not self.grooves:
            self.calculate_routing_paths(electrode_endpoints)
        
        geometries = []
        
        for groove in self.grooves:
            points = groove['points']
            width = groove.get('groove_width', self.routing_params['groove_width'])
            depth = self.routing_params['groove_depth']
            direction_angle = groove['direction_angle']
            side = groove['side']
            blade_width_inner = groove['blade_width_inner']
            blade_x = groove.get('blade_x', 0)
            blade_y = groove.get('blade_y', 0)
            blade_inner_x = groove.get('blade_inner_x', 0)
            blade_inner_y = groove.get('blade_inner_y', 0)
            
            for i in range(len(points) - 1):
                p1 = points[i]
                p2 = points[i + 1]
                
                segment = self.create_groove_segment(p1, p2, width, depth, direction_angle, side, 
                                                     blade_width_inner, blade_x, blade_y, 
                                                     blade_inner_x, blade_inner_y)
                if segment:
                    geometries.append(segment)
        
        if not geometries:
            return None
        
        combined = geometries[0]
        for geom in geometries[1:]:
            fuse = BRepAlgoAPI_Fuse(combined, geom)
            fuse.Build()
            if fuse.IsDone():
                combined = fuse.Shape()
        
        self.groove_geometries = combined
        return combined
    
    def create_all_routing_grooves_for_blade(self, electrode_endpoints, blade_index):
        """Create routing grooves for specified blade"""
        if not OCC_AVAILABLE:
            return None
        
        if not self.grooves:
            self.calculate_routing_paths(electrode_endpoints)
        
        # Filter routing grooves for specified blade
        blade_grooves = [g for g in self.grooves if g['blade_index'] == blade_index]
        
        geometries = []
        
        for groove in blade_grooves:
            points = groove['points']
            width = groove.get('groove_width', self.routing_params['groove_width'])
            depth = self.routing_params['groove_depth']
            direction_angle = groove['direction_angle']
            side = groove['side']
            blade_width_inner = groove['blade_width_inner']
            blade_x = groove.get('blade_x', 0)
            blade_y = groove.get('blade_y', 0)
            blade_inner_x = groove.get('blade_inner_x', 0)
            blade_inner_y = groove.get('blade_inner_y', 0)
            
            for i in range(len(points) - 1):
                p1 = points[i]
                p2 = points[i + 1]
                
                segment = self.create_groove_segment(p1, p2, width, depth, direction_angle, side, 
                                                     blade_width_inner, blade_x, blade_y, 
                                                     blade_inner_x, blade_inner_y)
                if segment:
                    geometries.append(segment)
        
        if not geometries:
            return None
        
        combined = geometries[0]
        for geom in geometries[1:]:
            fuse = BRepAlgoAPI_Fuse(combined, geom)
            fuse.Build()
            if fuse.IsDone():
                combined = fuse.Shape()
        
        return combined
