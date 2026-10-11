# Lessons learned, with their stories

Read a story when the reason behind a rule in `CLAUDE.md` matters, or before adding a lesson. Each
entry is the mistake that cost a retry or the verification that changed the plan, with its date; the
rule distilled from it lives in the "Working rules" section of `CLAUDE.md`. The rules carried from
serialize-db keep their stories in serialize-db's `.claude/memory/lessons.md`. A new lesson is
appended here at the end of the unit of work, and its rule is added to `CLAUDE.md` in the same
commit.

- **A tool moved out of the lab takes every lab-specific input as an argument** (2026-10-11). The
  first design of `package_job` read the house image's environment the way the original script did,
  from `images/dev-env/python/uv.lock` and the Dockerfile's `ARG PYTHON_VERSION` in an
  AWS-DataScience checkout. The user then said the package runs on a Linux host with internet, that
  the job's image is selectable, and that the target starts on the SageMaker default image, which
  has no lock in any repository. The input became a file of the image's environment plus
  `--python`; the subnet name pattern and the image name of `render` became arguments the same way,
  and the lab's values went to the documentation as examples.
- **A ported tool is verified against the original on the same input** (2026-10-11). The network
  tests of the first session passed in 1.3 s, fast enough to doubt that they built anything. The
  project the lab measured (`petl`, `requests`, `boto3`, `pyyaml`) was built with
  `package-uv.sh`/`package-uv-job.py` and with the package, and the outputs diffed:
  `packaging.md` holds the readings.
