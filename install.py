#!/usr/bin/env python3
from __future__ import annotations

import abc
import argparse
import enum
import os
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from abc import abstractmethod
from typing import Iterable
from typing import List
from typing import Optional
from typing import Tuple
from typing import Type

DEFAULT_INSTALL = 'local'
DEFAULT_BIN = os.path.join(DEFAULT_INSTALL, 'bin')


def main():
    loaders = [('tt', TinyTexLoader)]
    parser = cli(loaders)
    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
    else:
        args.func(args)


class Loader(abc.ABC):
    def __init__(self, profile: Profile):
        raise NotImplementedError('loader not implemented')

    @abstractmethod
    def install(self, kwargs):
        raise NotImplementedError('install not implemented')

    @staticmethod
    def install_args() -> List[Argument]:
        raise NotImplementedError('install_args not implemented')

    @abstractmethod
    def regenerate(self, kwargs):
        raise NotImplementedError('regenerate not implemented')

    @staticmethod
    def regenerate_args() -> List[Argument]:
        raise NotImplementedError('regerate_args not implemented')


class TinyTexLoader(Loader):
    DEFAULT_TEXPACKAGES = 'packages.txt'
    TINYTEX_VERSION = 'v2020.10'

    def __init__(self, profile: Profile):
        self.profile = profile

    @staticmethod
    def install_args() -> List[Argument]:
        return [
            argument('version', default=TinyTexLoader.TINYTEX_VERSION,
                     metavar='VERSION',
                     help='specify alternate TinyTeX version'),
            argument('no-packages', dest='no_packages', action='store_true',
                     help='do not install packages from list'),
            argument('packages-only', dest='packages_only',
                     action='store_true',
                     help=('only install packages from list; '
                           'overrides --no-packages')),
            argument('package-list', dest='package_list',
                     default=TinyTexLoader.DEFAULT_TEXPACKAGES,
                     metavar='FILE',
                     help='specify alternate TeX packages list'),
            argument('extra-packages', dest='extra_packages',
                     help='specify extra TeX packages to install'),
            argument('reinstall', action='store_true',
                     help='remove previous installation and reinstall')
        ]

    def install(self, args):
        if args.packages_only:
            self.install_packages(args.package_list,
                                  args.extra_packages)
            return

        reinstall = args.reinstall

        target = self.profile.target
        ext = self.profile.os.ext()
        tinytex_dir = self.tinytex_dir()

        print('Checking for existing installation...')
        skip_install = False
        if self.tinytex_exists():
            print('TinyTeX found, ', end='')
            if reinstall:
                print('removing...')
                shutil.rmtree(tinytex_dir)
            else:
                print('skipping installation...')
                skip_install = True

        if not skip_install:
            try:
                os.mkdir(target)
            except FileExistsError:
                pass

            print('Downloading TinyTeX release {}...'.format(args.version))
            archive_path = self.download_tinytex_release(args.version)

            print('Unpacking release archive...')
            if ext is Ext.TARGZ or ext is Ext.TGZ:
                with tarfile.open(archive_path, 'r:gz') as tar:
                    tar.extractall(target)
            else:
                with zipfile.ZipFile(archive_path) as archive:
                    archive.extractall(target)

            print('Renaming TinyTeX installation directory...')
            unpacked_dir = os.path.join(target, '.TinyTeX')
            os.rename(unpacked_dir, tinytex_dir)

            print('Removing TinyTeX archive...')
            try:
                os.remove(archive_path)
            except FileNotFoundError:
                pass

        self.regenerate_symlinks()

        print('Updating package index...')
        self.tlmgr('update', '--self')

        if not args.no_packages:
            self.install_packages(args.package_list,
                                  args.extra_packages)

    def install_packages(self, list_path: str, extra: Optional[str]):
        print("Installing packages from {}...".format(list_path))
        with open(list_path, 'r') as file:
            packages = [line.strip() for line in file]

        if extra is not None:
            packages += extra.split(',')

        self.install_tex_packages(packages)

    def install_tex_packages(self, packages: Iterable[str]):
        self.tlmgr('install', *packages)

    @staticmethod
    def regenerate_args() -> List[Argument]:
        return []

    def regenerate(self, kwargs):
        self.regenerate_symlinks()

    def regenerate_symlinks(self):
        print('Setting tlmgr sys_bin...')
        self.tlmgr_set_bin()

        print('Creating TinyTeX bin symlinks...')
        self.tlmgr_symlink_bin()

    def tlmgr_set_bin(self):
        bin_path_full = os.path.abspath(self.profile.bin_dir())
        self.tlmgr('option', 'sys_bin', bin_path_full)

    def tlmgr_symlink_bin(self):
        self.tlmgr('path', 'add')

    def tlmgr(self, *args: str):
        subprocess.call(['./tlmgr'] + list(args),  # nosec
                        cwd=self.tinytex_bin())

    def tinytex_exists(self) -> bool:
        return os.path.exists(self.tinytex_dir())

    def download_tinytex_release(self, version) -> str:
        release_name = 'TinyTeX-1-{version}.{ext}'.format(
            version=version, ext=self.profile.os.ext())
        url = ('https://github.com/yihui/tinytex-releases/releases/download/'
               '{version}/{release}').format(version=version,
                                             release=release_name)
        dest = os.path.join(self.profile.target,
                            'tinytex.{}'.format(self.profile.os.ext()))
        urllib.request.urlretrieve(url, dest)  # nosec
        return dest

    def tinytex_bin(self) -> str:
        arch = self.profile.os.arch()
        return os.path.join(self.tinytex_dir(), 'bin', arch)

    def tinytex_dir(self) -> str:
        return os.path.join(self.profile.target, 'tinytex')


LoaderConfig = Iterable[Tuple[str, Type[Loader]]]


class Installer:
    def __init__(self, profile: Profile, loaders: LoaderConfig):
        self.profile = profile
        self.loaders = [(ns, loader(self.profile)) for ns, loader in loaders]

    def install(self, kwargs):
        for ns, loader in self.loaders:
            args = self.__strip_namespace(kwargs, ns)
            loader.install(args)
        self.create_activate_files()

    def regenerate(self, kwargs):
        for ns, loader in self.loaders:
            args = self.__strip_namespace(kwargs, ns)
            loader.install(args)
        self.create_activate_files()

    def __strip_namespace(self, kwargs: dict, ns: str) -> DictAttr:
        prefix = ns + '.'
        args = {k[len(prefix):]: v for k, v in kwargs.items()
                if k.startswith(prefix)}
        return DictAttr(args)

    def create_activate_files(self):
        for s, f in [(self.profile.sh_activate_script(), 'activate'),
                     (self.profile.ps1_activate_script(), 'activate.ps1')]:
            filepath = os.path.join(self.profile.target, f)
            with open(filepath, 'w+') as file:
                file.write(s)


class Profile:
    def __init__(self, os: OS, target: str, bin_dir=None):
        self.os = os
        self.target = target
        self.bin = bin_dir

    def binary(self, name: str) -> str:
        return os.path.join(self.bin_dir(), name)

    def bin_dir(self) -> str:
        if self.bin is not None:
            return self.bin
        return os.path.join(self.target, 'bin')

    def sh_activate_script(self) -> str:
        bin = os.path.abspath(self.bin_dir())
        return SH_ACTIVATE_SCRIPT_FMT.format(bin=bin)

    def ps1_activate_script(self) -> str:
        bin = os.path.abspath(self.bin_dir())
        return PS1_ACTIVATE_SCRIPT_FMT.format(bin=bin)


class Ext(enum.Enum):
    TARGZ = 'tar.gz'
    TGZ = 'tgz'
    ZIP = 'zip'

    def __str__(self) -> str:
        return str(self.value)


class OS(enum.Enum):
    LINUX = 'linux'
    FREEBSD = 'freebsd'
    DARWIN = 'darwin'
    WIN32 = 'win32'

    def arch(self) -> str:
        if self is OS.LINUX or self is OS.FREEBSD:
            return 'x86_64-linux'
        elif self is OS.WIN32:
            return 'x86_64-darwin'
        else:
            return 'win32'

    def ext(o: OS) -> Ext:
        if o is OS.LINUX or o is OS.FREEBSD:
            return Ext.TARGZ
        elif o is OS.DARWIN:
            return Ext.TGZ
        else:
            return Ext.ZIP

    @staticmethod
    def is_linux() -> bool:
        return OS.is_platform('linux')

    @staticmethod
    def is_freebsd() -> bool:
        return OS.is_platform('freebsd')

    @staticmethod
    def is_darwin() -> bool:
        return OS.is_platform('darwin')

    @staticmethod
    def is_windows() -> bool:
        return OS.is_platform('win32')

    @staticmethod
    def is_platform(platform: str) -> bool:
        return sys.platform.startswith(platform)

    @staticmethod
    def get() -> Optional[OS]:
        if OS.is_linux():
            return OS.LINUX
        elif OS.is_freebsd():
            return OS.FREEBSD
        elif OS.is_darwin():
            return OS.DARWIN
        elif OS.is_windows():
            return OS.WIN32
        return None


def cli(loaders: LoaderConfig) -> argparse.ArgumentParser:
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
        installer = Installer(profile)
        installer.regenerate(vars(args))

    return cli


def profile_from_args(args) -> Profile:
    if args.use_os is not None:
        use_os = args.use_os
    else:
        use_os = OS.get()
    return Profile(use_os, args.target)


Argument = Tuple[str, dict]


def argument(name, **kwargs) -> Argument:
    return (name, kwargs)


class DictAttr(dict):
    def __getattr__(self, key):
        if key not in self:
            raise AttributeError(key)
        return self[key]

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        del self[key]


SH_ACTIVATE_SCRIPT_FMT = r"""#!/bin/sh
deactivate() {{
    # reset old environment variables
    if [ -n "${{_OLD_VIRTUAL_PATH:-}}" ]; then
        PATH="${{_OLD_VIRTUAL_PATH:-}}"
        export PATH
        unset _OLD_VIRTUAL_PATH
    fi

    # This should detect bash and zsh, which have a hash command that must
    # be called to get it to forget past commands.  Without forgetting
    # past commands the $PATH changes we made may not be respected
    if [ -n "${{BASH:-}}" -o -n "${{ZSH_VERSION:-}}" ] ; then
        hash -r
    fi

    if [ -n "${{_OLD_VIRTUAL_PS1:-}}" ] ; then
        PS1="${{_OLD_VIRTUAL_PS1:-}}"
        export PS1
        unset _OLD_VIRTUAL_PS1
    fi

    if [ ! "${{1:-}}" = "nondestructive" ] ; then
    # Self destruct!
        unset -f deactivate
    fi
}}

# unset irrelevant variables
deactivate nondestructive

_OLD_VIRTUAL_PATH="$PATH"
PATH="{bin}:$PATH"
export PATH

# This should detect bash and zsh, which have a hash command that must
# be called to get it to forget past commands.  Without forgetting
# past commands the $PATH changes we made may not be respected
if [ -n "${{BASH:-}}" -o -n "${{ZSH_VERSION:-}}" ] ; then
    hash -r
fi
"""

PS1_ACTIVATE_SCRIPT_FMT = r"""
$script:THIS_PATH = $myinvocation.mycommand.path
$script:BASE_DIR = Split-Path (Resolve-Path "$THIS_PATH/..") -Parent

function global:deactivate([switch] $NonDestructive) {{
    if (Test-Path variable:_OLD_VIRTUAL_PATH) {{
        $env:PATH = $variable:_OLD_VIRTUAL_PATH
        Remove-Variable "_OLD_VIRTUAL_PATH" -Scope global
    }}

    if (Test-Path function:_old_virtual_prompt) {{
        $function:prompt = $function:_old_virtual_prompt
        Remove-Item function:\_old_virtual_prompt
    }}

    if (!$NonDestructive) {{
        # Self destruct!
        Remove-Item function:deactivate
        Remove-Item function:pydoc
    }}
}}

# unset irrelevant variables
deactivate -nondestructive

New-Variable -Scope global -Name _OLD_VIRTUAL_PATH -Value $env:PATH

$env:PATH = "{bin}:" + $env:PATH
"""


if __name__ == '__main__':
    main()
