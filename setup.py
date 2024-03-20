import setuptools
import os

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="ezomero",
    version=os.environ.get('VERSION', '0.0.0'),
    maintainer="Dave Mellert",
    maintainer_email="Dave.Mellert@jax.org",
    description=("A suite of convenience functions for working"
                 " with OMERO. Written and maintained by the "
                 "Research IT team at The Jackson Laboratory."),
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/TheJacksonLaboratory/ezomero",
    packages=setuptools.find_packages(),
    install_requires=[
        'omero-py == 5.19.0',
        'numpy >= 1.22, < 2.0'
    ],
    extras_require={
        "tables": ["pandas"],
    },
    python_requires='>=3.8'
)
