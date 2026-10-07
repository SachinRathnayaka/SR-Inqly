# Third-party components

SR Inqly's custom source-available license applies to its original application code. It does not replace or restrict the licenses or rights applicable to third-party components.

- Python 3.13 — Python Software Foundation License and bundled notices: https://docs.python.org/3/license.html
- PySide6 / Shiboken6 / Qt — LGPLv3/GPLv3/commercial licensing as applicable to each distributed component; Qt third-party notices also apply: https://doc.qt.io/qt-6/licensing.html and https://doc.qt.io/qtforpython-6/licenses.html
- PyInstaller bootloader — GPL with the distribution exception described at https://pyinstaller.org/en/stable/license.html

The portable distribution keeps Qt libraries dynamically separate in `_internal`; do not remove license files bundled there. No additional restriction in SR Inqly's LICENSE is intended to prevent exercising applicable third-party LGPL rights, including replacing applicable libraries and debugging those replacements.

This notice is not a certification of complete distribution compliance. Before a public commercial release, review the exact bundled components, include all required notices/license texts and required source/relinking information, and confirm compatibility with the chosen distribution channel. Store assets in this project are preparation assets, not a submitted or certified Store package.

## Installer builder

Windows installer built with Inno Setup 6.7.3, Copyright Jordan Russell and Martijn Laan. The installed builder license text is included as `licenses/Inno-Setup-LICENSE.txt`. Builder information and commercial licensing options: https://jrsoftware.org/ .
