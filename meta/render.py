#!/usr/bin/env python3
"""Render a template at input to output"""


import argparse
import importlib.util
from os import listdir, makedirs
from os.path import isdir, isfile, join
from shutil import copyfile

from meta.config import Config


def main():
    """Entrypoint"""
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', required=True, help='input file')
    parser.add_argument('-o', '--output', required=True, help='output file')
    parser.add_argument('-e', '--env', default='dev', help='options set')
    args = parser.parse_args()

    Config(args.env)

    if not isdir(args.output):
        makedirs(args.output)

    pyfiles = [
        f for f in listdir(args.input)
        if isfile(join(args.input, f))
        and f.endswith('.py')
    ]

    for filename in pyfiles:
        dest = filename.split('.py')[0] + '.yml'
        with open(join(args.output, dest), 'w') as f:
            f.write(
                import_and_run(join(args.input, filename)),
            )

    ymlfiles = [
        f for f in listdir(args.input)
        if isfile(join(args.input, f))
        and f.endswith('.yml')
    ]

    for filename in ymlfiles:
        copyfile(join(args.input, filename), join(args.output, filename))


def import_and_run(path: str) -> str:
    """Import and run a template script"""
    spec = importlib.util.spec_from_file_location('script', path)
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)

    return script.render()


if __name__ == '__main__':
    main()
