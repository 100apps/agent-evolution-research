#!/usr/bin/env python3
"""Verify chunks and restore the exact addon ZIP, optionally safely extract it."""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import zipfile


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, help='Destination ZIP; existing files must be identical')
    p.add_argument('--extract-to', type=Path, help='Optional new extraction directory')
    args = p.parse_args()
    here = Path(__file__).resolve().parent
    manifest = json.loads((here / 'manifest.json').read_text(encoding='utf-8'))
    pieces = []
    for part in manifest['chunks']:
        name = part['name']
        if Path(name).name != name:
            raise SystemExit('Unsafe chunk path in manifest')
        data = (here / name).read_bytes()
        if len(data) != part['bytes'] or hashlib.sha256(data).hexdigest() != part['sha256']:
            raise SystemExit('Chunk integrity failure: ' + name)
        pieces.append(data)
    data = b''.join(pieces)
    if len(pieces) != manifest['chunk_count'] or len(data) != manifest['bytes'] or hashlib.sha256(data).hexdigest() != manifest['sha256']:
        raise SystemExit('Archive integrity failure')
    output = args.output or here / manifest['archive']
    if output.exists():
        if output.read_bytes() != data:
            raise SystemExit('Refusing to replace a different existing ZIP: ' + str(output))
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('xb') as f:
            f.write(data)
    print('Verified ZIP:', output)
    print('SHA-256:', manifest['sha256'])
    if args.extract_to:
        target = args.extract_to.resolve()
        if target.exists():
            raise SystemExit('Extraction destination must not already exist: ' + str(target))
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            seen = set()
            for info in archive.infolist():
                name = info.filename
                rel = PurePosixPath(name)
                if rel.is_absolute() or '..' in rel.parts or '\\' in name or ':' in name or name in seen or (info.external_attr >> 16) & 0o170000 == 0o120000:
                    raise SystemExit('Unsafe ZIP member: ' + name)
                seen.add(name)
            target.mkdir(parents=True)
            archive.extractall(target)
        print('Extracted to:', target)


if __name__ == '__main__':
    main()
