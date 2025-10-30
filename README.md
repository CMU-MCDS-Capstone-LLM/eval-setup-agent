## TODO

- [ ] Generate run.sh and build.sh separately

- [ ] Don't copy the repo into image. Instead map it to the image

  Try a manual example first

- [ ] Read through testing agent codebase

- [ ] Read through coding agent codebase

## How to set up environment to run evaluation on PyMigBench?

There are two pain points

1. Unlike SWE-Bench, PyMigBench doesn't give instruction on how to set up env for each data point.

2. Testing agent and coding agent need to use the same environment, so we must make the env into a docker image or dockerfile somehow.

## Prereq knowledge

### Test only on subset of PyMigBench

We won't be testing on all data points in PyMigBench, and we assume this in the rest of this doc unless specified. In specific, we only consider repos with the following properties

- The repo must have at least one unit test, since that allows us to test if the env is set up correctly, however minimal the test is.

  This is around 2/3 of the benchmark.

But we will provide a better way to set up environment. The original pymigbench paper's env discovery method only successfully set up env for 46 migrations

### What counts as env setup?

We will automatically set up the following dependencies for each repo in PyMigBench

1. Python intepreter

  e.g. python 3.11, python 2.7

2. System packages

  e.g. postgresql

3. Python packages

  e.g. Flask

Note that these dependencies doesn't count

- platform: we assume linux x86_64, the most common one.

### What counts as successful env setup?

For each repo in PyMigBench, we assume env setup is successful if the following two conditions are met

- installation of the dependencies raise no error (or error is fixed)

- existing unit tests in the repo runs successfully on multiple runs

  we require multiple runs to avoid flakiness, where ephemeral failure happens.

## Env setup process

### Env discovery

The original pymigbench paper already proposes a heuristic algo to discover these dependencies

- Python version

- System packages

However, the way python version is discovered doesn't make use of codebase content (e.g. one that hide in docker file), and system packages is ignored entirely, meaning projects such one those depending on external local database setup won't work.

We will combine llm and heuristic algo to discover env smartly, using either a workflow or agent to discover all three types of dependencies mentioned above.

### Env installtion & testing

We will start with a minimal linux docker image, either on ec2 or on local laptop, in which our algorithm will set up environment.

We will install the discovered env, run the tests with pytest, and iterate based on error log if any.

**What count as failed to setup**: We require the env installation to be completed with a given cost / step / token consumption, and consider env setup as failed if exceeding such threshold.

### Env saving & reusing

To save env, we will export the environment into a docker image.

To reuse env, we will upload the docker image to a single ECR repo, and use tags to differentiate images for diff data points. Since full eval on pymigbench will be conducted on AWS EC2 instances, we can simply pull from ECR to reuse the env with no cost (assume same region).

> Note that this does **requires all AWS services to be in the same region**. We will use **us-east-2** for experiment.

We can customize SWE Agent to start from existing docker image.

## Notes

- We must **run all aws services within the same region**. We will use **us-east-2** for experiment.

- dependencies added by migration is not installed. For example, if we migrate from pandas to polors, we will only install pandas, and not polors. Our coding agent is expected to install such dependencies as it performs migration.
