"""``scripts/space_values.py``: os valores lidos pelo SDK ``sagemaker-studio``, do projeto e do
ambiente Tooling dele.

Os testes de ``main`` trocam ``space_values._read_tooling_environment`` por um dublê, e a conta e
os ids são os de exemplo da documentação da AWS. Os testes com o SDK real rodam o script num
subprocesso contra um servidor local no lugar do DataZone; precisam do ``sagemaker-studio``, que o
projeto não instala, e rodam com ``uv run --with sagemaker-studio pytest
tests/test_space_values.py``.
"""

from __future__ import annotations

import http.server
import importlib.util
import json
import os
import subprocess
import sys
import threading
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from awsds_workflows import cli, render

# O script fica em scripts/, que o pythonpath do pytest põe no sys.path, e os dublês do aws vêm
# dos testes de render.
import space_values
from test_render import fake_aws, project_responses

KEY_ID = "1234abcd-12ab-34cd-56ef-1234567890ab"
KEY_ARN = f"arn:aws:kms:us-west-2:111122223333:key/{KEY_ID}"
ROLE_ARN = "arn:aws:iam::111122223333:role/datazone_usr_role_abc123_env456"

EXPECTED = {
    "REGION": "us-west-2",
    "ACCOUNT_ID": "111122223333",
    "PROJECT_ROLE_NAME": "datazone_usr_role_abc123_env456",
    "PROJECT_ID": "abc123",
    "DOMAIN_ID": "dzd_exemplo",
    "PROJECTS_BUCKET": "meu-bucket",
    "PROJECT_KEY_ID": KEY_ID,
    "PROJECT_SG": "sg-exemplo",
    "SUBNET_AZ1": "subnet-a",
    "SUBNET_AZ2": "subnet-b",
}


def tooling_environment(
    environment_id: str = "env456",
    security_group: str = "sg-exemplo",
) -> dict[str, Any]:
    """A resposta do ``GetEnvironment`` para o ambiente Tooling, com os recursos que o SDK lê."""
    return {
        "id": environment_id,
        "domainId": "dzd_exemplo",
        "projectId": "abc123",
        "awsAccountId": "111122223333",
        "awsAccountRegion": "us-west-2",
        "provisionedResources": [
            {"name": "securityGroup", "type": "string", "value": security_group},
            {"name": "privateSubnets", "type": "string", "value": "subnet-a,subnet-b"},
            {"name": "userRoleArn", "type": "string", "value": ROLE_ARN},
            {"name": "kmsKeyArn", "type": "string", "value": KEY_ARN},
            {
                "name": "s3BucketPath",
                "type": "string",
                "value": "s3://meu-bucket/dzd_exemplo/abc123/dev",
            },
        ],
    }


def replace_resource(
    environment: dict[str, Any],
    name: str,
    value: str | None,
) -> dict[str, Any]:
    """O ambiente com o valor do recurso ``name`` trocado por ``value``, ou sem o recurso quando
    ``value`` é ``None``."""
    resources = []
    for resource in environment["provisionedResources"]:
        if resource["name"] != name:
            resources.append(resource)
        elif value is not None:
            resources.append({**resource, "value": value})
    return {**environment, "provisionedResources": resources}


def fake_read_tooling_environment(
    result: dict[str, Any] | Exception,
    calls: list[str],
) -> Callable[[], tuple[str, str, dict[str, Any]]]:
    """Um dublê de ``space_values._read_tooling_environment`` que grava a chamada e devolve o
    projeto ``abc123``, o domínio ``dzd_exemplo`` e o ambiente dado, ou levanta a exceção dada."""

    def read_tooling_environment() -> tuple[str, str, dict[str, Any]]:
        """Grava a chamada e devolve o ambiente fabricado."""
        calls.append("lido")
        if isinstance(result, Exception):
            raise result
        return "abc123", "dzd_exemplo", result

    return read_tooling_environment


def test_values_come_from_the_project_and_the_tooling_environment() -> None:
    """Os valores saem dos ids do projeto e do domínio, da conta e da região do ambiente e dos
    recursos dele, com as duas primeiras sub-redes na ordem do ambiente."""
    subnets = " subnet-a , subnet-b,subnet-c "
    environment = replace_resource(tooling_environment(), "privateSubnets", subnets)
    values = space_values.values_from_environment("abc123", "dzd_exemplo", environment)
    assert values == EXPECTED


def test_what_is_missing_is_listed_with_the_resources_found() -> None:
    """A região e os recursos que faltam vão todos na mensagem, com os nomes dos recursos que o
    ambiente tem; um recurso vazio falta, e um recurso sem nome fica fora da lista."""
    environment = replace_resource(tooling_environment(), "securityGroup", None)
    environment = replace_resource(environment, "privateSubnets", "")
    environment["provisionedResources"].append({"type": "string", "value": "sem-nome"})
    del environment["awsAccountRegion"]
    with pytest.raises(space_values.ValuesError) as error_info:
        space_values.values_from_environment("abc123", "dzd_exemplo", environment)
    message = str(error_info.value)
    found = "kmsKeyArn, privateSubnets, s3BucketPath, userRoleArn"
    assert "o ambiente env456 não tem awsAccountRegion, privateSubnets, securityGroup" in message
    assert f"(os recursos provisionados: {found})" in message


def test_a_single_subnet_is_refused() -> None:
    """Uma só sub-rede é recusada: o job pede duas zonas."""
    environment = replace_resource(tooling_environment(), "privateSubnets", "subnet-a")
    with pytest.raises(space_values.ValuesError, match="nomeia 1 sub-redes"):
        space_values.values_from_environment("abc123", "dzd_exemplo", environment)


def test_the_role_path_stays_out_of_the_role_name() -> None:
    """O caminho de um papel, quando há, não entra no nome."""
    arn = "arn:aws:iam::111122223333:role/service-role/datazone_usr_role_abc123_env456"
    assert space_values.role_name_from_arn(arn) == "datazone_usr_role_abc123_env456"


def test_an_arn_that_is_not_an_iam_role_is_refused() -> None:
    """O ARN de uma sessão do STS não é o papel, e é recusado."""
    arn = "arn:aws:sts::111122223333:assumed-role/datazone_usr_role_abc123_env456/SageMaker"
    with pytest.raises(space_values.ValuesError, match="não é o ARN de um papel do IAM"):
        space_values.role_name_from_arn(arn)


def test_a_bucket_path_that_is_not_s3_is_refused() -> None:
    """Um ``s3BucketPath`` sem ``s3://`` é recusado."""
    with pytest.raises(space_values.ValuesError, match="não é um caminho s3://"):
        space_values.bucket_from_path("meu-bucket/dzd_exemplo/abc123/dev")


def test_a_key_alias_is_refused() -> None:
    """O ARN de um alias não dá o id que ``key/<PROJECT_KEY_ID>`` pede, e é recusado."""
    with pytest.raises(space_values.ValuesError, match="não é o ARN de uma chave"):
        space_values.key_id_from_arn("arn:aws:kms:us-west-2:111122223333:alias/minha-chave")


def test_main_prints_the_json_of_the_values_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """O script imprime o mesmo texto que ``awsds-workflows values`` imprime para os mesmos
    valores."""
    calls: list[str] = []
    double = fake_read_tooling_environment(tooling_environment(), calls)
    monkeypatch.setattr(space_values, "_read_tooling_environment", double)
    assert space_values.main() == 0
    printed = capsys.readouterr().out
    assert json.loads(printed) == EXPECTED
    assert len(calls) == 1

    values_file = tmp_path / "valores.json"
    values_file.write_text(printed, encoding="utf-8")
    assert cli.main(["values", "--values-file", str(values_file)]) == 0
    assert capsys.readouterr().out == printed


def test_main_prints_the_names_of_the_account_reading(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """O script imprime os nomes que a leitura da conta de ``values`` dá sem ``--image-name``."""
    monkeypatch.setattr(render, "_run_aws", fake_aws(project_responses(), []))
    from_account = render.read_values("perfil", subnet_name="projeto-private-*")

    double = fake_read_tooling_environment(tooling_environment(), [])
    monkeypatch.setattr(space_values, "_read_tooling_environment", double)
    assert space_values.main() == 0
    assert sorted(json.loads(capsys.readouterr().out)) == sorted(from_account)


def test_main_refuses_an_environment_without_a_value(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Um ambiente sem um recurso termina com 1, sem JSON, com o motivo na saída de erro."""
    calls: list[str] = []
    environment = replace_resource(tooling_environment(), "securityGroup", None)
    double = fake_read_tooling_environment(environment, calls)
    monkeypatch.setattr(space_values, "_read_tooling_environment", double)
    assert space_values.main() == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "o ambiente env456 não tem securityGroup" in captured.err
    assert len(calls) == 1


def test_an_environment_without_a_key_gives_the_other_values() -> None:
    """Um projeto sem chave KMS própria não tem ``kmsKeyArn``, como o ambiente alvo lido em
    2026-10-12, e os outros valores saem sem ``PROJECT_KEY_ID``."""
    environment = replace_resource(tooling_environment(), "kmsKeyArn", None)
    values = space_values.values_from_environment("abc123", "dzd_exemplo", environment)
    expected = dict(EXPECTED)
    del expected["PROJECT_KEY_ID"]
    assert values == expected


def test_main_warns_when_the_project_has_no_key(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Sem ``kmsKeyArn``, o script imprime o JSON sem ``PROJECT_KEY_ID``, termina com 0 e avisa
    na saída de erro; um ``kmsKeyArn`` vazio conta como ausente."""
    calls: list[str] = []
    environment = replace_resource(tooling_environment(), "kmsKeyArn", "")
    double = fake_read_tooling_environment(environment, calls)
    monkeypatch.setattr(space_values, "_read_tooling_environment", double)
    assert space_values.main() == 0
    captured = capsys.readouterr()
    assert "PROJECT_KEY_ID" not in json.loads(captured.out)
    assert "não tem kmsKeyArn" in captured.err
    assert "o JSON sai sem PROJECT_KEY_ID" in captured.err
    assert len(calls) == 1


def test_main_does_not_warn_when_the_project_has_a_key(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Com ``kmsKeyArn``, a saída de erro fica vazia."""
    double = fake_read_tooling_environment(tooling_environment(), [])
    monkeypatch.setattr(space_values, "_read_tooling_environment", double)
    assert space_values.main() == 0
    assert capsys.readouterr().err == ""


def test_main_lets_a_failure_of_the_sdk_through(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Uma falha do SDK ou do DataZone sai do script como a exceção do SDK, sem JSON."""
    calls: list[str] = []
    failure = RuntimeError("AccessDeniedException ao chamar GetProject")
    double = fake_read_tooling_environment(failure, calls)
    monkeypatch.setattr(space_values, "_read_tooling_environment", double)
    with pytest.raises(RuntimeError, match="AccessDeniedException ao chamar GetProject"):
        space_values.main()
    assert capsys.readouterr().out == ""
    assert len(calls) == 1


def test_main_without_the_sdk_exits_with_one(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Num Python sem o SDK, o script termina com 1, sem JSON, e nomeia o Python que rodou."""
    monkeypatch.setitem(sys.modules, "sagemaker_studio", None)
    assert space_values.main() == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "o SDK sagemaker-studio não está neste Python" in captured.err
    assert sys.executable in captured.err


# O script com o SDK real, num subprocesso, contra um servidor local no lugar do DataZone.

SPACE_METADATA = Path("/opt/ml/metadata/resource-metadata.json")
"""O arquivo que o SDK lê num espaço, no lugar das variáveis que os testes dão."""

PROJECT_PATH = "/v2/domains/dzd_exemplo/projects/abc123"
"""O caminho do ``GetProject`` do projeto de exemplo."""

# O código de erro que o servidor local dá a cada status de recusa.
ERROR_TYPES = {403: "AccessDeniedException", 404: "ResourceNotFoundException"}


def datazone_routes() -> dict[str, tuple[int, dict[str, Any]]]:
    """O status e o corpo da resposta a cada caminho que o SDK pede: o projeto, nenhuma conexão
    ``default.iam``, o blueprint Tooling e dois ambientes dele, dos quais o padrão é o de menor
    ``deploymentOrder``, que a lista dá em segundo."""
    environments = [
        {"id": "env-outro", "name": "Outro", "deploymentOrder": 2},
        {"id": "env456", "name": "Tooling", "deploymentOrder": 1},
    ]
    blueprint = {"id": "bp-tooling", "name": "Tooling", "provider": "Amazon SageMaker"}
    return {
        PROJECT_PATH: (200, {"id": "abc123", "name": "meu-projeto", "domainId": "dzd_exemplo"}),
        "/v2/domains/dzd_exemplo/connections": (200, {"items": []}),
        "/v2/domains/dzd_exemplo/environment-blueprints": (200, {"items": [blueprint]}),
        "/v2/domains/dzd_exemplo/environments": (200, {"items": environments}),
        "/v2/domains/dzd_exemplo/environments/env456": (200, tooling_environment()),
        "/v2/domains/dzd_exemplo/environments/env-outro": (
            200,
            tooling_environment("env-outro", "sg-outro"),
        ),
    }


@dataclass
class FakeDataZone:
    """As respostas do servidor local pelo caminho, os pedidos que ele recebeu, com o caminho e a
    chave de acesso que assinou cada um, e o endereço do servidor."""

    routes: dict[str, tuple[int, dict[str, Any]]] = field(default_factory=datazone_routes)
    requests: list[dict[str, str]] = field(default_factory=list)
    url: str = ""


def handler_for(
    fake: FakeDataZone,
) -> type[http.server.BaseHTTPRequestHandler]:
    """A classe que atende os pedidos do servidor local com as respostas de ``fake``."""

    class Handler(http.server.BaseHTTPRequestHandler):
        """Grava cada pedido em ``fake`` e responde com o status e o corpo do caminho dele."""

        def do_GET(self) -> None:
            """Grava o pedido e responde; um caminho sem resposta recebe 404."""
            path = self.path.split("?")[0]
            authorization = self.headers.get("Authorization", "")
            access_key = authorization.split("Credential=")[-1].split("/")[0]
            fake.requests.append({"path": path, "access_key": access_key})

            not_found = (404, {"message": f"{path} não existe no servidor local"})
            status, body = fake.routes.get(path, not_found)
            content = json.dumps(body).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(content)))
            if status in ERROR_TYPES:
                self.send_header("x-amzn-ErrorType", ERROR_TYPES[status])
            self.end_headers()
            self.wfile.write(content)

        def log_message(
            self,
            *args: object,
        ) -> None:
            """Não imprime o log de cada pedido."""

    return Handler


@pytest.fixture
def datazone() -> Iterator[FakeDataZone]:
    """Um servidor local no lugar do endpoint do DataZone, para o script rodar com o SDK real."""
    if importlib.util.find_spec("sagemaker_studio") is None:
        pytest.skip("o SDK sagemaker-studio não está neste Python (uv run --with sagemaker-studio)")
    if SPACE_METADATA.exists():
        pytest.skip(f"este Python roda num espaço: o SDK leria {SPACE_METADATA}")

    fake = FakeDataZone()
    server = http.server.HTTPServer(("127.0.0.1", 0), handler_for(fake))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    fake.url = f"http://127.0.0.1:{server.server_port}"
    yield fake
    server.shutdown()
    thread.join(timeout=5)


def run_script(
    fake: FakeDataZone,
    home: Path,
) -> subprocess.CompletedProcess[str]:
    """Roda o script num subprocesso, sem proxy nem configuração do ``aws``, com credenciais
    fabricadas e os campos do espaço por variáveis, que o SDK lê quando não há arquivo de
    metadados."""
    environment = {
        "PATH": os.environ["PATH"],
        "HOME": str(home),
        "AWS_ACCESS_KEY_ID": "AKIDESPACO",
        "AWS_SECRET_ACCESS_KEY": "segredo",
        "AWS_CONFIG_FILE": str(home / "config"),
        "AWS_SHARED_CREDENTIALS_FILE": str(home / "credentials"),
        "AWS_EC2_METADATA_DISABLED": "true",
        "DataZoneDomainId": "dzd_exemplo",
        "DataZoneProjectId": "abc123",
        "DataZoneDomainRegion": "us-west-2",
        "DataZoneEndpoint": fake.url,
    }
    return subprocess.run(
        [sys.executable, space_values.__file__],
        env=environment,
        capture_output=True,
        encoding="utf-8",
        timeout=120,
    )


def test_the_sdk_reads_the_default_tooling_environment(
    datazone: FakeDataZone,
    tmp_path: Path,
) -> None:
    """Com o SDK real, o script imprime só o JSON, lido do ambiente Tooling que o SDK escolhe,
    pelo endpoint que o espaço dá e com as credenciais do espaço."""
    completed = run_script(datazone, tmp_path)
    assert completed.returncode == 0, completed.stderr
    expected = json.dumps(EXPECTED, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    assert completed.stdout == expected

    paths = [request["path"] for request in datazone.requests]
    assert "/v2/domains/dzd_exemplo/environments/env456" in paths
    assert "/v2/domains/dzd_exemplo/environments/env-outro" not in paths
    assert {request["access_key"] for request in datazone.requests} == {"AKIDESPACO"}


def test_a_refusal_of_datazone_ends_without_json(
    datazone: FakeDataZone,
    tmp_path: Path,
) -> None:
    """Uma recusa do ``GetProject`` termina com 1 e o rastro do Python na saída de erro, sem
    JSON."""
    datazone.routes[PROJECT_PATH] = (403, {"message": "User is not authorized"})
    completed = run_script(datazone, tmp_path)
    assert completed.returncode == 1
    assert completed.stdout == ""
    assert "Traceback" in completed.stderr
    assert "AccessDeniedException" in completed.stderr
    assert PROJECT_PATH in [request["path"] for request in datazone.requests]
