"""Set hosted provider configuration through Vercel stdin, without printing credentials."""
import argparse
from pathlib import Path
import shutil
import subprocess

from apply_cloud_schema import read_env

ROOT = Path(__file__).resolve().parents[1]

def set_variable(name, value, secret=False):
    command = [shutil.which('vercel.cmd') or shutil.which('vercel'), 'env', 'add', name, 'production', '--force', '--yes',
               '--sensitive' if secret else '--no-sensitive']
    result = subprocess.run(command, input=value, text=True, capture_output=True, cwd=ROOT, timeout=60)
    if result.returncode:
        raise RuntimeError('Vercel rejected environment configuration for ' + name)
    print('Configured ' + name + (' as a server secret.' if secret else '.'))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--provider', choices=('gemini', 'llama'), required=True)
    parser.add_argument('--model', default='gemini-3.5-flash-lite')
    parser.add_argument('--provider-env-file', type=Path, required=True)
    parser.add_argument('--origin')
    args = parser.parse_args()
    values = read_env(args.provider_env_file)
    if args.provider == 'gemini':
        if not values.get('GEMINI_API_KEY'):
            parser.error('GEMINI_API_KEY is absent from the supplied ignored environment file')
        set_variable('GEMINI_API_KEY', values['GEMINI_API_KEY'], True)
    else:
        for name in ('INFERENCE_URL', 'INFERENCE_API_KEY'):
            if not values.get(name):
                parser.error(name + ' is absent from the supplied ignored environment file')
            set_variable(name, values[name], name.endswith('KEY'))
        if values.get('GEMINI_API_KEY'):
            set_variable('GEMINI_API_KEY', values['GEMINI_API_KEY'], True)
    set_variable('TRANSLATION_PROVIDER', args.provider)
    set_variable('GEMINI_TRANSLATION_MODEL', args.model)
    set_variable('GEMINI_VERIFICATION_MODEL', args.model)
    if args.origin:
        set_variable('APP_ORIGIN', args.origin)

if __name__ == '__main__':
    main()
