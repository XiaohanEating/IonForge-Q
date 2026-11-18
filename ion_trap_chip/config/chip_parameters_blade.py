"""
Blade-type Linear Paul Ion Trap Chip Parameters (V3)

Structure Description:
1. Top and bottom bases (T-shaped, with large central through hole)
2. Four vertical connecting columns (flat, narrow side facing center)
3. Four inclined blade tips (facing inward, forming central ion channel)
"""

import math


class BladeChipV3Parameters:
    """Blade Chip V3 Parameter Configuration"""

    def __init__(self):
        # ============ Overall Parameters ============
        self.overall_params = {
            'total_height': 80.0,      # Total height mm, from top base center to bottom base center
            'base_length': 70.0,       # Base length mm
            'base_width': 60.0,        # Base width mm
        }

        # ============ Base Parameters ============
        self.base_params = {
            'thickness': 8.0,          # Base thickness mm
            'center_hole_diameter': 12.0,   # Center ion channel hole diameter mm

            # Mounting holes
            'mount_hole_diameter': 5.0,
            'mount_hole_positions': [
                (-25, -18), (25, -18),
                (-25, 18), (25, 18),
            ],

            # T-shaped extension
            'extension_length': 16.0,
            'extension_width': 10.0,
        }

        # ============ Vertical Connecting Column Parameters ============
        self.column_params = {
            'width': 20.0,             # Column width mm (wide side)
            'thickness': 5.0,          # Column thickness mm (narrow side, facing center)
            'corner_offset': 26.0,     # Corner offset mm (increase to move columns closer to base corners)

            # Small holes on columns
            'hole_diameter': 4.0,      # Small hole diameter mm
            'num_holes_per_column': 7,  # Number of small holes per column
            'hole_spacing': 10.0,        # Hole spacing mm (along Z-axis)
            'hole_radial_offset': 8.0,  # Hole radial offset mm (in XY plane, positive outward, negative inward)
        }

        # ============ Blade Parameters ============
        self.blade_params = {
            'length': 24.0,           # Blade length mm
            'max_thickness': 5.0,     # Max thickness (connected to column) mm
            'min_thickness': 1.0,     # Min thickness (blade tip) mm
            'inward_angle': math.pi/3,  # Inward tilt angle (60 degrees) rad
            'offset': 18.0,           # Blade offset mm (distance from center to outer end)

            # Small holes on blades
            'hole_diameter': 4.0,      # Small hole diameter mm
            'num_holes_per_blade': 3,  # Number of small holes per blade
            'hole_spacing': 15.0,       # Hole spacing mm (along Z-axis)
            'hole_radial_offset': 10.0, # Hole radial offset mm (in XY plane, positive outward, negative inward)
        }

        # ============ Electrode Parameters ============
        self.electrode_params = {
            'electrode_depth': 0.1,          # Electrode etching depth mm (general)

            # Long electrode parameters (extending along Z-axis)
            'long_electrode_width': 1.0,  # Long electrode width mm
            'long_electrode_length': 50.0,  # Long electrode length (Z-axis direction) mm
            
            # Short electrode parameters (perpendicular to long electrodes)
            'short_electrode_width': 1.0,   # Short electrode width (Z-axis direction) mm
            'short_electrode_length': 5.0,  # Short electrode length (X-axis direction) mm

            # Individual parameters for each blade (blade 0: top-left, 1: bottom-right, 2: top-right, 3: bottom-left)
            # Left and right sides of the same blade share the same parameters
            'blade_params': {
                0: {  # Blade 0 (top-left)
                    'num_electrodes': 2,    # Number of short electrodes
                    'long_electrode_radial_offset': 13.8,  # Long electrode radial offset
                    'short_electrode_radial_offset': 10.5,  # Short electrode radial offset
                    'short_electrode_spacing': 24.0,  # Short electrode spacing (overrides global value)
                    'groove_spacing': 8.0,  # Distance between connection points at blade tip (0 means all lines connect at same point)
                    'groove_width': 1.0,    # Routing groove width mm (thinner than electrodes)
                },
                1: {  # Blade 1 (bottom-right)
                    'num_electrodes': 2,
                    'long_electrode_radial_offset': 13.8,
                    'short_electrode_radial_offset': 10.5,   
                    'short_electrode_spacing': 24.0,
                    'groove_spacing': 8.0,  # Distance between connection points at blade tip
                    'groove_width': 1.0,    # Routing groove width mm
                },
                2: {  # Blade 2 (top-right)
                    'num_electrodes': 4,
                    'long_electrode_radial_offset': 13.8,
                    'short_electrode_radial_offset': 10.5,   
                    'short_electrode_spacing': 8.0,
                    'groove_spacing': 0.0,  # Distance between connection points at blade tip
                    'groove_width': 0.1,    # Routing groove width mm
                },
                3: {  # Blade 3 (bottom-left)
                    'num_electrodes': 4,
                    'long_electrode_radial_offset': 13.8,  
                    'short_electrode_radial_offset': 10.5,  
                    'short_electrode_spacing': 8.0,
                    'groove_spacing': 0.0,  # Distance between connection points at blade tip
                    'groove_width': 0.1,    # Routing groove width mm
                },
            },
        }

        # ============ Routing Groove Parameters ============
        self.routing_params = {
            'groove_width': 1.0,      # Routing groove width mm (backup default)
            'groove_depth': 5.0,      # Routing groove etching depth mm (allows cutting through blade)
        }

        # ============ Calculate Derived Parameters ============
        self._calculate_derived_parameters()

    def _calculate_derived_parameters(self):
        """Calculate derived parameters"""
        bp = self.base_params
        op = self.overall_params
        cp = self.column_params

        # Base positions
        self.base_positions = {
            'top': {
                'x': 0.0, 'y': 0.0,
                'z': op['total_height']/2 - bp['thickness']/2
            },
            'bottom': {
                'x': 0.0, 'y': 0.0,
                'z': -op['total_height']/2 + bp['thickness']/2
            },
        }

        # Column connection points (four corners, vertically aligned)
        offset = cp['corner_offset']
        self.corner_points = [
            {'x': -offset, 'y': -offset},  # Bottom-left
            {'x': offset, 'y': -offset},   # Bottom-right
            {'x': -offset, 'y': offset},   # Top-left
            {'x': offset, 'y': offset},    # Top-right
        ]


# Create default parameter instance
default_blade_chip_v3_params = BladeChipV3Parameters()
