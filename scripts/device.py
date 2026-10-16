#!/usr/bin/env python3
"""Dependency-free HDC/UITest bridge. Never automatically retries input."""
import argparse
import json
import os
from pathlib import Path
import shutil
import shlex
import struct
import subprocess
import sys
import uuid


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--hdc')
    p.add_argument('--device')
    p.add_argument('--timeout', type=float, default=30)
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('devices')
    sub.add_parser('help')
    text = sub.add_parser('text', help='Input into focused field, or target coordinates')
    text.add_argument('value')
    text.add_argument('--at', nargs=2, type=int, metavar=('X', 'Y'))
    for name in ('observe', 'screenshot', 'layout'):
        sub.add_parser(name).add_argument('--out-dir', required=True)
    tap = sub.add_parser('tap')
    tap.add_argument('x', type=int)
    tap.add_argument('y', type=int)
    swipe = sub.add_parser('swipe')
    for name in ('x1', 'y1', 'x2', 'y2'):
        swipe.add_argument(name, type=int)
    a = p.parse_args()
    hdc = a.hdc or os.environ.get('HDC_PATH') or shutil.which('hdc')
    if not hdc:
        candidate = '/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc'
        if Path(candidate).is_file():
            hdc = candidate
    if not hdc:
        raise RuntimeError('HDC not found; use --hdc or HDC_PATH.')

    def run(args, targeted=True):
        cmd = [hdc] + (['-t', a.device] if targeted and a.device else []) + args
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=a.timeout)
        output = (r.stdout + r.stderr).strip()
        if r.returncode or any(x in output.lower() for x in ('[fail]', '[error]', 'no target', 'device not found')):
            raise RuntimeError(output or f'HDC exit {r.returncode}')
        return output

    if a.command == 'devices':
        print(json.dumps({'raw': run(['list', 'targets'], False)}, ensure_ascii=False))
        return
    if not a.device:
        raise RuntimeError('Select an explicit --device from devices output.')
    result = {'device': a.device}
    if a.command == 'help':
        result['help'] = run(['shell', 'uitest', 'help'])
        result['input_help'] = run(['shell', 'uitest', 'uiInput', 'help'])
    elif a.command == 'text':
        if not a.value or any(ord(c) < 32 or ord(c) == 127 for c in a.value):
            raise RuntimeError('Use nonempty single-line text without control characters.')
        if a.at and min(a.at) < 0:
            raise RuntimeError('Coordinates must be nonnegative original-screen pixels.')
        args = ['uitest', 'uiInput']
        args += ['inputText', *map(str, a.at), a.value] if a.at else ['text', a.value]
        # HDC forwards shell commands to the device shell. Quote there too.
        output = run(['shell', shlex.join(args)])
        if any(s in output.lower() for s in ('usage', 'missing parameter', 'not support', 'failed')):
            raise RuntimeError(output)
        result['output'] = output
        result['verification_required'] = True
    elif a.command in ('tap', 'swipe'):
        coords = [a.x, a.y] if a.command == 'tap' else [a.x1, a.y1, a.x2, a.y2]
        if min(coords) < 0:
            raise RuntimeError('Coordinates must be nonnegative original-screen pixels.')
        result['output'] = run(['shell', 'uitest', 'uiInput', 'click' if a.command == 'tap' else 'swipe'] + list(map(str, coords)))
    else:
        out = Path(a.out_dir).expanduser().resolve()
        out.mkdir(parents=True, exist_ok=True)
        token = 'harmony-' + uuid.uuid4().hex
        for kind in (('screenshot', 'layout') if a.command == 'observe' else (a.command,)):
            ext = 'png' if kind == 'screenshot' else 'json'
            remote = f'/data/local/tmp/{token}.{ext}'
            local = out / f'{token}.{ext}'
            run(['shell', 'uitest', 'screenCap' if kind == 'screenshot' else 'dumpLayout', '-p', remote])
            run(['file', 'recv', remote, str(local)])
            if not local.is_file() or not local.stat().st_size:
                raise RuntimeError(f'No artifact received: {local}')
            result[kind] = str(local)
            if kind == 'screenshot':
                with local.open('rb') as f:
                    header = f.read(24)
                if len(header) != 24 or header[:8] != b'\x89PNG\r\n\x1a\n':
                    raise RuntimeError('Screenshot is not a PNG.')
                result['width'], result['height'] = struct.unpack('>II', header[16:24])
            else:
                json.loads(local.read_text())
            try:
                run(['shell', 'rm', remote])
            except (RuntimeError, subprocess.TimeoutExpired) as exc:
                result.setdefault('warnings', []).append(f'Remote cleanup failed: {exc}')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
