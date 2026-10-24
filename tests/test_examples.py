"""Os exemplos de ``examples/``, cada um uma aplicação da CLI de CI/CD: cada workflow renderiza
com valores fabricados e é YAML válido, os placeholders de cada um, as variáveis da CLI traduzidas,
são os que
``scripts/space_values.py`` imprime mais os do ``extra_values.json`` do próprio exemplo, que
recusa o ``render`` enquanto um valor por preencher está como veio, os caminhos no S3 ficam sob
``shared/exemplos/<exemplo>/``, os scripts Bash não têm delimitador do Jinja, a task Python e o
módulo de ``UNLOAD`` rodam sobre dublês do
``boto3``, os dois ``.zip`` saem do projeto compartilhado com as raízes dos que rodaram no
ambiente alvo em 2026-10-12, e o ``.tar.gz`` do job, gravado por ``prepare_offline``, roda
extraído noutra pasta, sem ``uv`` no ambiente, com o resumo das execuções medidas (``network``).
O ``manifest.yaml`` de cada aplicação tem o nome da pasta e o workflow dela, cada item de storage
é uma pasta do exemplo copiada para ``exemplos/<exemplo>/<pasta>`` do projeto, os dois stages
declaram cada variável de stage do workflow, ``dev`` cria o workflow e ``test`` o cria e o
executa com ``trailLogs``, o workflow lê os arquivos onde o manifest os copia, e o ``code`` de
uma task Python ou Bash é o ``.zip`` de ``code/``, com os fontes que o workflow nomeia. No
``houseprice-etl``, o ``job.json`` é o ``CreateJob`` da task, e o script do job do Glue roda
sobre dublês do ``awsglue`` e do ``pyspark``.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import re
import runpy
import shutil
import subprocess
import sys
import types
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

import boto3
import pytest
import yaml
from botocore.client import BaseClient
from botocore.stub import Stubber

import demo_tasks
import redshift_unload
from awsds_demo_job import s3
from awsds_workflows import package_task, prepare_offline, render
from awsds_workflows.errors import RefusalError

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
# Os workflows das aplicações, um por exemplo, em workflows/.
DEFINITIONS = sorted(EXAMPLES.glob("*/workflows/*.yaml"))
DEFINITION_IDS = [definition.stem for definition in DEFINITIONS]
# Os manifests das aplicações da CLI de CI/CD.
MANIFESTS = sorted(EXAMPLES.glob("*/manifest.yaml"))
MANIFEST_IDS = [manifest.parent.name for manifest in MANIFESTS]
# A variável da CLI com que todo caminho de uma aplicação no bucket começa: a pasta shared/ do
# projeto.
SHARED = "{proj.connection.default.s3_shared.s3Uri}"

# Os valores que scripts/space_values.py imprime num espaço, fabricados sobre a conta de exemplo
# da AWS.
SPACE_VALUES = {
    "REGION": "us-west-2",
    "ACCOUNT_ID": "111122223333",
    "PROJECT_ROLE_NAME": "datazone_usr_role_abc123_def456",
    "PROJECT_ID": "abc123",
    "DOMAIN_ID": "dzd_xyz789",
    "PROJECTS_BUCKET": "amazon-sagemaker-111122223333-us-west-2-0123456789abc",
    "PROJECT_SG": "sg-0123456789abcdef0",
    "SUBNET_AZ1": "subnet-0123456789abcdef0",
    "SUBNET_AZ2": "subnet-0123456789abcdef1",
    "PROJECT_KEY_ID": "1234abcd-12ab-34cd-56ef-1234567890ab",
}
# Os valores por preencher no extra_values.json de um exemplo, pelo nome da definição, fabricados.
TO_FILL = {
    "demo-devenv-job": {"SMD_REGISTRY_ACCOUNT": "111122223333"},
    "redshift-unload": {
        "REDSHIFT_WORKGROUP": "meu-workgroup",
        "REDSHIFT_DATABASE": "dev",
        "REDSHIFT_TABLE": "meu_banco.meu_esquema.minha_tabela",
    },
}
# O sha256 do resumo de sample.csv nas execuções medidas, no laboratório (2026-10-11) e no
# ambiente alvo (2026-10-12), o que o teste do projeto compartilhado também confere.
RESULT_SHA256 = "1b2bc4d73bc49bca1a23a6d0971c1365362e785826a33adfcebec7925a248191"
# O que fica fora de uma cópia do projeto compartilhado: o que o uv e o pytest gravam.
GENERATED = shutil.ignore_patterns(".venv", ".python", "__pycache__", ".pytest_cache", "uv.lock")
# As raízes do .zip de cada task, as mesmas dos que rodaram no ambiente alvo em 2026-10-12, mais o
# six, que o projeto compartilhado fixa para a task Python também.
PROJECT_ROOTS = [
    "awsds_demo_job",
    "awsds_demo_job-0.1.0.dist-info",
    "petl",
    "petl-1.7.28.dist-info",
    "six-1.16.0.dist-info",
    "six.py",
]


def example_folder_of(
    definition: Path,
) -> Path:
    """A pasta do exemplo da definição, a de cima de ``workflows/``."""
    return definition.parent.parent


def placeholders_of(
    definition: Path,
) -> set[str]:
    """Os nomes dos placeholders da definição, com as variáveis da CLI de CI/CD traduzidas."""
    text = render.translate_cli_variables(definition.read_text(encoding="utf-8"))
    return set(render.PLACEHOLDER.findall(text))


def extra_values_of(
    definition: Path,
) -> dict[str, str]:
    """O ``extra_values.json`` da pasta do exemplo, como veio, ou nada quando a pasta não tem
    um."""
    model = example_folder_of(definition) / "extra_values.json"
    if not model.is_file():
        return {}
    return render.load_values(model)


def manifest_and_workflow_of(
    manifest_path: Path,
) -> tuple[dict[str, Any], str]:
    """O manifest de uma aplicação, lido, e o texto do workflow dela,
    ``workflows/<exemplo>.yaml``."""
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    name = manifest_path.parent.name
    workflow = manifest_path.parent / "workflows" / f"{name}.yaml"
    return manifest, workflow.read_text(encoding="utf-8")


@pytest.mark.parametrize("definition", DEFINITIONS, ids=DEFINITION_IDS)
def test_the_definition_renders_with_the_values_of_its_example(
    definition: Path,
) -> None:
    """A definição abre com o comentário de layout do editor, preenche com os valores do espaço,
    os do ``extra_values.json`` e os por preencher sem deixar placeholder, e o YAML tem a chave
    do nome do arquivo, com o mesmo ``dag_id`` e um ``operator`` por task."""
    text = definition.read_text(encoding="utf-8")
    layout = text.splitlines()[0]
    assert layout.startswith("# {")
    assert isinstance(json.loads(layout[2:]), dict)

    values = {**SPACE_VALUES, **extra_values_of(definition), **TO_FILL.get(definition.stem, {})}
    rendered = render.fill_placeholders(text, values)
    assert render.PLACEHOLDER.search(rendered) is None

    document = yaml.safe_load(rendered)
    assert list(document) == [definition.stem]
    workflow = document[definition.stem]
    assert workflow["dag_id"] == definition.stem
    for name, task in workflow["tasks"].items():
        assert "operator" in task, name


@pytest.mark.parametrize("definition", DEFINITIONS, ids=DEFINITION_IDS)
def test_the_definition_asks_only_for_the_values_of_its_example(
    definition: Path,
) -> None:
    """Os placeholders são os do espaço mais as chaves do ``extra_values.json``, cada chave dele é
    pedida pela definição ou por outro valor dele, e um exemplo tem o arquivo quando pede algo
    além do espaço."""
    placeholders = placeholders_of(definition)
    extra = extra_values_of(definition)
    referenced: set[str] = set()
    for value in extra.values():
        referenced.update(render.PLACEHOLDER.findall(value))
    assert placeholders <= set(SPACE_VALUES) | set(extra)
    assert set(extra) <= placeholders | referenced
    assert bool(extra) == bool(placeholders - set(SPACE_VALUES))


@pytest.mark.parametrize("definition", DEFINITIONS, ids=DEFINITION_IDS)
def test_the_values_to_fill_refuse_the_render_until_filled(
    definition: Path,
) -> None:
    """Um valor do ``extra_values.json`` que referencia a si mesmo está por preencher: com o
    arquivo como veio, o ``render`` recusa nomeando cada um, e nada mais."""
    extra = extra_values_of(definition)
    unfilled = sorted(name for name, value in extra.items() if value == f"<{name}>")
    assert unfilled == sorted(TO_FILL.get(definition.stem, {}))

    text = definition.read_text(encoding="utf-8")
    if not unfilled:
        render.fill_placeholders(text, {**SPACE_VALUES, **extra})
        return
    with pytest.raises(RefusalError, match=f"nenhum valor para: {', '.join(unfilled)}$"):
        render.fill_placeholders(text, {**SPACE_VALUES, **extra})


@pytest.mark.parametrize("definition", DEFINITIONS, ids=DEFINITION_IDS)
def test_the_definition_keeps_its_files_under_the_example_prefix(
    definition: Path,
) -> None:
    """Cada caminho no bucket do projeto fica sob ``shared/exemplos/<exemplo>/``: o literal depois
    do ``s3Uri`` da conexão, e, num prefixo sem o bucket, depois do domínio e do projeto, que é
    como o ``s3Uri`` se escreve."""
    text = render.translate_cli_variables(definition.read_text(encoding="utf-8"))
    for path in re.findall(r"<PROJECT_ID>/(\S+)", text):
        assert path.startswith(f"shared/exemplos/{definition.stem}/"), path


def test_the_bash_scripts_carry_no_jinja_delimiter() -> None:
    """Um ``.sh`` que um BashOperator chama passa pelo Jinja: nenhum tem ``{{`` nem ``{#``."""
    scripts = sorted(EXAMPLES.glob("demo-bash-operator/code/*.sh"))
    assert [script.name for script in scripts] == ["probe.sh", "reach_pypi.sh"]
    for script in scripts:
        text = script.read_text(encoding="utf-8")
        assert "{{" not in text, script.name
        assert "{#" not in text, script.name


def test_demo_tasks_prints_the_environment_and_hands_the_work_to_the_project(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``demo_tasks.run`` imprime o interpretador, o ``sys.path``, a credencial e a origem de cada
    pacote sondado, chama o modo S3 do projeto com os dois URIs e devolve a contagem."""
    calls: list[tuple[str, str]] = []

    class FakeSts:
        def get_caller_identity(self) -> dict[str, str]:
            return {"Arn": "arn:aws:sts::111122223333:assumed-role/papel/sessao"}

    def fake_client(
        name: str,
    ) -> FakeSts:
        assert name == "sts"
        return FakeSts()

    def fake_s3_run(
        inbox: str,
        outbox: str,
    ) -> int:
        calls.append((inbox, outbox))
        return 1

    monkeypatch.setattr(boto3, "client", fake_client)
    monkeypatch.setattr(s3, "run", fake_s3_run)

    assert demo_tasks.run("s3://meu-bucket/entrada/", "s3://meu-bucket/saida/", ti="c") == 1
    assert calls == [("s3://meu-bucket/entrada/", "s3://meu-bucket/saida/")]
    printed = capsys.readouterr().out
    assert printed.startswith(f"python {sys.version.split()[0]} em {sys.executable}\n")
    assert "\nsys.path: [" in printed
    assert "\ncredencial: arn:aws:sts::111122223333:assumed-role/papel/sessao\n" in printed
    assert f"\nimport yaml: {yaml.__version__} de {yaml.__file__}\n" in printed
    for name in demo_tasks.PROBED_PACKAGES:
        assert f"\nimport {name}: " in printed


def test_demo_tasks_refuses_an_empty_inbox(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sem objeto sob a entrada, ``run`` levanta ``RuntimeError``: o sensor viu um arquivo."""

    def fake_print_environment() -> None:
        return None

    def fake_s3_run(
        inbox: str,
        outbox: str,
    ) -> int:
        return 0

    monkeypatch.setattr(demo_tasks, "print_environment", fake_print_environment)
    monkeypatch.setattr(s3, "run", fake_s3_run)
    with pytest.raises(RuntimeError, match="nada sob s3://meu-bucket/entrada/"):
        demo_tasks.run("s3://meu-bucket/entrada/", "s3://meu-bucket/saida/")


@pytest.fixture
def fake_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Uma credencial e uma região fabricadas no ambiente, as que o ``boto3`` lê."""
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "chave-de-teste")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "segredo-de-teste")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "token-de-teste")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-west-2")


def stub_data_api(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[BaseClient, Stubber]:
    """Um cliente ``redshift-data`` com um ``Stubber``, que ``redshift_unload`` recebe no lugar do
    cliente real, e sem espera entre as leituras de estado."""
    client = boto3.client("redshift-data")

    def fake_client(
        name: str,
    ) -> BaseClient:
        assert name == "redshift-data"
        return client

    monkeypatch.setattr(redshift_unload.boto3, "client", fake_client)
    monkeypatch.setattr(redshift_unload, "POLL_SECONDS", 0)
    return client, Stubber(client)


def test_unload_text_escapes_the_query_and_carries_the_credentials(
    fake_credentials: None,
) -> None:
    """O ``UNLOAD`` dobra a contrabarra e a aspa simples da consulta e leva a credencial do
    processo em três cláusulas."""
    text = redshift_unload.unload_text("SELECT 'a\\b'", "s3://meu-bucket/prefixo/")
    assert text.startswith("UNLOAD ('SELECT ''a\\\\b''')\nTO 's3://meu-bucket/prefixo/'\n")
    assert "\nACCESS_KEY_ID 'chave-de-teste' SECRET_ACCESS_KEY 'segredo-de-teste' " in text
    assert "SESSION_TOKEN 'token-de-teste'\n" in text
    assert text.endswith("\nFORMAT AS PARQUET MANIFEST VERBOSE")


def test_unload_runs_the_three_commands_in_one_session(
    fake_credentials: None,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``unload`` abre a sessão com ``SELECT current_user``, roda o ``UNLOAD`` e lê
    ``pg_last_unload_count()`` na mesma sessão, imprime o usuário e a contagem e a devolve."""
    client, stubber = stub_data_api(monkeypatch)
    select = "SELECT * FROM meu_banco.meu_esquema.minha_tabela"
    prefix = "s3://meu-bucket/dzd_xyz789/abc123/shared/exemplos/redshift-unload/20261013T022213/"
    stubber.add_response(
        "execute_statement",
        {"Id": "c1", "SessionId": "sessao"},
        {
            "WorkgroupName": "meu-workgroup",
            "Database": "dev",
            "Sql": "SELECT current_user",
            "SessionKeepAliveSeconds": 60,
        },
    )
    stubber.add_response("describe_statement", {"Id": "c1", "Status": "FINISHED"}, {"Id": "c1"})
    stubber.add_response(
        "get_statement_result",
        {"Records": [[{"stringValue": "IAMR:user-project@abc123"}]]},
        {"Id": "c1"},
    )
    stubber.add_response(
        "execute_statement",
        {"Id": "c2"},
        {
            "SessionId": "sessao",
            "Sql": redshift_unload.unload_text(select, prefix),
            "SessionKeepAliveSeconds": 60,
        },
    )
    stubber.add_response("describe_statement", {"Id": "c2", "Status": "FINISHED"}, {"Id": "c2"})
    stubber.add_response(
        "execute_statement",
        {"Id": "c3"},
        {"SessionId": "sessao", "Sql": "SELECT pg_last_unload_count()"},
    )
    stubber.add_response("describe_statement", {"Id": "c3", "Status": "FINISHED"}, {"Id": "c3"})
    stubber.add_response("get_statement_result", {"Records": [[{"longValue": 101}]]}, {"Id": "c3"})

    with stubber:
        rows = redshift_unload.unload(
            select=select,
            destination=prefix.rstrip("/"),
            workgroup="meu-workgroup",
            database="dev",
            ti="contexto",
        )
    stubber.assert_no_pending_responses()
    assert rows == 101
    printed = capsys.readouterr().out
    assert printed.startswith("usuário do banco: IAMR:user-project@abc123\n")
    assert "\n101 linha(s) descarregada(s) em " in printed
    assert printed.endswith(f" s sob {prefix}\n")


def test_a_failed_command_raises_without_the_credentials(
    fake_credentials: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Um comando que termina em ``FAILED`` levanta ``RuntimeError`` com o erro da Data API e a
    credencial mascarada."""
    client, stubber = stub_data_api(monkeypatch)
    error = (
        "ERROR: syntax error in UNLOAD ('SELECT') TO 's3://meu-bucket/x/' "
        "ACCESS_KEY_ID 'chave-de-teste' SECRET_ACCESS_KEY 'segredo-de-teste' "
        "SESSION_TOKEN 'token-de-teste'"
    )
    stubber.add_response(
        "execute_statement",
        {"Id": "c1", "SessionId": "sessao"},
        {
            "WorkgroupName": "meu-workgroup",
            "Database": "dev",
            "Sql": "SELECT current_user",
            "SessionKeepAliveSeconds": 60,
        },
    )
    stubber.add_response(
        "describe_statement",
        {"Id": "c1", "Status": "FAILED", "Error": error},
        {"Id": "c1"},
    )

    with stubber, pytest.raises(RuntimeError, match="terminou em FAILED") as error_info:
        redshift_unload.unload(
            select="SELECT",
            destination="s3://meu-bucket/x/",
            workgroup="meu-workgroup",
            database="dev",
        )
    message = str(error_info.value)
    assert "segredo-de-teste" not in message
    assert "token-de-teste" not in message
    assert "SECRET_ACCESS_KEY '***' SESSION_TOKEN '***'" in message


@pytest.fixture(scope="module")
def locked_demo_project(
    tmp_path_factory: pytest.TempPathFactory,
) -> Path:
    """Uma cópia do projeto compartilhado ``awsds-demo-job`` travada com ``uv lock``, para os
    testes ``network`` do módulo."""
    project = tmp_path_factory.mktemp("exemplo") / "awsds-demo-job"
    shutil.copytree(EXAMPLES / "awsds-demo-job", project, ignore=GENERATED)
    subprocess.run(["uv", "lock", "--quiet"], cwd=project, check=True)
    return project


@pytest.mark.network
def test_the_python_archive_has_the_roots_of_the_target(
    locked_demo_project: Path,
    tmp_path: Path,
) -> None:
    """O ``.zip`` de ``demo-python-operator`` leva o módulo de entrada, o projeto e as
    dependências dele na raiz."""
    archive = package_task.build_archive(
        locked_demo_project,
        EXAMPLES / "demo-python-operator" / "code" / "demo_tasks.py",
        tmp_path / "demo-python-operator.zip",
    )
    assert archive.top_level == sorted(PROJECT_ROOTS + ["demo_tasks.py"])


@pytest.mark.network
def test_the_bash_archive_has_the_scripts_with_their_mode(
    locked_demo_project: Path,
    tmp_path: Path,
) -> None:
    """O ``.zip`` de ``demo-bash-operator`` leva os dois scripts executáveis na raiz, o projeto e
    as dependências dele, e nenhum módulo de entrada."""
    scripts = ["probe.sh", "reach_pypi.sh"]
    archive = package_task.build_archive(
        locked_demo_project,
        None,
        tmp_path / "demo-bash-operator.zip",
        include=[EXAMPLES / "demo-bash-operator" / "code" / script for script in scripts],
    )
    assert archive.top_level == sorted(PROJECT_ROOTS + scripts)
    with zipfile.ZipFile(archive.path) as opened:
        for script in scripts:
            mode = (opened.getinfo(script).external_attr >> 16) & 0o777
            assert mode & 0o111 == 0o111, script


@pytest.mark.network
def test_the_prepared_project_runs_extracted_elsewhere(
    locked_demo_project: Path,
    tmp_path: Path,
) -> None:
    """O ``.tar.gz`` do projeto compartilhado tem a raiz ``awsds-demo-job/``, o nome que o comando
    do job abre, e, extraído noutra pasta como esse comando faz, roda o job com o
    ``.venv/bin/python`` dele, num ambiente sem ``uv``, com o resumo das execuções medidas."""
    archive = prepare_offline.prepare_archive(
        locked_demo_project, tmp_path / "awsds-demo-job.tar.gz"
    )
    assert archive.root == "awsds-demo-job"

    elsewhere = tmp_path / "noutra-pasta"
    inbox = tmp_path / "inbox"
    outbox = tmp_path / "outbox"
    for folder in (elsewhere, inbox, outbox):
        folder.mkdir()
    shutil.copy(EXAMPLES / "awsds-demo-job" / "sample.csv", inbox)
    subprocess.run(["tar", "-xzf", archive.path, "-C", elsewhere], check=True)
    python = elsewhere / "awsds-demo-job" / ".venv" / "bin" / "python"
    command = [python, "-m", "awsds_demo_job", "--input", inbox, "--output", outbox]
    run = subprocess.run(
        command, env={"PATH": "/usr/bin:/bin"}, check=True, capture_output=True, text=True
    )
    first_line = run.stdout.splitlines()[0]
    assert first_line.startswith("python 3.12.")
    assert first_line.endswith(f" em {python}")
    result = (outbox / "sample.result.json").read_bytes()
    assert hashlib.sha256(result).hexdigest() == RESULT_SHA256


@pytest.mark.parametrize("manifest_path", MANIFESTS, ids=MANIFEST_IDS)
def test_the_manifest_names_the_example_and_its_workflow(
    manifest_path: Path,
) -> None:
    """O manifest tem o nome da pasta do exemplo e um workflow só, o de ``workflows/`` com o nome
    do exemplo e o mesmo ``dag_id``, na conexão ``default.workflow_serverless``, sem
    ``schedule``."""
    name = manifest_path.parent.name
    manifest, workflow_text = manifest_and_workflow_of(manifest_path)
    assert manifest["applicationName"] == name

    entries = manifest["content"]["workflows"]
    assert [entry["workflowName"] for entry in entries] == [name]
    assert entries[0]["connectionName"] == "default.workflow_serverless"

    document = yaml.safe_load(render.translate_cli_variables(workflow_text))
    assert list(document) == [name]
    assert document[name]["dag_id"] == name
    assert "schedule" not in document[name]


@pytest.mark.parametrize("manifest_path", MANIFESTS, ids=MANIFEST_IDS)
def test_the_storage_items_are_folders_of_the_example_copied_under_its_prefix(
    manifest_path: Path,
) -> None:
    """Cada item de ``content.storage`` é uma pasta do exemplo com o nome do item, sem
    ``connectionName``, e cada stage o copia para ``exemplos/<exemplo>/<pasta>`` da conexão
    ``default.s3_shared`` do projeto. Cada ``include`` nomeia um arquivo ou uma pasta, sem glob:
    o ``bundle`` da CLI 1.0.9 deixou de fora o ``code/*.zip``, com ``Warning: Pattern not found``,
    e levou o ``code/demo-python-operator.zip`` (2026-10-23)."""
    folder = manifest_path.parent
    manifest, _workflow_text = manifest_and_workflow_of(manifest_path)
    items = manifest["content"]["storage"]
    for item in items:
        assert "connectionName" not in item, item["name"]
        for pattern in item["include"]:
            assert Path(pattern).parts[0] == item["name"], pattern
            assert (folder / item["name"]).is_dir(), pattern
            assert not re.search(r"[*?\[]", pattern), pattern

    for stage_name, stage in manifest["stages"].items():
        deployment = stage["deployment_configuration"]["storage"]
        assert sorted(entry["name"] for entry in deployment) == sorted(
            item["name"] for item in items
        ), stage_name
        for entry in deployment:
            assert entry["connectionName"] == "default.s3_shared", stage_name
            assert entry["targetDirectory"] == f"exemplos/{folder.name}/{entry['name']}"


@pytest.mark.parametrize("manifest_path", MANIFESTS, ids=MANIFEST_IDS)
def test_the_stages_declare_every_stage_variable_of_the_workflow(
    manifest_path: Path,
) -> None:
    """Cada ``{env.NOME}`` do workflow está em ``environment_variables`` dos dois stages, como
    ``${NOME}`` lido do shell, e nenhum stage declara uma variável que o workflow não lê: uma sem
    declaração derruba o ``workflow.create`` da CLI 1.0.9 (laboratório, 2026-10-16)."""
    manifest, workflow_text = manifest_and_workflow_of(manifest_path)
    used = set(re.findall(r"\{env\.([A-Z][A-Z0-9_]+)\}", workflow_text))
    for stage_name, stage in manifest["stages"].items():
        declared = stage.get("environment_variables", {})
        assert set(declared) == used, stage_name
        for variable, value in declared.items():
            assert value == f"${{{variable}}}", variable


@pytest.mark.parametrize("manifest_path", MANIFESTS, ids=MANIFEST_IDS)
def test_dev_creates_the_workflow_and_test_creates_and_runs_it_trailing_the_logs(
    manifest_path: Path,
) -> None:
    """O stage ``dev`` cria o workflow, porque o ``deploy`` só copia os arquivos, e o ``test`` o
    cria e o executa com ``trailLogs: true``, que espera o fim; ``wait: true`` derruba a CLI
    1.0.9 (laboratório, 2026-10-16)."""
    name = manifest_path.parent.name
    manifest, _workflow_text = manifest_and_workflow_of(manifest_path)
    stages = manifest["stages"]
    assert list(stages) == ["dev", "test"]
    assert stages["dev"]["stage"] == "DEV"
    assert stages["test"]["stage"] == "TEST"

    create = {"type": "workflow.create", "workflowName": name}
    run = {"type": "workflow.run", "workflowName": name, "trailLogs": True}
    assert stages["dev"]["bootstrap"]["actions"] == [create]
    assert stages["test"]["bootstrap"]["actions"] == [create, run]


@pytest.mark.parametrize("manifest_path", MANIFESTS, ids=MANIFEST_IDS)
def test_the_workflow_reads_its_files_where_the_manifest_copies_them(
    manifest_path: Path,
) -> None:
    """Todo caminho do workflow no bucket começa pelo ``s3Uri`` da conexão e por
    ``exemplos/<exemplo>/``, um arquivo que ele nomeia numa pasta de storage existe no exemplo, e
    um exemplo que copia algo além do workflow lê algo do bucket."""
    folder = manifest_path.parent
    manifest, workflow_text = manifest_and_workflow_of(manifest_path)
    storage_names = {item["name"] for item in manifest["content"]["storage"]}
    prefix = f"exemplos/{folder.name}/"

    paths = re.findall(r"s3Uri\}([^\s\"']+)", workflow_text)
    if storage_names != {"workflows"}:
        assert paths, folder.name
    for path in paths:
        assert path.startswith(prefix), path
        parts = path[len(prefix) :].split("/")
        if parts[0] in storage_names and len(parts) == 2 and parts[1]:
            assert (folder / parts[0] / parts[1]).is_file(), path


@pytest.mark.parametrize("manifest_path", MANIFESTS, ids=MANIFEST_IDS)
def test_the_operator_code_is_the_zip_of_the_example_in_a_storage_item(
    manifest_path: Path,
) -> None:
    """Um exemplo com a pasta ``code/`` tem ``code``, o ``code/<exemplo>.zip`` que o
    ``package-task`` grava pelos passos da página, um item de storage o inclui, e cada módulo de
    ``python_callable`` e cada ``.sh`` que um ``bash_command`` nomeia está em ``code/``; um
    exemplo sem a pasta não tem ``code``."""
    folder = manifest_path.parent
    manifest, workflow_text = manifest_and_workflow_of(manifest_path)
    code = manifest["content"]["workflows"][0].get("code")
    if not (folder / "code").is_dir():
        assert code is None, code
        return
    assert code == f"code/{folder.name}.zip"
    patterns = []
    for item in manifest["content"]["storage"]:
        patterns.extend(item["include"])
    assert any(fnmatch.fnmatch(code, pattern) for pattern in patterns), patterns

    modules = re.findall(r"python_callable: (\w+)\.\w+", workflow_text)
    scripts = re.findall(r"bash_command: (\w+\.sh)$", workflow_text, flags=re.MULTILINE)
    assert modules or scripts, folder.name
    for module in modules:
        assert (folder / "code" / f"{module}.py").is_file(), module
    for script in scripts:
        assert (folder / "code" / script).is_file(), script


def test_the_job_model_is_the_create_job_of_the_workflow() -> None:
    """O ``job.json`` de ``houseprice-etl``, preenchido, é a entrada do ``CreateJob`` que o
    ``GlueJobOperator`` monta com a task do workflow: o nome, a descrição, o papel, uma execução
    por vez, nenhuma nova tentativa e o ``create_job_kwargs``, com o ``Command`` inteiro, o que o
    ``apache-airflow-providers-amazon`` 9.32.0 do worker enviou a um Glue simulado em 2026-10-14.
    O ``Command`` leva o ``PythonVersion`` que o ``GetJob`` devolve, porque sem ele o operador
    chamou ``UpdateJob`` em toda execução no laboratório (2026-10-16)."""
    folder = EXAMPLES / "houseprice-etl"
    job_text = (folder / "job.json").read_text(encoding="utf-8")
    job = json.loads(render.fill_placeholders(job_text, SPACE_VALUES))

    workflow_text = (folder / "workflows" / "houseprice-etl.yaml").read_text(encoding="utf-8")
    definition = yaml.safe_load(render.fill_placeholders(workflow_text, SPACE_VALUES))
    task = definition["houseprice-etl"]["tasks"]["run_glue_job"]
    expected = {
        "Name": task["job_name"],
        "Description": task["job_desc"],
        "Role": task["iam_role_arn"],
        "ExecutionProperty": {"MaxConcurrentRuns": 1},
        "Command": {"Name": "glueetl", "ScriptLocation": task["script_location"]},
        "MaxRetries": 0,
        **task["create_job_kwargs"],
    }
    assert job == expected
    assert job["Command"]["PythonVersion"] == "3"


class FakeWriter:
    """O ``DataFrame.write`` do dublê do Spark: grava cada escolha e o caminho, na ordem."""

    def __init__(self) -> None:
        self.choices: list[tuple[str, object]] = []

    def format(
        self,
        name: str,
    ) -> FakeWriter:
        self.choices.append(("format", name))
        return self

    def option(
        self,
        key: str,
        value: object,
    ) -> FakeWriter:
        self.choices.append((key, value))
        return self

    def mode(
        self,
        name: str,
    ) -> FakeWriter:
        self.choices.append(("mode", name))
        return self

    def save(
        self,
        path: str,
    ) -> None:
        self.choices.append(("save", path))


class FakeDataFrame:
    """O ``DataFrame`` do dublê do Spark: aplica ``transform`` a si mesmo e tem o seu
    ``write``."""

    def __init__(self) -> None:
        self.write = FakeWriter()

    def transform(
        self,
        function: Callable[[FakeDataFrame], FakeDataFrame],
    ) -> FakeDataFrame:
        return function(self)


class FakeReader:
    """O ``SparkSession.read`` do dublê: grava o formato e o caminho e devolve um
    ``FakeDataFrame``."""

    def __init__(self) -> None:
        self.choices: list[tuple[str, str]] = []
        self.frame = FakeDataFrame()

    def format(
        self,
        name: str,
    ) -> FakeReader:
        self.choices.append(("format", name))
        return self

    def load(
        self,
        path: str,
    ) -> FakeDataFrame:
        self.choices.append(("load", path))
        return self.frame


class FakeSparkSession:
    """O ``SparkSession`` do dublê: ``builder.getOrCreate()`` devolve a própria sessão."""

    def __init__(self) -> None:
        self.read = FakeReader()
        self.builder = self

    def getOrCreate(self) -> FakeSparkSession:
        return self


def test_the_glue_script_reads_the_parquet_and_appends_the_csv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """O script do job de ``houseprice-etl`` lê os dois caminhos dos argumentos do job, o Parquet
    de ``--SOURCE_PATH``, e grava os dados sem mudança em CSV, sem cabeçalho e sem compressão,
    acrescentando a ``--TARGET_PATH``, sobre dublês do ``awsglue`` e do ``pyspark``. No PySpark
    4.1.1, o do Glue 6.0, o mesmo script gravou um CSV por execução em 2026-10-14."""
    session = FakeSparkSession()
    asked: list[list[str]] = []

    def fake_get_resolved_options(
        argv: list[str],
        names: list[str],
    ) -> dict[str, str]:
        asked.append(names)
        return {name: argv[argv.index(f"--{name}") + 1] for name in names}

    glue_utils = types.ModuleType("awsglue.utils")
    glue_utils.getResolvedOptions = fake_get_resolved_options
    spark_sql = types.ModuleType("pyspark.sql")
    spark_sql.DataFrame = FakeDataFrame
    spark_sql.SparkSession = session
    monkeypatch.setitem(sys.modules, "awsglue", types.ModuleType("awsglue"))
    monkeypatch.setitem(sys.modules, "awsglue.utils", glue_utils)
    monkeypatch.setitem(sys.modules, "pyspark", types.ModuleType("pyspark"))
    monkeypatch.setitem(sys.modules, "pyspark.sql", spark_sql)

    source = "s3://meu-bucket/entrada/house-price.parquet"
    target = "s3://meu-bucket/saida/"
    argv = ["etl_houseprice.py", "--JOB_NAME", "houseprice-etl-abc123"]
    argv += ["--SOURCE_PATH", source, "--TARGET_PATH", target]
    monkeypatch.setattr(sys, "argv", argv)
    script = EXAMPLES / "houseprice-etl" / "glue" / "etl_houseprice.py"
    runpy.run_path(str(script), run_name="__main__")

    assert asked == [["SOURCE_PATH", "TARGET_PATH"]]
    assert session.read.choices == [("format", "parquet"), ("load", source)]
    assert session.read.frame.write.choices == [
        ("format", "csv"),
        ("header", False),
        ("compression", "uncompressed"),
        ("mode", "append"),
        ("save", target),
    ]
