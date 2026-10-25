#!/usr/bin/env python3
"""Create release archives from the explicit product manifest.

Copyright (c) 2026 Tomasz Fiedoruk. MIT.
No download, device access, signing, or installation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
STAMP = (2026, 10, 25, 0, 0, 0)


def archive(target, entries):
    # Stored ZIP avoids zlib-version differences. Order, attributes and time are fixed.
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_STORED) as z:
        for name, source in sorted(entries):
            info = zipfile.ZipInfo(name, STAMP)
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_STORED
            z.writestr(info, source.read_bytes())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, default=ROOT.parent/'release')
    args = p.parse_args()
    out = args.out.resolve()
    if out == ROOT or ROOT in out.parents:
        p.error('Choose an output directory outside the source repository')
    out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((ROOT/'build-manifest.json').read_text())
    products = []
    for product in manifest['archives']:
        target = out / product['name']
        archive(target, [(x['path'], ROOT/x['source']) for x in product['files']])
        products.append(target)
    for name in manifest['apks']:
        target = out/Path(name).name
        shutil.copyfile(ROOT/name, target)
        products.append(target)
    source_zip = out/('nasz-tv-'+manifest['version']+'-source.zip')
    archive(source_zip, [('nasz-tv/'+name, ROOT/name) for name in manifest['source_files']])
    products.append(source_zip)
    (out/'SHA256SUMS').write_text(''.join(
        hashlib.sha256(f.read_bytes()).hexdigest()+'  '+f.name+'\n' for f in sorted(products)))
    print('Built '+str(len(products))+' artifacts and SHA256SUMS')


if __name__ == '__main__': main()
