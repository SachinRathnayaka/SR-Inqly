# Third-party components

SR Inqly's custom source-available license applies to its original application code. It does not replace or restrict the licenses or rights applicable to third-party components.

- Python 3.13 — Python Software Foundation License and bundled notices: https://docs.python.org/3/license.html
- PySide6 / Shiboken6 / Qt — LGPLv3/GPLv3/commercial licensing as applicable to each distributed component; Qt third-party notices also apply: https://doc.qt.io/qt-6/licensing.html and https://doc.qt.io/qtforpython-6/licenses.html
- PyInstaller bootloader — GPL with the distribution exception described at https://pyinstaller.org/en/stable/license.html

The portable distribution keeps Qt libraries dynamically separate in `_internal`; do not remove license files bundled there. No additional restriction in SR Inqly's LICENSE is intended to prevent exercising applicable third-party LGPL rights, including replacing applicable libraries and debugging those replacements.

This notice is not a certification of complete distribution compliance. Before a public commercial release, review the exact bundled components, include all required notices/license texts and required source/relinking information, and confirm compatibility with the chosen distribution channel. Store assets in this project are preparation assets, not a submitted or certified Store package.

## Installer builder

Windows installer built with Inno Setup 6.7.3, Copyright Jordan Russell and Martijn Laan. The installed builder license text is included as `licenses/Inno-Setup-LICENSE.txt`. Builder information and commercial licensing options: https://jrsoftware.org/ .

## Exact runtime and source references for 2.1.2

The prepared Windows runtime uses Python 3.13.15, PySide6 6.11.2, Shiboken6 6.11.2 and Qt 6.11.2. It is built with PyInstaller 6.22.3. Qt is copyright The Qt Company Ltd. and contributors; PySide/Shiboken notices are retained in their upstream sources. See the included GPL/LGPL texts in `licenses/` and the upstream per-file/component notices.

- [Qt 6.11.2 full source archive](https://download.qt.io/official_releases/qt/6.11/6.11.2/single/qt-everywhere-src-6.11.2.tar.xz).
- [PySide6 6.11.2 source distribution](https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.11.2-src/).
- [Qt for Python licensing and component notices](https://doc.qt.io/qtforpython-6/licenses.html).

### Replacing dynamically linked LGPL libraries

1. Use the extracted portable package and keep a backup of the complete application directory.
2. Obtain the corresponding upstream source, preserve its notices, and build Windows x64 libraries using a compatible Qt/Python ABI and toolchain.
3. With SR Inqly closed, replace the relevant DLLs/modules under `_internal/PySide6` and `_internal/shiboken6`. Keep the module filenames and required dependent libraries consistent.
4. Run the portable executable and validate startup and the affected functionality. Restore the backup if an incompatible build fails.

The installer contains the same separately linked runtime layout. Its source ZIP contains the application code and build scripts, not the full third-party source archives linked above. Original application restrictions do not prohibit modification or reverse engineering required to debug modifications to applicable LGPL components. Review component-specific upstream notices when redistributing a changed runtime.
