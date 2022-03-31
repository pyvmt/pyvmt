#!/usr/bin/env python3

import setuptools
import pyvmt

with open('README.md', 'r', encoding='utf-8') as fh:
    long_description = fh.read()

setuptools.setup(name="pyvmt",
    version=pyvmt.__version__,
    author="PyVmt team",
    author_email="agirardi@fbk.eu",
    description="Library to create and check finite and infinite state transition systems",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pyvmt/pyvmt",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
    ],
    package_dir={"": "pyvmt"},
    packages=setuptools.find_packages(where="pyvmt"),
    python_requires=">=3.7",
    license='APACHE',
)
