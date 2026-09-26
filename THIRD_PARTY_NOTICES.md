# Third-Party Notices

Scuba Clips uses the packages below. Each package stays under its own license.
This file is a notice list, not a copy of the full license text.

## Runtime dependencies

| Package | Version | License | Upstream |
| --- | --- | --- | --- |
| [solidpython2](https://github.com/SolidCode/SolidPython) | 2.1.3 | LGPL-2.1 | https://github.com/SolidCode/SolidPython |
| [click](https://github.com/pallets/click) | 8.5.0 | BSD-3-Clause | https://github.com/pallets/click |
| [numpy](https://github.com/numpy/numpy) | 2.4.6 / 2.5.3 | BSD-3-Clause | https://github.com/numpy/numpy |
| [pillow](https://github.com/python-pillow/Pillow) | 12.3.0 | MIT-CMU | https://github.com/python-pillow/Pillow |

## Development dependencies

| Package | Version | License | Upstream |
| --- | --- | --- | --- |
| [ty](https://github.com/astral-sh/ty) | 0.0.83 | MIT | https://github.com/astral-sh/ty |
| [ruff](https://github.com/astral-sh/ruff) | 0.16.8 | MIT | https://github.com/astral-sh/ruff |

## Build dependency

| Package | License | Upstream |
| --- | --- | --- |
| [hatchling](https://github.com/pypa/hatch) | MIT | https://github.com/pypa/hatch |

## Transitive dependencies

| Package | Version | License | Upstream |
| --- | --- | --- | --- |
| [ply](https://github.com/dabeaz/ply) | 3.11 | BSD-3-Clause | https://github.com/dabeaz/ply |
| [setuptools](https://github.com/pypa/setuptools) | 84.0.0 | MIT | https://github.com/pypa/setuptools |

## Copyleft notice

### solidpython2 — LGPL-2.1

Scuba Clips imports solidpython2 as an unmodified library. The project does not
change the solidpython2 source and does not link it into a combined work.

The LGPL permits you to replace the library. To do so, install your own version
of solidpython2 in the environment, then run the project. The source of the
library is available from the upstream project:
https://github.com/SolidCode/SolidPython

The full license text is at:
https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html

## Permissive notices

- **click, numpy, ply** use BSD-3-Clause. Numpy also ships the permissive
  notices for the code that it bundles. See the `LICENSES` directory in the
  numpy source tree.
- **pillow** uses the MIT-CMU license.
- **ty, ruff, hatchling, setuptools** use the MIT license.
