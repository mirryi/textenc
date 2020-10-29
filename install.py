#!/usr/bin/env python3
from __future__ import annotations

from install.cli import cli_parser
from install.tinytex import TinyTexLoader

loaders = [('tt', TinyTexLoader)]
parser = cli_parser(loaders)
args = parser.parse_args()

if args.command is None:
    parser.print_help()
else:
    args.func(args)
