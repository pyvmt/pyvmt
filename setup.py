#!/usr/bin/env python3
#
#    Copyright 2022 Embedded Systems Unit, Fondazione Bruno Kessler
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.
#

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
    package_dir={},
    packages=setuptools.find_packages(include=['pyvmt', 'pyvmt.*']),
    python_requires=">=3.7",
    license='APACHE',
    install_requires=[ 'pysmt' ]
)
