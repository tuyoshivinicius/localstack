import glob
import os
import sys
from typing import Optional

from localstack import config


def venv_dir() -> str:
    return os.path.join(config.dirs.var_libs, "plugins/.venv")


def site_dir() -> Optional[str]:
    venv = venv_dir()
    if not os.path.exists(venv):
        return None

    if matches := glob.glob(os.path.join(venv, "lib/python*/site-packages")):
        return matches[0]
    else:
        return None


def inject_to_path():
    if path := site_dir():
        if path not in sys.path:
            sys.path.append(path)


def is_initialized() -> bool:
    return os.path.exists(venv_dir())
