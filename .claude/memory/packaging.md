# Packaging: the worker, the job's folder and `uv`

Read before changing `package_task`, `package_job` or `_uv`. The procedure is `docs/index.md`; this
file holds the facts the code relies on, with their dates and sources.

## The MWAA Serverless worker

From the guide's page *Using Python and Bash operators* (read 2026-10-10 and 2026-10-11, recorded in
AWS-DataScience's `docs/REFERENCES.md`):

- the code travels apart from the YAML, in the API's `Code` (an `S3Location`): one `.py`, one `.sh`
  or one `.zip`; 250 MB per file and unzipped, 75 GB of code per account;
- the `.zip` is extracted to `/usr/local/airflow/dags`, on `sys.path`; the guide says a
  `BashOperator` script runs there, while an inline command ran in a temporary folder, a script
  named as the command ran from a rendered copy in one, and a Bash task's `PYTHONPATH` starts
  with `/usr/local/airflow/dags`, before the worker's `site-packages` (2026-10-11,
  `environments.md`); a script called by its full path ran with the task's temporary folder as
  its working directory (the target, 2026-10-12); `python_callable` is `<module>.<function>`;
- dependencies are vendored at the archive's root for Linux x86_64 and Python 3.12;
- the pre-installed set (Airflow 3.0.6, Amazon provider 9.32.0, boto3 1.43.1, dag-factory 1.0.0, and
  PyYAML, lz4 and the AWS Encryption SDK family) wins over any bundled version in a Python task,
  measured on 2026-10-11: the worker's PyYAML 6.0.2 imported over the archive's 6.0.1
  (`environments.md`); in a Bash task's `python3` the archive's copy wins, measured in the target
  on 2026-10-12: `six` 1.16.0 imported from the `.zip`, though Airflow 3.0.6 needs a `six` of its
  own (`environments.md`, "The first Bash task");
- a 1 vCPU / 3 GiB worker, no internet by default, the execution role's credentials available to the
  task; 0.088 USD per task-hour, one-minute minimum;
- one worker per task, not per run: two tasks of one run ran in different subnets, and each
  task's log opens with `Preparing the execution environment.` (2026-10-11, `environments.md`).

The portal (*Serverless visual workflows*, re-read 2026-10-11): one uploaded file is stored as it
is, several are zipped into one archive; only `.py`, `.sh` and `.zip`; its dependency recipe
`pip install --target ./package` carries no platform flag. The fetches of the same page between
21:30 and 22:10 UTC that day returned about 6,000 characters with none of `Python Operator`,
`Operator Files`, `Python Callable` or `pip install --target`; the portal's fields the
documentation names come from the lab's own readings.

The definition's format (read 2026-10-11, `REFERENCES.md`): the guide's *Key concepts* page says
MWAA Serverless takes a YAML definition, validates it before running and accepts Jinja2, and
publishes no schema. AWS's converter `python-to-yaml-dag-converter-mwaa-serverless` writes
"dag-factory compatible Dags" for DagFactory 1.0, and the worker pre-installs dag-factory 1.0.0,
Astronomer's Apache-2.0 library that builds Airflow DAGs from YAML, outside the Apache Airflow
project. How the service turns the YAML into a DAG is not documented.

## The `BashOperator`

Read in the source of `apache-airflow-providers-standard` on 2026-10-11: 1.6.0, the version the
Airflow 3.0.6 constraints for Python 3.12 pin, and 1.20.0, the newest on PyPI (`REFERENCES.md`).
Which version the worker runs is not documented; it behaves as 1.6.0 does: on 2026-10-11 the
lab's `bash_command: reach_pypi.sh` ran as `['/usr/bin/bash', 'tmp6wm8sj1x.sh']`
(`environments.md`).

- A `bash_command` that does not end in `.sh` or `.bash` (`template_ext`) runs as
  `bash -c <command>`. One that does names a template file, read from the DAG's template path and
  rendered by Jinja into `bash_command`. 1.6.0 decides in `__init__`, from the name, and writes the
  rendered text to a temporary `.sh` in the working directory, run as `bash <file>`; 1.20.0
  decides in `execute`, from the rendered text, which ends in neither, and runs it as
  `bash -c <text>`. In both, the script's `$0` is not its path in the `.zip`. 1.6.0's test is
  `not bash_command.endswith(template_ext)` (`_is_inline_command`, re-read 2026-10-12), so a
  script's name followed by arguments runs inline, and the script form takes no argument.
- `cwd` defaults to `None`, and the subprocess hook then works in a new `TemporaryDirectory` with
  the prefix `airflowtmp`, the `/var/tmp/airflowtmp…` the lab read on 2026-10-11 and the target on
  2026-10-12.
- `env`, when given, replaces the task's environment unless `append_env` is true.
- Exit 0 succeeds, `skip_on_exit_code` (99 by default) skips, and any other code fails.

## The archive's file modes

Python's `zipfile.ZipFile.write` stores each file's mode in `external_attr` (a 0o755 script reads
0o100755); `ZipFile.extractall` drops it, and the file gets the default mode (0o644 under the umask
022), while Info-ZIP's `unzip` keeps it (probed 2026-10-11 on CPython 3.12.3 and 3.13.16, and
UnZip 6.00). `build_archive` copies the entry module and the `include` files with `shutil.copy2`,
which keeps the mode, so a script or a binary arrives executable when the extractor honors the
mode; how the service extracts is not documented. The worker keeps the mode: in the target's
first Bash task, on 2026-10-12, the two `include` scripts read `-rwxr-xr-x` in
`/usr/local/airflow/dags`, `six.py` and the DAG file `-rw-r--r--`, every entry owned by uid and
gid 997, and a script executed by its path ran (`environments.md`, "The first Bash task").

## The processing job's folder

- A `ProcessingInput` downloads an S3 prefix into a path under `/opt/ml/processing/`, and an
  extension module cannot be imported from a zip on `sys.path`, so the job's code is a folder.
- `PYTHONPATH` comes before the image's site-packages, as in a Bash task's `python3` on the worker
  and unlike a Python task, so a package in both shadows the image's copy: the folder holds only
  what the image lacks, at equal versions for everything shared (AWS-DataScience documents the
  numpy failure in `images/dev-env/python/pyproject.toml`).
- The house image holds `onnxruntime` 1.30.0, which publishes no wheel older than `manylinux_2_28`
  (measured 2026-10-11), so its glibc is at least 2.28 and `manylinux2014` cannot describe it;
  `JOB_PLATFORM` is `x86_64-manylinux_2_28`.
- The markers of the image's environment are evaluated by the package, not by a resolver: the house
  image holds `torch` from PyTorch's own index and packages with no wheel for every Python.

## The `uv` behaviors the code relies on

Read with uv 0.12.13 on 2026-10-11 unless dated otherwise:

- `uv export --locked` refuses a `uv.lock` that no longer matches `pyproject.toml`; `--prune <name>`
  removes the package and every dependency only it needs (a name absent from the lock is accepted);
  `--no-emit-project` leaves the project out; the output carries `--hash` continuation lines and
  indented `# via` annotations.
- `uv pip install --target <dir>` creates the folder and leaves a `.lock` file and a `bin/` there;
  an empty requirements file exits 0 and writes only `.lock`; `--only-binary :all:` with
  `--python-version` and `--python-platform` picks the target's wheels.
- `uv build --wheel` names a pure wheel `*-none-any.whl`; the package refuses any other.
- `uv pip list --format freeze` writes only `name==version` lines (formats: columns, freeze, json).
- `uv`'s error output is UTF-8 with box-drawing characters, so `_uv.run` decodes with `utf-8` and
  `errors="replace"`.

## The interpreter `uv` needs

Measured on 2026-10-11 and 2026-10-12 with uv 0.12.17, the house image's, in a simulation of a lab
space in a cloud container (Linux x86_64): `UV_PYTHON_DOWNLOADS=never`, an empty
`UV_PYTHON_INSTALL_DIR`, only a CPython 3.12.3 on `PATH`, and a venv of CPython 3.13.16 off every
search path standing for `/opt/awsds/venv` (`environments.md`, "`uv` in a lab space"):

- `uv export --locked` and `uv build` need an interpreter the project accepts, the one its
  `.python-version` names or else one its `requires-python` admits. With none found and downloads
  off they refuse with `No interpreter found for Python 3.13 in managed installations or search
  path` (`>=3.13` without a `.python-version`). `UV_PYTHON` names the interpreter and wins over
  `.python-version`.
- `_uv.run` passes no `env`, so the process's `UV_*` variables reach every uv call.
  `tests/test_uv.py::test_uv_python_reaches_the_call` holds it: it failed on 2026-10-12 against a
  `run` that dropped `UV_PYTHON` from the environment. It calls `uv venv`, which honours
  `UV_PYTHON`; `uv python find` ignores it (uv 0.11.32, 2026-10-12).
- Without `UV_PYTHON`, `package-job` on AWS-DataScience's `awsds-demo-deps` (`.python-version`
  3.13, `requires-python >=3.13`) and `package-task` on a project with `.python-version` 3.13 and
  `requires-python >=3.12` stopped at `uv export --locked`; with `UV_PYTHON` set to the 3.13 venv's
  interpreter, both wrote their output (176 files and 1,735,841 bytes; 150 entries, 1,186,338 bytes
  unzipped).
- With downloads on (2026-10-12), uv downloaded CPython 3.13.15 into the managed folder and
  `package-job` wrote the same files. Besides the project's three metadata files, petl's `RECORD`
  differed on the line of the removed `bin/petl`, whose shebang names the interpreter (815 bytes
  against 882).
- `uv tool install` ignores the `.python-version` of the folder it runs in (3.13 and 3.14 tried) and
  installed `awsds-workflows` on the only interpreter, CPython 3.12.3.

## The port verified against the original scripts

On 2026-10-11, on the project the lab measured (`petl`, `requests`, `boto3`, `pyyaml`,
`requires-python >=3.12`), with AWS-DataScience at `fef7bc2`:

- **`package-task` against `package-uv.sh`**: the same 277 files; every file's CRC equal except
  four `RECORD` files and the project's `direct_url.json` and `uv_cache.json`. A `RECORD` differs on
  the line of a removed `bin/` script (`bin/idna`), whose shebang carries the build's temporary
  path, and `direct_url.json` names the wheel by its temporary path. 938,837 bytes, 3,224,152
  unzipped; the compiled modules `charset_normalizer/cd` and `md`, both
  `cpython-312-x86_64-linux-gnu`. The `RECORD` files still list the removed `bin/` scripts, in the
  original's output too.
- **`package-job` against `package-uv-job.py`**, with the house environment as
  `uv export --frozen --no-dev --no-emit-project --no-hashes --no-header` of
  `images/dev-env/python` (1,981 lines): the same five conflicts (`boto3` and `botocore` 1.43.111
  against 1.43.92, `charset-normalizer` 3.5.2 against 3.5.1, `idna` 3.20 against 3.19, `urllib3`
  2.8.0 against 2.7.0) and the same 12-entry constraint block; after it and a re-lock, both wrote
  1,186,389 bytes, 12 packages from the image and only `petl` 1.7.29 in the folder, with equal
  `shasum` for every file but the same three metadata files.
- **`package-job` against the fixed `package-uv-job.py`** (AWS-DataScience's `fcc760b`), on
  2026-10-11 in the simulated space of "The interpreter `uv` needs", both naming the 3.13 venv
  through `UV_PYTHON`, on `awsds-demo-deps` with its constraint block (`pyarrow==24.0.0`): the same
  176 files and 1,735,841 bytes, equal but for the project's `RECORD`, `direct_url.json` (the
  wheel's temporary path) and `uv_cache.json` (the build's time). The space's own build of that
  folder ran in a job (`environments.md`).
- **The code review of 2026-10-12 against `main` (`0027433`)**: `uv export` moved to
  `_uv.export_closure`, which both packagers call (`package_task` writes its text to
  `requirements.txt`, where `--output-file` wrote it before), the `uv pip install` prefix to
  `_uv._install_arguments`, and `build_folder` split into `_check_inputs`, `_locked_closure` and
  `_write_requirements`. On a locked project depending on `requests` and `six`, with an environment
  file of the lock minus `six`, the old code built twice (the control) and the new code once: the
  `.zip` has the same 144 entries and 2,077,012 unzipped bytes, the folder the same 16 files (`six`
  vendored, five packages from the environment), and both differ only in the project's `RECORD`,
  `direct_url.json` and `uv_cache.json`, the three files that also differ between the two builds of
  the old code.
- **AWS-DataScience's adoption, 2026-10-12** (its PR #113, `decisions.md`, "AWS-DataScience adopts
  the package"), on the user's macOS laptop with uv 0.12.13: the package at `937a66a` and again at
  `3499530`, the `main` after PR #9, against the scripts at AWS-DataScience's `c0baddd`, with the
  same results at both commits.
  - `package-job` on `awsds-demo-deps`, the house environment as `uv export --frozen --no-dev
    --no-emit-project --no-hashes` of `images/dev-env/python` with its header and its `# via`
    annotations (1,983 lines): the same 176 files, equal but for the project's `RECORD`,
    `direct_url.json` and `uv_cache.json` and petl's `RECORD`.
  - `job-constraints` over that file: the 452 versions `package-uv-job.py --constraints` printed.
  - `package-task` on a throwaway project (`petl`, `requests`, `boto3`, `pyyaml`,
    `requires-python >=3.12`, an entry module): the same 278 entries as `package-uv.sh`.
  - `render`, on AWS-DataScience's twelve YAML files of `examples/sandbox-orchestration/` with their
    placeholders renamed to this package's names (`ACCOUNT_ID`, `JOB_IMAGE_URI`, `DEMO_PREFIX`
    written out as `<DOMAIN_ID>/<PROJECT_ID>/shared/orchestration-demo`): byte for byte what
    `render.py` printed from the old files, with the lab's values read by `--profile` and with
    fake values from a file; `--placeholders` gave each file back, and `values` read the values
    `render.py --values` read.
