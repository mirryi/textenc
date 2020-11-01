import argparse
import os

from .base import Installer
from .base import LoaderConfig
from .base import OS
from .base import Profile

DEFAULT_INSTALL = 'local'
DEFAULT_BIN = os.path.join(DEFAULT_INSTALL, 'bin')


def cli_parser(loaders: LoaderConfig) -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser('install.py')
    subparsers = cli.add_subparsers(dest='command')

    def subcommand(name=None, args=[], parent=subparsers):
        def decorator(func):
            if name is None:
                parser_name = func.__name__
            else:
                parser_name = name

            parser = parent.add_parser(
                parser_name, description=func.__doc__)
            for arg in args:
                parser.add_argument(*arg[0], **arg[1])
            parser.set_defaults(func=func)
        return decorator

    shared_args = [
        (['--os'], dict(dest='use_os', required=False,
                        choices=['linux', 'freebsd', 'darwin', 'win32'],
                        help='use alternate os installation')),
        (['-t', '--target'], dict(default=DEFAULT_INSTALL,
                                  metavar='DIR',
                                  help='installation target directory')),
    ]

    install_args = shared_args[:]
    for ns, loader in loaders:
        for name, kwargs in loader.install_args():
            flag = '--' + ns + '-' + name
            new_kwargs = kwargs.copy()
            new_kwargs['dest'] = ns + '.' + \
                (kwargs['dest'] if kwargs.get('dest') is not None else name)
            install_args.append(([flag], new_kwargs))

    @subcommand(name='install', args=install_args)
    def install_command(args):
        profile = profile_from_args(args)
        installer = Installer(profile, loaders)
        installer.install(vars(args))

    regenerate_args = shared_args[:]
    for ns, loader in loaders:
        for name, kwargs in loader.regenerate_args():
            flag = '--' + ns + '-' + name
            new_kwargs = kwargs.copy()
            new_kwargs['dest'] = ns + '.' + \
                (kwargs['dest'] if kwargs.get('dest') is not None else name)
            regenerate_args.append(([flag], new_kwargs))

    @subcommand(name='regenerate', args=regenerate_args)
    def regenerate_command(args):
        profile = profile_from_args(args)
        installer = Installer(profile, loaders)
        installer.regenerate(vars(args))

    return cli


def profile_from_args(args) -> Profile:
    if args.use_os is not None:
        use_os = args.use_os
    else:
        use_os = OS.get()
    return Profile(use_os, args.target)
