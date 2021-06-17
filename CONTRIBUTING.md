How to contribute to ezomero
=================================

Developing Open Source is great fun!  Join us on the ![image.sc forums] (https://forum.image.sc) and tell us
which of the following challenges you'd like to solve.

* Mentoring is available for those new to scientific programming in Python.
* If you're looking for something to implement or to fix, you can browse the
  ![open issues on GitHub](https://github.com/TheJacksonLaboratory/ezomero/issues?q=is%3Aopen).
* The technical detail of the development process is summed up below.
  
Development process
-------------------

Here's the long and short of it:

1. If you are a first-time contributor:

   * Go to `https://github.com/TheJacksonLaboratory/ezomero
     <https://github.com/TheJacksonLaboratory/ezomero>`_ and click the
     "fork" button to create your own copy of the project.

   * Clone the project to your local computer::

      git clone https://github.com/your-username/ezomero.git

   * Change the directory::

      cd ezomero

   * Add the upstream repository::

      git remote add upstream https://github.com/TheJacksonLaboratory/ezomero.git

   * Now, you have remote repositories named:

     - ``upstream``, which refers to the ``ezomero`` repository
     - ``origin``, which refers to your personal fork


2. Develop your contribution:

   * Pull the latest changes from upstream::

      git checkout main
      git pull upstream main

   * Create a branch for the feature you want to work on. Since the
     branch name will appear in the merge message, use a sensible name
     such as 'add-retrieve-tags'::

      git checkout -b add-retrieve-tags

   * Commit locally as you progress (``git add`` and ``git commit``)

3. To submit your contribution:

   * Push your changes back to your fork on GitHub::

      git push origin add-retrieve-tags

   * Enter your GitHub username and password (repeat contributors or advanced
     users can remove this step by `connecting to GitHub with SSH
     <https://help.github.com/en/github/authenticating-to-github/connecting-to-github-with-ssh>`_).

   * Go to GitHub. The new branch will show up with a green Pull Request
     button - click it.


4. Review process:

   * Reviewers (the other developers and interested community members) will
     write inline and/or general comments on your Pull Request (PR) to help
     you improve its implementation, documentation, and style.  Every single
     developer working on the project has their code reviewed, and we've come
     to see it as a friendly conversation from which we all learn and the
     overall code quality benefits.  Therefore, please don't let the review
     discourage you from contributing: its only aim is to improve the quality
     of the project, not to criticize (we are, after all, very grateful for the
     time you're donating!).

   * To update your pull request, make your changes on your local repository
     and commit. As soon as those changes are pushed up (to the same branch as
     before) the pull request will update automatically.

   * `Github Actions <https://github.com/features/actions>`__, running a 
     continuous integration service, is triggered after each Pull Request update 
     to build the code and run unit tests of your branch. The tests must pass 
     before your PR can be merged. If they fail, you can find out why by clicking 
     on the "failed" icon (red cross) and inspecting the build and test log.

   * A pull request must be approved by core team members before merging.

5. Document changes

   If your change introduces any API modifications, please let us know - we
   need to re-generate the docs!

.. note::

   To reviewers: if it is not obvious from the PR description, add a short
   explanation of what a branch did to the merge message and, if closing a
   bug, also add "Closes #123" where 123 is the issue number.


Divergence between ``upstream main`` and your feature branch
------------------------------------------------------------

If GitHub indicates that the branch of your Pull Request can no longer
be merged automatically, merge the main branch into yours::

   git fetch upstream main
   git merge upstream/main

If any conflicts occur, they need to be fixed before continuing.  See
which files are in conflict using::

   git status

Which displays a message like::

   Unmerged paths:
     (use "git add <file>..." to mark resolution)

     both modified:   file_with_conflict.txt

Inside the conflicted file, you'll find sections like these::

   ```
   <<<<<<< HEAD
   The way the text looks in your branch
   =======
   The way the text looks in the main branch
   >>>>>>> main
   ```

Choose one version of the text that should be kept, and delete the
rest::

   The way the text looks in your branch

Now, add the fixed file::

   git add file_with_conflict.txt

Once you've fixed all merge conflicts, do::

   git commit


Build environment setup
-----------------------

Your local Python environment should have the packages specified in 

Guidelines
----------

* All code should have tests (see `test coverage`_ below for more details).
* All code should be documented, to the same
  `standard <https://numpydoc.readthedocs.io/en/latest/format.html#docstring-standard>`_ as NumPy and SciPy.

Stylistic Guidelines
--------------------

* Set up your editor to remove trailing whitespace.  Follow `PEP08
  <https://www.python.org/dev/peps/pep-0008/>`__.  Check code with pyflakes / flake8.

* Use numpy data types instead of strings (``np.uint8`` instead of
  ``"uint8"``).

* Use the following import conventions::

   import numpy as np
   import matplotlib.pyplot as plt
   from scipy import ndimage as ndi

   # only in Cython code
   cimport numpy as cnp
   cnp.import_array()

* When documenting array parameters, use ``image : (M, N) ndarray``
  and then refer to ``M`` and ``N`` in the docstring, if necessary.

* Refer to array dimensions as (plane), row, column, not as x, y, z. See
  :ref:`Coordinate conventions <numpy-images-coordinate-conventions>`
  in the user guide for more information.

* Functions should support all input image dtypes.  Use utility functions such
  as ``img_as_float`` to help convert to an appropriate type.  The output
  format can be whatever is most efficient.  This allows us to string together
  several functions into a pipeline, e.g.::

   hough(canny(my_image))

* Use ``Py_ssize_t`` as data type for all indexing, shape and size variables
  in C/C++ and Cython code.

* Use relative module imports, i.e. ``from .._shared import xyz`` rather than
  ``from skimage._shared import xyz``.

* Wrap Cython code in a pure Python function, which defines the API. This
  improves compatibility with code introspection tools, which are often not
  aware of Cython code.

* For Cython functions, release the GIL whenever possible, using
  ``with nogil:``.


Testing
-------

See the testing section of the Installation guide.

Test coverage
-------------

Tests for a module should ideally cover all code in that module,
i.e., statement coverage should be at 100%.

To measure the test coverage, install
`pytest-cov <https://pytest-cov.readthedocs.io/en/latest/>`__
(using ``pip install pytest-cov``) and then run::

  $ make coverage

This will print a report with one line for each file in `skimage`,
detailing the test coverage::

  Name                                             Stmts   Exec  Cover   Missing
  ------------------------------------------------------------------------------
  skimage/color/colorconv                             77     77   100%
  skimage/filter/__init__                              1      1   100%
  ...


Testing your fork locally
-------------------------------------------

Travis-CI checks all unit tests in the project to prevent breakage.

Before sending a pull request, you may want to check that Travis-CI
successfully passes all tests. To do so,

* Go to `Travis-CI <https://travis-ci.org/>`__ and follow the Sign In link at
  the top

* Go to your `profile page <https://travis-ci.org/profile>`__ and switch on
  your scikit-image fork

It corresponds to steps one and two in
`Travis-CI documentation <https://docs.travis-ci.com/user/tutorial/#to-get-started-with-travis-ci-using-github>`__
(Step three is already done in scikit-image).

Thus, as soon as you push your code to your fork, it will trigger Travis-CI,
and you will receive an email notification when the process is done.

Every time Travis is triggered, it also calls on `Codecov
<https://codecov.io>`_ to inspect the current test overage.


Bugs
----

Please `report bugs on GitHub <https://github.com/TheJacksonLaboratory/ezomero/issues>`_.

