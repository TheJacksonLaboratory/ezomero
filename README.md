![Run Tests](https://github.com/TheJacksonLaboratory/ezomero/workflows/Run%20Tests/badge.svg?event=push) ![](https://raw.githubusercontent.com/TheJacksonLaboratory/ezomero/main/coverage.svg)

# ezomero
A module with convenience functions for writing Python code that interacts with OMERO.


# Installation

Just `pip install ezomero` and you should be good to go! The repo contains a `requirements.txt` file with the specific package versions we test `ezomero` with, but any Python>=3.6 and latest `omero-py` and `numpy` _should_ work -  note that this package is in active development!

# Usage

In general, you will need to create a `BlitzGateway` object using `ezomero.connect()`, then pass the `conn` object to most of these helper functions along with function-specific parameters.


# Documentation

Documentation is available at https://thejacksonlaboratory.github.io/ezomero/
