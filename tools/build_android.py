#!/usr/bin/env python3
"""Build the shipped Android sources without private history or signing material.

Copyright (c) 2026 Tomasz Fiedoruk. MIT.
The result is an aligned unsigned APK. Sign it with your own external keystore.
"""
import argparse
from pathlib import Path
import subprocess
import tempfile
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('module', choices=['tv-shortcut', 'voice'])
    parser.add_argument('--android-jar', type=Path, required=True)
    parser.add_argument('--build-tools', type=Path, required=True)
    parser.add_argument('--d8-jar', type=Path, help='Optional D8 classpath; default: build-tools/lib/d8.jar')
    parser.add_argument('--java-home', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    source = ROOT / 'src/android' / args.module
    tools, java, platform = args.build_tools.resolve(), args.java_home.resolve(), args.android_jar.resolve()
    dex = (args.d8_jar or tools/'lib/d8.jar').resolve()
    manifest = ET.parse(source/'AndroidManifest.xml').getroot()
    minimum = manifest.find('uses-sdk').get('{http://schemas.android.com/apk/res/android}minSdkVersion')
    output = args.out.resolve()
    if output.exists():
        parser.error('Output exists; choose a new path')
    def run(*cmd):
        subprocess.run([str(x) for x in cmd], check=True, stdin=subprocess.DEVNULL)
    with tempfile.TemporaryDirectory(prefix='nasz-tv-android-') as tmp:
        build = Path(tmp)
        for name in ['classes','dex']: (build/name).mkdir()
        run(tools/'aapt2','compile','--dir',source/'res','-o',build/'resources.zip')
        run(tools/'aapt2','link','-o',build/'unsigned.apk','-I',platform,
            '--manifest',source/'AndroidManifest.xml',build/'resources.zip')
        run(java/'bin/javac','--release','8','-encoding','UTF-8','-classpath',platform,
            '-d',build/'classes',*sorted((source/'src').rglob('*.java')))
        run(java/'bin/java','-cp',dex,'com.android.tools.r8.D8','--release','--min-api',minimum,
            '--lib',platform,'--output',build/'dex',*sorted((build/'classes').rglob('*.class')))
        with zipfile.ZipFile(build/'unsigned.apk','a') as archive:
            entry = zipfile.ZipInfo('classes.dex',(2026,10,25,0,0,0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry,(build/'dex/classes.dex').read_bytes())
        output.parent.mkdir(parents=True,exist_ok=True)
        run(tools/'zipalign','4',build/'unsigned.apk',output)
    print(output.name + ': unsigned; use apksigner before installation')


if __name__ == '__main__': main()
