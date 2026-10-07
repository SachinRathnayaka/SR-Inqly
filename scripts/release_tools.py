"""Release validation shared by packaging, CI and local upload checks."""
from pathlib import Path
import hashlib
import re
import subprocess
import zipfile

ROOT_FILES={'README.md','LICENSE','THIRD_PARTY_NOTICES.md','CHANGELOG.md','CONTRIBUTING.md','SECURITY.md',
            'requirements.txt','requirements-dev.txt','run.py','.gitignore','.gitattributes'}
ROOT_DIRS={'src','scripts','tests','docs','assets','licenses','.github','packaging'}
SECRET=re.compile(rb'(?:ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|sk-[A-Za-z0-9]{30,}|AKIA[A-Z0-9]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)')

def source_files(root):
    root=Path(root).resolve()
    if (root/'SOURCE_MANIFEST.txt').is_file() and not (root/'.git').exists():
        tracked=(root/'SOURCE_MANIFEST.txt').read_text(encoding='utf-8').splitlines()
    else:
        tracked=subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0')
    result=[]
    for name in sorted(filter(None,tracked)):
        rel=Path(name);path=root/rel
        if rel.is_absolute() or '..' in rel.parts:raise ValueError('Unsafe source path')
        if rel.parts[0] not in ROOT_DIRS and name not in ROOT_FILES:continue
        if any(part.lower().startswith('.env') for part in rel.parts) or path.suffix.lower() in {'.pfx','.p12','.pem','.key','.log','.pyc'}:
            raise ValueError('Forbidden source file: '+name)
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError('Missing or linked source file: '+name)
        if SECRET.search(path.read_bytes()):raise ValueError('Possible secret in source file: '+name)
        result.append(path)
    return result

def validate_versions(root,version):
    root=Path(root)
    spec=(root/'packaging/windows_version.txt').read_text(encoding='utf-8')
    installer=(root/'packaging/installer.iss').read_text(encoding='utf-8')
    parts=','.join(version.split('.'))+',0'
    if f'#define AppVersion "{version}"' not in installer or f"'FileVersion','{version}'" not in spec or f"'ProductVersion','{version}'" not in spec or f'filevers=({parts})' not in spec or f'prodvers=({parts})' not in spec:
        raise ValueError('Installer / executable version does not match branding')

def release_names(version):
    return (f'SR.Inqly.Setup.{version}.exe',f'SR-Inqly-{version}-Windows-Portable.zip',f'SR-Inqly-{version}-Source.zip')

def verify_release(folder,version):
    folder=Path(folder);expected=set(release_names(version))
    lines=(folder/f'SHA256SUMS-{version}.txt').read_text(encoding='utf-8').splitlines()
    seen=set()
    for line in lines:
        digest,name=line.split('  ',1)
        if name not in expected or name in seen:raise ValueError('Unexpected checksum file entry')
        seen.add(name)
        with (folder/name).open('rb') as handle:actual=hashlib.file_digest(handle,'sha256').hexdigest()
        if actual!=digest:
            raise ValueError('Checksum mismatch: '+name)
        if name.endswith('.zip'):
            with zipfile.ZipFile(folder/name) as archive:
                if archive.testzip():raise ValueError('Corrupt archive: '+name)
    if seen!=expected:raise ValueError('Missing release checksum entry')
