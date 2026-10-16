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
- The job image is selectable: a custom image or the SageMaker default image. The target cannot
  create custom images yet, so the work starts with the default image (user statement of
  2026-10-11). The default image is SageMaker Distribution 4.5, the version the target's space
  shows: the "4.15" of the statement of 2026-10-11, which the user section of `CLAUDE.md` still
  carries, is a typo (the user, 2026-10-13).

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
`.claude/memory/OPEN_QUESTIONS.md`; the section on a Python or Bash task keeps its own state line,
which since 2026-10-11 says that a `.zip` built by hand ran in the lab and that no `.zip` of
`package-task` has run on a worker.

On 2026-10-12 the user asked for a review of the `pdoc` documentation, the README and the
docstrings for language: clear, succinct and direct writing for someone learning to build MWAA
workflows in SageMaker, the material being read to learn. The reading of that request, which the
user confirmed on 2026-10-12 by choosing "Redação e abertura" over "Só a redação" and
"Reorganizar" (PR #9): the reader uses a SageMaker
Unified Studio project (project, space, portal) and does not know the Airflow or the MWAA; every
term is introduced where it first appears (worker, task, operator, job de processamento, sensor,
placeholder, endpoint de VPC, limite de permissões, módulo de extensão, fechamento travado,
manylinux); `docs/index.md` opens with a section of concepts and the reading order of a first
workflow, and keeps every other section, anchor, fact, measurement and date; the vocabulary is
"espaço" (never "space") and "ambiente alvo" (never "o alvo" for the environment; "o alvo" stays
for the platform a build targets); a measurement reads "medido no laboratório em <data>" and a
missing one "ainda não medido". The same review asked for the code against the Python standards
and for simplicity; its changes keep the behavior and the CLI, and are a commit of the same PR,
by the user's choice of 2026-10-12 ("Um PR" over "Dois PRs"), as the repository's git rule asks.

On 2026-10-12 at 02:49 UTC the user asked whether the `pdoc` site could be in dark mode ("o pdoc
poderia ser em "dark-mode" ?"), and at 02:56 UTC chose "Sempre escuro" over "Seguir o sistema",
the decision card's recommendation: every reader sees the site dark, whatever their system's
setting. The colors are in `docs/theme/`, the folder pdoc reads with `-t`: pdoc 16.0.0's
`dark-mode` example for the page and Pygments' `monokai` for the code, as in that example.

On 2026-10-16 at 00:42 UTC the user asked for a revision of the `pdoc` documentation against a
critique of it: no walls of text; procedures as numbered steps, each terminal command in its own
code block; the lab diary (dates, "medido em", "ainda não medido") apart from the manual; visible
callouts for warnings, errors and restrictions; and an opening that says who the documentation is
for and what problem it solves, with a quickstart. At 00:56 UTC, on a decision card the
coordinator session relayed, the user chose "Página própria" over marking the measurements in the
text: the lab's dates, readings and history moved to their own page, `awsds_workflows.lab_notes`
(`docs/laboratorio.md`), and a section of the guide or of the examples' page keeps a `> [!NOTE]`
with the step's state (`**Estado**: ...`) and a link to its notes. This replaces the PR #9
convention above of "medido no laboratório em <data>" and "ainda não medido" in the text. The
callouts are markdown2's GitHub alerts (`> [!NOTE]`, `[!TIP]`, `[!IMPORTANT]`, `[!WARNING]`,
`[!CAUTION]`), colored for the dark site by `docs/theme/custom.css`. Every section and anchor of
`docs/index.md` and `docs/exemplos.md` stays, and the opening of `docs/index.md` has "Para quem
é", "O problema que resolve" and the section "Início rápido". The CLI subsection of
`docs/exemplos.md` keeps its commands for the examples' reform, which owns it.

## The supported Python versions

On 2026-10-11 at 20:55 UTC the user asked that the package be compatible with Python 3.12 and that
the tests run on 3.12, 3.13 and 3.14: `requires-python` is `>=3.12`, and `tests.yml` runs the three
versions on Ubuntu. The repository's `.python-version`, the project venv and `docs.yml` stay on
3.13, Claude's default, named in the PR. Only `requires-python` blocked 3.12: with it relaxed, the
67 tests passed on 3.12, 3.13 and 3.14 (`environments.md`), and vermin 1.8.0 read nothing newer
than Python 3.9 in `src/` and `tests/`. `requires-python` has no upper bound, so 3.15 installs
untested.

`pyproject.toml`, `.github/workflows/tests.yml`, `README.md`, `docs/index.md`.

## The Bash task

On 2026-10-11 the user asked how a `BashOperator` differs from a `PythonOperator`, whether one can
run any binary or a Python script, what must be packaged, and whether the package could help.
Claude answered in the thread, with `bash-operator/bash-operator.md` in the Claude project's
library, and asked whether to update the package: "Só a doc" (Claude's recommendation: correct
`docs/index.md` with the lab's measurements and write the Bash task's section), "Doc e --include"
or "Nada agora". At 21:45:54 UTC the user chose "Doc e --include": the documentation work, plus
`package-task` taking `--include`, repeatable, to put scripts and binaries at the archive's root,
with the entry module optional.

Claude's choices inside that decision, named in the PR:

- **The entry module stays a positional argument, now optional** (`project [entry_module]
  archive`), so the existing command line keeps working. `argparse` then refuses an option between
  the positionals (`unrecognized arguments`), and the documentation puts the options after the
  `.zip`.
- **A name already at the root is refused**, whether a package, the entry module or another
  included file, rather than overwritten; the rule also covers the entry module, which
  `build_archive` copied over a file of the same name before.
- **The entry module and the included files are copied after the cleanup**, which would delete an
  included `.pyc` or `.lock`.
- **The documentation has a binary's caller copy it and `chmod +x`**, although the archive keeps
  each file's mode (`ZipFile.write` stores it, now under a test), since Python's `zipfile`
  extraction drops the mode and the service's extraction is not documented (`packaging.md`).

At 22:12:50 UTC the user asked for a section on the `BashOperator` in the `pdoc` documentation,
"caso já não tenha feito". The subsection of the code section became the top-level section
"Uma task Bash", with its own row in the page's table of sections and a table that sets a Bash
task against a Python task.

`src/awsds_workflows/package_task.py`, `src/awsds_workflows/cli.py`, `docs/index.md` ("Uma task
Bash").

## The values read inside a space

On 2026-10-11 at 21:04 UTC the user asked for a Python script, run in a project space, that prints
the JSON `values` prints, because their user may lack the permissions `values` needs; they expected
`import boto3` and an instance of the SDK's `Project` to carry what the space knows. At 21:19 UTC,
on a decision card, the user chose DataZone as the source of `PROJECT_KEY_ID` ("Pede ao DataZone o
ambiente Tooling do projeto, a fonte que o SDK usa"), over the key of an object in the project's S3
path and over writing it by hand. The first version read nine values from the space's metadata
file and called `GetEnvironment` on its `DataZoneEnvironmentId` without `Project()`, which had
failed in the target with `ProfileNotFound (DomainExecutionRoleCreds)` on 2026-09-21.

At 21:39 UTC the user stated that `from sagemaker_studio import Project` and `project = Project()`
work in the target ("funciona no ambiente alvo"), and at 21:40 UTC proposed adapting the script to
use `project`. At 21:47 UTC, on a decision card, the user chose "Tudo pelo SDK" ("Os 10 valores vêm
do Project() e do ambiente Tooling, a fonte do SDK para criar um job, e o arquivo de metadados sai
do script") over reading only the key through `project.kms_key_arn`. The script takes the ids from
`Project()` and every other value from the default Tooling environment the SDK finds, and a
DataZone failure ends without JSON, where the first version printed nine values
(`environments.md`, "The project space").

`scripts/space_values.py`, `tests/test_space_values.py`, `docs/index.md`.

## The comparison of definitions

On 2026-10-11 at 23:26 UTC the user asked how to reconcile the definition kept in git with the one
SageMaker keeps in `dev/workflows/` of the project's bucket. Claude answered that git is the source
and S3 the deployed copy, and offered a comparison that reads the two YAML files and shows only the
real differences, with PyYAML as a dependency. At 23:47 UTC the user answered "sim, pode incluir".

Claude's choices inside that decision, named in PR #7, which the user confirmed on 2026-10-12 at
02:13 UTC, after the merge, with "sim, ficou bom assim":

- **The module and the subcommand are `compare`, the function `compare_definitions`**, which takes
  two paths, as `render.load_values` does, and refuses a missing file, a file that is not YAML and
  a document that is not a mapping. It does not restore the placeholders: the documentation chains
  `render --placeholders` and `compare`.
- **The output is one line per side of a difference**: `- path: value` for what only the first file
  has, `+ path: value` for what only the second has, and a changed value gives both. The path joins
  keys with `.` and list positions with `[i]`, the value is JSON on one line, and the order follows
  the first file's keys, then the keys only the second has.
- **Values compare with their type** (`true` and `1` differ), and **lists by position**.
- **`compare` exits 0 with or without differences** and prints "as definições têm o mesmo
  conteúdo" when there are none; 1 stays a refusal and 2 a usage error.
- **`pyyaml>=6` is a floor**, like `packaging>=24`; `uv` resolved 6.0.3 on 2026-10-12.

On the lab's two pairs of an imported template and the definition the portal saved
(AWS-DataScience's `examples/sandbox-orchestration/devenv-job/` and `definitions/`, read on
2026-10-12), `compare_definitions` printed only `+ demo-devenv-job.is_paused_upon_creation: false`,
where a text `diff` of the project pair, the layout line left out, printed 107 lines. The service
ignores that key: each `update-workflow` answered `ignored attributes: is_paused_upon_creation`
(AWS-DataScience's stage 6d, 2026-09-10). `tests/test_compare.py` repeats the portal's changes on
a definition of its own.

`src/awsds_workflows/compare.py`, `src/awsds_workflows/cli.py`, `tests/test_compare.py`,
`docs/index.md` ("A definição que o portal salvou").

## The findings of AWS-DataScience's PR #110

On 2026-10-11 at 23:50 UTC the user asked whether the documentation and the code needed updating
after AWS-DataScience's PR #110 (merged as `c0baddd`), which ran a processing job over a uv project
with dependencies, and after an error in a space: `package-uv-job.py` stopped with `No interpreter
found for Python 3.14`, the space's Python downloads being off. Claude reproduced the error's second
half in a simulated space: `package-job` and `package-task` stop the same way when the project asks
for a Python the space's uv cannot find, and uv's own `UV_PYTHON` naming the job's interpreter
unblocks both with no code change (`packaging.md`, "The interpreter `uv` needs"). On a decision
card, at 00:03:45 UTC on 2026-10-12, the user chose "Só a doc" (Claude's recommendation: a draft PR
with `docs/index.md`, the docstring of `package_job` and the memory; in a space, uv's own
`UV_PYTHON`) over "Doc e opção" (a `--uv-python` option on `package-job` and `package-task` that
passes the interpreter to uv) and "Nada agora".

Claude's choices inside that decision, named in the PR:

- **A test holds what the documentation promises**: `tests/test_uv.py` checks that `UV_PYTHON`
  reaches the uv call and that a missing interpreter is refused with the message the refusal tables
  quote.
- **The `:raises` fields of `build_folder` and `build_archive` name the missing interpreter**, and
  `_uv`'s docstring says that uv inherits the process's environment.

`docs/index.md` ("O Python que o `uv` usa", the refusal tables, the job with dependencies, "Como
ler uma execução", "Limpeza"), `src/awsds_workflows/package_job.py`, `tests/test_uv.py`.

## AWS-DataScience adopts the package

On 2026-10-12, in a session of the AWS-DataScience repository, the user asked to adapt the guidance
on creating workflows to this package, so that AWS-DataScience's support scripts could be deleted
("Adapte as orientações sobre criação de workflows utilizando a ferramenta do repositório
`https://github.com/felipenoris/awsds-workflows`. Com isso, poderemos eliminar os scripts de apoio
do AWS-DataScience."). AWS-DataScience's PR #113 rewrote its runbook
`docs/plan/runbooks/serverless-workflows.md` around the CLI, with a section on the tool (§T),
deleted `render.py`, `package-uv.sh` and `package-uv-job.py`, and renamed the placeholders of its
example YAML to this package's names. The same day the user answered the three choices that
session put to them:

- "pode utilizar a main do pacote": the runbook installs the package by git URL from `main`, with
  no commit pinned, and updates it with `uv tool upgrade awsds-workflows`. A change to a CLI
  option or to a message on `main` therefore reaches that runbook, which quotes both and names the
  commits it was measured at (`937a66a` and `3499530`);
- "tudo bem ficar o zip": AWS-DataScience's `operators/build.sh` stays, because its Python archive
  vendors PyYAML to show the worker's copy winning (its Stage 6i verification viii), and
  `package-task` prunes PyYAML by design;
- "tudo bem em relação às mensagens de erro": the runbook's refusal tables quote this package's
  pt-BR messages, keep only the rows with a way through specific to the lab, and link this
  documentation for the rest.

Then the user asked this session to fix what this repository needed ("Pode corrigir o que for
necessário no awsds-workflows"). The measurements behind the adoption are in `packaging.md` ("The
port verified against the original scripts") and `environments.md` ("The build host").

On 2026-10-12 at 01:44 UTC, in this repository's project, the user asked to check what else needed
revising after that commit (`40caedb`) and to revise the code and the documentation as needed
("Verifique se algo a mais precisa ser revisado neste repositório awsds-workflows considerando os
ajustes do commit. Revise o que for necessário no código e documentação."). No behavior changed:
everything the runbook quotes exists in this repository, read that day at AWS-DataScience's
`c40f8b4`: the subcommands `render`, `values`, `compare`, `package-job`, `job-constraints` and
`package-task`; the options `--profile`, `--subnet-name`, `--image-name`, `--project`,
`--placeholders`, `--values-file`, `--environment`, `--python`, `--platform`, `--include` and
`--omit`; the messages `já existe: nomeie uma pasta nova`, `acima do limite de 250000000 bytes do
worker`, `já está na raiz do .zip`, `não há uv.lock em`, `não é Python puro` and `o lock do
projeto e o ambiente da imagem discordam`, and the printed `próximo passo`; the placeholder names;
`scripts/space_values.py`; and the anchors `#os-valores-de-dentro-de-um-espaco`,
`#a-pasta-de-codigo-com-package-job` and `#o-zip-com-package-task` of the `pdoc` site. The
documentation and the docstrings of `package_task` were behind the lab's stage log, and were
brought to it (`environments.md`, "The AWS-DataScience lab").

`docs/index.md` ("Instalação", "A imagem do job", "Regras de autoria", and on the second request
"Os conceitos", "As peças", "A rede", "O código de uma task Python ou Bash", "Uma task Bash", "A
definição que o portal salvou"), `README.md`, `src/awsds_workflows/package_task.py`.

## The examples folder

The user asked on 2026-10-13 (03:30 UTC) for the package to be self-contained in functionality,
documentation and examples, so that a user of the repository reproduces the five workflows
exercised in the target (`probe-worker`, `redshift-unload`, `demo-bash-operator`,
`demo-python-operator`, `demo-devenv-job`): a maintenance that makes the package render them, an
examples folder with instructions per workflow taking the `space_values.json` of
`scripts/space_values.py` as the input, copying files from AWS-DataScience's examples where
needed. The session of that day (branch `claude/awsds-workflows-examples-yn6vxj`) asked the user
three questions at 03:39 UTC, which the user answered at 04:04 UTC, and made the other choices
below, which await the user's word:

- **`--values-file` repeats**, each file completing and overriding the account's reading and the
  files before it, in command-line order, and **each example brings a model values file**,
  `examples/<exemplo>/extra_values.json`, the second `--values-file` after `space_values.json`
  (the user's answer 1, "de acordo com a recomendação"; the name because `.gitignore` ignores
  `valores*.json`). The values a space does not give stay in that file as values to fill: the
  job's `SMD_REGISTRY_ACCOUNT`, the unload's `REDSHIFT_WORKGROUP`, `REDSHIFT_DATABASE` and
  `REDSHIFT_TABLE`.
- **The prefix of an example in the project's bucket is the placeholder `EXAMPLE_PREFIX`**, set
  by its `extra_values.json` to `shared/exemplos/<exemplo>`, `~/shared/exemplos/<exemplo>/` in a
  space, in place of the personal folder the target's runs used (the user's answer 2, "um
  placeholder no arquivo de valores extras"; the question had written `<EXAMPLES_PREFIX>`, and
  the session chose the singular, since each example's file sets its own). The inbox, the outbox
  and, for the job, the code folder `awsds-demo-job/` sit under it.
- **The file a space writes is `space_values.json`**, the user's name for it; `valores*.json` and
  `space_values*.json` stay out of git.
- **A value may reference other placeholders** (the session's choice, awaiting the user's word):
  `fill_placeholders` and `restore_placeholders` resolve them one level before the text, and a
  value that references a placeholder without a value, or itself, is refused as a placeholder
  without a value. It lets the job's model file hold `JOB_IMAGE_URI` as
  `<SMD_REGISTRY_ACCOUNT>.dkr.ecr.<REGION>.amazonaws.com/sagemaker-distribution-prod:4.5.2-cpu`,
  independent of the region, and makes `"NAME": "<NAME>"` the form of a value to fill, so an
  unfilled model refuses the render instead of reaching the portal.
- **One uv project serves the three `demo-*`**, `examples/awsds-demo-job/`: the lab's project
  rewritten in pt-BR with `uv_build`, `petl==1.7.28` and `six==1.16.0` as dependencies (the
  target's Python archive carried only `petl`, its Bash archive both); the job's own code needs
  only the standard library.
- **The job's code input is the `.tar.gz` of the project folder prepared with its own
  interpreter** (the user, 2026-10-13 04:55 UTC: "Sim, faça o `demo-devenv-job` nesse formato").
  The answer 3 of 04:04 UTC ("conforme a recomendação") had kept the folder copied as it is, with
  `PYTHONPATH=/opt/ml/processing/code/src`, as the target's definition did; in the same message
  the user asked whether a `.tar.gz` of the prepared folder, `.venv/` included, extracted on the
  job's volume, works in place of a folder of many small files expanded in S3, as they do with
  serialize-db's `prepare_offline.sh` and `tar`. The session answered yes, with the relocation,
  platform and volume caveats, and the user decided at 04:55 UTC. At 05:15 UTC the user asked
  that the package carry the tooling, the documentation the instructions and the example the new
  way ("Certifique-se de que o pacote tem o ferramental necessário, e que a documentação tenha
  as instruções necessárias, e o exemplo agora reflita a nova forma de configurar"), so the
  preparation is the subcommand `prepare-offline` (`prepare_offline.prepare_archive`), and the
  script the session had first written in the shared project left. The session's choices for
  it, awaiting the user's word: the names `prepare-offline`, `prepare_offline`,
  `prepare_archive` and `OfflineArchive`, from the user's `prepare_offline.sh` of serialize-db;
  `DEFAULT_PYTHON` 3.12, the worker's and the default image's, with `--python` for another; the
  command works on a temporary copy of the project, never on the folder, which keeps its
  `.venv/`; it requires `uv.lock` and syncs `--locked`, and the lock stays in the archive; the
  interpreter is the CPython `uv` downloads into `.python/` of the copy (`UV_PYTHON_INSTALL_DIR`,
  `UV_PYTHON_DOWNLOADS=automatic`, `UV_MANAGED_PYTHON=1`, `UV_PROJECT_ENVIRONMENT` and
  `UV_LINK_MODE=copy` for that call only, through `_uv.run`'s `env`), never one of the machine;
  `--no-dev --no-editable`, so no editable `.pth` needs rewriting in the job; every absolute link
  made relative, and one pointing out of the copy refused; the root is the project folder's name;
  the archive carries no owner (uid and gid 0) and is gzip level 6; the proof extracts the
  archive and runs its `.venv/bin/python` without `uv` in the environment, reading the project's
  version and `sys.prefix`, before the archive replaces an existing one; any platform but Linux
  x86_64 is refused before any download. The definition's code input is the prefix `code/` with
  that one object, and the job's command chowns `code` and `outbox`, extracts with `tar -xzf` and
  runs `.venv/bin/python -m awsds_demo_job`, so `JOB_PYTHON` and `PYTHONPATH` left the example.
  The `network` tests repeat the relocation proof (`.claude/memory/packaging.md`).
- **The definitions are the ones that ran in the target**, with the prefix changed and the
  target's Redshift names as placeholders (`REDSHIFT_*`), like the account's values.
- **`demo_tasks.py` also prints `sys.path` and probes `six`**, which the target's run did not: it
  answers the open question on the Python task's precedence when it runs.
- **The examples' tests** (`tests/test_examples.py`) render each definition with fabricated
  values, check the placeholder sets and the prefix, run the Python task and the `UNLOAD` module
  over doubles (`botocore.stub.Stubber`), and build both archives (`network`); `boto3` joined the
  `dev` group for them, and pytest's `testpaths` and `pythonpath` reach into `examples/`.

At 03:32 UTC the same day the user asked for a new `pdoc` page with the instructions to configure
all these examples, "bem diretas, similar ao que fizemos aqui no chat". The session wrote it as
`docs/exemplos.md`, the page `awsds_workflows.examples` through the docstring-only module
`src/awsds_workflows/examples.py` (serialize-db's `technology_review.py` pattern), with the
commands, the expected output and the checks of the chat threads "Exemplos no ambiente alvo" and
"Tasks de workflow para ETL", each step saying where it runs. The session's own choice, awaiting
the user's word: the steps live only on the page, and the per-example READMEs keep what each
example shows, what its logs say and what the target's runs read, with a link to the page's
section; `examples/README.md` keeps the table, the shared project, the prefix and the tests.

On 2026-10-14 (23:44 UTC, in the Claude project's thread on a Visual ETL job in an application)
the user asked to put "todo esse exemplo" in the repository "como uma aplicação de exemplo": the
target's Visual ETL job packaged as an application of the CI/CD CLI `aws-smus-cicd-cli` 1.0.9,
which the thread had written for the target in the Claude project's library (`alvo/visual-etl/`,
with the target's values). At 23:42 UTC, on a decision card, the user had decided that a job an
application carries is edited in the application's script, in git, and that the Visual ETL flow
is only a draft whose generated script is copied once. The session of that day (branch
`claude/project-thread-8oxrm3`) wrote `examples/houseprice-etl/` with these choices, which await
the user's word:

- **The folder** `examples/houseprice-etl/`, the target workflow's name, holds the definition with
  the package's placeholders at its root, for the portal through `render`, and the application one
  level down in `aplicacao/`, so `tests/test_examples.py`, whose `DEFINITIONS` globs
  `examples/*/*.yaml`, does not take the manifest for a definition.
- **Two forms of one workflow**: the definition, and `aplicacao/workflows/houseprice-etl.yaml` with
  the CLI's variables (`{proj.id}`, `{proj.iam_role_arn}`,
  `{proj.connection.default.s3_shared.s3Uri}`, `{domain.region}`) for the `deploy`; a test maps each
  variable to the placeholder of the same value and asserts both fill the same.
- **The subnets** keep their placeholders in the CLI form, since the CLI has no variable for them,
  and `render` fills them once in a copy outside the repository, the start of the application's own
  repository. The job gets two network connections,
  `datazone-glue-network-connection-<SUBNET_AZ1|SUBNET_AZ2>-<PROJECT_ID>-dev`, from the two subnets
  `space_values.py` prints, where the target's Visual ETL job had three; that the space's
  `privateSubnets` are the connections' subnets is inferred.
- **The manifest's region** is `${DOMAIN_REGION}`, the CLI's environment substitution, beside
  `${DOMAIN_ID}`, `${DEV_PROJECT_NAME}` and `${TEST_PROJECT_NAME}`.
- **`job.json`** is the task's `CreateJob` input with placeholders, rendered like the definition,
  to create the job by hand if `glue:GetJob` on a missing job is refused; a test asserts it equal
  to the operator's input built from the task.
- **The paths** sit under `EXAMPLE_PREFIX`, `shared/exemplos/houseprice-etl` (`jobs/`, `entrada/`,
  `saida/`), and the CLI's target directories are `exemplos/houseprice-etl/jobs` and
  `exemplos/houseprice-etl/workflows` under `default.s3_shared`, in place of the target copy's
  `shared/houseprice-etl/`.
- **No data ships with the example**: the steps convert the preparation's `sample.csv` into
  `entrada/house-price.parquet` with the space's pandas, or take a Parquet the project's Visual ETL
  flow reads.

## The examples as applications

AWS-DataScience's D41 (the user's decisions of 2026-10-15, 04:40, 05:29 and 05:45 UTC, in its PR
#137, amended by its PR #138 of 2026-10-16) made the SageMaker application, a folder with the
manifest the CI/CD CLI `aws-smus-cicd-cli` reads, the unit that moves between projects and accounts:
in dev and test the CLI deploys it, and the pipeline deploys its bundle beyond. What it fixed for
this package: one YAML per example, in the CLI's notation, with `render` learning the CLI's
variables; a processing job's code as the job's input under `src/`, the image carrying only the
lock; the application's Glue job created or updated by the operator in dev and test and owned by the
application's slice in Staging and Production (item 9); `{env.VAR}` for a value no project holds
(item 1, amended); the order of the work (item 6): the lab's measurements first, then this reform,
then AWS-DataScience's `examples/app-etl/`; Stage 10's decision 6, that the copy for another account
is a translation of the CLI's variables into that account's literals, out of this reform; Stage 10's
decision 13, no `schedule` in a promoted workflow; Stage 8's decision 9, that the `lint` lives in
this package. The CLI was measured with `houseprice-etl` between two Sandbox projects, from the
user's laptop, on 2026-10-15 and 2026-10-16 (`cicd-cli.md`).

On those measurements the user decided, on cards: `update_config` stays the literal `true`, with
`create_job_kwargs`, in dev and test, and the promoted copy drops both (2026-10-16 03:24 UTC, option
B, after a stage variable in that field was measured to change nothing); and how the job is born in
a project where it does not exist: a `glue:GetJob` grant on the jobs no project holds (2026-10-16
05:50 UTC, "vamos pela opção 1: um grant de glue:GetJob", the recommended option of the card of
02:14 UTC, over the job created once from `job.json` and a Python task that creates it). The grant
is written in the lab's Terraform (AWS-DataScience PR #143, `sandbox/workflows/`, the statement
`GetAGlueJobNoProjectHolds`: `glue:GetJob` on `job/*-<project id>` with no
`AmazonDataZoneProject` tag) and in the target's change request. The lab applied it on 2026-10-16
at 14:54 UTC, and a run at 15:22 UTC, from a deleted job, created the job by the operator
(`cicd-cli.md`, "The Glue job in the lab"); the target's is unapplied, and the examples' steps
keep the `job.json` path for a project whose role lacks the grant.

The session of 2026-10-16 (branch `claude/smus-applications-rw30u1`, PR #20) wrote the plan in the
Claude project's library (`discussoes/plano-reforma-exemplos.md`) and asked three questions, which
the user answered at 04:20 UTC, "Perguntas 1, 2, e 3: faça conforme sua recomendação":

- **One application per example**, each folder with its own manifest, which reads and deploys alone,
  like `app-etl`; not one application with six workflows.
- **The prefix is the literal `exemplos/<exemplo>`** after the `s3Uri` of the connection
  `default.s3_shared`, the project's `shared/` folder; `EXAMPLE_PREFIX` left, since the CLI gives
  `shared/` and a variable prefix would need a stage variable per example.
- **The `lint` comes in a following PR**, before `app-etl`, with the rules (a) to (h) of Stage 8's
  step 5.6, the manifest's and Stage 10's Glue rule; this PR keeps the examples' form.

The session's choices, awaiting the user's word, which replace those of "The examples folder" where
the two meet:

- **The folder is the application**: `manifest.yaml` at the root, the workflow in
  `workflows/<exemplo>.yaml` in the CLI's notation, the tasks' sources in `code/`, the job's code
  input in `src/`, the Glue script in `glue/` (the names of AWS-DataScience's plan after its PR
  #138; `glue/` for the `jobs/` of 2026-10-14). The definition with placeholders at the root and
  `aplicacao/` left, since `render` gives the portal's definition from the CLI's workflow, and
  `tests/test_examples.py` reads `examples/*/workflows/*.yaml`.
- **`render` translates the CLI's variables before filling** (`CLI_VARIABLES`,
  `translate_cli_variables`): `{proj.id}`, `{proj.iam_role_arn}`,
  `{proj.connection.default.s3_shared.s3Uri}`, its `.bucket`, which the CLI derives from the URI,
  `{domain.id}` and `{domain.region}` by their expression with placeholders, `{env.NOME}` by
  `<NOME>`, and a variable outside the table refused, the rule (a) of the lint; `compare` normalizes
  both sides the same way, with `{{ params.NOME }}`, the form the CLI writes a stage variable in, as
  `<NOME>`; `render --placeholders` does not change.
- **The subnets, the security group, the job's image and the Redshift names are stage variables**,
  `{env.NOME}`, declared in both stages as `${NOME}` read from the shell, because the CLI has no
  variable for them and a `{env.NOME}` without a declaration stops `workflow.create` (lab,
  2026-10-16); the `run` passes them as the run's parameters, so a workflow of the CLI runs by the
  CLI and is read in the portal.
- **`extra_values.json` stays only where the portal path has a value to fill**: `demo-devenv-job`
  (`SMD_REGISTRY_ACCOUNT` and the `JOB_IMAGE_URI` built from it) and `redshift-unload` (the three
  `REDSHIFT_*`); the other four render with `space_values.json` alone.
- **The manifest's form is the one the CLI 1.0.9 accepted in the lab**: `content.storage` items
  without `connectionName`, so `bundle` and `deploy` read the folders from disk beside the manifest;
  `content.workflows[0]` with the folder's name, `connectionName: default.workflow_serverless` and
  `code: code/<exemplo>.zip` where a task has a `.zip`; the stages `dev` and `test` with
  `${DOMAIN_ID}`, `${DOMAIN_REGION}`, `${DEV_PROJECT_NAME}` and `${TEST_PROJECT_NAME}`;
  `bootstrap.actions` with `workflow.create` in both and `workflow.run` with `trailLogs: true` in
  `test`, since `wait: true` crashes the 1.0.9; `deployment_configuration.storage` with
  `targetDirectory: exemplos/<exemplo>/<pasta>` on `default.s3_shared`.
- **The `.zip` and the `.tar.gz` are written into the folder the manifest uploads**: `package-task`
  into `code/<exemplo>.zip`, `prepare-offline` into `src/awsds-demo-job.tar.gz`, and
  `redshift-unload`'s `.zip` by Python's `zipfile`, since its module needs only the worker's
  `boto3`; they, and the CLI's bundle in `artifacts/`, stay out of git.
- **`demo_tasks.run` and `awsds_demo_job.s3` take `s3://` URIs** for the inbox and the outbox,
  because the CLI gives the connection's whole `s3Uri` and not the key without the bucket; the
  summary is the same.
- **The `houseprice-etl`'s task carries the whole `Command`** (`Name`, `ScriptLocation`,
  `PythonVersion: "3"`) in `create_job_kwargs`, because the lab's `UpdateJob` every run came from
  that field, which `GetJob` returns with `PythonVersion` and the operator's input lacked; a run
  without `UpdateJob` is not measured. The job is created once per project with `job.json`, in the
  CLI's notation, where the project role lacks the `glue:GetJob` grant of the user's decision of
  05:50 UTC (above).
- **The documentation's shape**: `docs/exemplos.md` leads every example through the CLI in a shared
  section, with the commands as they ran in the lab (`--skip-validation`, `--no-events`, the readers
  `get-workflow-run` and `get-log-events`), the portal as the other path through `render`, and a
  `**Estado**` line per example saying what ran by the CLI and by the portal; the dates and readings
  on `awsds_workflows.lab_notes` (its sections "A aplicação pela CLI de CI/CD" and
  "houseprice-etl"); `docs/index.md` carries the translation table under "Os valores da definição"
  and the `compare` of a CLI workflow.

## The lint of an application

The `lint` lives in this package by Stage 8's decision 9 of AWS-DataScience, and comes in the PR
after the reform of the examples, before `app-etl`, by the user's answer of 2026-10-16 04:20 UTC
("The examples as applications"). Its mandate: the rules (a) to (h) of Stage 8's step 5.6, the
manifest's rules, Stage 10's Glue rule (class 2c) and the refusal of `schedule` (Stage 10's
decision 13); the rule (d), the `VersionId` of the code in S3, is the pipeline's and stays out.
The session of 2026-10-16 wrote the plan in the Claude project's library
(`discussoes/plano-lint.md`) and asked three questions, which the user answered at 05:52 and
05:54 UTC:

- **Both modes now** (1 (a)): the authoring mode over the repository's files in the CLI's
  notation, and the promoted mode (`--promoted`) over a rendered copy, with the plan's full set
  of rules; not the authoring mode alone with the promoted one left for Stage 10.
- **The volume's KMS key only in the promoted mode** (2 (a)): `VolumeKmsKeyId` is required of a
  processing job in a promoted copy and not in authoring, where the default image's job in the
  target has no project key.
- **Any class of the Amazon provider, plus Python and Bash** (3 (b)): the `operator` passes when
  it is a class of `airflow.providers.amazon.aws.` or the `PythonOperator` or `BashOperator` of
  `airflow.providers.standard.operators.`, with no nominal table of the 199 classes AWS lists
  (`operators.md`, read 2026-10-16), and `SageMakerNotebookOperator` refused by name (Stage 6d's
  decision 14 (b)); the user asked for the context first ("pode explicar qual o contexto?") and
  chose (b) over a table copied from the page, which would go stale as AWS adds operators.

The session's choices listed in PR #21, confirmed by the user on 2026-10-16 at 14:30 UTC ("Ok em
relação a suas 5 escolhas"): `schedule` refused in both modes, since an example runs by `run` and
a promoted workflow by a state machine; `retries` written in every task, since the service assumes
1; the job's `MaxRuntimeInSeconds` capped at 2,820 s, 13 minutes under the task's 3,600 s for the
job's provisioning and shutdown, a margin chosen and not measured; the promoted mode asking for
`--prefix`, so the `codigo` and `glue` rules never silently skip on a pipeline; and the project
values found by patterns over the text (`datazone_usr_role_`, `dzd_`, `smus-projects`,
`dev/operatorFiles/`, `DataZone*`, `ProjectS3Path`, `alias/*-project`, the keys `domain_id` and
`project_id`). The session's other choices, not put to the user: the tag `AmazonDataZoneProject`
and the project's network connection pass in authoring and fail in the promoted mode; the
definition's quota read as 50,000 bytes; and `lint_application` reading the files as the CLI
1.0.9 does, each `include` a folder or a `glob`, each `exclude` by folder, path or basename.

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
  AWS-DataScience's exercise used, is gone. AWS-DataScience's examples took these names on
  2026-10-12 ("AWS-DataScience adopts the package").
- **`--subnet-name` is required with `--profile`**: the lab's pattern `awsds-sandbox-private-*` is
  the documented example, not a default.
- **`--omit PACOTE`, repeatable, replaces the `OMIT` variable** of `package-uv.sh`, and
  **`job-constraints` is a subcommand** where the script had `--constraints`.
- **The messages and the printed output are pt-BR** (the language rule); `uv`'s stay English.
  AWS-DataScience's runbook quotes them in pt-BR since 2026-10-12, which the user accepted for that
  runbook ("AWS-DataScience adopts the package").
- **The CI runs on Ubuntu only**, since the package runs on Linux; serialize-db's runs on Ubuntu and
  Windows.
- **`uv` is not a dependency**: it is called as a program, and the house image refuses a change of
  its uv version. **`packaging>=24` is a floor**, not a pin, so the package installs beside an
  environment that pins its own.
- **`docs/index.md` is the runbook**, included by the package's docstring, as serialize-db's
  `docs/index.md` is its main page; there is no separate operation page.
