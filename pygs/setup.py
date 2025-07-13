#!/usr/bin/env python3
"""
Setup script for graphserver with SWIG extensions.
"""

from setuptools import setup, Extension
import os

# Get the directory containing this script
setup_dir = os.path.dirname(os.path.abspath(__file__))
core_dir = os.path.join(setup_dir, '..', 'core')

# Define the SWIG extension for Vector
vector_swig_module = Extension(
    'graphserver._vector_swig',
    sources=[
        os.path.join(core_dir, 'vector.i'),  # SWIG interface file
    ],
    include_dirs=[core_dir],  # Include core directory for headers
    swig_opts=['-python'],
    language='c',
)

# Read version from pyproject.toml or set default
version = "1.0.0"

setup(
    ext_modules=[vector_swig_module],
)