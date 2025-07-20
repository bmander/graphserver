from pathlib import Path

from setuptools import Extension, setup

# Path to core library
core_path = (Path(__file__).parent / ".." / "core").resolve()
core_include = str(core_path / "include")
core_build = str(core_path / "build")

# Define the extension module
extension = Extension(
    "_graphserver",
    sources=["src/graphserver/_graphserver.c"],
    include_dirs=[core_include],
    library_dirs=[core_build],
    libraries=["m"],
    extra_objects=[str(core_path / "build" / "libgraphserver_core.a")],
    extra_compile_args=["-std=c99", "-Wall", "-Wextra"],
    extra_link_args=[],
)

# Setup is configured in pyproject.toml, but we need setup.py for C extensions
setup(
    ext_modules=[extension],
)
