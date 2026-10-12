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

On 2026-10-12, on the user's laptop with uv 0.12.13, `uv tool upgrade awsds-workflows` moved a tool
installed from a git URL with no revision to the commit `main` gained after the install: a local
bare repository stood for GitHub, with `UV_TOOL_DIR` and `UV_TOOL_BIN_DIR` in a scratch folder. The
installed commit is the `commit_id` of the tool environment's `direct_url.json`; `uv tool list
--show-version-specifiers` prints the source URL and the version, 0.1.0, but no commit.
AWS-DataScience's runbook installs the package this way, from `main` (`decisions.md`,
"AWS-DataScience adopts the package").

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
- **A workflow with `Code` runs since 2026-10-11.** The worker's environment is prepared from the
  copy of the code the service took at the save: a `GetObject` by `airflow-serverless.amazonaws.com`
  on `mwaa-serverless-code-files-<AWS-owned account>-us-west-2-prod`, keyed by account, workflow,
  version and the upload's key, through the S3 gateway endpoint. The endpoint's allow-list refused
  it, and the worker failed before any task with `Execution environment preparation failed due to an
  internal server error`, its only CloudTrail call `CreateLogStream` through the `logs` endpoint;
  only a trail of S3 network activity events named the refusal (`VpceAccessDenied`).
  AWS-DataScience's `vpc-v0.4.0` admitted `mwaa-serverless-code-files-*-<region>-prod` (6i decision
  7, taken as (a)), and the re-run `N05WyTNjUcdxbw0` ended `SUCCESS` in 96 s. Its `.zip` was built
  by the by-hand recipe (`operators/build.sh`: the entry module, the project's package, petl 1.7.28
  and PyYAML 6.0.1 for the worker, 187 entries, 996,234 bytes): `petl` imported from
  `/usr/local/airflow/dags/petl/`, and `yaml` 6.0.2 from the worker's
  `/opt/mwaa-serverless-venv/lib64/python3.12/site-packages/`, so the pre-installed copy wins in a
  Python task.
- **A Bash task with inline commands** (run `b7FgLsjotHxaCde`, a workflow with no `Code`,
  2026-10-11): the working directory `/var/tmp/airflowtmp…`, not `/usr/local/airflow/dags`;
  `python3` the worker's `/opt/mwaa-serverless-venv/bin/python3` 3.12.14, with boto3 and botocore
  1.43.1; `AWS_REGION` and `AWS_DEFAULT_REGION` set to the region; the caller the project role,
  session `AmazonMWAAServerless`, through the `sts` interface endpoint; the seven variables the
  portal injects (`DataZoneDomainId`, `DataZoneDomainRegion`, `DataZoneEndpoint`,
  `DataZoneEnvironmentId`, `DataZoneProjectId`, `DataZoneStage`, `ProjectS3Path`) present, though
  `get-workflow` returns no `EnvironmentVariables`. `/usr/local/airflow/dags` held "the user's shell
  files" (the log's words) owned by `mwaa-serverless-user`, the DAG file dag-factory generated
  (`<uuid>.py`), an `ex_<uuid>` folder and `logs/`. A task that tried PyPI failed in about 2 s at
  name resolution: the VPC's DNS firewall answered `NXDOMAIN`, which the worker's resolver reported
  as errno 16.
- **A save with no code**: the editor pre-fills *Operator files zip S3 location*, and with no file
  there the save is refused with `ValidationException: Code not found in specified S3 location`;
  emptying the field makes the save send `code` null (2026-10-11).
- **A processing job with dependencies** (run `aB2zorz48GP67hx`, 2026-10-11, the stage log's pass
  3b): the workflow `demo-devenv-deps`, imported into a new workflow whose editor had pre-filled
  *Operator files zip S3 location* with `dev/operatorFiles/demo-devenv-deps.zip` and no file
  (emptied before the save), saved at 22:36:12Z; its log group existed from the save, empty and
  with no retention. The code input was a folder built in a space by AWS-DataScience's
  `package-uv-job.py` (176 files, 1,735,841 bytes: the project, petl 1.7.29 and msgspec 0.22.0 for
  CPython 3.13 on `x86_64-manylinux_2_28`; the fresh lock had pyarrow 26.0.0 against the image's
  24.0.0 until the constraint block) and copied with `cp -r` to `~/shared/jobs/`: 192 objects, the
  176 files and 16 zero-byte folder markers the space's `shared/` writes, which did not disturb the
  download. The job (created 23:06:03Z, processing 23:08:56Z to 23:16:26Z, 450 s) imported petl and
  msgspec's `_core.cpython-313-x86_64-linux-gnu.so` from `/opt/ml/processing/code`, and pyarrow
  24.0.0 from `/opt/awsds/venv/lib/python3.13/site-packages`; its JSON and Parquet outputs are byte
  for byte the laptop's. The run took 909 s and the processing task 791 s, about 3 minutes before
  `ProcessingStartTime`, 7 of image pull and 2.5 after `ProcessingEndTime` before `Completed`
  (AWS-DataScience's runbook); `get-workflow-run`'s `RunState` read `QUEUED` until 23:06:16Z,
  after the sensor had finished. About 0.029 USD: 15.2 task-minutes, 0.022 USD, and 450 s of
  `ml.t3.medium`, 0.006 USD.
- **`uv` in a lab space** (the user's run, 2026-10-11): `which python` answered
  `/opt/conda/bin/python` and `which uv` `/opt/conda/bin/uv`, the distribution's uv, 0.12.17 by
  AWS-DataScience's records of the house image (the space's version was not printed). The base
  image sets `UV_PYTHON_DOWNLOADS=never`, and the house CPython 3.13 lives under
  `/opt/awsds/python`, installed by a `uv python install` whose `UV_PYTHON_INSTALL_DIR` only the
  build step sets, so uv finds the distribution's Python only (AWS-DataScience's
  `images/README.md`); the image exports `AWSDS_PYTHON_ENV=/opt/awsds/venv`.
  `package-uv-job.py` stopped there with `No interpreter found for Python 3.14 in virtual
  environments, managed installations, or search path`, the repository's `.python-version` read
  by the shebang's `uv run --script`; its fix, AWS-DataScience's `fcc760b`, asks the shebang for
  `--python >=3.11` and names `$AWSDS_PYTHON_ENV/bin/python` to its uv commands through
  `UV_PYTHON`. What the package does there is in `packaging.md` ("The interpreter `uv` needs").

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

## The project space

What `scripts/space_values.py` relies on, read on 2026-10-11 from a cloud container in the code of
the SDK `sagemaker-studio` 1.1.35 (PyPI wheel; 1.1.32 holds the same code on these points). A lab
space ran the script on 2026-10-11; no target space has.

- **`Project()` works in the target** (user statement of 2026-10-11, 21:39 UTC). On 2026-09-21,
  when the target had no `~/.aws/config`, 1.1.32's `Project()` failed there with
  `ProfileNotFound (DomainExecutionRoleCreds)`; the `DomainExecutionRoleCreds` profile is in the
  lab space's `~/.aws/config` (serialize-db, 2026-09-19).
- **The script in a lab space** (the user, 2026-10-11, 22:21 UTC): `python space_values.py >
  valores.json`, in `~/awsds-workflows/scripts` of a space of the lab's project, printed the ten
  values, `REGION` `us-west-2`. The reading is in the Claude project's library,
  `valores/valores-lab.json`, kept out of git for its ids; the space's SDK version was not read. At
  22:43 UTC the user ran `awsds-workflows values --profile awsds-infra-sandbox-1 --subnet-name
  'awsds-sandbox-private-*' --project <project>` on the laptop, from this branch's checkout, and it
  printed the same JSON byte for byte (an empty `diff`), the account id included. AWS-DataScience's
  stage logs agree on nine of the ten, all but the account id, which they mask, and each is the
  value `values` reads: the project and the domain (06i, 2026-10-10, 0.1); the project role, the
  account's only one, and its group `datazone-<project>-dev` (06h, 2026-09-21); the private subnets
  of `usw2-az1` and `usw2-az2` (`10.20.0.0/18` and `10.20.64.0/18`, 05b, 2026-09-20, from the EC2
  API) in the script's order, the zone order `values` sorts by; the project key, which 06i's 0.1
  names by the role's `KmsKeyId` tag and its pass 2 (2026-10-11) by its id; the bucket
  `awsds-sandbox-smus-projects` (06i's 0.1, and the `DomainBucketName` tag of the domain's first
  project role, 06a, 2026-08-22). In this lab the environment's subnet order is the zone order.
- **The metadata file** `/opt/ml/metadata/resource-metadata.json` is where a space writes the
  project's data; AWS's user guide ("Accessing metadata") names only `ProjectS3Path`. The SDK reads
  a field at the file's root, then in `AdditionalMetadata`
  (`_get_field_from_sagemaker_space_metadata_json`); without the file, from the environment
  variable of the same name, then from `AIRFLOW__WORKFLOWS__<...>` on MWAA. Its code reads
  `ExecutionRoleArn` (the account is `split(":")[4]`), `DataZoneDomainId`, `DataZoneDomainRegion`,
  `DataZoneEndpoint`, `DataZoneEnvironmentId`, `DataZoneProjectId`, `DataZoneStage`,
  `DataZoneUserId`, `ProjectS3Path`, `NotebookId` and `SpaceName`; `PrivateSubnets` and
  `SecurityGroup` appear only in its test fixtures, one id each. The root `DomainId` is the
  SageMaker domain.
- **`Project()`** takes `DataZoneDomainId` and `DataZoneProjectId` from there, builds the singleton
  `SageMakerStudioAPI`, whose `__init__` runs again on every call, and calls DataZone's
  `GetProject` and `ListConnections` (`default.iam`). Each `__init__` also reads the project's S3
  path from the default Tooling environment, falling back to `ProjectS3Path` in silence.
- **The SDK's DataZone client** calls `DataZoneEndpoint` when the file has it, else
  `https://datazone.<region>.api.aws`, and signs with the profile `DomainExecutionRoleCreds` when
  `/home/sagemaker-user/.aws/config` names it, else with the default chain, with botocore's default
  timeouts and retries. The SDK loads its own DataZone model (`boto3_models`), where a
  `ListEnvironments` item carries `provisionedResources` and the internal `deploymentOrder`.
- **The default Tooling environment** (`ProjectService.get_project_default_environment`) is the
  project's environment of the managed blueprint `Tooling`, then `ToolingLite`, with the smallest
  `deploymentOrder` (`ListEnvironmentBlueprints`, `ListEnvironments`), else the environment of the
  `default.iam` or `project.iam` connection. `project.kms_key_arn` and `project.s3.root` read
  `kmsKeyArn` and `s3BucketPath` from its `GetEnvironment`; the job the SDK creates
  (`RemoteExecutionClient`) takes `securityGroup`, `privateSubnets` (split on `,`), `userRoleArn`
  and `kmsKeyArn` from it, and requires `awsAccountRegion`, `awsAccountId`, `id` and
  `provisionedResources`.
- **The script against a local DataZone server** (`uv run --with sagemaker-studio==1.1.35`,
  CPython 3.13.16, boto3 1.43.111): eleven `GET`s, three of them from the second
  `SageMakerStudioAPI()` (the blueprint, the environments and the environment again); stdout held
  only the JSON, and an `AccessDeniedException` on `GetProject` ended with exit 1 and the traceback
  on stderr. Importing `sagemaker_studio` took 3.73 s; the SDK pulls 102 packages (pandas, pyarrow,
  duckdb, awswrangler, deltalake and database drivers).
- **The managed policy `SageMakerStudioProjectUserRolePolicy`** v75 grants, with no condition, on
  the domain of the principal tag `AmazonDataZoneDomain`, `datazone:GetProject`,
  `ListConnections`, `GetEnvironment`, `ListEnvironments`, `ListEnvironmentBlueprints` and
  `GetDomainExecutionRoleCredentials`, among others; `iam:GetRole` in the principal's account; and
  `ec2:DescribeSubnets`, `DescribeSecurityGroups` and `DescribeVpcs` on `*` (re-read 2026-10-11).
  Whether the target's project role carries it is unread.
- **boto3 1.43.111** calls `https://datazone.sa-east-1.api.aws` for the target's region; the
  target's probe resolved `datazone.sa-east-1.amazonaws.com` to the interface endpoint, and the
  `api.aws` name was never resolved there. AWS's page on DataZone interface endpoints names neither.
  `Project()` working means the SDK reaches DataZone there; which name it calls is unread.
- **botocore 1.43.111** reads
  `Config(connect_timeout=5, read_timeout=20, retries={"total_max_attempts": 1})` as retry mode
  `legacy` with one attempt (a local server answering 503 got one request); the script's first
  version used it. The timeout of a connection that never opens was not measured: the container's
  proxy answers 403 for a private address.
