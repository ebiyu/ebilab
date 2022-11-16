from setuptools import setup, find_packages

setup(
    name="ebilab",
    install_requires=[
        "tqdm",
        "numpy",
        "pandas",
        "matplotlib",
        "watchdog",
        "click",
        "pyvisa",
    ],
    setup_requires=[
        "setuptools_scm"
    ],
    # extras_require={
    #     "develop": ["dev-packageA", "dev-packageB"]
    # },
    use_scm_version={
        "version_scheme": "release-branch-semver",
        "local_scheme": "node-and-date",
        "parentdir_prefix_version": "ebilab-",
        "fallback_version": "0.0+UNKNOWN",
    },
    entry_points={
        "console_scripts": [
            "ebilab=ebilab.cli:cli",
        ],
    },
    packages=find_packages(
        include=["ebilab", "ebilab.*"],
    ),
)
