"""A setuptools based setup module.

See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path
here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

with open('requirements.txt') as f:
    requirements = f.read().splitlines()


# Arguments marked as "Required" below must be included for upload to PyPI.
# Fields marked as "Optional" may be commented out.

setup(
    name='scipion-em-em3dfold',  # Required
    version='0.1',  # Required
    description='Plugin to use EM3DFold within the Scipion framework',  # Required
    long_description=long_description,  # Optional
    url='https://github.com/scipion-em/scipion-em-em3dfold',  # Optional
    author='Blanca Pueche',  # Optional
    author_email='scipion@cnb.csic.es',  # Optional
    keywords='scipion cryoem imageprocessing scipion-3.0',  # Optional
    packages=find_packages(),
    include_package_data=True,
    package_data={  # Optional
        'em3dfold': [''],
    },
    classifiers=[  # Optional
    ],
    install_requires=[requirements], # Optional
    entry_points={
            'pyworkflow.plugin': 'em3dfold = em3dfold'
        },

)
