- We restrict to python 3.5 and above, for pytest support

- Must add pytest, pytest-cov, coverage as dependencies to repo env

- Mount the repo to the container to run pytest, instead of copying it into the image

- We need two versions of python, one for repo and one for lsp

- Need to make this easy to turn into pipeline task.
