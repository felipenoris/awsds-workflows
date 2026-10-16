# User Instructions

Do not edit this section. You're free to edit all other sections of this file.

These are the instructions written by the user.

## Project Goals

The main goal is to build a utility Python package that packages Python libraries in the format the
tasks of an Amazon MWAA Serverless workflow expect, and renders the workflow definitions (the
pipelines) of a SageMaker Unified Studio project. The tools were created in the AWS-DataScience
repository, in the runbook `docs/plan/runbooks/serverless-workflows.md` and the scripts of
`examples/sandbox-orchestration/`, and this package isolates them.

- The package runs on Linux with internet access. What it generates is copied to the SageMaker
  environment, which has no internet access.

- A Python or Bash task (`PythonOperator`, `BashOperator`) receives its code as one `.zip` with every
  dependency at its root, built for the worker's interpreter and platform, without the packages the
  worker pre-installs.

- A SageMaker processing task runs in the image the job names, with no network: its code input is a
  folder holding the project and only the packages that image lacks, at the image's versions for
  everything they share.

- The job image is selectable: a custom image, or the SageMaker default image (currently 4.15). The
  target environment cannot create custom images yet, so the work starts with the default image.

- The projects are managed by `uv`.

- A workflow definition keeps every account-scoped value as a `<PLACEHOLDER>`; the render fills them
  with the project's values, and the reverse turns a definition the portal saved back into
  placeholders.

## References

- <https://github.com/felipenoris/AWS-DataScience/blob/main/docs/plan/runbooks/serverless-workflows.md>
- <https://github.com/felipenoris/serialize-db>
- <https://docs.aws.amazon.com/mwaa/latest/mwaa-serverless-userguide/operators-python-bash-detail.html>
- <https://docs.aws.amazon.com/sagemaker-unified-studio/latest/userguide/serverless-visual-workflows.html>
- <https://docs.aws.amazon.com/sagemaker/latest/dg/byoc-input-and-output.html>

# Guidelines

## Project

- This repo is a Python library.

- Use `uv` to manage the Python version and the dependencies.

- The package supports Python 3.12 or later (`requires-python`), and `tests.yml` tests 3.12, 3.13
  and 3.14; the repository's `.python-version`, the project venv and `docs.yml` use 3.13.

- Use `pytest` to write tests.

- Use [`pdoc`](https://pdoc.dev/) to generate the documentation as static HTML.

## Tools installed in the current environment

- `uv`

- `gh`

- `cargo`

- `git`

- `aws`

## git

When you need to commit in this repo, do it on a new branch prefixed with `claude/` and open a PR. While a PR you opened is still open, every new commit goes to that PR's branch; do not open another branch or PR. Submit your commits incrementally. The user will merge when needed. After the merge, sync the local copy of the repo to the `main` branch (sometimes the user will do that for you).

## AWS target environment

- The package runs on Linux with internet access, where `uv` reaches PyPI. What it writes is copied
  to the SageMaker environment, which has no internet access, and nothing is installed where the
  code runs.

- The SageMaker environment is the target that serialize-db's `SUITE_ALVO.md` refers to: SageMaker
  Unified Studio (Ubuntu Linux, amd64), with no internet and no proxy. Its readings are in
  `.claude/memory/environments.md`.

- A Python or Bash task runs on the MWAA Serverless worker: CPython 3.12 on Linux x86_64, with the
  packages the worker pre-installs, no internet and no proxy.

- A processing job runs the image it names, network-isolated: the SageMaker default image
  (SageMaker Distribution 4.5 at the start; the "4.15" of the user section is a typo, by the
  user's word of 2026-10-13) or a custom image.

- The lab where every step was measured is the AWS-DataScience Sandbox account (`us-west-2`), whose
  custom image is the house image `awsds-sandbox-dev-env`.

## Language convention (important)

All prose in this repo is **Brazilian Portuguese (pt-BR)**: README files, code comments, docstrings, printed output, test messages, and shell-script comments. When editing or adding content, keep writing in pt-BR to match.

Placeholder names (`<PROJECT_ID>`) and the keys of a workflow definition are code identifiers, in English.

Code identifiers (variable and function names) are in English.

This `CLAUDE.md` is in English, for AI-assistant tooling.

## `REFERENCES.md`

Record in this file every website you visit when searching for information.

## The documents that track the work

`.claude/memory/OPEN_QUESTIONS.md` is the only planning document the work keeps updated: it holds
the pending items, the doubts and the decisions waiting on the user, in pt-BR. Add an item when the
work finds a question it cannot close; remove it when the answer lands where it stays (the
docstring or test of the code it decides, `.claude/memory/decisions.md` or a theme file of
`.claude/memory/`), and name that place in the report. The repository has no `plan/` folder.

A new measurement goes, with its date, to the docstring or test of the code it justifies, to the
PR description and to its theme file in `.claude/memory/`. The measurements the tools were built on,
up to 2026-10-11, are in AWS-DataScience's runbook and in its stage log
`docs/log/log-stage-06i-sandbox-orchestration.md`, cited here by their dates.

## Chat

Chat with the user in Brazilian Portuguese. Tag your answers with [guess] or [uncertain] when you are not confident.

Challenge the user with questions when they propose something bad or wrong, or when you have a better idea.

Be direct and succinct.

## Writing style

These rules apply to every text in the repository: Markdown, code comments, and this file. The test for
a sentence is whether the reader does something with it. Facts, identifiers, measurements and their
dates, commands, quoted output and a log entry's provenance are never cut; the words around them are.

1. **A heading names its subject**, in the file's own vocabulary: "Account tree", "The identities the
   battery runs as". Not a label that needs the body to be understood ("The map"), and not a
   rhetorical tail ("and why each one is the one it is").
2. **No counts in headings or titles.** "The two identities", "Four rules for reading this picture",
   "ONE MATCHER, TWO INPUTS" go stale the day an item is added, and the number is not the information.
   Write "The identities", "Rules for reading this picture", "The DNS Firewall coverage matcher".
3. **Every sentence has a subject, headings included.** "True now, and expected to change" becomes
   "Readings a later stage changes".
4. **Lead with the subject**, then its status: "The WireGuard Elastic IP is not allocated here; it is
   transferred from Sandbox." Never a preamble that reveals the subject at its end ("WHAT IS NOT HERE,
   AND THE ABSENCE IS THE STEP AFTER THIS ONE: the WireGuard Elastic IP").
5. **No capitals for emphasis.** The plain sentence carries the same fact. Bold marks the one term a
   reader scans for, never a whole sentence.
6. **No revision artifacts in headings or prose.** Edit dates, "(revised 2026-08-17, by the user)",
   "row four, inverted", "REWRITTEN 2026-09-06", "the list grew one entry at step 3" belong to git
   history. A date stays when it dates a measurement.
7. **A code comment states what the code does and the constraint it obeys.** It does not narrate how the
   file got here, argue that something is "expected rather than a finding", or cite a lesson in place of
   the fact. A comment the reader of the code does not need is deleted.
8. **Delete what carries no information**: rhetorical connectives ("and that is the point", "which is
   the whole reason", "said out loud"), a second phrasing of the same fact, and a justification another
   document already records. One short sentence beats a chain of clauses joined by dashes.
9. **Shorter is the goal; a fact removed is a defect.** When a cut would drop a measurement, an
   identifier or a verdict, keep the sentence.

## Python Code Style

### Core principle

- When writing Python code, use [PEP 8 Style](https://peps.python.org/pep-0008/).
- Use docstrings to explain function interface and purpose.
- Add code examples when writing docstrings for public interface.
- Add comments for each logical block of code, explaining what you're doing.

IMPORTANT: prioritize code that is easy for humans to read and review over short or "clever" code.
Test: would a junior data scientist on the team understand this snippet in a single read? If not, simplify.

### Simplicity
- Write the minimum code that solves the requested problem. Nothing speculative.
- Do not add abstractions, classes, parameters, or configuration that were not requested.
- Prefer functions over classes. Use classes only when there is real state; prefer `dataclass` over inheritance hierarchies.
- Do not handle errors for scenarios that cannot happen.
- If the solution got long, look for a more direct version before delivering, or break it into subfunctions.

### Structure
- Short functions with a single responsibility and a name that describes what they do.
- Use early returns instead of nested `if`s; at most 2 levels of nesting.
- Break long expressions into intermediate variables with descriptive names.
- Prefer separate functions over one generic function controlled by boolean flags.
- Do not use bare `except:` or generic `except Exception` without re-raising.
- A function with at least one parameter declares one parameter per line, with a trailing comma, and
  `) -> T:` on its own line; `ruff format` keeps the layout through the trailing comma. `self`
  and `cls` do not count: a method with only `self` or `cls` stays on one line, like a function
  without parameters (serialize-db user decisions of 2026-10-01).

### Constructs to avoid
- Comprehensions with more than one `for` or a complex condition → use an explicit loop.
- `lambda` beyond trivial expressions → use a named `def`.
- Nested ternaries → use `if/elif/else`.
- Walrus operator (`:=`), `functools.reduce`, `map`/`filter` with lambda.
- Metaprogramming: metaclasses, custom decorators, dynamic `getattr`/`setattr`, monkey-patching.
- `from module import *`.
- One-liners that do several things at once.

### Names, types, and comments
- Descriptive names instead of abbreviations (`balance_by_account`, not `bba` or `df2`).
- Type hints on all function signatures.
- Short docstring on public functions: what it does, inputs, and output.
- Comments explain *why*, not *what*. Do not comment the obvious.

### Docstrings

The standard every public function, method and class follows (serialize-db user decision of
2026-09-24), which `pdoc` renders with `--docformat restructuredtext`:

- **Layout.** A summary line saying what the function does or returns, the behavior as prose, an
  `Exemplo:` block opened by `.. code-block:: python` (or `shell`) on the public interface, and the
  fields last, after a blank line.
- **Level tag.** Every docstring opens with `[public]`, `[protected]` or `[private]`, the level of
  the name it documents, before the summary (serialize-db user decision of 2026-10-11): a module by
  its package's `__all__` and the `_` prefix, a module-level name by the module's `__all__` and the
  prefix, a class member or attribute by its own prefix bounded by the class's level (a dunder takes
  the class's level, a nested function is private). A protected docstring names who uses it ("para
  os empacotadores") and does not say "protegida". A name public by the evaluation of its intended
  use opens with `[public] [uso do cliente]` ("Naming conventions"). `tests/test_package.py` checks
  every file of `src/awsds_workflows/`, the mark only after `[public]`.
- **Fields.** `:param name:` for every parameter pdoc shows, in signature order, except `self` and
  `cls` (`*parts` is `:param parts:`); `:return:` when the annotation is not `None`, and for a
  context manager what `with` gives, and never on a property, which pdoc shows as an attribute whose
  summary says what it holds; one `:raises Exc:` per exception the function raises deliberately,
  directly or through the package's own helpers: a package exception by its full name
  (`awsds_workflows.errors.RefusalError`), the only form pdoc 16 links to the class, a third-party
  one by its module (`subprocess.CalledProcessError`) and a builtin bare (`ValueError`). A
  third-party exception that only propagates stays out, unless the reader acts on it. pdoc reads
  only `param`, `return` and `raises`, and ignores `:returns:` and `:raise:`.
- **Field text.** pt-BR, starting lowercase and ending with a period: what the argument is, its
  unit, its accepted values and what `None` or the default means; continuation lines indent four
  spaces. The first line of a `:param` or `:raises` field holds no other colon, a quoted `s3://`
  included, because pdoc 16 reads the name up to the last colon of that line.
- **One place per fact.** A sentence about one argument, the return or one exception lives in its
  field, not in the prose too; the prose keeps what the function does as a whole, and a moved
  sentence keeps every identifier, number and date.
- **Constructors and attributes.** A dataclass documents its constructor by one docstring per field,
  a string right after the field; a regular class documents its arguments in the `__init__`
  docstring, and each public `self.x` gets a docstring right after the assignment. A
  `typing.Protocol` says in its class docstring that the `(*args, **kwargs)` pdoc shows is the
  `__init__` of `typing.Protocol`.
- **Checks.** Every line stays within 100 characters, and the built site is read as the working
  rules ask: a misread field shows as a bold name holding a colon, which
  `grep -o '<strong>[^<]*:[^<]*</strong>'` over the built HTML finds, or as literal `**` opening
  a list item, which `grep -rn '<li>\*\*'` finds.

### When editing existing code
- Follow the style of the surrounding code, even if you would prefer another.
- Change only what the task requires; do not refactor unrelated code.
- If you notice improvements outside the scope, mention them instead of changing them.

## `secrets/`

Never read the contents of the `secrets` folder.

# Claude Memory

Use this section to store your memory for this project. Keep this file within a size budget of 75 KB.

## How this memory is organized

This file is loaded whole into every session, so it holds what every session needs: the index of the
repository and of the memory files, the working rules, the naming conventions and where the work stands.
The facts, the stories and the pending items live in `.claude/memory/`, one file per theme, read on
demand with the Read tool and never imported with `@`, which would load them all. Each theme file
opens with when to read it, and a fact that a file of the repository details ends with that file.
A fact found in a session is appended to its theme file; this file changes when a rule, a
convention, an index entry or the state of the work changes. The budget above is never a reason to
drop a fact: what does not fit here goes to a theme file.

| Memory file | Read it before |
| --- | --- |
| `.claude/memory/decisions.md` | Changing an interface or a behavior, or answering a "why": what the user stated and decided, with dates, and the design choices of the first session that wait on the user's confirmation. |
| `.claude/memory/OPEN_QUESTIONS.md` | Planning a session, or when the work finds a question it cannot close: what has no answer yet (pt-BR), one item per pending question, with the run or the decision that will close it. |
| `.claude/memory/lessons.md` | Adding a lesson, or when the reason behind a working rule matters: the dated stories of this repository; the stories of the rules carried from serialize-db are in serialize-db's `.claude/memory/lessons.md`. |
| `.claude/memory/environments.md` | Running anything in the lab or the target, or dating a measurement: the build host, the AWS-DataScience lab, the serialize-db target and its network readings, the images. |
| `.claude/memory/packaging.md` | Code on `package_task`, `package_job` or `_uv`: the worker, the job's folder, the `uv` behaviors the code relies on, and the verification of the port against the original scripts. |
| `.claude/memory/cicd-cli.md` | Code on the manifests of `examples/`, on the CLI's notation in `render` or `compare`, or a `deploy` of an example: what the CI/CD CLI `aws-smus-cicd-cli` 1.0.9 does, its variables and its commands, and what each did in the lab on 2026-10-15 and 2026-10-16. |

## Repository index

Read the file listed here before researching its subject again. `REFERENCES.md` collects every URL
consulted so far, grouped by subject.

| File | Subject |
| --- | --- |
| `README.md` | The minimum: the two workflow badges, the requirements (Linux with internet, `uv`, Python 3.12 or later, `aws` only for the account reading), the installation by git URL (never by name: the name is free on PyPI, read 2026-10-11) and its upgrade with `uv tool upgrade awsds-workflows`, the examples section pointing at `examples/` and at the page `awsds_workflows.examples`, and the development commands: `uv sync --all-groups`, `uv run pytest` (`-m "not network"` skips the tests that need PyPI), the Ruff check, the `pdoc` build with `-t docs/theme` and the tests on another Python with `uv run --isolated --python`. |
| `docs/index.md` | The package documentation for `pdoc`, included by the docstring of `src/awsds_workflows/__init__.py`, in pt-BR: AWS-DataScience's runbook `serverless-workflows.md` adapted to the package. It names no external project: AWS-DataScience's provenance is in `.claude/memory/decisions.md` ("The documentation") and its links in `REFERENCES.md`. It is written for a reader who uses a SageMaker Unified Studio project and does not know the Airflow or the MWAA: each term is introduced where it first appears, and the vocabulary is "espaço" and "ambiente alvo" (user request of 2026-10-12). A procedure is numbered steps, each command in its own block; warnings, errors and restrictions are GitHub alerts (`> [!WARNING]` and the other kinds); the lab's dates and readings are on the page `awsds_workflows.lab_notes`, and a section keeps a `> [!NOTE]` with its state (`**Estado**: ...`) and a link to its notes (user's choice of 2026-10-16, "The documentation" in `.claude/memory/decisions.md`). Sections: the opening (who it is for, the problem it solves, the commands, the pages), "Início rápido" (one Python task from the project to the run, then what to read next), the concepts (the workflow and its definition, the task types and where each runs, the worker, why the code is packaged, the lab against the target), installation (`uv tool upgrade` to follow `main`, and the Python `uv` uses, `UV_PYTHON` in a space), the pieces, the job image (default SageMaker Distribution 4.5 or custom, and what changes: `JOB_IMAGE_URI`, `JOB_PYTHON`, `--python`, the environment file), the project's permission (the IAM policy JSON), the network (the endpoints the worker and the job used in the lab, and the target's readings), authoring rules (the YAML format AWS defines, with its page), a processing task (the environment's demands, `package-job` step by step, refusals, the project folder prepared in a `.tar.gz` with its own interpreter by `prepare-offline`, step by step with its refusals, a full example definition), a Python or Bash task's code (`package-task` with `--include`, the archive, the Python task's definition, the `.zip` in the workflow, by hand), a Bash task (a table against a Python task, the command, the worker's environment, the `Code`, the archive's code in the command), the definition's values (`render`, `values`, the placeholder table, the CI/CD CLI's variables and what `render` reads in their place, `compare` against the definition the portal saved, a CLI workflow included), reading a run back, cleaning up. Anchors are pdoc's ASCII slugs (`#a-imagem-do-job`). The opening, the quickstart and the section "Os exemplos" point at the page `awsds_workflows.examples`. |
| `docs/laboratorio.md` | The page `awsds_workflows.lab_notes` of the `pdoc` site, included by the docstring of the docstring-only module `src/awsds_workflows/lab_notes.py`, by the user's choice of 2026-10-16: what ran in the lab, in the target and on the packaging machine, with the date of each reading, and what has not been measured yet. It opens with the environments (the lab, the target, the packaging machine) and the list of what waits on a measurement; each section has the heading of the guide's section it serves and opens with a link back to it (`No guia:`, or `Nos passos:` for the examples, last), and each bullet opens with the place and the date in bold (`**Laboratório, 2026-10-11.**`, `**Ainda não medido**:`), with no colon inside the bold so the misread-field grep stays clean. A new measurement that the documentation reports goes here, and the guide's `**Estado**` line changes with it. |
| `docs/exemplos.md` | The page `awsds_workflows.examples` of the `pdoc` site, included by the docstring of the docstring-only module `src/awsds_workflows/examples.py` (the way serialize-db's `technology_review.py` includes a page), by the user's request of 2026-10-13: the examples of `examples/` as a procedure, in the order the commands run, each step saying where it runs ("na máquina que empacota", "no espaço", "no portal"), with the exact commands, what each prints and what to check, in the direct style of the chat that exercised them; since 2026-10-16 each section is numbered steps with each command in its own block, warnings as GitHub alerts, and a `> [!NOTE]` with the example's state and a link to its notes on `awsds_workflows.lab_notes`, which holds the dates of the runs. Sections: the preparation (the package and the CLI installed, the two files that go to a space, `space_values.py`, the `mount` check of `~/shared/`, the shell variables the manifests read, `DOMAIN_ID`, `DOMAIN_REGION`, `DEV_PROJECT_NAME` and `TEST_PROJECT_NAME`, and the credential exported from the profile), the application by the CI/CD CLI, shared by every example (the manifest's form, `describe`, `deploy --targets dev --skip-validation --no-events`, `run`, the reading with `get-workflow-run` and `get-log-events`, `bundle` and `deploy --targets test` over the bundle, the portal read-only), the portal steps (the `render` of the CLI's workflow with `space_values.json` and, where a value to fill exists, `extra_values.json`, then the import), one section per example (`probe-worker`, `demo-python-operator` and `demo-bash-operator` with the `.zip` `package-task` writes into `code/`, `demo-devenv-job` with the `.tar.gz` `prepare-offline` writes into `src/` and the job's network and image as stage variables, `redshift-unload` with the `.zip` of the module by `zipfile`, the three names as stage variables and the `GRANT`, `houseprice-etl` with the Parquet, the job created once with `job.json` and the subnets as stage variables), cleanup. It links into the main page with `../awsds_workflows.html#<anchor>` and into the notes with `lab_notes.html#<anchor>`; the per-example READMEs link to it with `awsds_workflows/examples.html#<exemplo>`. |
| `docs/theme/` | The `pdoc` template directory, passed with `-t docs/theme` by `docs.yml` and the README: `theme.css` and `syntax-highlighting.css`, which pdoc reads in place of its own files of the same name, and `custom.css`, which pdoc includes after its own CSS: the colors of the alerts (`> [!NOTE]`, `[!TIP]`, `[!IMPORTANT]`, `[!WARNING]`, `[!CAUTION]`), which pdoc's `content.css` draws light, each with a translucent background, its color on the left border and pdoc's own icon recolored by Jinja's `replace` and `urlencode` filters, as `content.css` includes it. The site is always dark, by the user's choice ("The documentation" in `.claude/memory/decisions.md`): the colors of pdoc 16.0.0's `dark-mode` example, with `color-scheme: dark` so the browser draws the search box and the scrollbars dark, and Pygments 2.21.0's `monokai` for the code, generated with `pygmentize -f html -a .pdoc-code -S monokai`. pdoc includes the files as Jinja templates, so a `{#` or `{{` in them breaks the build (`TemplateSyntaxError`, probed 2026-10-12), and its minifier strips their comments. |
| `.github/` | `tests.yml`, on Ubuntu only (the package runs on Linux) with Python 3.12, 3.13 and 3.14 (the `python-version` of `setup-uv` over `.python-version`), imports every module after `uv sync --no-dev` and runs `awsds-workflows --help`, then `ruff check`, `ruff format --check` and the whole `pytest` suite, network tests included, on push to `main`, on pull request and by hand; `docs.yml` publishes the `pdoc` site, with the colors of `docs/theme/` (`-t`), to <https://felipenoris.github.io/awsds-workflows/> on push to `main` (the repository's Pages source is "GitHub Actions": `build_type` `workflow` in `gh api repos/felipenoris/awsds-workflows/pages`, read 2026-10-12). |
| `src/awsds_workflows/` | The package: `errors.py` (`RefusalError`, the one exception, which the CLI prints and turns into exit 1), `_uv.py` (private: `run`, whose `env` completes the process environment for one call, `export_closure`, `install_requirements`, `build_pure_wheel`, `install_wheels`, `remove_leftovers`, the protected helpers of the packagers, and the private `_install_arguments`), `package_task.py` (`build_archive`, whose entry module is optional and whose `include` puts the files a Bash task calls at the root, `TaskArchive`, `WORKER_PYTHON` 3.12, `WORKER_PLATFORM` `x86_64-manylinux2014`, `WORKER_PROVIDED`, `ARCHIVE_LIMIT_BYTES` 250,000,000), `package_job.py` (`build_folder`, `environment_versions`, `JobFolder`, `JOB_PLATFORM` `x86_64-manylinux_2_28`; the private parser `_read_pins` refuses any line that is not `name==version`), `prepare_offline.py` (`prepare_archive`, `OfflineArchive`, `DEFAULT_PYTHON` 3.12: the `.tar.gz` of a uv project folder synced on a temporary copy with `uv sync --locked --no-dev --no-editable` and the CPython `uv` downloads into `.python/`, every link relative, the root the folder's name, the owner 0/0, proved by extraction before it replaces an existing archive; refuses any platform but Linux x86_64 before any download; `_system` is the seam the tests replace), `render.py` (`fill_placeholders`, `restore_placeholders`, `translate_cli_variables`, `load_values`, `read_values`, `PLACEHOLDER`, `CLI_VARIABLES`; a value may reference other placeholders, resolved one level by the private `_resolve_values` before either path, and a value that references a placeholder without a value, or itself, is refused as missing, which makes `"NAME": "<NAME>"` a value to fill in a model file; a file in the CI/CD CLI's notation is translated before the fill, each variable of `CLI_VARIABLES` (`{proj.id}`, `{proj.iam_role_arn}`, `{proj.connection.default.s3_shared.s3Uri}` and its `.bucket`, `{domain.id}`, `{domain.region}`) by its expression with placeholders and `{env.NOME}` by `<NOME>`, and a variable outside the table is refused; `_run_aws` is the seam the tests replace), `compare.py` (`compare_definitions`: two definitions read with PyYAML's `safe_load`, the CLI's variables and `{{ params.NOME }}` normalized to placeholders on both sides, the differences of content as `-`/`+` lines), `lint.py` (`lint_definition`, `lint_application`, `Finding`, `Report`: the rules of an application of the CI/CD CLI, by name, `forma`, `projeto`, `datas`, `operador`, `limites`, `imagem`, `job`, `templates`, `codigo`, `glue` and `manifest`, in the authoring mode over the repository's files in the CLI's notation and in the promoted mode over a rendered copy; the limits of the service's pages read 2026-10-16, the job's `MaxRuntimeInSeconds` capped at 2,820 s, a chosen margin; `lint_application` reads the files as the CLI 1.0.9 does, and the prefixes of the `codigo` and `glue` rules are the folders every stage copies), `examples.py` (docstring only: the page `awsds_workflows.examples`, which includes `docs/exemplos.md`; `__all__` empty), `lab_notes.py` (docstring only, the same way: the page `awsds_workflows.lab_notes`, which includes `docs/laboratorio.md`) and `cli.py` (`awsds-workflows package-task [--include]`, `package-job`, `prepare-offline [--python]`, `job-constraints`, `render [--placeholders]`, which takes a file with placeholders or in the CLI's notation, `values`, `compare`, `lint [--promoted] [--prefix] [--instance-type] [--image-repository]`, which prints each finding on a line and exits 1, or `ok` with the files read, with `--promoted` asking for `--prefix` and refused on a folder, with `--values-file` repeatable on `render` and `values`, each file over the account's reading and the files before it; only `main` public). What each does is in the docstrings; `pyproject.toml` holds the runtime dependencies (`packaging>=24` and `pyyaml>=6`, floors so the package installs beside an environment that pins its own), the `dev` (with `boto3`, for the examples' tests) and `docs` groups, the `network` marker, the `testpaths` and `pythonpath` that reach into `examples/`, and `[tool.ruff]`. |
| `scripts/space_values.py` | Outside the package, run in a project space with the space's Python: prints the JSON of `values` without `--image-name` through the SDK `sagemaker-studio`. `Project()` gives `PROJECT_ID` and `DOMAIN_ID`; the other values come from the default Tooling environment (`SageMakerStudioAPI().project_api.get_project_default_environment` and DataZone's `GetEnvironment`): `awsAccountId`, `awsAccountRegion` and the provisioned resources `userRoleArn`, `s3BucketPath`, `kmsKeyArn`, `securityGroup` and `privateSubnets`. A missing value exits 1 without JSON, and an SDK or DataZone failure propagates as a traceback. The SDK is imported inside `_read_tooling_environment`, the seam the tests replace; `pythonpath = ["scripts"]` in `pyproject.toml` puts the script on the tests' `sys.path`. Its facts are in `.claude/memory/environments.md` ("The project space"). |
| `examples/` | The example workflows, one folder each, every one an application of the CI/CD CLI `aws-smus-cicd-cli` 1.0.9 (the user's answers of 2026-10-16, "The examples as applications" in `.claude/memory/decisions.md`): `manifest.yaml` at the root, the workflow in `workflows/<exemplo>.yaml` in the CLI's notation (`{proj.*}` and `{domain.*}` for the project's values, `{env.NOME}` for what no project holds, declared as a stage variable in both stages), the tasks' sources in `code/`, where `package-task` writes the `.zip` the storage item `code` uploads and the workflow's `code` names, `src/` in `demo-devenv-job`, empty in git, where `prepare-offline` writes the `.tar.gz` of the job's code input, `glue/` in `houseprice-etl` with the job's script, and a pt-BR `README.md` that says what the example shows, task by task, its manifest and what each run read; the steps are the page `docs/exemplos.md`, which every README links to; `examples/README.md` indexes them (the table with where each ran, the shared project, the prefix, the tests). The prefix of an example in the project's bucket is the literal `exemplos/<exemplo>` after the `s3Uri` of the connection `default.s3_shared`, the project's `shared/` folder, where `deploy` copies the manifest's folders. The manifests name no `connectionName` on the storage items, so `bundle` and `deploy` read the folders from disk beside the manifest; they read `${DOMAIN_ID}`, `${DOMAIN_REGION}`, `${DEV_PROJECT_NAME}`, `${TEST_PROJECT_NAME}` and each stage variable as `${NOME}` from the shell, and run `workflow.create` in both stages and `workflow.run` with `trailLogs: true` in `test`, since `wait: true` crashes the 1.0.9. `awsds-demo-job/` is the uv project the three `demo-*` share (`uv_build`, `petl==1.7.28` and `six==1.16.0`; a CSV in, a JSON summary out, `python -m awsds_demo_job` for the job and `python -m awsds_demo_job.s3` for the worker, with the inbox and the outbox as the `s3://` URIs the CLI gives; its own `tests/`), `demo-python-operator/` (`code/demo_tasks.py`, the entry module, which prints the interpreter, `sys.path`, the credential and where `petl`, `six` and `yaml` come from), `demo-bash-operator/` (`code/probe.sh`, `code/reach_pypi.sh`, four tasks), `demo-devenv-job/` (the job on the default image, no KMS key, the network and the image as stage variables; the code input is one object, the `.tar.gz` of the project folder that `prepare-offline` writes from `awsds-demo-job/` into `src/`, which the job's command extracts on the volume and runs with its own `.venv/bin/python`), `probe-worker/` (inline, no `code`), `redshift-unload/` (`code/redshift_unload.py`, the Data API `UNLOAD` with the worker's credentials; its `.zip` is built with Python's `zipfile`, since the module needs only the worker's `boto3`; the three names `REDSHIFT_WORKGROUP`, `REDSHIFT_DATABASE` and `REDSHIFT_TABLE` as stage variables) and `houseprice-etl/` (a Visual ETL job of the target: the task `GlueJobOperator` creates or updates the Glue job `houseprice-etl-{proj.id}` and runs it, with the whole `Command` in `create_job_kwargs` and `update_config: true`; `job.json` is its `CreateJob` input in the CLI's notation, to create the job once by hand where the project role's policy refuses `glue:GetJob` on a job that does not exist yet; with the `glue:GetJob` grant on the jobs no project holds the operator creates it (lab, 2026-10-16, both); the subnets are `{env.SUBNET_AZ1}` and `{env.SUBNET_AZ2}`; no data ships, and the steps convert `sample.csv` to Parquet in a space). The portal is the other path: `render` translates the CLI's variables and fills the workflow with `space_values.json` and, in `demo-devenv-job` and `redshift-unload` only, with the model file `extra_values.json`, whose values to fill (`SMD_REGISTRY_ACCOUNT` and the `JOB_IMAGE_URI` built from it, the three `REDSHIFT_*`) are each `"NAME": "<NAME>"`, which the render refuses until filled. What `package-task` and `prepare-offline` write in `code/` and `src/`, and the CLI's bundle in `artifacts/`, stay out of git (`.gitignore`). The target's org names and the user's folder are placeholders here. |
| `tests/` | `conftest.py` (`write_project`: a pure uv project in `tmp_path`, locked with `uv lock`), `test_package.py` (the level tags and the public submodules, copied from serialize-db), `test_uv.py` (with `run`'s `env` over a project that asks for a Python the machine lacks), `test_package_task.py`, `test_package_job.py`, `test_prepare_offline.py` (the refusals before any download, over a double of `_system`, a refusal that leaves the old archive, and, `network`, the archive's root, links and owner and the extracted folder run elsewhere without `uv`), `test_render.py` (the values that reference placeholders, the CLI's variables translated and one outside the table refused, the account reading over a fabricated `aws`, AWS's example account `111122223333`), `test_compare.py` (a saved definition that repeats the portal's re-serialization measured in the lab, a CLI workflow against what the CLI deployed, with `{{ params.NOME }}`), `test_cli.py` (doubles of the package functions, real refusals), `test_lint.py` (one failing case per rule over fabricated definitions and applications in `tmp_path`, a fabricated definition and application that pass, a promoted copy that passes, every application of `examples/` passing in the authoring mode with its files read, and the rendered `demo-devenv-job` in the promoted mode refusing only what the per-account translation changes), `test_examples.py` (every workflow of `examples/*/workflows/` rendered with the CLI's variables translated and fabricated values and parsed, the placeholder sets, the refusal while a value to fill is as it came, the files under `exemplos/<exemplo>/`, the Bash scripts without Jinja delimiters, `demo_tasks.run` and `redshift_unload.unload` over doubles and `botocore.stub.Stubber`, both archives built from the shared project and the job's `.tar.gz` prepared and run extracted elsewhere, `network`; every manifest against its workflow: the folder's name and its workflow, the storage items copied under `exemplos/<exemplo>/` in both stages, every stage variable of the workflow declared in both, `workflow.create` in `dev` and `workflow.run` with `trailLogs` in `test`, the files the workflow reads where the manifest copies them, the `.zip` of `code/` as the `code` where a task has one; for `houseprice-etl`, `job.json` is the task's `CreateJob` with the whole `Command`, and the Glue script runs over doubles of `awsglue` and `pyspark`) and `test_space_values.py` (a double of `_read_tooling_environment`, and the script with the real SDK in a subprocess against a local DataZone server, skipped without `sagemaker-studio`, which the project does not install: `uv run --with sagemaker-studio pytest tests/test_space_values.py`). The `network` tests lock and build real projects and need PyPI. |

## Working rules

Each rule is distilled from a lesson. The rules carried from serialize-db keep their dates, and their
stories are in serialize-db's `.claude/memory/lessons.md`; a lesson learned here adds its story to
this repository's `.claude/memory/lessons.md` and its rule here, in the same commit.

- **A tool moved out of the lab takes every lab-specific input as an argument**: the house image's
  lock path, the subnet name pattern and the image name became `--environment`, `--subnet-name` and
  `--image-name`, and the lab's value went to the documentation as an example (2026-10-11).
- **A ported tool is verified against the original on the same input before it replaces it**: build
  one project with both, diff the file lists and the contents, and explain each difference
  (2026-10-11; serialize-db's "a validated instrument is refactored against its own report").
- **A lab fact the documentation repeats is read against the lab's stage log before an answer or a
  change relies on it**: AWS-DataScience's `docs/log/log-stage-06i-sandbox-orchestration.md` kept
  measuring after `docs/index.md` was ported, and the page said the `.zip` was blocked the evening
  the lab ran one (2026-10-11); a rewrite of the page reads each "Estado no laboratório" line and
  each "não medido" against that log first, since keeping every fact keeps the stale ones too
  (2026-10-12).
- **A documented behavior becomes a test assertion only after a probe reproduces it**: run a ten-line
  probe first, assert the observed value, record the rest in the session report (2026-09-19).
- **A claim of "writes nothing" or "needs nothing" is verified in a stripped environment**: no `AWS_*`
  and no proxy variables, proxies pointed at a closed port, an empty `HOME` for the subprocess (2026-09-19).
- **A script that resolves paths by pattern runs on both platforms before it is trusted**; it stops when
  the pattern matches nothing. macOS has no `timeout` command: time a subprocess from Python (2026-09-19).
- **Nothing unpinned enters the project venv**: try a package in a scratch venv, read the versions
  after any install, restore with `uv sync --all-groups` (2026-09-19, 2026-09-23).
- **The pytest layout has no `__init__.py`**: `tests/conftest.py` is imported as `conftest` and its
  folder lands on `sys.path`, so `from conftest import write_project` works; module basenames stay
  unique across `tests/`.
- **Before a commit**: `uv run pytest` green with the `AWS_*` variables removed (`env -u
  AWS_ACCESS_KEY_ID -u AWS_SECRET_ACCESS_KEY -u AWS_SESSION_TOKEN -u AWS_PROFILE
  AWS_EC2_METADATA_DISABLED=true`), because the GitHub runner has none (2026-09-24); `uv run ruff
  check` and `uv run ruff format --check` clean (2026-10-01); the `pdoc` site built and read for
  misread fields; every `](...md)` link target checked; `git status` clean of stray files; this file
  under budget; `git branch --show-current` a `claude/` branch whose PR is still open (`gh pr view
  --json state`), because the user merges between turns, and a merged PR means a new branch
  (2026-09-21).
- **Git and shell traps**: after `git mv`, add the new path; in zsh, quote `--include=*.md`, run a command
  held in a variable as `${=command}`, and never pass `====` to `echo` (it is `=command` expansion,
  hit again on 2026-10-11); a Bash result above about 50 KB goes to a file; read long documents in
  `sed -n` ranges; `awk 'length > 100'` counts bytes under mawk, so a line-length check over pt-BR
  text runs in Python (2026-10-16).
- **Restructuring a document is a scripted splice followed by checks**: list the headings, grep for
  references to the removed sections and for stale identifiers, test every link target; when trimming or
  moving memory, list the backticked spans and numbers of the old text missing from the new one, because
  a fact removed is a defect (2026-09-19).
- **A change the user did not ask for is named in the report**, and a rule proposed without confirmation
  is marked as awaiting it.
- **A variable set to the empty string is not absent**: render `(vazia)` apart from `(ausente)`, restore a
  variable to the value found instead of removing it, run the failing case and the fix side by side
  (2026-09-20).
- **A probe's inputs must separate the hypotheses**: pick values whose outcomes differ per hypothesis
  before wording a rule (2026-09-20); here, a compiled dependency (`charset_normalizer`) is what tells a
  build for the worker from a build for this machine.
- **A section moved between files carries its deixis**: grep the moved block for "abaixo", "acima",
  "este", "desta" and "seção", and turn each reference that now crosses files into a link (2026-09-20).
- **A read-only claim over the user's data is proved by a copy and a `diff -r`**, plus a grep for `open(`,
  `write`, `mkdir`, `unlink`, `remove` and `rmtree`; a fixture carries the defects the tool must find
  (2026-09-20).
- **A documented phrase is read two ways until something runs**: write the plainest reading, mark the
  other in `.claude/memory/OPEN_QUESTIONS.md`, grep the repository before calling a question open,
  and grep tables and lists when a fact changes (2026-09-20).
- **The environment's sensitive identifiers never enter git**: the repository is public; accounts,
  DataZone ids, subnets, security groups, KMS keys and buckets that carry an account id stay out of
  every file, a definition keeps them as placeholders, and the tests use AWS's example account
  `111122223333` (serialize-db's masking rule of 2026-09-23).
- **A script the user ran in the target outranks a design written without one**: AWS-DataScience's
  measured runs are the reference the package repeats (2026-09-20, 2026-09-21).
- **A memory that hits its ceiling is split, not trimmed**: a fact goes to its theme file in
  `.claude/memory/`, and this file changes only when a rule, a convention or an index entry changes
  (2026-09-21).
- **A state change is confirmed by the effect the caller depends on**, never by a system function
  believed to report it (2026-09-21).
- **`secrets/` stays unread unless the user names a path inside it**, and nothing read there is copied
  into git (2026-09-21).
- **A document revision reads every section against the decisions memory**: grep the documents for
  the old rule's vocabulary after the decision lands, and read the tables that index names
  (2026-09-21).
- **A draft calls every input kind its signature accepts** (2026-09-21).
- **A generated file is generated twice and diffed before a test asserts it equal to its versioned
  copy** (2026-09-21).
- **`uv` resolution needs every configured index reachable**: an index the workflows cannot reach
  stays out of the repository, and an empty `UV_CONFIG_FILE` is the way to ignore a `[tool.uv]`
  section when one must (2026-09-21).
- **A comparison between two designs runs both under the same conditions** (2026-09-22).
- **A verdict measured on a draft is measured again after a decision changes the draft's output**
  (2026-09-22).
- **A library's warning is a reading, never a guard**: guard on the state the library exposes
  (2026-09-22).
- **A requirement is measured in the user's own words before it is reported kept**, and a weaker form
  is reported as weaker (2026-09-23).
- **A checkout may be shared with another session**: read `git status -sb` and `git reflog -5`
  before creating a branch or committing, add files by path, and agree by message on the order of
  edits to files two sessions touch (2026-09-23).
- **Every behavior a docstring promises has an assertion that fails without it**: run the new
  assertion against the old code before trusting it (2026-09-23).
- **A secret is masked where it leaves**: the printed lines and the reports go through the mask
  (2026-09-23).
- **A hook that selects tests by suite reads the marker, never `item.keywords`**, which also holds
  every parameter id (2026-09-23).
- **A test that runs a default which writes points the default at the authorized root first**
  (2026-09-23).
- **A compatibility the library claims is run against an instance of it** (2026-09-23): the
  worker's platform tag is asserted on the archive's compiled modules, never on the flag passed.
- **A routine the runbook asks the operator to size prints its own measure**: `package-task` and
  `package-job` print the size, the target and the top level (2026-09-24).
- **A long-running script writes its report as it goes** (2026-09-24).
- **A documentation convention is checked in the rendered page as well as in the source**: build
  the pdoc site and read the fields it renders; a misread field renders as a bold name holding a
  colon or as literal `**` opening a list item (2026-09-24, 2026-10-11).
- **A diff is split into commits from an empty index**: read `git diff --cached --stat` before each
  commit (2026-09-24).
- **A test double of a library function forwards `**options`**: before changing how a function is
  called, grep the tests for `monkeypatch.setattr(<module>, "<function>"` (2026-09-24).
- **One condition per `assert`** (2026-09-24).
- **A test double calls the original through a reference saved before the swap, and a failure
  case matches its own message and asserts that its double ran** (2026-09-28).
- **A double that leaves before the test ends enters through `monkeypatch.context()`**:
  `monkeypatch.undo()` in a test body also undoes the patches of the fixtures that share the
  test's `monkeypatch` (2026-10-10).
- **A date read from git history is checked for a shallow clone**: read
  `git rev-parse --is-shallow-repository` (2026-10-11).

## Naming conventions

Python variables, functions, parameters, modules and the API are English. Each module separates
three levels of name: public, the interface client code imports, which `pdoc` documents; protected,
used by another module of the package; private, used only inside its module. A name is public when
the evaluation of its intended use finds that the package's users call, build or read it; a type a
public function returns is public too (`TaskArchive`, `JobFolder`). A name that evaluation made
public, which the code that calls it would leave protected or private, carries the mark
`[uso do cliente]` right after its level tag. The module's `__all__` lists the public names and only
those; protected is unprefixed, private carries the `_` prefix, and every docstring opens with its
level's tag ("Docstrings"). The package's `__all__` lists its public submodules, the only ones
`pdoc` documents; `_uv` is private and holds protected functions.

One module per tool, named after what it builds: `package_task` builds the task archive
(`build_archive`), `package_job` the job folder (`build_folder`), `prepare_offline` the `.tar.gz` of a project
folder prepared with its own interpreter (`prepare_archive`, the user's own name for the
procedure, from the `prepare_offline.sh` of serialize-db), `render` fills and restores the
placeholders, `compare` compares two definitions (`compare_definitions`), `lint` checks an
application or a definition against the rules (`lint_application`, `lint_definition`), each
rule named by a lowercase pt-BR word without accents (`codigo`) that the finding prints. A CLI
subcommand is kebab-case and names the module's job (`package-task`, `package-job`,
`prepare-offline`, `job-constraints`, `render`, `values`, `compare`, `lint`). A placeholder is
`<NAME>` in upper case (`PLACEHOLDER` in
`render`), English, and generic: `ACCOUNT_ID`, not `SANDBOX_ACCOUNT_ID`;
`JOB_IMAGE_URI` and `JOB_PYTHON` describe the job's image whatever it is. A variable the package
requires starts with `AWSDS_WORKFLOWS_`; none exists today, and the package reads no configuration
file: the CLI takes explicit arguments. A test may read and replace the private names of the module
it tests (`render._run_aws`, `package_task._write_archive`), the seams the interface hides on
purpose (serialize-db user decision of 2026-10-11).

## Where the work stands

The first session (2026-10-11, from the AWS-DataScience repository) created the package on branch
`claude/package-structure` and its PR: the three tools of AWS-DataScience's runbook ported to
`package_task`, `package_job` and `render`, the CLI, the tests, the CI, the `pdoc` documentation
(`docs/index.md`, the runbook adapted in pt-BR) and this file. The port was verified against the
original scripts on the project the lab measured (`.claude/memory/packaging.md`). In the lab, a
`.zip` built by hand ran in a Python task on 2026-10-11, once the S3 gateway endpoint admitted the
service's code bucket (`.claude/memory/environments.md`).

A session on branch `claude/bash-operator-hchepx` (2026-10-11) gave `package-task` `--include` and
an optional entry module, by the user's decision ("The Bash task" in `.claude/memory/decisions.md`),
and brought `docs/index.md` to the lab's readings of that day, with a section on the Bash task.

A session on branch `claude/values-script-sagemaker-jacgnb` (2026-10-11) wrote
`scripts/space_values.py`, which reads the values inside a project space through the SDK
`sagemaker-studio`, by the user's choices ("The values read inside a space" in
`.claude/memory/decisions.md`). It ran in a lab space on 2026-10-11 and printed the same JSON as
`values` on the same account (`.claude/memory/environments.md`, "The project space").

A session on branch `claude/docs-self-contained-ddz04c` (2026-10-11 and 2026-10-12) took
AWS-DataScience out of the documentation (PR #2), removed its section on the state of the work
(PR #3), and pointed the authoring rules at AWS's page on the YAML format and added `compare`,
with PyYAML (PR #7), by the user's decisions (`.claude/memory/decisions.md`, "The documentation"
and "The comparison of definitions").

A session on branch `claude/deps-findings-szsjhp` (2026-10-11 and 2026-10-12) brought
`docs/index.md` to AWS-DataScience's PR #110, a processing job over a uv project with dependencies,
and documented uv's own `UV_PYTHON` for a space where uv finds no Python the project accepts, by the
user's choice ("The findings of AWS-DataScience's PR #110" in `.claude/memory/decisions.md`). The
package's code did not change; `package-job` wrote the lab's folder in a simulated space
(`.claude/memory/packaging.md`, "The interpreter `uv` needs").

A session on branch `claude/review-docs-code-2aux2x` (2026-10-12) rewrote `docs/index.md`, the
README and the module docstrings for a reader learning to build workflows, by the user's request
("The documentation" in `.claude/memory/decisions.md`), keeping every section, anchor, fact and
date. The code review of the same request, for the Python standards and simplicity, is the second
commit of the same PR, with no change of behavior or CLI: the `uv export` and the `uv pip install`
prefix of both packagers in `_uv`, `build_folder` in named steps, and the outputs of the old and
the new code compared on one project (`.claude/memory/packaging.md`).

A session from the AWS-DataScience repository (2026-10-12, branch
`claude/aws-datascience-adoption`) moved AWS-DataScience's workflow guidance onto the package (its
PR #113, which deletes its three scripts) and recorded the user's decisions on it, the package
installed from `main` among them ("AWS-DataScience adopts the package" in
`.claude/memory/decisions.md`). It measured the package at `937a66a` and `3499530` against the
original scripts on the lab's files (`.claude/memory/packaging.md`), corrected `docs/index.md` on
an import over a saved workflow from the lab's stage log, and added `uv tool upgrade` to the
installation, measured (`.claude/memory/environments.md`, "The build host").

A session on branch `claude/runbook-followup-r95ohb` (2026-10-12) checked what else the adoption
called for, by the user's request ("AWS-DataScience adopts the package" in
`.claude/memory/decisions.md`). No behavior changed, since everything AWS-DataScience's runbook
quotes exists here; `docs/index.md` and the docstrings of `package_task` were brought to the
lab's stage log on the Bash task over a `.zip`, one worker per task, a code snapshot per save,
errno 16, `compare` over the saved definitions and the inbox consumed one drop at a time
(`.claude/memory/environments.md`).

A session on branch `claude/pdoc-dark-mode-ud3zoq` (2026-10-12) made the `pdoc` site always
dark, by the user's choice ("The documentation" in `.claude/memory/decisions.md`): the colors
are in `docs/theme/`, which `docs.yml` and the README pass with `-t`. The package's code did not
change.

A session on branch `claude/target-examples-lg273m` (2026-10-12) began exercising
AWS-DataScience's `examples/sandbox-orchestration/` in the target, the processing task first, by
the user's request. `scripts/space_values.py` stopped in a target space because the project there
has no project KMS key (no `kmsKeyArn` in the Tooling environment), and it now prints the other
nine values with a warning, as the SDK creates its own job without a key
(`.claude/memory/environments.md`, "The project space"). A target space then read the
distribution's CPython 3.12.14, `sagemaker-user` with sudo, `~/shared` on s3fs and a SageMaker API
that answers; the space runs SageMaker Distribution 4.5 (the user, 2026-10-13, for whom the
"4.15" of the user section is a typo), and the first target definition names `4.5.2-cpu`, the
newest 4.5 tag on public ECR (`.claude/memory/environments.md`, "The target"). The first
workflow run there (18:12 UTC) passed its S3 sensor and failed on `DescribeProcessingJob`, the
lab's first refusal; the grant of
`docs/index.md` ("A permissão do projeto") went to the user as adjusted copies of the target's
Terraform, built on the user's current version of it, in the Claude project's library
(`alvo/terraform/`), not applied yet. At 19:16 UTC a Python task over a `package-task` archive ran
there, the package's first archive on a worker, with no change to the target's Terraform: the code's
copy reached the worker, STS answered, `petl` came from the archive and PyYAML 6.0.2 from the
worker, and the result's sha256 was the lab's (`.claude/memory/environments.md`, "The target").
At 19:35 UTC a Bash task over a `package-task` archive with two `--include` scripts ran there too:
the worker kept the scripts' executable bit, a module ran with `python3 -m` without a `cd`, a
script ran by its full path, the archive's `six` came before the worker's, the result's sha256 was
the same, and the task that tried PyPI failed with errno 101 as designed
(`.claude/memory/environments.md`, "The first Bash task"). A review of these findings, by the
user's request of 20:22 UTC, made `values` and `render` take a project role without a `KmsKeyId`
tag, with the warning `space_values.py` prints, wrote that a job's `PYTHONPATH` precedence is a
Bash task's and the inverse of a Python task's (`package_job`, `docs/index.md`), dropped the
claim that the target has no SageMaker endpoint from `render`, and left the Python task's
precedence mechanism as an open question.

A session on branch `claude/project-thread-ez12z6` (2026-10-13) recorded what an inline Bash task
read on a target worker: the disk, the CPUs and the memory, the tools and the packages, every
`WORKER_PROVIDED` package among them (`.claude/memory/environments.md`, "The target"). The
package's code did not change.

A session on branch `claude/awsds-workflows-examples-yn6vxj` (2026-10-13) created `examples/`, by
the user's request ("The examples folder" in `.claude/memory/decisions.md`): the five workflows
that ran in the target, each with its definition, its code and a pt-BR `README.md`, over one shared
uv project; `--values-file` became repeatable, each file over the previous;
`scripts/space_values.py` and `docs/index.md` name the file `space_values.json`, and
`docs/index.md` gained "Os exemplos". By the user's second request of the same day, the steps of
the five examples became the `pdoc` page `awsds_workflows.examples` (`docs/exemplos.md`, through
the docstring-only module `examples.py`), in the direct style of the chat that exercised them, and
the READMEs point at it. The user's answers of 04:04 UTC made each example's extra values a
versioned model file, `extra_values.json`, and the examples' prefix its placeholder
`EXAMPLE_PREFIX`; the session added, as its own choice, that a value may reference other
placeholders (`render.py`). By the user's decision of 04:55 UTC, the job's code input became one
object, the `.tar.gz` of the project folder prepared with its own CPython 3.12, which the job's
command extracts on the volume, and by the user's request of 05:15 UTC the preparation is the
package's own tooling, the subcommand `prepare-offline` (`prepare_offline.py`), which the
documentation and the example use; the relocation was proved on the build host
(`.claude/memory/packaging.md`), not in a job yet.
The archives built from the examples were compared with the target's
(`.claude/memory/packaging.md`); no example ran from the repository's copies yet
(`.claude/memory/OPEN_QUESTIONS.md`).

A session on branch `claude/project-thread-8oxrm3` (2026-10-14) added
`examples/houseprice-etl/`, by the user's request of 23:44 UTC ("The examples folder" in
`.claude/memory/decisions.md`): a Visual ETL job of the target as an application of the CI/CD
CLI, whose workflow creates or updates the Glue job and runs it, after the user decided at 23:42
UTC that such a job is edited in the application's script, in git. The script, the operator,
`job.json` and the CLI's `bundle` were checked outside AWS that day (the example's
`README.md`); the example has not run in a project, and the target-ready copy is in the Claude
project's library (`alvo/visual-etl/`). The package's code did not change.

A session on branch `claude/pdoc-docs-readability-5i3oci` (2026-10-16) revised the `pdoc`
documentation against a critique the user brought: numbered steps with each command in its own
block, warnings as GitHub alerts colored for the dark site (`docs/theme/custom.css`), an opening
with who the documentation is for, the problem it solves and a quickstart, and the lab's dates and
readings moved to their own page, `awsds_workflows.lab_notes` (`docs/laboratorio.md`), by the
user's choice ("The documentation" in `.claude/memory/decisions.md`). Every section and anchor
stays; the package's code did not change.

A session on branch `claude/smus-applications-rw30u1` (2026-10-15 and 2026-10-16, PR #20) made each
example of `examples/` an application of the CI/CD CLI `aws-smus-cicd-cli` 1.0.9, after
AWS-DataScience's D41 made the application the unit that moves between projects and accounts (the
user, 2026-10-15) and the lab measured the CLI with `houseprice-etl` between two Sandbox projects,
from the user's laptop, on 2026-10-15 and 2026-10-16 (`.claude/memory/cicd-cli.md`): the first
`deploy`, the `glue:GetJob` the project role's policy refuses on a job that does not exist, the job
created once from `job.json`, the `UpdateJob` every run from the `Command`, the `bundle` and the
`test` leg with `trailLogs`. By the user's answers of 2026-10-16 (04:20 UTC, "The examples as
applications" in `.claude/memory/decisions.md`): one application per example, the prefix the literal
`exemplos/<exemplo>`, without `EXAMPLE_PREFIX`, and the `lint` in a following PR. `render`
translates the CLI's variables (`CLI_VARIABLES`, `translate_cli_variables`) and `compare` normalizes
both sides, with `{{ params.NOME }}`; `demo_tasks.run` and `awsds_demo_job.s3` take `s3://` URIs;
each folder holds `manifest.yaml`, `workflows/` and `code/`, `src/` or `glue/`, and
`extra_values.json` stays only where the portal path has a value to fill; `docs/exemplos.md` leads
each example through the CLI, with the portal as the other path, `docs/laboratorio.md` holds the
CLI's readings, and `docs/index.md` the translation table. The five examples that ran in the target
have not run by the CLI, and the `houseprice-etl` has not run with the whole `Command`
(`.claude/memory/OPEN_QUESTIONS.md`).

A second session on branch `claude/smus-applications-rw30u1` (2026-10-16, restarted from `main`
after PR #20 merged) added the `lint`, by the user's answer of 04:20 UTC and the three of 05:52
and 05:54 UTC ("The lint of an application" in `.claude/memory/decisions.md`): `lint.py`, the
subcommand `lint`, `tests/test_lint.py`, the subsection "O lint" of `docs/index.md`, the step
before the `deploy` in `docs/exemplos.md`, and the pages of the service read for the limits
(`REFERENCES.md`). The six applications pass in the authoring mode; the promoted mode has run on
no pipeline. The same day the user chose how the Glue job is born, a `glue:GetJob` grant on the
jobs no project holds (05:50 UTC), written in AWS-DataScience's PR #143 and the target's change
request.

A third session on the same branch (2026-10-16, restarted from `main` after PR #21 merged)
recorded the user's confirmation of the lint's five choices (14:30 UTC) and the lab's measurement
of the grant, applied there at 14:54 UTC, after which a run from a deleted job created the job by
the operator (`.claude/memory/cicd-cli.md`, "The Glue job in the lab"), in the memory, the lab
notes, the example's README and the steps page; the target's grant is unapplied, and the steps
keep `job.json` for a project without it. The package's code did not change.

What waits: the user's confirmation of the design choices listed in `.claude/memory/decisions.md`
("Design choices of the first session", "The examples folder", "The examples as applications" and
the three of "The lint of an application" not put to the user); the target's change request
applied, the processing job's grant and the `glue:GetJob`, and a run that creates the processing
job, which measures the image's facts and the job's path; a Bash task whose `Code` is a lone `.py`
or `.sh`, and one with `env` and no `append_env`; a Python task that prints its `sys.path`;
`package-job` run in a lab space and its folder in a job; a job over the `.tar.gz` of
`prepare-offline`; the five examples that ran in the target run by the CLI from the repository's
copies, and the `houseprice-etl` run without `UpdateJob`; the `lint --promoted` on a pipeline and
the translation of a workflow for another account, with AWS-DataScience's Stage 10. Each one is an
item in `.claude/memory/OPEN_QUESTIONS.md`.
