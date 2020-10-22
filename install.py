#!/usr/bin/env python3
from __future__ import annotations

import argparse
import enum
import os
import shutil
import stat
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from typing import Optional

DEFAULT_INSTALL = 'local'
DEFAULT_BIN = os.path.join(DEFAULT_INSTALL, 'bin')
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


install_args = [
    argument('-t', '--target', default=DEFAULT_INSTALL,
             metavar='DIR',
             help='installation target directory'),
    argument('--tinytex-version', default=TINYTEX_VERSION,
             metavar='VERSION',
             help='specify alternate TinyTeX version'),
    argument('--reinstall', action='store_true',
             help='remove previous installation and reinstall')
]


@subcommand(args=install_args)
def install(args):
    o = OS.get()

    profile = InstallerProfile(
        args.tinytex_version, o, args.target, args.reinstall)
    installer = Installer(profile)
    installer.install()


class Installer:
    def __init__(self, profile: InstallerProfile):
        self.profile = profile

    def install(self):
        target = self.profile.target
        version = self.profile.version
        ext = self.profile.os.ext()

        print('Checking for existing installation...')
        skip_install = False
        if self.check_for_existing():
            print('TinyTeX found, ', end='')
            if self.profile.reinstall:
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

            print('Downloading TinyTeX release {}...'.format(version))
            archive_path = self.download_tinytex_release()

            print('Unpacking release archive...')
            if ext is Ext.TARGZ or ext is Ext.TGZ:
                with tarfile.open(archive_path, 'r:gz') as tar:
                    tar.extractall(target)
            else:
                with zipfile.ZipFile(archive_path) as archive:
                    archive.extractall(target)

            print('Renaming TinyTeX installation directory...')
            os.rename(self.profile.tinytex_unpacked_dir(),
                      self.profile.tinytex_dir())

            print('Removing TinyTeX archive...')
            try:
                os.remove(archive_path)
            except FileNotFoundError:
                pass

        print('Setting tlmgr sys_bin...')
        self.tlmgr_set_bin()

        print('Creating TinyTeX bin symlinks...')
        self.tlmgr_symlink_bin()

        print('Creating activation script...')
        self.create_activate_sh()

    def tlmgr_set_bin(self):
        bin_path_full = os.path.abspath(self.profile.bin_dir())
        subprocess.call(['./tlmgr', 'option', 'sys_bin',
                         bin_path_full], cwd=self.profile.tinytex_bin())

    def tlmgr_symlink_bin(self):
        subprocess.call(['./tlmgr', 'path', 'add'],
                        cwd=self.profile.tinytex_bin())

    def create_activate_sh(self):
        filepath = os.path.join(self.profile.target, 'activate')
        script_str = self.profile.sh_activate_script()
        with open(filepath, 'w+') as f:
            f.write(script_str)

    def check_for_existing(self) -> bool:
        return os.path.exists(self.profile.tinytex_dir())

    def download_tinytex_release(self) -> str:
        url = self.profile.tinytex_release_url()
        dest = os.path.join(self.profile.target,
                            'tinytex.{}'.format(self.profile.os.ext()))
        urllib.request.urlretrieve(url, dest)
        return dest


class InstallerProfile:
    def __init__(self, version: str, os: OS, target: str,
                 reinstall: bool, bin_dir=None):
        self.version = version
        self.os = os
        self.target = target
        self.reinstall = reinstall
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

    def tinytex_unpacked_dir(self) -> str:
        return os.path.join(self.target, '.TinyTeX')

    def tinytex_release_name(self) -> str:
        return 'TinyTeX-1-{version}.{ext}'.format(
            version=self.version, ext=self.os.ext())

    def tinytex_release_url(self) -> str:
        release = self.tinytex_release_name()
        return ('https://github.com/yihui/tinytex-releases/releases/download/'
                '{version}/{release}').format(version=self.version,
                                              release=release)

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
