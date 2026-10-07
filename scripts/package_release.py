"""Build release archives and checksums; never uploads to an external service."""
from pathlib import Path
import hashlib
import sys
import zipfile
import argparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'src'))
from branding import VERSION
from release_tools import source_files,validate_versions,verify_release
validate_versions(ROOT,VERSION)

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output-dir', type=Path, default=ROOT / 'dist')
parser.add_argument('--source-only', action='store_true', help='Refresh source and checksums, preserving existing Windows binaries.')
args = parser.parse_args()
output = args.output_dir.resolve()
output.mkdir(exist_ok=True)
portable = output / f'SR-Inqly-{VERSION}-Windows-Portable.zip'
source = output / f'SR-Inqly-{VERSION}-Source.zip'
app = output / 'SR Inqly'
if not args.source_only:
    if not (app / 'SR Inqly.exe').exists():raise SystemExit('Build the application first.')
    with zipfile.ZipFile(portable, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(app.rglob('*')):
            if path.is_file():archive.write(path, Path('SR Inqly') / path.relative_to(app))
with zipfile.ZipFile(source, 'w', zipfile.ZIP_DEFLATED) as archive:
    sources=source_files(ROOT)
    archive.writestr('sr-inqly/SOURCE_MANIFEST.txt',''.join(path.relative_to(ROOT).as_posix()+'\n' for path in sources))
    for path in sources:
        relative = path.relative_to(ROOT)
        archive.write(path, Path('sr-inqly') / relative)
for path in (portable, source):
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:raise SystemExit(f'Corrupt archive: {path.name}')
installer = output / f'SR.Inqly.Setup.{VERSION}.exe'
original_installer = output / f'SR Inqly Setup {VERSION}.exe'
if original_installer.exists():
    import shutil
    shutil.copy2(original_installer, installer)
if not installer.exists():raise SystemExit('Build the installer before packaging the release.')
files = (installer, portable, source)
(output / f'SHA256SUMS-{VERSION}.txt').write_text(''.join(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+path.name+'\n' for path in files),encoding='utf-8')
verify_release(output,VERSION)
for path in files:print(path.name, f'{path.stat().st_size / 1048576:.2f} MiB')
