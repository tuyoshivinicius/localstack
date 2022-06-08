from packaging.version import Version


def increment_major(cur: Version) -> Version:
    return Version(f"{cur.major + 1}.0.0")


def increment_minor(cur: Version) -> Version:
    return Version(f"{cur.major}.{cur.minor + 1}.0")


def increment_patch(cur: Version) -> Version:
    return Version(f"{cur.major}.{cur.minor}.{cur.micro + 1}")


def increment_patch_dev(cur: Version) -> Version:
    return Version(f"{cur.major}.{cur.minor}.{cur.micro + 1}.dev")
