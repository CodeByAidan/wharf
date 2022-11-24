import re
from pathlib import Path

from setuptools import setup

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

path = Path(__file__).parent / "wharf" / "__init__.py"
version = re.search(r"\d[.]\d[.]\d", path.read_text()).group(0)  # type: ignore

packages = [
    "lanyard",
]


setup(
    name="wharf",
    author="SawshaDev",
    version=version,
    packages=packages,
    license="MIT",
    description="An minimal discord api wrapper that allows you to do what you want to do",
    install_requires=requirements,
    python_requires=">=3.8.0",
)
