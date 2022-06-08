#!/bin/bash

function next_version() {
    source .venv/bin/activate
    python <<EOF
from localstack import __version__
from localstack.utils import version
from packaging.version import Version

next_version = version.increment_patch(Version(__version__))
print(next_version)
print(version.increment_patch_dev(next_version))
print(version.increment_minor(next_version))
EOF
}

release_version=$(next_version | head -n1)
next_dev_version=$(next_version | head -n2 | tail -n1)
minor_boundary=$(next_version | tail -n1)

echo "preparing release for $release_version"

sed -i "s/^__version__ = .*/__version__ = \"${release_version}\"/g" localstack/__init__.py
sed -i -r "s/^    localstack-ext(.*)>=.*/    localstack-ext\1>=${release_version}/g" setup.cfg

git add localstack/__init__.py setup.cfg
git commit --no-verify -m "release version ${release_version}" > /dev/null
git tag -a "v${release_version}" -m "release version ${release_version}"

echo "please double check the git log and then press enter to push the tag"
read -s

echo "git push && git push --tags"

echo "preparing next development iteration $next_dev_version"

sed -i "s/^__version__ = .*/__version__ = \"${next_dev_version}\"/g" localstack/__init__.py
sed -i -r "s/^    localstack-ext(.*)>=.*/    localstack-ext\1>=${next_dev_version},<${minor_boundary}/g" setup.cfg

git add localstack/__init__.py setup.cfg
git commit --no-verify -m "prepare next development iteration" > /dev/null
