"""
Blade-type Linear Paul Ion Trap Chip Builder (V6)

Structure Description:
1. Top and bottom bases (chamfered rectangles with large center hole)
2. Four vertical connecting columns (X-shaped cross in top view, narrow side facing center)
"""

import math

try:
    from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse
    from OCC.Core.BRep import BRep_Builder
    from OCC.Core.TopoDS import TopoDS_Compound, TopoDS_Shape
    OCC_AVAILABLE = True
except ImportError as e:
    print(f"OCC import failed: {e}")
    OCC_AVAILABLE = False

from ion_trap_chip.config.chip_parameters_blade import BladeChipV3Parameters
from .geometry_blade import BladeBaseBuilder, BladeColumnBuilder, BladeTrapezoidBuilder
from .geometry_blade import BladeElectrodeGenerator
from .routing_blade import BladeRoutingGenerator


class BladeChipV6Builder:
    """Blade Chip V6 Builder - with isosceles trapezoidal blades and electrode routing"""
    
    def __init__(self, params=None):
        self.params = params if params else BladeChipV3Parameters()
        self.parts = {}
        self.compound = None
        
        if OCC_AVAILABLE:
            # Initialize geometry builders
            self.base_builder = BladeBaseBuilder(self.params)
            self.column_builder = BladeColumnBuilder(self.params)
            self.blade_builder = BladeTrapezoidBuilder(self.params)
            
            # Initialize electrode and routing groove generators
            self.electrode_generator = BladeElectrodeGenerator(self.params)
            self.routing_generator = BladeRoutingGenerator(self.params)
            
            self._init_compound()
        else:
            self.base_builder = None
            self.column_builder = None
            self.blade_builder = None
            self.electrode_generator = None
            self.routing_generator = None
    
    def _init_compound(self):
        """Initialize compound geometry"""
        self.compound = TopoDS_Compound()
        builder = BRep_Builder()
        builder.MakeCompound(self.compound)
    
    def build(self):
        """Build complete assembly (with isosceles trapezoidal blades and etched electrodes, routing grooves)"""
        if not OCC_AVAILABLE:
            print("Error: PythonOCC not available")
            return None
        
        print("Building blade chip assembly V6...")
        self.parts = {}
        
        # 1. Build top and bottom bases
        top_base = self.base_builder.build(is_top=True)
        self.parts['top_base'] = top_base
        print("  Built top base")
        
        bottom_base = self.base_builder.build(is_top=False)
        self.parts['bottom_base'] = bottom_base
        print("  Built bottom base")
        
        # 2. Build four X-shaped columns
        columns = []
        for i in range(4):
            column = self.column_builder.build(i)
            columns.append(column)
            self.parts[f'column_{i+1}'] = column
        print("  Built 4 X-shaped columns")
        
        # 3. Build four isosceles trapezoidal blades and cut holes through columns
        blades = []
        blade_cylinders = []
        for i in range(4):
            blade, cylinders = self.blade_builder.build(i)
            blades.append(blade)
            blade_cylinders.append(cylinders)
            self.parts[f'blade_{i+1}'] = blade
            
            # Cut column with blade hole cylinders
            for cylinder in cylinders:
                column = BRepAlgoAPI_Cut(columns[i], cylinder).Shape()
                columns[i] = column
            
            # Update columns in parts
            for col_idx, column in enumerate(columns):
                self.parts[f'column_{col_idx+1}'] = column
        
        print("  Built 4 trapezoidal blades (holes cut through columns)")
        
        # 4. Generate electrode geometry (etching grooves)
        print("  Generating electrodes...")
        electrode_geometry = self.electrode_generator.create_all_electrode_geometries()
        
        # Debug info: print electrode count and positions
        num_electrodes = len(self.electrode_generator.electrodes)
        print(f"    Generated {num_electrodes} electrodes")
        
        # Print first few electrode positions
        if num_electrodes > 0:
            for i, electrode in enumerate(self.electrode_generator.electrodes[:4]):
                if electrode['type'] == 'long':
                    dim = electrode['z_length']
                else:
                    dim = electrode['z_width']
                print(f"    Electrode {i}: blade={electrode['blade_index']}, "
                      f"x={electrode['x']:.2f}, y={electrode['y']:.2f}, z={electrode['z']:.2f}, "
                      f"dim={dim:.2f}")
        
        # 5. Generate routing groove geometry
        print("  Generating routing grooves...")
        electrode_endpoints = self.electrode_generator.get_electrode_endpoints()
        routing_geometry = self.routing_generator.create_all_routing_grooves(electrode_endpoints)
        
        # 6. Etch electrodes into blades (Boolean subtraction) - etch each blade individually
        print("  Etching electrodes into blades...")
        for i in range(4):
            blade_electrode_geometry = self.electrode_generator.create_electrode_geometry_for_blade(i)
            if blade_electrode_geometry:
                cut = BRepAlgoAPI_Cut(blades[i], blade_electrode_geometry)
                cut.Build()
                if cut.IsDone():
                    blades[i] = cut.Shape()
                    self.parts[f'blade_{i+1}'] = blades[i]
                    print(f"    Blade {i+1}: Cut succeeded")
                else:
                    print(f"    Blade {i+1}: Cut FAILED")
            else:
                print(f"    Blade {i+1}: No electrode geometry")
        print("  Electrodes etched successfully")
        
        # 7. Etch routing grooves into blades (Boolean subtraction) - etch each blade individually
        if routing_geometry:
            print("  Etching routing grooves into blades...")
            for i in range(4):
                blade_routing_geometry = self.routing_generator.create_all_routing_grooves_for_blade(electrode_endpoints, i)
                if blade_routing_geometry:
                    cut = BRepAlgoAPI_Cut(blades[i], blade_routing_geometry)
                    cut.Build()
                    if cut.IsDone():
                        blades[i] = cut.Shape()
                        self.parts[f'blade_{i+1}'] = blades[i]
                        print(f"    Blade {i+1}: Routing cut succeeded")
                    else:
                        print(f"    Blade {i+1}: Routing cut FAILED")
                else:
                    print(f"    Blade {i+1}: No routing geometry")
            print("  Routing grooves etched successfully")
        else:
            print("  Warning: No routing geometry generated")
        
        # 8. Assemble all parts
        self._assemble()
        
        print("Blade chip assembly V6 built successfully with etched electrodes and routing!")
        return self.compound
    
    def _assemble(self):
        """Assemble all parts"""
        if not self.compound:
            self._init_compound()
        
        builder = BRep_Builder()
        for name, part in self.parts.items():
            builder.Add(self.compound, part)
        
        print(f"  Assembled {len(self.parts)} parts")
    
    def export_step(self, filename=None):
        """Export to STEP file"""
        if not self.compound:
            self.build()
        
        if not filename:
            filename = "blade_chip_v6.step"
        
        try:
            from OCC.Core.IFSelect import IFSelect_RetDone
            from OCC.Core.STEPControl import STEPControl_Writer
            
            writer = STEPControl_Writer()
            writer.Transfer(self.compound, IFSelect_RetDone)
            status = writer.Write(filename)
            
            if status:
                print(f"Successfully exported to: {filename}")
                return filename
            else:
                print("STEP export failed")
                return None
        except Exception as e:
            print(f"Export failed: {e}")
            return None


# Test code
if __name__ == "__main__":
    builder = BladeChipV6Builder()
    assembly = builder.build()
    
    if assembly:
        output_path = "example_blade/blade_chip_assembly_V6.step"
        builder.export_step(output_path)
        print(f"Exported to: {output_path}")