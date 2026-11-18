"""Main entry point for ion trap chip generator"""

import sys
import os
import math

class IonTrapChipGenerator:
    """Main class for ion trap chip generator"""
    
    def __init__(self, chip_type="standard"):
        """
        Initialize ion trap chip generator
        
        Args:
            chip_type: Chip type, supports "standard" or "blade"
        """
        self.chip_type = chip_type
        self._generated_chip = None
        self._builder = None
        
        if chip_type == "blade":
            self._init_blade_chip()
        else:
            self._init_standard_chip()
    
    def _init_standard_chip(self):
        """Initialize standard ion trap chip"""
        try:
            from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox
            OCC_AVAILABLE = True
        except ImportError:
            OCC_AVAILABLE = False
        
        if OCC_AVAILABLE:
            from ion_trap_chip.config.chip_parameters_piercing import ChipParameters, ElectrodeParameters, RoutingParameters
            from ion_trap_chip.core.coordinate_system import CoordinateSystem
            from ion_trap_chip.core.chip_builder_piercing import IonTrapChipGenerator as StandardChipGenerator
            
            self.chip_builder = StandardChipGenerator()
            
            # Get parameters from the builder
            self.chip_params = self.chip_builder.chip_params
            self.electrode_params = self.chip_builder.electrode_params
            self.routing_params = self.chip_builder.routing_params
        else:
            self.chip_params = None
            self.electrode_params = None
            self.routing_params = None
            self.chip_builder = None
            print("OCC import failed: No module named 'OCC'")
    
    def _init_blade_chip(self):
        """Initialize blade chip"""
        from ion_trap_chip.core.chip_builder_blade import BladeChipV6Builder
        
        self.blade_builder = BladeChipV6Builder()
    
    def generate_chip(self):
        """Generate complete ion trap chip"""
        print(f"Generating {self.chip_type} type ion trap chip...")
        
        if self.chip_type == "blade":
            if self.blade_builder:
                self._generated_chip = self.blade_builder.build()
            else:
                print("Error: PythonOCC not available")
                self._generated_chip = None
        else:
            if self.chip_builder:
                self._generated_chip = self.chip_builder.create_complete_ion_trap_chip()
            else:
                print("Error: PythonOCC not available")
                self._generated_chip = None
        
        if self._generated_chip:
            print("Chip generation completed!")
        else:
            print("Chip generation failed!")
        
        return self._generated_chip
    
    def visualize(self):
        """Visualize generated chip"""
        if not self._generated_chip:
            print("Generating chip for visualization...")
            self.generate_chip()
        
        if self._generated_chip:
            from ion_trap_chip.utils.visualization import ChipVisualizer
            visualizer = ChipVisualizer()
            visualizer.visualize_chip(self._generated_chip)
        else:
            print("Cannot visualize: chip generation failed")
    
    def export(self, filename=None, format="step"):
        """Export chip to file"""
        if not self._generated_chip:
            print("Generating chip for export...")
            self.generate_chip()
        
        if self._generated_chip:
            if format.lower() == "step":
                if self.chip_type == "blade":
                    if filename is None:
                        filename = "blade_chip.step"
                    return self.blade_builder.export_step(filename)
                else:
                    if filename is None:
                        filename = "ion_trap_chip.step"
                    from ion_trap_chip.utils.export import ChipExporter
                    exporter = ChipExporter()
                    return exporter.export_to_step(self._generated_chip, filename)
            else:
                print(f"Unsupported format: {format}")
                return False
        else:
            print("Cannot export: chip generation failed")
            return False
    
    def _collect_visualization_points(self):
        """Collect all marker points for visualization (standard chip)"""
        points_data = {
            'electrode_corners': self.chip_builder.electrode_builder.electrode_corner_points,
            'extended_points': self.chip_builder.electrode_builder.electrode_extended_points,
            'first_turning_points': self.chip_builder.path_calculator.first_turning_points,
            'second_turning_points': self.chip_builder.path_calculator.second_turning_points,
        }
        return points_data
    
    def print_chip_info(self):
        """Print chip information"""
        if self.chip_type == "blade":
            from ion_trap_chip.config.chip_parameters_blade import BladeChipV3Parameters
            print("\n=== Blade Ion Trap Chip Parameters ===")
            params = self.blade_builder.params if self.blade_builder else BladeChipV3Parameters()
            print(f"Chip type: Blade-type linear Paul ion trap")
            print(f"Overall dimensions: {params.overall_params['base_length']} × {params.overall_params['base_width']} × {params.overall_params['total_height']} mm")
            print(f"Column dimensions: {params.column_params['width']} × {params.column_params['thickness']} × {params.overall_params['total_height']} mm")
            print(f"Blade dimensions: Length {params.blade_params['length']} mm, Max thickness {params.blade_params['max_thickness']} mm, Min thickness {params.blade_params['min_thickness']} mm")
            print(f"Blade inward angle: {params.blade_params['inward_angle']:.2f} rad ({params.blade_params['inward_angle']*180/math.pi:.1f} degrees)")
            print(f"Ion channel hole: Diameter {params.base_params['center_hole_diameter']} mm")
        else:
            print("\n=== Standard Ion Trap Chip Parameters ===")
            if self.chip_params:
                cp = self.chip_params
                print(f"Substrate dimensions: {cp['base_length']} × {cp['base_width']} mm")
                print(f"Layer thickness: {cp['layer_thickness']} mm")
                print(f"Long slot dimensions: {cp['trap_long_length']} × {cp['trap_long_width_surface']} mm")
                print(f"Short slot dimensions: {cp['trap_short_length']} × {cp['trap_short_width_surface']} mm")
                
                if self.electrode_params:
                    ep = self.electrode_params
                    print(f"Electrode dimensions: {ep['electrode_width']} × {ep['gap_width']} mm")
                    print(f"Electrode depth: {ep['electrode_depth']} mm")
                    
                    total_electrodes = sum(self.chip_builder.electrode_region_counts.values())
                    print(f"Total electrodes: {total_electrodes}")
                    print("Electrode distribution by region:")
                    for region, count in self.chip_builder.electrode_region_counts.items():
                        print(f"  {region}: {count}")
                
                if cp['circular_holes']['enabled']:
                    print(f"Circular holes: Radius {cp['circular_holes']['radius']} mm")
                    print(f"Circular hole positions: {cp['circular_holes']['positions']}")
            else:
                print("Chip parameters not loaded (OCC module not available)")


def main():
    """Main function"""
    print("=" * 60)
    print("     Ion Trap Chip Generator")
    print("=" * 60)
    
    # Select chip type
    print("\nPlease select chip type:")
    print("1. Standard Ion Trap Chip")
    print("2. Blade-type Linear Paul Ion Trap Chip")
    
    while True:
        try:
            choice = int(input("Please enter your choice (1/2): "))
            if choice in [1, 2]:
                break
            else:
                print("Please enter a valid choice (1 or 2)")
        except ValueError:
            print("Please enter a number")
    
    if choice == 1:
        chip_type = "standard"
        output_file = "example_piercing/ion_trap_chip_piercing.step"
    else:
        chip_type = "blade"
        output_file = "example_blade/blade_chip_assembly.step"
    
    # Create generator
    generator = IonTrapChipGenerator(chip_type=chip_type)
    
    # Print chip information
    generator.print_chip_info()
    
    # Generate chip
    generator.generate_chip()
    
    # Export chip
    success = generator.export(filename=output_file)
    
    if success:
        print(f"\nChip successfully exported to: {output_file}")
    
    # Ask for visualization
    visualize_choice = input("\nDo you want to visualize? (y/n): ").lower()
    if visualize_choice == 'y' or visualize_choice == 'yes':
        generator.visualize()
    
    print("\nProgram ended")


if __name__ == "__main__":
    main()
