from __future__ import annotations

import abc
import enum
import os
import sys
from abc import abstractmethod
from typing import Iterable
from typing import List
from typing import Optional
from typing import Tuple
from typing import Type

Argument = Tuple[str, dict]


def argument(name, **kwargs) -> Argument:
    return (name, kwargs)


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
            loader.regenerate(args)
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

    if [ -n "${{_OLD_TEXINPUTS:-}}" ]; then
        TEXINPUTS="${{_OLD_TEXINPUTS:-}}"
        export TEXINPUTS
        unset _OLD_TEXINPUTS
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

_OLD_TEXINPUTS="$TEXINPUTS"
TEXINPUTS=".:./sty:"
export TEXINPUTS

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

    if (Test-Path variable:_OLD_TEXINPUTS) {{
        $env:TEXINPUTS = $variable:_OLD_TEXINPUTS
        Remove-Variable "_OLD_TEXINPUTS" -Scope global
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

New-Variable -Scope global -Name _OLD_TEXINPUTS -Value $env:TEXINPUTS

$env:TEXINPUTS = ".:./sty:"
"""
