![](https://raw.githubusercontent.com/TheJacksonLaboratory/ezomero/main/coverage.svg) [![badge-doi](https://img.shields.io/badge/doi-10.1101%2F2023.06.29.546930-purple)](https://doi.org/10.1101/2023.06.29.546930) 

# ezomero
A module with convenience functions for writing Python code that interacts with OMERO.


# Installation

ezomero's dependencies are easily pip-installable from PyPI, except for `zeroc-ice==3.6.5`. For those, we recommend pip-installing using one of the [wheels](https://github.com/glencoesoftware/zeroc-ice-py-linux-x86_64/releases) provided by Glencoe Software (use the one compatible  with your OS/Python version - link provided is for Linux wheels, for more information see [this Glencoe Software blog post](https://www.glencoesoftware.com/blog/2023/12/08/ice-binaries-for-omero.html)).

In general, we **strongly** recommend starting from a clean virtual environment, `pip install`ing `zeroc-ice` from a Glencoe wheel, and only then doing `pip install ezomero`. 

If you want to use `get_table` and `post_table` to/from Pandas dataframes, you need to install `ezomero[tables]` - that install an optional `pandas` dependency. Installing ezomero without this will default `get_table` and `post_table` to use lists of row lists as their default.

# Usage

In general, you will need to create a `BlitzGateway` object using `ezomero.connect()`, then pass the `conn` object to most of these helper functions along with function-specific parameters.


# Documentation

Documentation is available at https://thejacksonlaboratory.github.io/ezomero/

# Development

You will need Docker installed and running to run the tests.

Setup your "omero" python environment with a local ezomero and pytest:
```
> conda activate omero  # Activate your omero environment with conda or pip
(omero) > cd /your_local_clone/ezomero
(omero) > pip install -e .
(omero) > pip install pytest
```

To run the tests, startup the test OMERO server with Docker and run pytest
```
> cd /your_local_clone/ezomero
> docker-compose -f tests/docker-compose.yml up -d
> conda activate omero
(omero) > python -m pytest .\tests
```
