import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import contextlib
import io
import json
import subprocess
import sys

spec = importlib.util.spec_from_file_location('device', Path(__file__).resolve().parents[1] / 'scripts/device.py')
device = importlib.util.module_from_spec(spec)
spec.loader.exec_module(device)


def node(text='搜索', **attrs):
    return {'attributes': dict(text=text, bounds='[10,20][110,60]', type='Button', **attrs)}


def query(**kw):
    return SimpleNamespace(text=None, id=None, type=None, description=None, contains=False, **kw)


class SelectorTests(unittest.TestCase):
    def test_bounds_and_exact_matching(self):
        nodes = device.flatten({'children': [node(), node('搜索结果')]})
        args = query(); args.text = '搜索'
        found = device.matches(nodes, args)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]['center'], [60, 40])
        args.contains = True
        self.assertEqual(len(device.matches(nodes, args)), 2)

    def test_hidden_disabled_and_invalid_bounds(self):
        tree = {'children': [node(visible='false'), node(enabled='false'),
                             {'attributes': {'visible': 'false'}, 'children': [node()]},
                             {'attributes': {'text': '搜索', 'bounds': '[0,0][0,0]'}}]}
        args = query(); args.text = '搜索'
        self.assertEqual(device.matches(device.flatten(tree), args), [])

    def test_combined_selectors(self):
        args = query(); args.text = '搜索'; args.id = 'submit'
        found = device.matches(device.flatten({'children': [node(id='submit'), node(id='other')]}), args)
        self.assertEqual(len(found), 1)

    def test_ambiguous_click_does_not_inject(self):
        commands = []
        def run(cmd, **kw):
            commands.append(cmd)
            if 'recv' in cmd:
                Path(cmd[-1]).write_text(json.dumps({'children': [node(), node()]}))
            return subprocess.CompletedProcess(cmd, 0, 'No Error', '')
        argv = ['device.py', '--hdc', '/fake/hdc', '--device', 'TEST', 'click', '--text', '搜索']
        with patch.object(sys, 'argv', argv), patch.object(subprocess, 'run', run), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(device.main(), 1)
        self.assertFalse(any('uiInput' in ' '.join(cmd) for cmd in commands))


if __name__ == '__main__':
    unittest.main()
