![](https://raw.githubusercontent.com/TheJacksonLaboratory/ezomero/main/coverage.svg) [![badge-doi](https://img.shields.io/badge/doi-10.1101%2F2023.06.29.546930-purple)](https://doi.org/10.1101/2023.06.29.546930) 

# ezomero
A module with convenience functions for writing Python code that interacts with OMERO.


# Installation

Just `pip install ezomero` and you should be good to go! The repo contains the specific package versions we test `ezomero` with in `setup.py`, but any Python>=3.8 and latest `omero-py` and `numpy` _should_ work -  note that this package is in active development!

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
