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

- Use Python 3.13.

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
  (SageMaker Distribution 4.15 at the start) or a custom image.

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

## Repository index

Read the file listed here before researching its subject again. `REFERENCES.md` collects every URL
consulted so far, grouped by subject.

| File | Subject |
| --- | --- |
| `README.md` | The minimum: the two workflow badges, the requirements (Linux with internet, `uv`, Python 3.13, `aws` only for the account reading), the installation by git URL (never by name: the name is free on PyPI, read 2026-10-11) and the development commands: `uv sync --all-groups`, `uv run pytest` (`-m "not network"` skips the tests that need PyPI), the Ruff check and the `pdoc` build. |
| `docs/index.md` | The package documentation for `pdoc`, included by the docstring of `src/awsds_workflows/__init__.py`, in pt-BR: AWS-DataScience's runbook `serverless-workflows.md` adapted to the package. It names no external project: AWS-DataScience's provenance is in `.claude/memory/decisions.md` ("The documentation") and its links in `REFERENCES.md`. Sections: the state (lab, 2026-10-11), installation, the pieces, the job image (default SageMaker Distribution 4.15 or custom, and what changes: `JOB_IMAGE_URI`, `JOB_PYTHON`, `--python`, the environment file), the project's permission (the IAM policy JSON), the network (the endpoints the worker and the job used in the lab, and the target's readings), authoring rules, a processing task (the environment's demands, `package-job` step by step, refusals, measurements, a full example definition), a Python or Bash task (`package-task`, the archive, the definition, by hand), the definition's values (`render`, `values`, the placeholder table), reading a run back, cleaning up. Anchors are pdoc's ASCII slugs (`#a-imagem-do-job`). |
| `.github/` | `tests.yml`, on Ubuntu only (the package runs on Linux), imports every module after `uv sync --no-dev` and runs `awsds-workflows --help`, then `ruff check`, `ruff format --check` and the whole `pytest` suite, network tests included, on push to `main`, on pull request and by hand; `docs.yml` publishes the `pdoc` site to <https://felipenoris.github.io/awsds-workflows/> on push to `main` (the repository's Pages source must be "GitHub Actions"). |
| `src/awsds_workflows/` | The package: `errors.py` (`RefusalError`, the one exception, which the CLI prints and turns into exit 1), `_uv.py` (private: `run`, `target_options`, `install_requirements`, `build_pure_wheel`, `install_wheels`, `remove_leftovers`, protected helpers of both packagers), `package_task.py` (`build_archive`, `TaskArchive`, `WORKER_PYTHON` 3.12, `WORKER_PLATFORM` `x86_64-manylinux2014`, `WORKER_PROVIDED`, `ARCHIVE_LIMIT_BYTES` 250,000,000), `package_job.py` (`build_folder`, `environment_versions`, `JobFolder`, `JOB_PLATFORM` `x86_64-manylinux_2_28`; the private parser `_read_pins` refuses any line that is not `name==version`), `render.py` (`fill_placeholders`, `restore_placeholders`, `load_values`, `read_values`, `PLACEHOLDER`; `_run_aws` is the seam the tests replace) and `cli.py` (`awsds-workflows package-task`, `package-job`, `job-constraints`, `render [--placeholders]`, `values`; only `main` public). What each does is in the docstrings; `pyproject.toml` holds the one runtime dependency (`packaging>=24`, a floor so the package installs beside an environment that pins its own), the `dev` and `docs` groups, the `network` marker and `[tool.ruff]`. |
| `tests/` | `conftest.py` (`write_project`: a pure uv project in `tmp_path`, locked with `uv lock`), `test_package.py` (the level tags and the public submodules, copied from serialize-db), `test_uv.py`, `test_package_task.py`, `test_package_job.py`, `test_render.py` (the account reading over a fabricated `aws`, AWS's example account `111122223333`) and `test_cli.py` (doubles of the package functions, real refusals). The `network` tests lock and build real projects and need PyPI. |

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
  `sed -n` ranges.
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
(`build_archive`), `package_job` the job folder (`build_folder`), `render` fills and restores the
placeholders. A CLI subcommand is kebab-case and names the module's job (`package-task`,
`package-job`, `job-constraints`, `render`, `values`). A placeholder is `<NAME>` in upper case
(`PLACEHOLDER` in `render`), English, and generic: `ACCOUNT_ID`, not `SANDBOX_ACCOUNT_ID`;
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
original scripts on the project the lab measured (`.claude/memory/packaging.md`). Nothing has run in
the target yet, and no archive of `package-task` has run on a worker anywhere.

What waits: the user's confirmation of the design choices listed in `.claude/memory/decisions.md`
("Design choices of the first session"); the GitHub Pages source set to "GitHub Actions" before
`docs.yml` first runs on `main`; the first workflow in the target with the SageMaker Distribution
4.15, which measures the network question and the image's facts; AWS-DataScience switching its
runbook and examples to the package. Each one is an item in `.claude/memory/OPEN_QUESTIONS.md`.
