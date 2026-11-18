"""
Blade Ion Trap Electrode Generation Module
Electrode arrangement: Long electrodes extend along Z-axis, short electrodes are perpendicular to long electrodes (towards blade tip)

Geometry Parameter Description (Coordinate system: X-blade radial, Y-perpendicular to blade surface, Z-axial):
┌─────────────────────────────────────────────────────────────┐
│  Long electrodes (slender structures along Z-axis):         │
│    - Z-axis length: long_electrode_length (config param)    │
│    - Blade direction width: long_electrode_width (config)   │
│    - Etching depth: electrode_depth (config param)          │
│                                                              │
│  Short electrodes (perpendicular to long, towards tip):      │
│    - Z-axis width: short_electrode_height (config param)    │
│    - Tip direction length: short_electrode_width (config)   │
│    - Etching depth: electrode_depth (config param)          │
└─────────────────────────────────────────────────────────────┘
"""
import math

try:
    from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox
    from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Fuse
    from OCC.Core.gp import gp_Pnt, gp_Trsf, gp_Ax1, gp_Dir, gp_GTrsf
    from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_GTransform
    OCC_AVAILABLE = True
except ImportError as e:
    print(f"OCC import failed in blade_electrode_generator: {e}")
    OCC_AVAILABLE = False


class BladeElectrodeGenerator:
    """Blade Ion Trap Electrode Generator"""

    def __init__(self, params):
        self.params = params
        self.electrode_params = params.electrode_params
        self.blade_params = params.blade_params
        self.overall_params = params.overall_params
        self.base_params = params.base_params

        self.electrodes = []
        self.electrode_geometries = None

    def _get_config_params(self):
        """Get configuration parameters (read from config file)

        Configuration parameter mapping to code variables:
        ┌─────────────────────────┬────────────────────────────────┐
        │ Config parameter name   │ Code variable name             │
        ├─────────────────────────┼────────────────────────────────┤
        │ long_electrode_length   │ long_z_len                     │
        │   Long electrode Z length│                                │
        ├─────────────────────────┼────────────────────────────────┤
        │ long_electrode_width    │ long_radial_wid                │
        │   Long electrode width  │ (width in plane perpendicular  │
        │   in blade direction    │   to blade length)             │
        ├─────────────────────────┼────────────────────────────────┤
        │ short_electrode_width   │ short_z_wid                    │
        │   Short electrode Z width│                                │
        ├─────────────────────────┼────────────────────────────────┤
        │ short_electrode_length  │ short_tip_len                  │
        │   Short electrode length│ (extension length towards tip) │
        │   towards tip           │                                │
        ├─────────────────────────┼────────────────────────────────┤
        │ electrode_depth         │ etch_depth                     │
        │   Etching depth         │ (inward perpendicular to      │
        │                         │   blade surface)               │
        └─────────────────────────┴────────────────────────────────┘
        """
        ep = self.electrode_params

        return {
            'long_z_len': ep.get('long_electrode_length', 20.0),
            'long_radial_wid': ep.get('long_electrode_width', 2.0),
            'short_z_wid': ep.get('short_electrode_width', 5.0),   # Short electrode Z-width
            'short_tip_len': ep.get('short_electrode_length', 4.0),  # Short electrode tip length
            'etch_depth': ep.get('electrode_depth', 0.5),
        }

    def _get_blade_params(self, blade_index):
        """Get individual parameters for specified blade

        Each blade can have independent:
        - num_electrodes: Number of short electrodes
        - long_electrode_radial_offset: Long electrode radial offset
        - short_electrode_radial_offset: Short electrode radial offset
        - short_electrode_spacing: Short electrode spacing
        """
        ep = self.electrode_params
        blade_params = ep.get('blade_params', {})
        current = blade_params.get(blade_index, {})

        return {
            'num_short_electrodes': current.get('num_electrodes', ep.get('num_electrodes_per_blade', 4)),
            'long_radial_offset': current.get('long_electrode_radial_offset', ep.get('long_electrode_radial_offset', 0.0)),
            'short_radial_offset': current.get('short_electrode_radial_offset', ep.get('short_electrode_radial_offset', 0.0)),
            'short_spacing': current.get('short_electrode_spacing', ep.get('short_electrode_spacing', None)),
        }

    def calculate_electrode_positions(self):
        """Calculate all electrode positions

        Electrode parameter dictionary structure (unified naming):
        ┌──────────────────────────────────────────────────────┐
        │ Common fields:                                       │
        │   x, y, z: Electrode center coordinates              │
        │   type: 'long' or 'short'                            │
        │   side: 'left' or 'right'                            │
        │   blade_index: Blade index (0-3)                     │
        │   electrode_index: Electrode index                   │
        │   direction_angle: Blade orientation angle           │
        │   blade_width_at_pos: Blade width at this position   │
        │   blade_x, blade_y: Blade outer end coordinates      │
        │   blade_inner_x, blade_inner_y: Blade tip coordinates│
        │   inner_point: Blade tip coordinate tuple            │
        │                                                       │
        │ Long electrode fields (extending along Z-axis):      │
        │   z_length: Z-axis length                            │
        │   blade_width: Blade direction width                 │
        │               (in plane perpendicular to Z-axis)     │
        │   etch_depth: Etching depth (inward perpendicular to│
        │               blade surface)                         │
        │   z_min, z_max: Z-axis boundaries                   │
        │                                                       │
        │ Short electrode fields (perpendicular to long,       │
        │                        towards tip):                 │
        │   z_width: Z-axis width                              │
        │   tip_length: Tip direction length                   │
        │               (extending towards blade tip)          │
        │   etch_depth: Etching depth (inward perpendicular to│
        │               blade surface)                         │
        └──────────────────────────────────────────────────────┘
        """
        ep = self.electrode_params
        blp = self.blade_params

        electrodes = []
        blade_offset = blp.get('offset', 18.0)
        blade_length = blp['length']
        blade_center_z = 0

        cfg = self._get_config_params()

        for blade_index in range(4):
            if blade_index == 0:
                outer_x, outer_y = -blade_offset, blade_offset
            elif blade_index == 1:
                outer_x, outer_y = blade_offset, -blade_offset
            elif blade_index == 2:
                outer_x, outer_y = blade_offset, blade_offset
            else:
                outer_x, outer_y = -blade_offset, -blade_offset

            direction_angle = math.atan2(-outer_y, -outer_x)

            inner_x = outer_x + math.cos(direction_angle) * blade_length
            inner_y = outer_y + math.sin(direction_angle) * blade_length

            bp = self._get_blade_params(blade_index)

            electrode_center_x = inner_x - math.cos(direction_angle) * bp['long_radial_offset']
            electrode_center_y = inner_y - math.sin(direction_angle) * bp['long_radial_offset']

            blade_width_outer = blp['max_thickness']
            blade_width_inner = blp['min_thickness']

            distance_from_outer = math.sqrt(
                (electrode_center_x - outer_x)**2 +
                (electrode_center_y - outer_y)**2
            )

            blade_width_at_pos = blade_width_outer - (blade_width_outer - blade_width_inner) * (
                distance_from_outer / blade_length)

            dx = inner_x - outer_x
            dy = inner_y - outer_y
            length = math.sqrt(dx * dx + dy * dy)
            if length > 0:
                normal_x = -dy / length
                normal_y = dx / length
            else:
                normal_x = 0
                normal_y = 0

            half_blade_width = blade_width_at_pos / 2
            left_x = electrode_center_x + normal_x * half_blade_width
            left_y = electrode_center_y + normal_y * half_blade_width
            right_x = electrode_center_x - normal_x * half_blade_width
            right_y = electrode_center_y - normal_y * half_blade_width

            electrodes.extend(self._create_long_electrodes(
                blade_index, left_x, left_y, right_x, right_y,
                blade_center_z, direction_angle, inner_x, inner_y,
                outer_x, outer_y, blade_width_at_pos, cfg))

            electrodes.extend(self._create_short_electrodes(
                blade_index, left_x, left_y, right_x, right_y,
                blade_center_z, direction_angle, inner_x, inner_y,
                outer_x, outer_y, blade_width_at_pos, cfg, bp))

        self.electrodes = electrodes
        return electrodes

    def _create_long_electrodes(self, blade_index, left_x, left_y, right_x, right_y,
                                 blade_center_z, direction_angle, inner_x, inner_y,
                                 outer_x, outer_y, blade_width_at_pos, cfg):
        """Create long electrodes (left and right sides)"""
        electrodes = []

        long_electrode = {
            'blade_index': blade_index,
            'type': 'long',
            'direction_angle': direction_angle,
            'blade_x': outer_x,
            'blade_y': outer_y,
            'blade_inner_x': inner_x,
            'blade_inner_y': inner_y,
            'blade_width_at_pos': blade_width_at_pos,
            'inner_point': (inner_x, inner_y, blade_center_z),
            'z_length': cfg['long_z_len'],
            'blade_width': cfg['long_radial_wid'],
            'etch_depth': cfg['etch_depth'],
            'z_min': blade_center_z - cfg['long_z_len'] / 2,
            'z_max': blade_center_z + cfg['long_z_len'] / 2,
        }

        for side, side_x, side_y, idx in [('left', left_x, left_y, 0),
                                            ('right', right_x, right_y, 1)]:
            elec = long_electrode.copy()
            elec['side'] = side
            elec['electrode_index'] = idx
            elec['x'] = side_x
            elec['y'] = side_y
            elec['z'] = blade_center_z
            electrodes.append(elec)

        return electrodes

    def _create_short_electrodes(self, blade_index, left_x, left_y, right_x, right_y,
                                  blade_center_z, direction_angle, inner_x, inner_y,
                                  outer_x, outer_y, blade_width_at_pos, cfg, bp):
        """Create short electrodes (left and right sides, perpendicular to long electrodes)"""
        electrodes = []

        num_short = bp['num_short_electrodes']
        short_spacing = bp['short_spacing']

        if num_short <= 0:
            return electrodes

        short_z_wid = cfg['short_z_wid']

        if short_spacing is not None:
            spacing = short_spacing
            total_len = (num_short - 1) * spacing
            start_z = blade_center_z - total_len / 2
        elif num_short > 1:
            spacing = (cfg['long_z_len'] - short_z_wid) / (num_short - 1)
            start_z = blade_center_z - cfg['long_z_len'] / 2 + short_z_wid / 2
        else:
            spacing = 0
            start_z = blade_center_z

        short_electrode_base = {
            'blade_index': blade_index,
            'type': 'short',
            'direction_angle': direction_angle,
            'blade_x': outer_x,
            'blade_y': outer_y,
            'blade_inner_x': inner_x,
            'blade_inner_y': inner_y,
            'blade_width_at_pos': blade_width_at_pos,
            'inner_point': None,
            'z_width': short_z_wid,
            'tip_length': cfg['short_tip_len'],
            'blade_width': short_z_wid,  # Short electrode uses its own width parameter
            'etch_depth': cfg['etch_depth'],
            'short_radial_offset': bp.get('short_electrode_radial_offset', 0.0),
        }

        for i in range(num_short):
            short_z = start_z + i * spacing

            for side, side_x, side_y, idx in [('left', left_x, left_y, i + 2),
                                                ('right', right_x, right_y,
                                                 i + 2 + num_short)]:
                elec = short_electrode_base.copy()
                elec['side'] = side
                elec['electrode_index'] = idx
                elec['x'] = side_x
                elec['y'] = side_y
                elec['z'] = short_z
                elec['inner_point'] = (inner_x, inner_y, short_z)
                electrodes.append(elec)

        return electrodes

    def create_electrode_geometry(self, electrode):
        """Create single electrode geometry

        Long electrode geometry: Extends along Z-axis, width in plane perpendicular to Z-axis, etching depth perpendicular to blade surface
        Short electrode geometry: Extends along blade direction (towards tip), width along Z-axis, etching depth perpendicular to blade surface

        Args:
            electrode: Electrode parameter dictionary containing:
                - type: 'long' or 'short'
                - x, y, z: Center coordinates
                - direction_angle: Rotation angle
                Long electrode: z_length, blade_width, etch_depth
                Short electrode: z_width, tip_length, etch_depth
        """
        if not OCC_AVAILABLE:
            return None

        x = electrode['x']
        y = electrode['y']
        z = electrode['z']
        electrode_type = electrode['type']
        direction_angle = electrode['direction_angle']

        if electrode_type == 'long':
            z_dim = electrode['z_length']
            blade_wid = electrode['blade_width']
        else:
            z_dim = electrode['z_width']
            blade_wid = electrode['blade_width'] if 'blade_width' in electrode else electrode['tip_length']

        etch_depth = electrode['etch_depth']
        blade_width_at_pos = electrode['blade_width_at_pos']

        actual_depth = min(etch_depth, blade_width_at_pos / 2 - 0.01)

        blade_inner_x = electrode.get('blade_inner_x', electrode['blade_x'])
        blade_inner_y = electrode.get('blade_inner_y', electrode['blade_y'])
        blade_x = electrode['blade_x']
        blade_y = electrode['blade_y']

        dx = blade_inner_x - blade_x
        dy = blade_inner_y - blade_y
        length_norm = math.sqrt(dx * dx + dy * dy)

        if length_norm > 0:
            normal_x = -dy / length_norm
            normal_y = dx / length_norm
            blade_dir_x = dx / length_norm
            blade_dir_y = dy / length_norm
        else:
            normal_x = 0
            normal_y = 0
            blade_dir_x = 0
            blade_dir_y = 0

        half_z = z_dim / 2
        half_blade_wid = blade_wid / 2

        if electrode_type == 'long':
            p_min = gp_Pnt(x - half_blade_wid, y - half_blade_wid, z - half_z)
            p_max = gp_Pnt(x + half_blade_wid, y + half_blade_wid, z + half_z)
            
            p_min = gp_Pnt(p_min.X() - normal_x * actual_depth, 
                          p_min.Y() - normal_y * actual_depth, 
                          p_min.Z())
            p_max = gp_Pnt(p_max.X() - normal_x * actual_depth, 
                          p_max.Y() - normal_y * actual_depth, 
                          p_max.Z())
        else:
            tip_length = electrode['tip_length']
            
            # Calculate direction from electrode position to blade tip directly
            dx_to_tip = blade_inner_x - x
            dy_to_tip = blade_inner_y - y
            dist_to_tip = math.sqrt(dx_to_tip ** 2 + dy_to_tip ** 2)
            
            # Limit electrode length to not exceed distance to tip
            actual_tip_length = min(tip_length, dist_to_tip - 0.1)
            
            # Adjust direction based on quadrant (referencing blade_chip_builder.py logic)
            # Blade direction differs in different quadrants, need to adjust extension direction
            # Use blade outer end position to determine quadrant
            outward_direction_x = -1 if blade_x > 0 else 1
            outward_direction_y = -1 if blade_y > 0 else 1    
            
            # Calculate outward direction unit vector
            dist_from_center = math.sqrt(blade_x**2 + blade_y**2)
            if dist_from_center > 0:
                outward_x = blade_x / dist_from_center
                outward_y = blade_y / dist_from_center
            else:
                outward_x = 0
                outward_y = 0
            
            # Calculate direction vector towards blade tip (considering quadrant)
            # Tip direction = inward direction = -outward direction
            dir_x = -outward_x * outward_direction_x
            dir_y = -outward_y * outward_direction_y
            
            # Short electrode radial offset (referencing hole position calculation logic)
            # Offset direction = outward direction * direction coefficient
            short_radial_offset = electrode.get('short_radial_offset', 0.0)
            offset_x = short_radial_offset * outward_x * outward_direction_x
            offset_y = short_radial_offset * outward_y * outward_direction_y
            
            start_x = x + offset_x
            start_y = y + offset_y
            end_x = x + offset_x + dir_x * actual_tip_length
            end_y = y + offset_y + dir_y * actual_tip_length
            
            # Short electrode cube: extends along blade direction (towards tip), uses its own parameters
            # Blade direction: start_x -> end_x, start_y -> end_y (length = short_electrode_length)
            # Perpendicular to blade: uses short_z_wid (width = short_electrode_width)
            # Z-axis direction: uses short_z_wid (thickness)
            p_min = gp_Pnt(start_x, start_y - half_blade_wid, z - half_z)
            p_max = gp_Pnt(end_x, start_y + half_blade_wid, z + half_z)
            
            # Apply etching depth only in negative normal direction (towards blade interior)
            p_min = gp_Pnt(p_min.X() - normal_x * actual_depth, 
                          p_min.Y() - normal_y * actual_depth, 
                          p_min.Z())
            p_max = gp_Pnt(p_max.X() - normal_x * actual_depth, 
                          p_max.Y() - normal_y * actual_depth, 
                          p_max.Z())

        box = BRepPrimAPI_MakeBox(p_min, p_max).Shape()

        trsf = gp_Trsf()
        axis = gp_Ax1(gp_Pnt(x, y, z), gp_Dir(0, 0, 1))
        trsf.SetRotation(axis, direction_angle)

        gtrsf = gp_GTrsf()
        gtrsf.SetTrsf(trsf)
        box = BRepBuilderAPI_GTransform(box, gtrsf, True).Shape()

        return box

    def create_all_electrode_geometries(self):
        """Create all electrode geometries and fuse them"""
        if not OCC_AVAILABLE:
            return None

        if not self.electrodes:
            self.calculate_electrode_positions()

        geometries = []
        for electrode in self.electrodes:
            geom = self.create_electrode_geometry(electrode)
            if geom:
                geometries.append(geom)

        if not geometries:
            return None

        combined = geometries[0]
        for geom in geometries[1:]:
            fuse = BRepAlgoAPI_Fuse(combined, geom)
            fuse.Build()
            if fuse.IsDone():
                combined = fuse.Shape()

        self.electrode_geometries = combined
        return combined

    def create_electrode_geometry_for_blade(self, blade_index):
        """Create electrode geometry for specified blade"""
        if not OCC_AVAILABLE:
            return None

        if not self.electrodes:
            self.calculate_electrode_positions()

        blade_electrodes = [e for e in self.electrodes if e['blade_index'] == blade_index]

        if not blade_electrodes:
            return None

        geometries = []
        for electrode in blade_electrodes:
            geom = self.create_electrode_geometry(electrode)
            if geom:
                geometries.append(geom)

        combined = geometries[0]
        for geom in geometries[1:]:
            fuse = BRepAlgoAPI_Fuse(combined, geom)
            fuse.Build()
            if fuse.IsDone():
                combined = fuse.Shape()

        return combined

    def get_electrode_endpoints(self):
        """Get electrode endpoints (for routing)"""
        if not self.electrodes:
            self.calculate_electrode_positions()

        endpoints = []
        for electrode in self.electrodes:
            if electrode['type'] == 'short':
                # Convert side to number: left=0, right=1
                side_num = 0 if electrode['side'] == 'left' else 1
                endpoints.append({
                    'x': electrode['x'],
                    'y': electrode['y'],
                    'z': electrode['z'],
                    'blade_index': electrode['blade_index'],
                    'electrode_key': (electrode['blade_index'],
                                      electrode['electrode_index'], side_num),
                    'inner_point': electrode['inner_point'],
                    'direction_angle': electrode['direction_angle'],
                    'blade_x': electrode['blade_x'],
                    'blade_y': electrode['blade_y'],
                    'blade_inner_x': electrode.get('blade_inner_x', electrode['blade_x']),
                    'blade_inner_y': electrode.get('blade_inner_y', electrode['blade_y']),
                    'side': side_num
                })

        return endpoints
