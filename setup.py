from setuptools import setup, find_packages

setup(
    name="ebilab",
    author="Yusuke Ebihara",
    author_email="yusuke@ebihara.me",
    url="https://ebilab.readthedocs.io/",
    description="Python package for my research",
    install_requires=[
        "tqdm",
        "numpy",
        "pandas",
        "matplotlib",
        "watchdog",
        "click",
        "pyvisa",
        "GitPython",
    ],
    project_urls={
        "GitHub repository": "https://github.com/ebiyuu1121/ebilab",
    },
    include_package_data=True,
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
            "ebilab=ebilab._cli:cli",
        ],
    },
    packages=find_packages(
        include=["ebilab", "ebilab.*"],
    ),
    classifiers=[
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
