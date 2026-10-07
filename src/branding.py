"""Public identity, resources and developer information."""
from pathlib import Path
import sys
NAME = 'SR Inqly'
VERSION = '2.1.2'
DEVELOPER = 'Sachin Rathnayaka'
GITHUB = 'https://github.com/SachinRathnayaka'
COPYRIGHT = 'Copyright © 2026 Sachin Rathnayaka. All Rights Reserved.'
SOURCE_MODEL = 'Source Available'
LICENSE_SUMMARY = ('Free for personal/non-commercial app use. Commercial app use requires prior written permission. '
                   'Commercial resale, unauthorized redistribution, rebranding, and publishing modified versions '
                   'are prohibited without prior written permission from Sachin Rathnayaka.')
ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent.parent))
def resource(name):
    return ROOT / name
