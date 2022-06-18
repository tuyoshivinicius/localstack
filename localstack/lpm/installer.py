import dataclasses
import functools
import os.path
from abc import ABC
from pathlib import Path
from typing import List, Tuple, Callable, Dict, Optional

from plugin import Plugin, PluginManager

from localstack import config

Installer = Tuple[str, Callable]


class InstallerRepository(Plugin):
    namespace = "localstack.installer"

    def get_installer(self) -> List[Installer]:
        raise NotImplementedError


class InstallerManager:
    def __init__(self):
        self.repositories: PluginManager[InstallerRepository] = PluginManager(
            InstallerRepository.namespace
        )

    @functools.lru_cache()
    def get_installers(self) -> Dict[str, Callable]:
        installer: List[Installer] = []

        for repo in self.repositories.load_all():
            installer.extend(repo.get_installer())

        return dict(installer)

    def install(self, package: str, *args, **kwargs):
        installer = self.get_installers().get(package)

        if not installer:
            raise ValueError("no installer for package %s" % package)

        return installer(*args, **kwargs)


@dataclasses.dataclass
class Package:
    package_dir: str
    version: str


class AbstractPackageInstaller(ABC):
    package_dir: str
    default_version: str

    def __init__(self, package_dir: str, default_version: str) -> None:
        super().__init__()
        self.package_dir = package_dir
        self.default_version = default_version

    def package(self, root: Optional[str | os.PathLike], version: str) -> Package:
        raise NotImplementedError

    def __call__(self, install_root: Optional[str | os.PathLike] = None, version: str = None) -> Package:
        if version is None:
            version = self.default_version

        static_libs = Path(config.dirs.static_libs)
        if self.is_installed(static_libs, version):
            return self.package(static_libs, version)

        var_libs = Path(config.dirs.var_libs)
        if self.is_installed(var_libs, version):
            return self.package(static_libs, version)

        if install_root is None:
            install_root = var_libs

        package_dir = self.resolve_package_dir(install_root, version)
        package_dir.mkdir(parents=True, exist_ok=True)
        return self.install(package_dir, version)

    def is_installed(self, root: Path, version: str) -> bool:
        return os.path.exists(self.resolve_package_dir(root, version))

    def install(self, package_dir: Path, version: str) -> Package:
        raise NotImplementedError

    def resolve_package_dir(self, root: str | os.PathLike, version: str) -> Path:
        package_dir = self.package_dir.replace(f"{version}", version)
        return Path(os.path.join(root, package_dir))
