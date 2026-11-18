"""Generate a default blade or segmented STEP model."""
from pathlib import Path
import argparse
from ion_trap_chip.verification.cad import describe
from ion_trap_chip.utils.export import ChipExporter

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kind', choices=['blade', 'segmented'])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    if args.kind == 'blade':
        from ion_trap_chip.core.chip_builder_blade import BladeChipV6Builder
        shape = BladeChipV6Builder().build()
    else:
        from ion_trap_chip.core.chip_builder_piercing import IonTrapChipGenerator
        shape = IonTrapChipGenerator().create_complete_ion_trap_chip()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if not ChipExporter().export_to_step(shape, str(args.output)):
        raise RuntimeError('STEP export failed')
    print(describe(shape))

if __name__ == '__main__':
    main()
