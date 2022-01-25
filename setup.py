"""
Build and install the project.
"""
from setuptools import setup, find_packages


NAME = "cmaqpy"
FULLNAME = "cmaqpy"
AUTHOR = "The CMAQPy Developers"
AUTHOR_EMAIL = "jas983@cornell.edu"
MAINTAINER = "Jeffrey Sward"
MAINTAINER_EMAIL = AUTHOR_EMAIL
LICENSE = "BSD License"
URL = "https://github.com/jeffreysward/cmaqpy"
DESCRIPTION = "CMAQ Model Automation, Postprocessing, and Visualization"
KEYWORDS = "Air Quality Modeling, Chemical Transport Model"
# with open("README.rst") as f:
#     LONG_DESCRIPTION = "".join(f.readlines())

CLASSIFIERS = [
    "Development Status :: 2 - Pre-Alpha",
    "Intended Audience :: Science/Research",
    "Topic :: Scientific/Engineering",
    "Programming Language :: Python :: 3 :: Only",
]
PLATFORMS = "Any"
PACKAGES = find_packages()
SCRIPTS = []
PACKAGE_DATA = {
    # "cmaqpy": ["cmaqpy/data/*"],
}
INSTALL_REQUIRES = [
    "numpy",
    "scipy",
    "pandas",
    "xarray",
]
PYTHON_REQUIRES = ">=3.7"

if __name__ == "__main__":
    setup(
        name=NAME,
        fullname=FULLNAME,
        description=DESCRIPTION,
        author=AUTHOR,
        author_email=AUTHOR_EMAIL,
        maintainer=MAINTAINER,
        maintainer_email=MAINTAINER_EMAIL,
        license=LICENSE,
        url=URL,
        platforms=PLATFORMS,
        scripts=SCRIPTS,
        packages=PACKAGES,
        package_data=PACKAGE_DATA,
        classifiers=CLASSIFIERS,
        keywords=KEYWORDS,
        install_requires=INSTALL_REQUIRES,
        python_requires=PYTHON_REQUIRES,
    )
