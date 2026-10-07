"""Verify the exact three files selected for upload against their checksums."""
import argparse
from pathlib import Path
import sys
from release_tools import verify_release,validate_versions
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'src'))
from branding import VERSION
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--folder',type=Path,default=ROOT/'dist')
parser.add_argument('--version',default=VERSION)
args=parser.parse_args()
validate_versions(ROOT,VERSION)
verify_release(args.folder,args.version)
print('PASS: exact release assets, versions, ZIP integrity and SHA-256 checksums')
