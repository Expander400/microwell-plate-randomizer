"""Make a clean source ZIP without Git, caches, or local settings."""

from pathlib import Path
import runpy
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = runpy.run_path(str(ROOT / 'microwell_plate_randomizer' / '__init__.py'))['__version__']
PREFIX = f'microwell-plate-randomizer-{VERSION}'
TOP_LEVEL = (
    'README.md', 'LICENSE', 'CHANGELOG.md', 'CONTRIBUTING.md', 'pyproject.toml',
    'MANIFEST.in', '.gitignore', '.gitattributes', 'plate_randomizer_gui.py',
    'start_windows.bat', 'start_mac_linux.command',
)
FOLDERS = ('microwell_plate_randomizer', 'tests', 'docs', 'examples', 'tools', '.github')
LOCAL_ONLY = {'docs/PUBLISHING.md', 'examples/original_randomizer.py'}


def main():
    files = [ROOT / name for name in TOP_LEVEL]
    for name in FOLDERS:
        files.extend(path for path in (ROOT / name).rglob('*')
                     if path.is_file() and '__pycache__' not in path.parts
                     and path.relative_to(ROOT).as_posix() not in LOCAL_ONLY
                     and path.suffix in {'.py', '.md', '.txt', '.yml', '.png'})
    destination = ROOT / 'dist' / f'{PREFIX}.zip'
    destination.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            archive.write(path, f'{PREFIX}/{path.relative_to(ROOT).as_posix()}')
    print(destination)


if __name__ == '__main__':
    main()
