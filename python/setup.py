from setuptools import setup, Extension
import os

# Path to core library
core_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "core"))
core_include = os.path.join(core_path, "include")
core_build = os.path.join(core_path, "build")

# Define the extension module
extension = Extension(
    '_graphserver',
    sources=['src/graphserver/_graphserver.c'],
    include_dirs=[core_include],
    library_dirs=[core_build],
    libraries=['m'],
    extra_objects=[os.path.join(core_build, 'libgraphserver_core.a')],
    extra_compile_args=['-std=c99', '-Wall', '-Wextra'],
    extra_link_args=[],
)

# Setup is configured in pyproject.toml, but we need setup.py for C extensions
setup(
    ext_modules=[extension],
)