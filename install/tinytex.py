import os
import shutil
import subprocess
import tarfile
import urllib.request
import zipfile
from typing import Iterable
from typing import List
from typing import Optional

from .base import Argument
from .base import argument
from .base import Ext
from .base import Loader
from .base import Profile


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
                     metavar='PACKAGES',
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
