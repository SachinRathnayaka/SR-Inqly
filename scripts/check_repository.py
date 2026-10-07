"""Check public documentation links and source layout without network access."""
from pathlib import Path
import re
import sys
import ast

ROOT=Path(__file__).resolve().parent.parent
failures=[]
documents=[p for p in ROOT.rglob('*.md') if not {'build','dist','.git'}.intersection(p.relative_to(ROOT).parts)]
for document in documents:
    text=document.read_text(encoding='utf-8-sig')
    for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',text):
        target=target.split(' "')[0].strip('<>')
        if target.startswith(('https://','http://','mailto:','#')):continue
        path=(document.parent/target.split('#')[0]).resolve()
        if not path.exists():failures.append(f'{document.relative_to(ROOT)}: missing {target}')
for folder in ('src','scripts','tests'):
    for source in (ROOT/folder).glob('*.py'):
        try:ast.parse(source.read_text(encoding='utf-8-sig'),filename=str(source))
        except SyntaxError as error:failures.append(str(error))
for path in ('README.md','LICENSE','THIRD_PARTY_NOTICES.md','.gitignore','run.py','packaging/windows.spec','packaging/installer.iss'):
    if not (ROOT/path).is_file():failures.append(f'Missing required file: {path}')
if failures:
    print('\n'.join(failures));raise SystemExit(1)
sys.path.insert(0,str(ROOT/'src'))
from branding import VERSION
from release_tools import source_files,validate_versions
validate_versions(ROOT,VERSION)
source_files(ROOT)
print(f'PASS: release version and public source gate; local links in {len(documents)} documents; Python syntax and required public files')
