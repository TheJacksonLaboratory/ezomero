import setuptools
import os

setuptools.setup(
    version=os.environ.get('VERSION', '0.0.0'),
)
