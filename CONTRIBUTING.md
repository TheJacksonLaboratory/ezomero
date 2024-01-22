How to contribute to ezomero
=================================

Developing Open Source is great fun!  Join us on the [image.sc forums](https://forum.image.sc) and tell us
which of the following challenges you'd like to solve.

* Mentoring is available for those new to scientific programming in Python.
* If you're looking for something to implement or to fix, you can browse the
  [open issues on GitHub](https://github.com/TheJacksonLaboratory/ezomero/issues?q=is%3Aopen).
* The technical detail of the development process is summed up below.


Stylistic Guidelines
--------------------

* Functions should strive to, whenever possible, have arguments and returns in common Python types, or in numpy/scipy types. No passing OMERO objects back and forth!

* If there is a function from the base [OMERO-py API](https://downloads.openmicroscopy.org/omero/5.6.3/api/python/) that does something (e.g., return an `omero.gateway.ImageWrapper` or similar from a `conn.getObject`), we do not need to duplicate it. Wrapping OMERO-py functions for simpler input/output is fine.

* Think twice before adding dependencies. Do you need to? Can you do the same thing with base types and/or numpy?

* Keep things simple. ezomero is not supposed to be a fully-featured OMERO API; it is explicitly designed to be an easy-to-use API. If your function is not easy to use, it probably does not fit here.

* Set up your editor to remove trailing whitespace.  Follow [PEP08](https://www.python.org/dev/peps/pep-0008/).  Check code with pyflakes / flake8.

* Use relative module imports, i.e. ``from ._misc import xyz`` rather than
  ``from ezomero._misc import xyz``.
  
  
Development process
-------------------

Here's the long and short of it:

1. If you are a first-time contributor:

   * Go to [https://github.com/TheJacksonLaboratory/ezomero](https://github.com/TheJacksonLaboratory/ezomero) and click the
     "fork" button to create your own copy of the project.

   * Clone the project to your local computer:

      `git clone https://github.com/your-username/ezomero.git`

   * Change the directory:

      `cd ezomero`

   * Add the upstream repository:

      `git remote add upstream https://github.com/TheJacksonLaboratory/ezomero.git`

   * Now, you have remote repositories named:

     - ``upstream``, which refers to the ``ezomero`` repository
     - ``origin``, which refers to your personal fork


2. Develop your contribution:

   * Pull the latest changes from upstream:

      `git checkout main`
      `git pull upstream main`

   * Create a branch for the feature you want to work on. Since the
     branch name will appear in the merge message, use a sensible name
     such as 'add-retrieve-tags':

      `git checkout -b add-retrieve-tags`

   * Commit locally as you progress (``git add`` and ``git commit``)

3. To submit your contribution:

   * Push your changes back to your fork on GitHub::

      git push origin add-retrieve-tags

   * Enter your GitHub username and password (or [connect to GitHub with SSH](https://help.github.com/en/github/authenticating-to-github/connecting-to-github-with-ssh) - password authenticating via git without an access token and will be discontinued by Aug 13, 2021).

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

   * [Github Actions](https://github.com/features/actions), running a 
     continuous integration service, is triggered after each Pull Request update 
     to build the code and run unit tests of your branch. The tests must pass 
     before your PR can be merged. If they fail, you can find out why by clicking 
     on the "failed" icon (red cross) and inspecting the build and test log.

   * A pull request must be approved by core team members before merging.

5. Document changes

   If your change introduces any API modifications, please let us know - we
   need to re-generate the docs!

Note:

   To reviewers: if it is not obvious from the PR description, add a short
   explanation of what a branch did to the merge message and, if closing a
   bug, also add "Closes #123" where 123 is the issue number.


Divergence between ``upstream main`` and your feature branch
------------------------------------------------------------

If GitHub indicates that the branch of your Pull Request can no longer
be merged automatically, merge the main branch into yours:

   `git fetch upstream main`
   `git merge upstream/main`

If any conflicts occur, they need to be fixed before continuing.  See
which files are in conflict using:

   `git status`

Which displays a message like:

```
   Unmerged paths:
     (use "git add <file>..." to mark resolution)

     both modified:   file_with_conflict.txt
 ```

Inside the conflicted file, you'll find sections like these:

   ```
   <<<<<<< HEAD
   The way the text looks in your branch
   =======
   The way the text looks in the main branch
   >>>>>>> main
   ```

Choose one version of the text that should be kept, and delete the
rest:

   ```
   The way the text looks in your branch
   ```

Now, add the fixed file:

   `git add file_with_conflict.txt`

Once you've fixed all merge conflicts, do:

   `git commit`


Build environment setup
-----------------------

Your local Python environment should have the packages specified in [requirements.txt](https://github.com/TheJacksonLaboratory/ezomero/blob/main/requirements.txt). That, and a local clone of the repo, is all you need to start writing code for ezomero.

Guidelines
----------

* All code should have tests (see `test coverage` below for more details).
* All code should be documented, to the same
  [standard](https://numpydoc.readthedocs.io/en/latest/format.html#docstring-standard) as NumPy and SciPy.


Testing your fork locally
-------------------------------------------

Github Actions checks all unit tests in the project to prevent breakage. It will run whenever you submit a PR.

Before sending a pull request, you may want to check that your local fork 
successfully passes all tests. To do so,

* You will need [docker-compose](https://docs.docker.com/compose/), and you will need [pytest](https://docs.pytest.org/en/6.2.x/) on your local Python environment.

* Go to your local fork folder and run `docker-compose -f tests/docker-compose.yml up -d`. This will start a local OMERO server that will be used for testing.

* Now, just run `pytest tests/`. 


Bugs
----

Please [report bugs on GitHub](https://github.com/TheJacksonLaboratory/ezomero/issues).

