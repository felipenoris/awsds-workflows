# The CI/CD CLI

Read before code on the manifests of `examples/`, on the CLI's notation in `render` or `compare`, or
a `deploy` of an example: what the CLI `aws-smus-cicd-cli` 1.0.9 does, read in its code on
2026-10-14 and measured in the lab on 2026-10-15 and 2026-10-16 with `houseprice-etl`, between two
Sandbox projects of AWS-DataScience's account, from the user's laptop. The readings the
documentation reports are on the page `awsds_workflows.lab_notes` (`docs/laboratorio.md`, "A
aplicação pela CLI de CI/CD" and "houseprice-etl"), and the example's `README.md` holds every run;
this file keeps what they leave out and the facts in one place.

## The commands and the variables

- **The commands**: `version`, `describe`, `bundle`, `deploy`, `monitor`, `create`, `logs`, `run`,
  `test`, `destroy`, `integrate`; there is no `delete`, and `destroy` is unexercised.
  `aws-smus-cicd-cli --version` prints `aws-smus-cicd-cli 1.0.9`, and `describe --manifest
  manifest.yaml --connect` lists the stages and each project's connections.
- **The manifest's `${VAR}`** is resolved by the CLI's `helpers/utils.py` with the regex
  `\$\{([^${}:]+)(?::([^${}]*))?\}`, so `${VAR:default}` works, and a variable unset without a
  default stops any command, `describe` included, with `Variable ${VAR} is not set and has no
  default value`.
- **A workflow's `{env.VAR}`** becomes `{{ params.VAR }}` in the definition the CLI writes; a
  `{env.VAR}` outside the stage's `environment_variables` stops `workflow.create` with `Failed to
  resolve variables`. The `run`, and the `workflow.run` of the bootstrap, pass the stage's
  `environment_variables` as the run's override parameters, the `OverrideParameters` of
  `get-workflow-run`, read at the run, with no new deploy and no version spent; a run started in the
  portal has no value for them.
- **The project's variables** the CLI resolves at the deploy: `{proj.id}`, `{proj.iam_role_arn}`,
  `{proj.connection.default.s3_shared.s3Uri}` (`s3://<bucket>/<domínio>/<projeto>/shared/`), its
  `.bucket`, `{domain.id}` and `{domain.region}`; the subnets and the security group it does not
  expose, so they are stage variables.
- **The deployed workflow's name** is `<applicationName>_<project>_<workflowName>`, every character
  outside `[A-Za-z0-9_]` as `_`.
- **`bundle --targets test`** writes `./artifacts/<applicationName>.zip` (1,648 bytes for
  `houseprice-etl`: the script and the workflow as in git, the variables unresolved, no manifest
  inside), with no AWS identity; **`deploy --bundle-archive-path`** still copies the storage folders
  from disk beside the manifest, since the items name no `connectionName`.
- **`deploy`** copies the storage folders to the stage's `targetDirectory` and creates the workflow
  through `bootstrap.workflow.create`, `READY` and manual only, with the project's role, network and
  key, like one made in the portal; the definition saved in S3 is the resolved one. Its validation
  simulates the IAM without the context keys of the real calls and fails here every time, so the
  examples run with `--skip-validation`; the event it publishes at the end has no handler in 1.0.9,
  hence `--no-events`. Every `deploy` spends a workflow version, changed or not (2 for 2 in the test
  project, 3 for 3 in dev).
- **`run`** prints `🚀 Starting workflow run: <name>`, `🔗 ARN: <arn>` and `📋 Run ID: <id>`; `monitor`
  and `logs` misread a run (`INITIALIZING` with `Start Time: N/A`, `No log events found` with 40
  events in the stream), so the readers are `aws mwaa-serverless get-workflow-run --workflow-arn
  <ARN> --run-id <RUN_ID>` and `aws logs get-log-events`.
- **`workflow.run` with `wait: true`** crashes the CLI with a `TypeError` right after starting the
  run, which ends `SUCCESS` on its own; `trailLogs: true` returns 0 after about 5.5 min, no log
  streamed, for a run of 149 s; the exit 1 on a failed run was read in the code, not measured.
- **The credential**: the CLI's `boto3` does not read the cache the `aws` CLI keeps for an SSO
  profile; with the token expired it stopped with `Token has expired and refresh failed`, and `eval
  "$(aws configure export-credentials --profile <perfil> --format env)"` resolved.

## The Glue job in the lab

- **`glue:GetJob` on a job that does not exist** is refused to the project role:
  `SageMakerStudioProjectUserRolePolicy` authorizes `GetJob`, `UpdateJob`, `StartJobRun` and
  `GetJobRun` only on a job tagged `AmazonDataZoneProject` with the project, and a missing job has
  no tag; the operator reads the name before creating, so the first run in a project stops at
  `GetJob` with `AccessDenied` and no `CreateJob`. The job created once with `job.json` (`aws glue
  create-job --cli-input-json`) made the following runs `SUCCESS`: the Glue job in 86 s on the
  second, the CSV equal to the input, one CSV more in `saida/` per run; in the test project 124 s
  and 545 lines, and 149 s for the repeated run.
- **The `glue:GetJob` grant on the jobs no project holds**, the user's decision of 2026-10-16
  05:50 UTC (`decisions.md`, "The examples as applications"), measured the same day: the lab's
  policy `awsds-sandbox-workflows` at `v3` with the statement `GetAGlueJobNoProjectHolds`
  (`glue:GetJob` on `job/*-<project id>` with no `AmazonDataZoneProject` tag), applied at 14:54
  UTC; the dev project's job deleted at 15:18 UTC; the run of 15:22 UTC, from the lab's copy of
  the example, `SUCCESS` in 139 s. CloudTrail, the project role's session: `GetJob`
  `EntityNotFoundException` ("Job not found."), no longer `AccessDenied`; `CreateJob` `ok` under
  the managed policy's `GlueCreateAndTagPermissions` alone; `StartJobRun` `ok`. The task's log:
  "Checking if job already exists", then "Creating job". The job came out with the project role,
  the script under `glue/`, the connections rendered, `PythonVersion: "3"` filled by the service
  and the project's tag. The negative control, by `simulate-principal-policy` on the dev
  project's role: `GetJob` on the test project's job, on a free name ending in the test project's
  id and on a name with another suffix `implicitDeny`; on a free name ending in its own id
  `allowed`. The target's change request carries the same statement, unapplied.
- **A run whose definition references a parameter the manifest does not declare fails at the
  render**, before any task and any Glue call: the dev workflow in the morning's experimental
  form, `update_config: "{{ params.GLUE_UPDATE_CONFIG }}"`, run after the job's deletion from the
  repository's manifest, which declares no such variable, ended with `User template error: DAG
  template rendering failed: 'dict object' has no attribute 'GLUE_UPDATE_CONFIG'`; the parameter
  is not rendered empty. A portal run, which passes no parameters, would fail the same way
  (inferred). The `lint`'s `manifest` rule refuses an `{env.NOME}` a stage does not declare.
- **`UpdateJob` every run** with the definition unchanged: `GetJob` returns the `Command` with
  `PythonVersion: "3"` and the operator's input lacked it; the example carries the whole `Command`
  since, unmeasured. `update_config` from a stage variable changes nothing: the field is not a
  template field, and the operator called `UpdateJob` with `"false"` and with the empty text, both
  true as text; the literal `true` stays in dev and test (the user's card of 2026-10-16,
  `decisions.md`).
- **The run's parameters**: the definition the CLI saved has `{{ params.SUBNET_AZ1 }}`, the run
  carries the stage's values, and the job came out with the connection names filled. The lab filled
  the two subnets by hand in the stage variables; that they are the `privateSubnets`
  `space_values.py` prints is inferred.
