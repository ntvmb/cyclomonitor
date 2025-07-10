from setuptools import setup, find_packages
import pathlib

__version__ = "2025.7.10"

here = pathlib.Path(__file__).parent.resolve()

# Get the long description from the README file
long_description = (here / "README.md").read_text(encoding="utf-8")

setup(
    name="cyclomonitor",
    version=__version__,
    description="Discord bot that helps you keep tabs on tropical cyclones.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ntvmb/cyclomonitor",
    author="Nathaniel Greenwell",
    author_email="nategreenwell@live.com",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Internet",
        "Topic :: Scientific/Engineering",
        "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3 :: Only",
    ],
    keywords=[
        "weather",
        "discord",
        "discord bot",
        "discord-py",
        "typhoon",
        "hurricane",
        "tropical cyclone",
        "atcf",
        "py-cord",
        "ibtracs",
    ],
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.8",
    install_requires=["aiohttp>=3.6.0", "aiofiles>=23.2.1"],
    extras_require={
        "bot": ["py-cord>=2.6.1", "audioop-lts; python_version >= '3.13'", "tendo"],
    },
    project_urls={
        "Bug Reports": "https://github.com/ntvmb/cyclomonitor/issues",
        "Source": "https://github.com/ntvmb/cyclomonitor",
    },
)
