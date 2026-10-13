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
- **One worker per task**: in run `b7FgLsjotHxaCde` the tasks `caller_identity` and `reach_pypi`
  ran on workers in the az1 and az2 private subnets, and each task's log, in every run, opens with
  `Preparing the execution environment.` (2026-10-11).
- **A Bash task over a `.zip`** (run `xn9EZ2kgVIMcI7h`, 2026-10-11, the stage log's pass 5): the
  workflow `demo-bash-operator`, its `Code` a `.zip` built by hand (`operators/build.sh`:
  `reach_pypi.sh` and the project's package at the root, 4,849 bytes). The inline `run_command`
  printed `cwd /var/tmp/airflowtmp…` and
  `PYTHONPATH=/usr/local/airflow/dags:/usr/local/airflow/dags:/opt/mwaa-serverless-venv/lib/python3.12/site-packages`,
  then ran `cd /usr/local/airflow/dags && python3 -m awsds_demo_job.s3 ...`, `SUCCESS` in 9 s;
  `reach_pypi`, whose `bash_command` is `reach_pypi.sh`, ran as
  `['/usr/bin/bash', 'tmp6wm8sj1x.sh']`, the script rendered as a template into a temporary file,
  and failed as designed in 13 s. The import into the saved probe's editor was refused at the save
  (`ConflictException`) and uploaded the archive all the same; the probe was deleted, and the next
  save created the workflow.
- **Every save takes a new code snapshot** (the stage's verification vii, 2026-10-11): a save that
  only set the description (`UpdateWorkflow`, the code pinned to the same S3 version) made a new
  workflow version and moved `CodeSnapshottedAt` from 21:35:48Z to 21:42:08Z; the description
  landed in the definition as the DAG's `description` key.
- **`compare` over the lab's saved definitions** (2026-10-12, AWS-DataScience's
  `examples/sandbox-orchestration/README.md`): each of the six definitions the portal saved,
  against the file it was imported from, printed `is_paused_upon_creation: false`, and two printed
  an edit made on purpose besides: verification vii's description, and a command the probe's
  template changed after its run.
- **The inbox contract** (the stage's decision 4, taken by the user on 2026-10-12): the inbox is
  consumed as a prefix, one drop at a time; a file that lands between the job's download and
  `remove_source` is deleted unprocessed and stays only as a noncurrent version of the versioned
  bucket.
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
  S3 Tables resolve public and time out (probes of 2026-09-21 and 2026-09-23, from a space; the
  SageMaker name probed is not the API's, "A space on 2026-10-12" below).
- `uv`, `git` and `aws` on the `PATH`, no `gh`, no `~/shared`, no `~/.aws/config`; system Python
  3.12.14 in `/opt/conda` (2026-09-21); container credentials lasting about an hour; `AWS_REGION`
  and `AWS_DEFAULT_REGION` both `sa-east-1`.
- **The job image** starts as the SageMaker default image; the target cannot create custom images
  yet (user statement of 2026-10-11). The target's space runs SageMaker Distribution 4.5, the
  version the portal shows (the user, 2026-10-13; the "4.15" of 2026-10-11 was a typo), the minor
  the lab's house image is built on. The distribution's tags on public ECR run to 4.5.2: the 4.x
  line holds 4.0 to 4.5, each version also tagged `<major>.<minor>-cpu`, beside `4-cpu` and
  `latest-cpu` (read 2026-10-12 with the anonymous token,
  `https://public.ecr.aws/v2/sagemaker/sagemaker-distribution/tags/list`). Which 4.5 patch the
  space runs is unread.
- **A space on 2026-10-12** (the user, 17:39 UTC, in `~/shared/<user>/workflows`):
  `/opt/conda/bin/python --version` printed `Python 3.12.14`; `id` printed
  `uid=1000(sagemaker-user) gid=100(users) groups=100(users)`; `sudo -n true` succeeded, so the
  space's sudo needs no password; `mount | grep -i shared` printed
  `s3fs on /mnt/custom-file-systems/s3/shared type fuse.s3fs (rw,nosuid,nodev,relatime,user_id=0,group_id=0,allow_other)`,
  a mount the 2026-09-21 probe did not find; the public SSM
  parameter `/aws/service/sagemaker-distribution/ecr-account-id` answered with an AWS account, the
  registry of the distribution's `sagemaker-distribution-prod` in `sa-east-1`; and `aws sagemaker
  list-processing-jobs --max-results 1 --cli-connect-timeout 5` printed `{"ProcessingJobSummaries":
  []}` with exit 0, so the SageMaker API answers from a space. The 2026-09-21 and 2026-09-23 probes
  had resolved `sagemaker.sa-east-1.amazonaws.com` (serialize-db's `probes/space.py` builds
  `<service>.<region>.amazonaws.com`), a name the API does not use: botocore 1.43.111 calls
  `https://api.sagemaker.sa-east-1.amazonaws.com` (read 2026-10-12), the private DNS name of the
  `sagemaker.api` interface endpoint the target's Terraform declares. At 18:07 UTC the files the
  user copied into `~/shared/<user>/orchestration-demo/` were listed by `aws s3 ls` under
  `s3://<bucket>/<domain>/<project>/shared/<user>/orchestration-demo/`, so `~/shared` is the
  `shared/` folder of the project's prefix in the project bucket.
- **The first workflow run, 2026-10-12** (the user, 18:12 UTC): `demo-devenv-job`, imported in the
  portal from the definition rendered for the target (image `sagemaker-distribution-prod:4.5.2-cpu`,
  no KMS key, the folders under `shared/<user>/orchestration-demo/`). `wait_for_file` passed, so the
  worker listed the inbox in S3. `run_project` failed in 1.5 s with `AccessDeniedException` on
  `sagemaker:DescribeProcessingJob` for the proposed name `demo-devenv-20261012T181230`, as
  `assumed-role/datazone_usr_role_<project>_<environment>/AmazonMWAAServerless`, `because no
  identity-based policy allows the sagemaker:DescribeProcessingJob action`: the worker runs as the
  project role, reaches the SageMaker API, and wrote the task's log, which the portal showed. It is
  the lab's first refusal of 2026-10-10 (`docs/index.md`, "A permissão do projeto"); no job was
  created, and the message names no service control policy and no permissions boundary.
- **The target's Terraform** (the user's current version, sent on 2026-10-12 and read that day):
  the domain, the blueprint configurations (Tooling, DataLake, MLExperiments), a project profile
  that deploys Tooling and DataLake on create, and the project are CloudFormation stacks. The VPC
  has no internet route, only a Transit Gateway route to another account's VPC; it has interface
  endpoints with private DNS for `sagemaker.api`, `sagemaker.runtime`, `sts`, `ecr.api`,
  `ecr.dkr`, `glue`, `redshift`, `redshift-data`, `logs`, `secretsmanager`, `datazone`, the Studio
  endpoint, `ssm`, `ssmmessages` and `athena`, an S3 gateway endpoint with no endpoint policy, and
  no KMS endpoint. The project bucket defaults to SSE-KMS with the account's customer key, and the
  Tooling blueprint configuration sets no permissions boundary. It passes `terraform validate` on
  its own with the providers its lock file pins (aws 5.100.0, time 0.14.0). The copy on the user's
  laptop, a commit of 2026-09-04 read first that day, lagged it in 17 files and lacked 3, among
  them the Redshift module's `security_group_id` output, so it failed `validate`. The grant of
  `docs/index.md` ("A permissão do projeto") went to the user as adjusted copies of the current
  version (a new file in its compute module and a `project_role_names` variable), `terraform
  validate` passing and the rendered policy equal to the documented one. Not applied yet.
- **The first Python task, 2026-10-12** (the user, 19:16 UTC): `demo-python-operator`, the lab's
  definition rendered for the target (the folders under `shared/<user>/orchestration-demo/python/`),
  imported in the portal, its `.zip` uploaded in *Settings → Storage* before the save. The `.zip`
  was the first archive of `package-task` on a worker: built on the build host from a copy of the
  lab's `awsds-demo-job` with `petl==1.7.28` as its one dependency and the lab's `demo_tasks.py` as
  the entry module, 152 entries and 261,205 bytes, with `awsds_demo_job`, `demo_tasks.py`, `petl`
  and their `dist-info` at the root and no PyYAML. `run_project`'s log printed `Preparing the
  execution environment.` at 19:16:27.970Z and `Execution environment is ready.` 0.1 s later, so
  the worker got the code's copy; then `python 3.12.14 at /opt/mwaa-serverless-venv/bin/python3`,
  `caller arn:aws:sts::<account>:assumed-role/datazone_usr_role_<project>_<environment>/AmazonMWAAServerless`,
  `import petl: 1.7.28 from /usr/local/airflow/dags/petl/__init__.py`,
  `import yaml: 6.0.2 from /opt/mwaa-serverless-venv/lib64/python3.12/site-packages/yaml/__init__.py`,
  `sample.csv: 10 rows -> s3://<bucket>/<domain>/<project>/shared/<user>/orchestration-demo/python/outbox/20261012T191631Z/sample.result.json; source deleted`
  and `1 object(s) processed`, and `Task finished` with exit code 0 in 2.44 s, on a worker whose
  host name is a private `ip-10-…` address. The result's sha256, read in a space with `sha256sum`,
  is `1b2bc4d73bc49bca1a23a6d0971c1365362e785826a33adfcebec7925a248191`, the lab's of 2026-10-11.
  The worker fetched the service's copy of the code, which the lab's endpoint allow-list had
  refused, presumably through the S3 gateway endpoint the target's Terraform declares with no
  policy; it reached STS; and it listed, read, wrote and deleted objects in the project's folder.
  With the region set, boto3 1.43.1 calls STS at `https://sts.sa-east-1.amazonaws.com`, the private
  DNS name of the target's `sts` interface endpoint; botocore 1.43.111 reads `AWS_DEFAULT_REGION`
  and not `AWS_REGION`, and with only `AWS_REGION` set its STS client calls the global
  `https://sts.amazonaws.com` (probed on the build host, 2026-10-12). The lab's worker set both.
- **The first Bash task, 2026-10-12** (the user, 19:34 to 19:38 UTC): `demo-bash-operator`, the
  lab's definition rendered for the target (the folders under
  `shared/<user>/orchestration-demo/bash/`) with a fourth task, `probe_bash`, inline and with no
  dependency, that printed what `docs/index.md` marked as not measured; the `.zip` was uploaded in
  *Settings → Storage* before the save. It came from `package-task --include reach_pypi.sh
  --include probe.sh` over a copy of the lab's `awsds-demo-job` with `petl==1.7.28` and
  `six==1.16.0`: 161 entries and 272,943 bytes, the two scripts stored as 0o100755 and `six.py` as
  0o100644. Each task ran on a worker with its own host name, a private `ip-10-…` address.
  `probe_bash` (19:34:56Z to 19:35:09Z, exit 0 in 11.74 s) printed the working directory
  `/var/tmp/airflowtmp…` and the lab's `PYTHONPATH`; `ls -ln /usr/local/airflow/dags` showed every
  entry owned by uid and gid 997, `probe.sh` and `reach_pypi.sh` as `-rwxr-xr-x`, `six.py` and the
  DAG file `<uuid>.py` (806 bytes) as `-rw-r--r--`, and the folders `awsds_demo_job`, `petl`, the
  three `dist-info`, `ex_<uuid>`, `logs` and `__pycache__`, so the worker's extraction keeps the
  modes the `.zip` stores. With no `cd`, `python3 -m awsds_demo_job.s3 --help` printed the module's
  `usage:` line; `petl` 1.7.28 was imported from `/usr/local/airflow/dags/petl/__init__.py` and
  `six` 1.16.0 from `/usr/local/airflow/dags/six.py`, though the worker's Airflow 3.0.6 needs a
  `six` of its own (`apache-airflow-core` requires `python-dateutil`, which requires `six`, and
  Airflow's constraints for Python 3.12 pin `six` 1.17.0; PyPI metadata read 2026-10-12, the
  worker's copy not printed), so a Bash task's `python3` imports the `.zip`'s copy first.
  `bash /usr/local/airflow/dags/probe.sh um dois` printed `$0 = /usr/local/airflow/dags/probe.sh`,
  the arguments `um dois` and the task's working directory, and
  `/usr/local/airflow/dags/probe.sh tres`, executed directly, printed the same with `tres` and
  exited 0. `run_command` (19:35:31Z to 19:35:43Z, exit 0 in 9.21 s) printed
  `cwd /var/tmp/airflowtmp…`, the same `PYTHONPATH`,
  `python 3.12.14 at /opt/mwaa-serverless-venv/bin/python3` and
  `sample.csv: 10 rows -> s3://<bucket>/<domain>/<project>/shared/<user>/orchestration-demo/bash/outbox/20261012T193536Z/sample.result.json; source deleted`;
  the result's sha256, read in a space, is the Python task's `1b2bc4d7…a248191`. `reach_pypi`
  (19:36:19Z to 19:38:18Z), whose `bash_command` is `reach_pypi.sh`, ran as
  `['/usr/bin/bash', 'tmp….sh']` after `Tmp dir root location: /var/tmp`, the script rendered into
  a temporary copy as in the lab. It printed no proxy variable, `pypi.org` resolved to a public
  address, `urllib: URLError(OSError(101, 'Network is unreachable'))` and `urllib: 43 s` (the
  script's timeout is 10 s per connection), then pip 23.2.1, the worker's, with
  `[Errno 101] Network is unreachable` on `/simple/pip/` and `/simple/six/` and `pip: 64 s`; the
  command exited 1 and the task failed in 116.23 s, as designed, so the run ended `FAILED`. The
  lab's DNS firewall had refused the name in about 2 s (errno 16). The user said at 19:47 UTC that
  the target has no internet for now.

What these readings mean for a workflow there is an open question (`OPEN_QUESTIONS.md`, "A rede do
alvo para um workflow"): the worker's code fetch and its S3, STS, SageMaker and log calls answered
on 2026-10-12, a task's attempt at PyPI failed with errno 101, and the job's own path, from the
image pull on, was never read.

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
- **The script in a target space** (the user, 2026-10-12, 17:15 UTC, run as `python
  space_values.py` in `~/shared/<user>/workflows`, a folder the 2026-09-21 probe did not have):
  exit 1 with `o ambiente <ambiente> não tem kmsKeyArn`. `Project()` and the SDK's DataZone calls
  worked; the default Tooling environment's provisioned resources were `SageMakerSpacesDomain`,
  `ScheduleGroupName`, `allowConnectionToUserGovernedEmrClusters`, `athenaOutputUri`,
  `athenaSparkWorkGroupName`, `athenaWorkGroupName`, `cloudFormationStackId`,
  `enableNetworkIsolation`, `enableS3AccessGrantsForTools`,
  `enableTrustedIdentityPropagationPermissions`, `enableUserBackgroundSessions`,
  `enableWorkflowsConfigV2`, `glueNetworkConnection0` to `glueNetworkConnection2`,
  `isDefaultToolingEnvironment`, `logGroupArn`, `logGroupName`, `logGroupRetention`,
  `nonGitProjectRepositoryLocation`, `privateSubnets`, `s3BucketArn`, `s3BucketPath`,
  `sageMakerDomainId`, `securityGroup`, `systemRole-AmazonBedrockLambdaExecutionRoleArn`,
  `systemRole-AmazonBedrockServiceRoleArn`, `userRoleArn`, `userRoleName` and `vpcId`. The
  target's project has no project KMS key. The SDK 1.1.35 takes that case as normal: its
  `RemoteExecutionClient` reads `kmsKeyArn` with a `None` default and creates its training job
  without `KmsKeyId` and `VolumeKmsKeyId` (read 2026-10-12), so the script prints the other nine
  values and a warning since then. `CreateProcessingJob`'s API reference lists both fields as
  optional and does not say what encrypts the volume and the output without them (read
  2026-10-12). At 17:39 UTC the script of this branch, run as `python space_values.py >
  valores.json` in the same folder, printed the warning on stderr and the nine values; the order of
  the subnets against the zones was not read there.
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
