#!/bin/bash

# Create package files
python setup.py sdist --format=gztar

# Wheel file
python setup.py bdist_wheel --python-tag py3
