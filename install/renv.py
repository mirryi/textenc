import subprocess
from typing import List

from .base import Argument
from .base import Loader
from .base import Profile


class RenvLoader(Loader):

    def __init__(self, profile: Profile):
        self.profile = profile

    @staticmethod
    def install_args() -> List[Argument]:
        return []

    def install(self, args):
        print('Hydrating from renv lock')
        self.hydrate()

    @staticmethod
    def regenerate_args() -> List[Argument]:
        return []

    def regenerate(self, args):
        pass

    def hydrate(self):
        self.rscript('renv::hydrate()')

    def rscript(self, command: str):
        subprocess.call(['Rscript', '-e', command])  # nosec
