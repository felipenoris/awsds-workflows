"""Os exemplos de ``examples/``: cada definição renderiza com valores fabricados e é YAML válido,
os placeholders de cada uma são os que ``scripts/space_values.py`` imprime mais os do
``extra_values.json`` do próprio exemplo, que recusa o ``render`` enquanto um valor por preencher
está como veio, os caminhos no S3 ficam sob ``<EXAMPLE_PREFIX>/``, que esse arquivo fixa em
``shared/exemplos/<exemplo>``, a task Python e o módulo de ``UNLOAD`` rodam sobre dublês do
``boto3``, e os dois ``.zip`` saem do projeto compartilhado com as raízes dos que rodaram no
ambiente alvo em 2026-10-12 (``network``).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import boto3
import pytest
import yaml
from botocore.client import BaseClient
from botocore.stub import Stubber

import demo_tasks
import redshift_unload
from awsds_demo_job import s3
from awsds_workflows import package_task, render
from awsds_workflows.errors import RefusalError

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
DEFINITIONS = sorted(EXAMPLES.glob("*/*.yaml"))
DEFINITION_IDS = [definition.stem for definition in DEFINITIONS]

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


def placeholders_of(
    definition: Path,
) -> set[str]:
    """Os nomes dos placeholders da definição."""
    return set(render.PLACEHOLDER.findall(definition.read_text(encoding="utf-8")))


def extra_values_of(
    definition: Path,
) -> dict[str, str]:
    """O ``extra_values.json`` da pasta da definição, como veio, ou nada quando a pasta não tem
    um."""
    model = definition.with_name("extra_values.json")
    if not model.is_file():
        return {}
    return render.load_values(model)


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
    """Cada caminho no bucket do projeto fica sob ``<EXAMPLE_PREFIX>/``, que o
    ``extra_values.json`` do exemplo fixa em ``shared/exemplos/<exemplo>``."""
    text = definition.read_text(encoding="utf-8")
    paths = re.findall(r"<PROJECT_ID>/(\S+)", text)
    for path in paths:
        assert path.startswith("<EXAMPLE_PREFIX>/"), path
    if paths:
        prefix = extra_values_of(definition)["EXAMPLE_PREFIX"]
        assert prefix == f"shared/exemplos/{definition.stem}"


def test_the_bash_scripts_carry_no_jinja_delimiter() -> None:
    """Um ``.sh`` que um BashOperator chama passa pelo Jinja: nenhum tem ``{{`` nem ``{#``."""
    for script in sorted(EXAMPLES.glob("*/*.sh")):
        text = script.read_text(encoding="utf-8")
        assert "{{" not in text, script.name
        assert "{#" not in text, script.name


def test_demo_tasks_prints_the_environment_and_hands_the_work_to_the_project(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``demo_tasks.run`` imprime o interpretador, o ``sys.path``, a credencial e a origem de cada
    pacote sondado, chama o modo S3 do projeto com o bucket e os prefixos e devolve a contagem."""
    calls: list[tuple[str, str, str]] = []

    class FakeSts:
        def get_caller_identity(self) -> dict[str, str]:
            return {"Arn": "arn:aws:sts::111122223333:assumed-role/papel/sessao"}

    def fake_client(
        name: str,
    ) -> FakeSts:
        assert name == "sts"
        return FakeSts()

    def fake_s3_run(
        bucket: str,
        inbox: str,
        outbox: str,
    ) -> int:
        calls.append((bucket, inbox, outbox))
        return 1

    monkeypatch.setattr(boto3, "client", fake_client)
    monkeypatch.setattr(s3, "run", fake_s3_run)

    assert demo_tasks.run("meu-bucket", "entrada/", "saida/", ti="contexto") == 1
    assert calls == [("meu-bucket", "entrada/", "saida/")]
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
        bucket: str,
        inbox: str,
        outbox: str,
    ) -> int:
        return 0

    monkeypatch.setattr(demo_tasks, "print_environment", fake_print_environment)
    monkeypatch.setattr(s3, "run", fake_s3_run)
    with pytest.raises(RuntimeError, match="nada sob s3://meu-bucket/entrada/"):
        demo_tasks.run("meu-bucket", "entrada/", "saida/")


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
    shutil.copytree(
        EXAMPLES / "awsds-demo-job",
        project,
        ignore=shutil.ignore_patterns(".venv", "__pycache__", ".pytest_cache", "uv.lock"),
    )
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
        EXAMPLES / "demo-python-operator" / "demo_tasks.py",
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
        include=[EXAMPLES / "demo-bash-operator" / script for script in scripts],
    )
    assert archive.top_level == sorted(PROJECT_ROOTS + scripts)
    with zipfile.ZipFile(archive.path) as opened:
        for script in scripts:
            mode = (opened.getinfo(script).external_attr >> 16) & 0o777
            assert mode & 0o111 == 0o111, script
