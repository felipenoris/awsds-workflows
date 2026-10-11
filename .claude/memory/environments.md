# The environments

Read before running anything in the lab or the target, or dating a measurement. The identifiers of
both accounts stay out of this file and of every file in the repository, which is public.

## The build host

Linux with internet access, where `uv` reaches PyPI (user statement of 2026-10-11). What the package
writes there is copied to the SageMaker environment. The first session ran on the user's macOS
laptop (uv 0.12.13, aarch64), where the whole suite passed, the network tests included; the target
platform of every build is passed as `--python-platform`, so the host's platform does not leak into
an archive (the compiled modules carry `x86_64-linux-gnu`).

On 2026-10-11 a cloud container (Linux x86_64, uv 0.11.32) ran the suite with `requires-python`
`>=3.12` on CPython 3.12.13, 3.13.16 and 3.14.6 (`uv run --isolated --python X.Y pytest`): 67
passed on each, 8 of them `network`, with pytest 9.1.1 and packaging 26.3. `UV_PYTHON` chose the
interpreter of `uv sync` and `uv run` over the `.python-version` 3.13. The GitHub workflow of PR #4
read the same 67 on CPython 3.12.3 (the runner's `/usr/bin/python3.12`), 3.13.16 and 3.14.8,
with `setup-uv` setting `UV_PYTHON` from the matrix; its uv 0.13.0 warns that the
`uv-build>=0.12.10,<0.13.0` of `[build-system]` does not contain the current uv version.

## The AWS-DataScience lab

The Sandbox account of AWS-DataScience, `us-west-2`, a SageMaker Unified Studio project where every
step of the runbook was measured in October 2026 (its stage log
`docs/log/log-stage-06i-sandbox-orchestration.md`):

- **The custom image** is the house image `awsds-sandbox-dev-env`, built on SageMaker Distribution
  4.5.2 (`4.5.2-cpu`, pinned by digest), 6.97 GB; the house environment is `/opt/awsds/venv`, CPython
  3.13, and the distribution's own is `/opt/conda/bin/python`, CPython 3.12. Its container user is
  `sagemaker-user` (uid 1000), and `sudo` works inside a processing job (2026-10-11).
- **The space reaches PyPI** through an explicit proxy with an allow-list; nothing is exported in
  the shell since the house image's `default-v0.2.0`.
- **The processing task works end to end** (run `f9L7CKQzmUQWQTR`, 2026-10-11): about 15 minutes and
  0.03 USD, 7.5 of the job's 8 minutes pulling the image. `CreateProcessingJob` and every
  `DescribeProcessingJob` came through the `sagemaker.api` interface endpoint, as the project role
  with session name `AmazonMWAAServerless`; the image pull carried no `vpcEndpointId`, so the
  platform pulls outside the project's network and an isolated job needs no ECR endpoint.
- **A workflow with `Code` does not run**: the worker fails while preparing its environment, before
  any task, with an internal error; its only CloudTrail call is `CreateLogStream` through the `logs`
  endpoint. The reading, not yet measured, is the S3 gateway endpoint's allow-list refusing the
  bucket where the service keeps its copy of the code (AWS-DataScience's 6i decision 7, open).

## The target

The SageMaker environment serialize-db's `SUITE_ALVO.md` refers to (user statement of 2026-10-11).
From serialize-db's `.claude/memory/environments.md` and `CLAUDE.md`, read 2026-10-11:

- SageMaker Unified Studio, Ubuntu Linux, amd64, region `sa-east-1`; a sandbox, not production.
- **No internet and no proxy** (`Network is unreachable`). S3 names resolve public and connect
  through the gateway endpoint; interface endpoints exist for STS, the three Redshift APIs and the
  workgroup host, Glue, Athena, Secrets Manager and DataZone; KMS, IAM, SageMaker, Lake Formation and
  S3 Tables resolve public and time out (probes of 2026-09-21 and 2026-09-23, from a space).
- `uv`, `git` and `aws` on the `PATH`, no `gh`, no `~/shared`, no `~/.aws/config`; system Python
  3.12.14 in `/opt/conda` (2026-09-21); container credentials lasting about an hour; `AWS_REGION`
  and `AWS_DEFAULT_REGION` both `sa-east-1`.
- **The job image** starts as the SageMaker default image, SageMaker Distribution 4.15; the target
  cannot create custom images yet (user statement of 2026-10-11).

What these readings mean for a workflow there is an open question (`OPEN_QUESTIONS.md`, "A rede do
alvo para um workflow"): they were taken from a space, and the worker's network was never read.
