#!/usr/bin/env python3
from __future__ import annotations

import argparse
import enum
import os
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from typing import Iterable
from typing import Optional

DEFAULT_INSTALL = 'local'
DEFAULT_BIN = os.path.join(DEFAULT_INSTALL, 'bin')
DEFAULT_TEXPACKAGES = 'packages.txt'
TINYTEX_VERSION = 'v2020.10'

cli = argparse.ArgumentParser('build.py')
subparsers = cli.add_subparsers(dest='command')


def main():
    args = cli.parse_args()
    if args.command is None:
        cli.print_help()
    else:
        args.func(args)


def subcommand(name=None, args=[], parent=subparsers):
    '''Convenience subcommand decorator'''
    def decorator(func):
        if name is None:
            parser_name = func.__name__
        else:
            parser_name = name

        parser = parent.add_parser(parser_name, description=func.__doc__)
        for arg in args:
            parser.add_argument(*arg[0], **arg[1])
        parser.set_defaults(func=func)
    return decorator


def argument(*name_or_flags, **kwargs):
    return ([*name_or_flags], kwargs)


shared_args = [
    argument('--os', dest='use_os', required=False,
             choices=['linux', 'freebsd', 'darwin', 'win32'],
             help='use alternate os installation'),
    argument('-t', '--target', default=DEFAULT_INSTALL,
             metavar='DIR',
             help='installation target directory'),
]

install_args = shared_args + [
    argument('--tinytex-version', default=TINYTEX_VERSION,
             metavar='VERSION',
             help='specify alternate TinyTeX version'),
    argument('--no-packages', dest='no_packages', action='store_true',
             help='do not install packages from list'),
    argument('--packages-only', dest='packages_only', action='store_true',
             help='only install packages from list; overrides --no-packages'),
    argument('--package-list', dest='package_list',
             default=DEFAULT_TEXPACKAGES, metavar='FILE',
             help='specify alternate TeX packages list'),
    argument('--extra-packages', dest='extra_packages',
             help='specify extra TeX packages to install'),
    argument('--reinstall', action='store_true',
             help='remove previous installation and reinstall')
]


@subcommand(args=install_args)
def install(args):
    profile = profile_from_args(args)
    installer = Installer(profile)

    if not args.packages_only:
        installer.install_tinytex(args.tinytex_version, args.reinstall)
        if not args.no_packages:
            install_packages(installer, args.package_list,
                             args.extra_packages)
    else:
        install_packages(installer, args.package_list,
                         args.extra_packages)


def install_packages(installer: Installer, list_path: str,
                     extra: Optional[str]):
    print("Installing packages from {}...".format(list_path))
    with open(list_path, 'r') as file:
        packages = [line.strip() for line in file]

    if extra is not None:
        packages += extra.split(',')

    installer.install_tex_packages(packages)


regenerate_args = shared_args


@subcommand(args=regenerate_args)
def regenerate(args):
    profile = profile_from_args(args)
    installer = Installer(profile)
    installer.regenerate_symlinks()


def profile_from_args(args) -> InstallerProfile:
    if args.use_os is not None:
        use_os = args.use_os
    else:
        use_os = OS.get()
    return InstallerProfile(use_os, args.target)


class Installer:
    def __init__(self, profile: InstallerProfile):
        self.profile = profile

    def install_tinytex(self, tinytex_version: str, reinstall: bool):
        target = self.profile.target
        ext = self.profile.os.ext()

        print('Checking for existing installation...')
        skip_install = False
        if self.tinytex_exists():
            print('TinyTeX found, ', end='')
            if reinstall:
                print('removing...')
                shutil.rmtree(self.profile.tinytex_dir())
            else:
                print('skipping installation...')
                skip_install = True

        if not skip_install:
            try:
                os.mkdir(target)
            except FileExistsError:
                pass

            print('Downloading TinyTeX release {}...'.format(tinytex_version))
            archive_path = self.download_tinytex_release(tinytex_version)

            print('Unpacking release archive...')
            if ext is Ext.TARGZ or ext is Ext.TGZ:
                with tarfile.open(archive_path, 'r:gz') as tar:
                    tar.extractall(target)
            else:
                with zipfile.ZipFile(archive_path) as archive:
                    archive.extractall(target)

            print('Renaming TinyTeX installation directory...')
            unpacked_dir = os.path.join(self.profile.target, '.TinyTeX')
            os.rename(unpacked_dir, self.profile.tinytex_dir())

            print('Removing TinyTeX archive...')
            try:
                os.remove(archive_path)
            except FileNotFoundError:
                pass

        self.regenerate_symlinks()

        print('Updating package index...')
        self.tlmgr('update', '--self')

        print('Creating activation script...')
        self.create_activate_sh()

    def install_tex_packages(self, packages: Iterable[str]):
        self.tlmgr('install', *packages)

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
        subprocess.call(['./tlmgr'] + list(args),
                        cwd=self.profile.tinytex_bin())

    def create_activate_sh(self):
        filepath = os.path.join(self.profile.target, 'activate')
        script_str = self.profile.sh_activate_script()
        with open(filepath, 'w+') as f:
            f.write(script_str)

    def tinytex_exists(self) -> bool:
        return os.path.exists(self.profile.tinytex_dir())

    def download_tinytex_release(self, version) -> str:
        release_name = 'TinyTeX-1-{version}.{ext}'.format(
            version=version, ext=self.profile.os.ext())
        url = ('https://github.com/yihui/tinytex-releases/releases/download/'
               '{version}/{release}').format(version=version,
                                             release=release_name)
        dest = os.path.join(self.profile.target,
                            'tinytex.{}'.format(self.profile.os.ext()))
        urllib.request.urlretrieve(url, dest)
        return dest


class InstallerProfile:
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

    def tinytex_bin(self) -> str:
        arch = self.os.arch()
        return os.path.join(self.tinytex_dir(), 'bin', arch)

    def tinytex_dir(self) -> str:
        return os.path.join(self.target, 'tinytex')

    def sh_activate_script(self) -> str:
        bin = os.path.abspath(self.bin_dir())
        return SH_ACTIVATE_SCRIPT_FMT.format(bin=bin)


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


SH_ACTIVATE_SCRIPT_FMT = """#!/bin/sh
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

    unset VIRTUAL_ENV
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


if __name__ == '__main__':
    main()
