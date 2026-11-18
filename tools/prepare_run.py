"""Prepare an isolated run using user-supplied simulation inputs."""
from pathlib import Path
import argparse
import json

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--model',type=Path,help='Existing reference MPH; omit for analytical control only.')
    parser.add_argument('--reference-profiles',type=Path,help='Directory containing three private reference profile files.')
    args = parser.parse_args()
    target = args.output.resolve()
    protected = [ROOT/p for p in ['results','ion_trap_chip','experiments','tools','docs','.git']]
    if target == ROOT or any(p.resolve() == target or p.resolve() in target.parents for p in protected):
        parser.error('Choose an output directory outside source and published results.')
    config = {}
    if args.model:
        model = args.model.resolve()
        if not model.is_file() or model.suffix.lower() != '.mph': parser.error('--model must be an existing MPH file')
        config['model'] = str(model)
    if args.reference_profiles:
        folder = args.reference_profiles.resolve()
        expected = ['comsol_profile_reference'+s+'_tight.npz' for s in ['', '_fine', '_finer']]
        if not all((folder/name).is_file() for name in expected): parser.error('Missing reference profiles; see docs/reproduction.md')
        config['reference_profiles'] = str(folder)
    target.mkdir(parents=True,exist_ok=False)
    (target/'inputs.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
    (target/'.ionforge-run').write_text('Prepared isolated run directory',encoding='utf-8')
    print(target)

if __name__ == '__main__': main()
