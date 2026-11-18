"""Create A7/B7 affine edits from electrodes exported by inspect_model."""
from experiments.paths import run_data
from ion_trap_chip.verification.cad import extend_y

def main():
    folder = run_data()
    for label in ['A7','B7']:
        source = folder/(label+'.step')
        if not source.is_file():
            raise FileNotFoundError(f'Run inspect_model first; missing {source.name}')
        extend_y(source,folder/'cad'/(label+'_20um.step'),label,0.020)

if __name__ == '__main__': main()
