"""Run standalone regressions in an isolated, ignored output directory."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
HEADLESS = ('document', 'performance', 'scene_cache', 'cache_eviction', 'text_cache_move')
parser = argparse.ArgumentParser()
parser.add_argument('--all', action='store_true', help='Run native Windows UI checks too; affects focus and clipboard.')
parser.add_argument('--headless', action='store_true', help='Run model/renderer checks without a desktop.')
parser.add_argument('checks', nargs='*', help='Names without check_ prefix, e.g. text tool_toggle.')
args = parser.parse_args()
if args.all and args.checks:parser.error('Use either --all or named checks.')
checks = sorted(p.stem[6:] for p in (ROOT / 'tests').glob('check_*.py') if p.stem not in ('check_package', 'check_fetcher_stress')) if args.all else args.checks or HEADLESS
output = ROOT / 'build' / 'test-artifacts'
output.mkdir(parents=True, exist_ok=True)
env = os.environ.copy()
env['PYTHONPATH'] = str(ROOT / 'src') + os.pathsep + env.get('PYTHONPATH', '')
if args.headless or not args.all and not args.checks:env['QT_QPA_PLATFORM'] = 'offscreen'
for name in checks:
    test = ROOT / 'tests' / f'check_{name}.py'
    if not test.is_file():raise SystemExit(f'Unknown check: {name}')
    subprocess.run([sys.executable, str(test)], cwd=output, env=env, check=True)
print(f'PASS: {len(checks)} checks')
