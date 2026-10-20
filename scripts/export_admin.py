"""Export the standalone admin project without local environments or secrets."""
import argparse
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1] / 'admin-portal'
FILES = ['app.py', 'requirements.txt', 'render.yaml', 'vercel.json', '.python-version', '.vercelignore', 'README.md', '.env.example', '.gitignore']


def export(destination):
    paths = [ROOT / name for name in FILES]
    for directory in ['templates', 'static']:
        paths.extend(path for path in (ROOT / directory).rglob('*') if path.is_file())
    if any(path.is_symlink() or not path.is_file() for path in paths):
        raise ValueError('An admin project file is missing or is a symlink.')
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in paths:
            archive.write(path, 'Anredseller-Admin/' + path.relative_to(ROOT).as_posix())
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination')
    print(export(parser.parse_args().destination))
