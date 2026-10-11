# What the user stated and decided

Read before changing an interface or a behavior of the package, and whenever a "why" question comes
up: these are facts stated by the user, not visible in the code, with their dates, in the order they
were taken. The design choices Claude made in the first session, which wait on the user's
confirmation, are in their own section at the end.

## The package and its name

On 2026-10-11 the user decided to isolate the tools of AWS-DataScience's runbook
`docs/plan/runbooks/serverless-workflows.md` in a utility Python package: the packaging of Python
libraries in the format MWAA Serverless expects, and the render scripts of the pipelines. The user
proposed `mwaa-packaging`; Claude suggested `awsds-workflows`, and the user created the public
repository `felipenoris/awsds-workflows` (MIT) under that name the same day. The reasons for the
name:

- "MWAA" alone names the provisioned Amazon MWAA, whose packaging is another format
  (`requirements.txt`, `plugins.zip`, a DAGs folder); the service used here calls itself
  `mwaa-serverless` (CLI `aws mwaa-serverless`, log groups `/aws/mwaa-serverless/`).
- Half of the packaging targets a SageMaker processing job, not MWAA, which only orchestrates it.
- The render is not packaging, and it is the part Stage 10 of AWS-DataScience grows (one
  definition rendered per environment).
- `awsds` is AWS-DataScience's project prefix, already on its Python projects (`awsds-tools`,
  `awsds-dev-env`, `awsds-demo-job`).

Every candidate name returned 404 on PyPI's JSON API on 2026-10-11 (`mwaa-packaging`,
`mwaa-serverless`, `awsds-workflows`, ...). A free name on a public index is the dependency-confusion
shape, so the package is installed by git URL or path, never by name.

## The repository's rules

On 2026-10-11 the user asked for a `CLAUDE.md` with the same rules as serialize-db's, changing only
the package's goal; then for the `pdoc` documentation in serialize-db's mold, the CI on GitHub,
`pytest` tests, serialize-db's Python style rules, and a review of the docstrings.

## Where the package runs

- The package runs on Linux with internet access; once generated, what it produces is copied to the
  SageMaker environment, which has no internet access (user statement of 2026-10-11).
- The target SageMaker environment is the one serialize-db's `SUITE_ALVO.md` refers to (user
  statement of 2026-10-11); its readings are in `environments.md`.
- The job image is selectable: a custom image or the SageMaker default image, currently 4.15. The
  target cannot create custom images yet, so the work starts with the default image (user statement
  of 2026-10-11).

## The documentation

On 2026-10-11 the user asked for the AWS-DataScience orchestration runbook adapted in Portuguese,
first in the README and then moved to the `pdoc` index, `docs/index.md`, with the README keeping
only the installation, the requirements and how to run the tests.

On 2026-10-11 the user asked that the documentation read as a self-contained project:
`docs/index.md`, the README and the docstrings name no external project, and AWS-DataScience's
links stay only in `REFERENCES.md` and in this memory. The documentation calls the lab "o
laboratório, uma conta de testes em `us-west-2`" and its image "a imagem do laboratório". What it
no longer says:

- `docs/index.md` is adapted from AWS-DataScience's runbook
  <https://github.com/felipenoris/AWS-DataScience/blob/main/docs/plan/runbooks/serverless-workflows.md>.
- "O laboratório" is AWS-DataScience's Sandbox account (`us-west-2`), and "a imagem do
  laboratório" is its house image `awsds-sandbox-dev-env`.
- The project role's policy of "A permissão do projeto" is, in the lab, AWS-DataScience's slice
  `terraform-live/sandbox/workflows/`.
- `package_task` was ported from `package-uv.sh` and `package_job` from `package-uv-job.py`, both in
  AWS-DataScience's `examples/sandbox-orchestration/`; the measurements of 2026-10-11 in their
  docstrings were taken with those scripts (`.claude/memory/packaging.md`).

On 2026-10-11 the user asked to remove the "O estado" section from `docs/index.md`. Its facts stay
in `.claude/memory/environments.md` ("The AWS-DataScience lab") and in
`.claude/memory/OPEN_QUESTIONS.md`; the section on a Python or Bash task keeps its own warning that
no `.zip` has run on a worker.

## The supported Python versions

On 2026-10-11 at 20:55 UTC the user asked that the package be compatible with Python 3.12 and that
the tests run on 3.12, 3.13 and 3.14: `requires-python` is `>=3.12`, and `tests.yml` runs the three
versions on Ubuntu. The repository's `.python-version`, the project venv and `docs.yml` stay on
3.13, Claude's default, named in the PR. Only `requires-python` blocked 3.12: with it relaxed, the
67 tests passed on 3.12, 3.13 and 3.14 (`environments.md`), and vermin 1.8.0 read nothing newer
than Python 3.9 in `src/` and `tests/`. `requires-python` has no upper bound, so 3.15 installs
untested.

`pyproject.toml`, `.github/workflows/tests.yml`, `README.md`, `docs/index.md`.

## Design choices of the first session

Taken by Claude on 2026-10-11 and named in the first PR; each waits on the user's confirmation.

- **`package-job` reads the job image's environment from a file** (`--environment`, one
  `name==version` line per package, optional PEP 508 marker) and takes `--python` as a required
  argument. The original script read the house image's `uv.lock` and Dockerfile from an
  AWS-DataScience checkout, which describes only the lab's custom image; the file comes from
  `uv pip list --format freeze` in a space running the job's image, or from the `uv export` of the
  project that builds a custom image. A line that is not `name==version` is refused, because the
  `name @ file:///...` that `pip freeze` writes for a conda package, ignored, would vendor a package
  the image holds.
- **`render` takes values from a JSON file, from the account, or both**, the file completing and
  overriding the account: the target's space reaches neither IAM nor SageMaker, so the account
  reading cannot run there.
- **The placeholders are generic**: `ACCOUNT_ID` replaces `SANDBOX_ACCOUNT_ID`; `JOB_IMAGE_URI`
  (the image's full URI, read with `--image-name` for a custom image) replaces `REGISTRY_ACCOUNT_ID`
  plus `IMAGE_DIGEST`; `JOB_PYTHON`, the interpreter path, is new; `DEMO_PREFIX`, which only
  AWS-DataScience's exercise used, is gone. AWS-DataScience's examples keep the old names until they
  switch to the package.
- **`--subnet-name` is required with `--profile`**: the lab's pattern `awsds-sandbox-private-*` is
  the documented example, not a default.
- **`--omit PACOTE`, repeatable, replaces the `OMIT` variable** of `package-uv.sh`, and
  **`job-constraints` is a subcommand** where the script had `--constraints`.
- **The messages and the printed output are pt-BR** (the language rule), so the refusal tables of
  AWS-DataScience's runbook no longer quote the package's own messages; `uv`'s stay English.
- **The CI runs on Ubuntu only**, since the package runs on Linux; serialize-db's runs on Ubuntu and
  Windows.
- **`uv` is not a dependency**: it is called as a program, and the house image refuses a change of
  its uv version. **`packaging>=24` is a floor**, not a pin, so the package installs beside an
  environment that pins its own.
- **`docs/index.md` is the runbook**, included by the package's docstring, as serialize-db's
  `docs/index.md` is its main page; there is no separate operation page.
