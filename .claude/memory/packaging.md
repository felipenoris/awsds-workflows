# Packaging: the worker, the job's folder and `uv`

Read before changing `package_task`, `package_job` or `_uv`. The procedure is `docs/index.md`; this
file holds the facts the code relies on, with their dates and sources.

## The MWAA Serverless worker

From the guide's page *Using Python and Bash operators* (read 2026-10-10 and 2026-10-11, recorded in
AWS-DataScience's `docs/REFERENCES.md`):

- the code travels apart from the YAML, in the API's `Code` (an `S3Location`): one `.py`, one `.sh`
  or one `.zip`; 250 MB per file and unzipped, 75 GB of code per account;
- the `.zip` is extracted to `/usr/local/airflow/dags`, on `sys.path`, which is also a
  `BashOperator` script's working directory; `python_callable` is `<module>.<function>`;
- dependencies are vendored at the archive's root for Linux x86_64 and Python 3.12;
- the pre-installed set (Airflow 3.0.6, Amazon provider 9.32.0, boto3 1.43.1, dag-factory 1.0.0, and
  PyYAML, lz4 and the AWS Encryption SDK family) wins over any bundled version, which no run has
  measured;
- a 1 vCPU / 3 GiB worker, no internet by default, the execution role's credentials available to the
  task; 0.088 USD per task-hour, one-minute minimum.

The portal (*Serverless visual workflows*, re-read 2026-10-11): one uploaded file is stored as it
is, several are zipped into one archive; only `.py`, `.sh` and `.zip`; its dependency recipe
`pip install --target ./package` carries no platform flag.

The definition's format (read 2026-10-11, `REFERENCES.md`): the guide's *Key concepts* page says
MWAA Serverless takes a YAML definition, validates it before running and accepts Jinja2, and
publishes no schema. AWS's converter `python-to-yaml-dag-converter-mwaa-serverless` writes
"dag-factory compatible Dags" for DagFactory 1.0, and the worker pre-installs dag-factory 1.0.0,
Astronomer's Apache-2.0 library that builds Airflow DAGs from YAML, outside the Apache Airflow
project. How the service turns the YAML into a DAG is not documented.

## The processing job's folder

- A `ProcessingInput` downloads an S3 prefix into a path under `/opt/ml/processing/`, and an
  extension module cannot be imported from a zip on `sys.path`, so the job's code is a folder.
- `PYTHONPATH` comes before the image's site-packages, so a package in both shadows the image's
  copy: the folder holds only what the image lacks, at equal versions for everything shared
  (AWS-DataScience documents the numpy failure in `images/dev-env/python/pyproject.toml`).
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
