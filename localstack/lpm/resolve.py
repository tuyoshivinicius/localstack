import os
from pathlib import Path
from typing import Optional, List

from localstack import config


def get_package_search_paths() -> List[Path]:
    return [
        Path(config.dirs.static_libs),
        Path(config.dirs.var_lib),
    ]


def var_lib_dir() -> Path:
    return Path(config.dirs.var_lib)


def search_package_dir(package_dir: str | os.PathLike) -> Optional[Path]:
    for path in get_package_search_paths():
        if path.joinpath(package_dir).exists():
            return path

    return None
