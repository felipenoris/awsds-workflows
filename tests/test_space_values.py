"""``scripts/space_values.py``: os valores lidos dos metadados de um espaço do projeto, e a chave
KMS do DataZone.

Nenhum teste chama a AWS nem lê ``/opt/ml/metadata``: os metadados são um arquivo fabricado em
``tmp_path``, e a chamada ao DataZone é um dublê de ``space_values._get_environment``. A conta e os
ids são os de exemplo da documentação da AWS. Os testes da chamada real ao DataZone, sobre um
servidor local, precisam do ``boto3``, que o projeto não instala, e rodam com
``uv run --with boto3 pytest tests/test_space_values.py``.
"""

from __future__ import annotations

import http.server
import json
import os
import sys
import threading
from collections.abc import Iterator
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

EXPECTED = {
    "REGION": "us-west-2",
    "ACCOUNT_ID": "111122223333",
    "PROJECT_ROLE_NAME": "datazone_usr_role_abc123_env456",
    "PROJECT_ID": "abc123",
    "DOMAIN_ID": "dzd_exemplo",
    "PROJECTS_BUCKET": "meu-bucket",
    "PROJECT_SG": "sg-exemplo",
    "SUBNET_AZ1": "subnet-a",
    "SUBNET_AZ2": "subnet-b",
}


def space_metadata() -> dict[str, Any]:
    """Os metadados de um espaço, no formato dos dados de teste do SDK ``sagemaker-studio``: o
    papel na raiz, os dados do projeto em ``AdditionalMetadata``, e o ``DomainId`` da raiz, que é o
    domínio do SageMaker e não o do DataZone."""
    return {
        "AppType": "JupyterLab",
        "DomainId": "d-exemplo",
        "SpaceName": "meu-espaco",
        "ExecutionRoleArn": "arn:aws:iam::111122223333:role/datazone_usr_role_abc123_env456",
        "AdditionalMetadata": {
            "DataZoneDomainId": "dzd_exemplo",
            "DataZoneDomainRegion": "us-west-2",
            "DataZoneEnvironmentId": "env456",
            "DataZoneProjectId": "abc123",
            "DataZoneScopeName": "dev",
            "PrivateSubnets": "subnet-a,subnet-b",
            "ProjectS3Path": "s3://meu-bucket/dzd_exemplo/abc123/dev",
            "SecurityGroup": "sg-exemplo",
        },
    }


def tooling_environment(
    key_arn: str = KEY_ARN,
) -> dict[str, Any]:
    """A resposta do ``GetEnvironment`` para o ambiente Tooling, com a chave entre os recursos
    provisionados."""
    return {
        "id": "env456",
        "provisionedResources": [
            {"name": "securityGroup", "type": "string", "value": "sg-exemplo"},
            {"name": "kmsKeyArn", "type": "string", "value": key_arn},
        ],
    }


def fake_get_environment(
    response: dict[str, Any] | Exception,
    calls: list[tuple[str, str, str, str | None]],
):
    """Um dublê de ``space_values._get_environment`` que grava a chamada e devolve a resposta, ou
    levanta a exceção dada."""

    def get_environment(
        domain_id: str,
        environment_id: str,
        region: str,
        endpoint_url: str | None,
    ) -> dict[str, Any]:
        """Grava a chamada e devolve a resposta fabricada."""
        calls.append((domain_id, environment_id, region, endpoint_url))
        if isinstance(response, Exception):
            raise response
        return response

    return get_environment


@pytest.fixture
def space(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    """O arquivo de metadados fabricado no lugar do de ``/opt/ml/metadata``, e a região do
    espaço."""
    path = tmp_path / "resource-metadata.json"
    path.write_text(json.dumps(space_metadata()), encoding="utf-8")
    monkeypatch.setattr(space_values, "METADATA_PATH", path)
    monkeypatch.setenv("AWS_REGION", "us-west-2")
    return path


def test_values_come_from_the_metadata_and_the_region() -> None:
    """Os valores saem do papel, dos campos do DataZone, do caminho S3, do grupo e das duas
    primeiras sub-redes, na ordem do arquivo."""
    metadata = space_metadata()
    metadata["AdditionalMetadata"]["PrivateSubnets"] = " subnet-a , subnet-b,subnet-c "
    values = space_values.values_from_metadata(metadata, {"AWS_REGION": "us-west-2"})
    assert values == EXPECTED


def test_a_field_at_the_root_is_read_as_well() -> None:
    """Um campo pode estar na raiz do JSON em vez de ``AdditionalMetadata``, como o SDK lê."""
    metadata = space_metadata()
    metadata["SecurityGroup"] = metadata["AdditionalMetadata"].pop("SecurityGroup")
    values = space_values.values_from_metadata(metadata, {"AWS_REGION": "us-west-2"})
    assert values["PROJECT_SG"] == "sg-exemplo"


def test_the_region_falls_back_to_aws_default_region() -> None:
    """Sem ``AWS_REGION``, a região vem de ``AWS_DEFAULT_REGION``."""
    environ = {"AWS_DEFAULT_REGION": "sa-east-1"}
    values = space_values.values_from_metadata(space_metadata(), environ)
    assert values["REGION"] == "sa-east-1"


def test_a_space_without_a_region_is_refused() -> None:
    """Sem as duas variáveis de região, os valores são recusados."""
    with pytest.raises(space_values.MetadataError, match="não define AWS_REGION"):
        space_values.values_from_metadata(space_metadata(), {})


def test_missing_fields_are_listed_with_the_fields_found() -> None:
    """Os campos que faltam vão todos na mensagem, com os nomes que o arquivo tem."""
    metadata = space_metadata()
    del metadata["AdditionalMetadata"]["PrivateSubnets"]
    metadata["AdditionalMetadata"]["SecurityGroup"] = " "
    with pytest.raises(space_values.MetadataError) as error_info:
        space_values.values_from_metadata(metadata, {"AWS_REGION": "us-west-2"})
    message = str(error_info.value)
    assert "campos ausentes nos metadados: PrivateSubnets, SecurityGroup" in message
    assert "o arquivo tem: AdditionalMetadata, AppType" in message


def test_a_single_subnet_is_refused() -> None:
    """Uma só sub-rede é recusada: o job pede duas zonas."""
    metadata = space_metadata()
    metadata["AdditionalMetadata"]["PrivateSubnets"] = "subnet-a"
    with pytest.raises(space_values.MetadataError, match="nomeia 1 sub-redes"):
        space_values.values_from_metadata(metadata, {"AWS_REGION": "us-west-2"})


def test_two_security_groups_are_refused() -> None:
    """Mais de um grupo de segurança é recusado, como em ``values``."""
    metadata = space_metadata()
    metadata["AdditionalMetadata"]["SecurityGroup"] = "sg-a,sg-b"
    with pytest.raises(space_values.MetadataError, match="não nomeia um só grupo"):
        space_values.values_from_metadata(metadata, {"AWS_REGION": "us-west-2"})


def test_the_role_path_stays_out_of_the_role_name() -> None:
    """O caminho de um papel, quando há, não entra no nome."""
    arn = "arn:aws:iam::111122223333:role/service-role/datazone_usr_role_abc123_env456"
    assert space_values.role_from_arn(arn) == ("111122223333", "datazone_usr_role_abc123_env456")


def test_an_arn_that_is_not_an_iam_role_is_refused() -> None:
    """O ARN de uma sessão do STS não é o papel, e é recusado."""
    arn = "arn:aws:sts::111122223333:assumed-role/datazone_usr_role_abc123_env456/SageMaker"
    with pytest.raises(space_values.MetadataError, match="não é o ARN de um papel do IAM"):
        space_values.role_from_arn(arn)


def test_a_project_path_that_is_not_s3_is_refused() -> None:
    """Um ``ProjectS3Path`` sem ``s3://`` é recusado."""
    with pytest.raises(space_values.MetadataError, match="não é um caminho s3://"):
        space_values.bucket_from_path("meu-bucket/dzd_exemplo/abc123/dev")


def test_the_key_id_comes_from_the_environment_of_the_space(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A chave é o fim do ``kmsKeyArn`` do ambiente do espaço, pedido ao DataZone na região do
    domínio, no endpoint do ``boto3`` quando o arquivo não tem ``DataZoneEndpoint``."""
    calls: list[tuple[str, str, str, str | None]] = []
    double = fake_get_environment(tooling_environment(), calls)
    monkeypatch.setattr(space_values, "_get_environment", double)
    assert space_values.project_key_id(space_metadata()) == KEY_ID
    assert calls == [("dzd_exemplo", "env456", "us-west-2", None)]


def test_the_key_is_asked_at_the_endpoint_of_the_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Com ``DataZoneEndpoint`` no arquivo, a chamada vai a ele, como no SDK."""
    metadata = space_metadata()
    endpoint = "https://datazone.us-west-2.api.aws"
    metadata["AdditionalMetadata"]["DataZoneEndpoint"] = endpoint
    calls: list[tuple[str, str, str, str | None]] = []
    double = fake_get_environment(tooling_environment(), calls)
    monkeypatch.setattr(space_values, "_get_environment", double)
    assert space_values.project_key_id(metadata) == KEY_ID
    assert calls == [("dzd_exemplo", "env456", "us-west-2", endpoint)]


def test_an_environment_without_the_key_is_refused_with_its_resources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Um ambiente sem ``kmsKeyArn`` é recusado, com os recursos que ele tem na mensagem."""
    response = {"provisionedResources": [{"name": "securityGroup", "value": "sg-exemplo"}]}
    calls: list[tuple[str, str, str, str | None]] = []
    monkeypatch.setattr(space_values, "_get_environment", fake_get_environment(response, calls))
    with pytest.raises(space_values.KeyNotReadError, match="recursos provisionados: securityGroup"):
        space_values.project_key_id(space_metadata())
    assert len(calls) == 1


def test_a_key_alias_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """O ARN de um alias não dá o id que ``key/<PROJECT_KEY_ID>`` pede, e é recusado."""
    alias = "arn:aws:kms:us-west-2:111122223333:alias/minha-chave"
    calls: list[tuple[str, str, str, str | None]] = []
    double = fake_get_environment(tooling_environment(alias), calls)
    monkeypatch.setattr(space_values, "_get_environment", double)
    with pytest.raises(space_values.KeyNotReadError, match="não é o ARN de uma chave"):
        space_values.project_key_id(space_metadata())
    assert len(calls) == 1


def test_the_key_is_not_asked_without_the_environment_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sem ``DataZoneEnvironmentId``, a chave não é pedida ao DataZone."""
    metadata = space_metadata()
    del metadata["AdditionalMetadata"]["DataZoneEnvironmentId"]
    calls: list[tuple[str, str, str, str | None]] = []
    double = fake_get_environment(tooling_environment(), calls)
    monkeypatch.setattr(space_values, "_get_environment", double)
    with pytest.raises(space_values.KeyNotReadError, match="DataZoneEnvironmentId"):
        space_values.project_key_id(metadata)
    assert calls == []


def test_main_prints_the_json_of_the_values_command(
    space: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """O script imprime o mesmo texto que ``awsds-workflows values`` imprime para os mesmos
    valores."""
    calls: list[tuple[str, str, str, str | None]] = []
    double = fake_get_environment(tooling_environment(), calls)
    monkeypatch.setattr(space_values, "_get_environment", double)
    assert space_values.main() == 0
    printed = capsys.readouterr().out
    assert json.loads(printed) == {**EXPECTED, "PROJECT_KEY_ID": KEY_ID}

    values_file = tmp_path / "valores.json"
    values_file.write_text(printed, encoding="utf-8")
    assert cli.main(["values", "--values-file", str(values_file)]) == 0
    assert capsys.readouterr().out == printed


def test_main_prints_the_names_of_the_account_reading(
    space: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """O script imprime os nomes que a leitura da conta de ``values`` dá sem ``--image-name``."""
    monkeypatch.setattr(render, "_run_aws", fake_aws(project_responses(), []))
    from_account = render.read_values("perfil", subnet_name="projeto-private-*")

    double = fake_get_environment(tooling_environment(), [])
    monkeypatch.setattr(space_values, "_get_environment", double)
    assert space_values.main() == 0
    assert sorted(json.loads(capsys.readouterr().out)) == sorted(from_account)


def test_main_prints_the_values_without_the_key_when_datazone_fails(
    space: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Uma falha do DataZone tira só a chave do JSON, com o motivo na saída de erro, e o script
    termina com 0."""
    calls: list[tuple[str, str, str, str | None]] = []
    refusal = space_values.KeyNotReadError("o DataZone recusou ou não respondeu: AccessDenied")
    monkeypatch.setattr(space_values, "_get_environment", fake_get_environment(refusal, calls))
    assert space_values.main() == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out) == EXPECTED
    assert "PROJECT_KEY_ID fora do JSON, para entrar à mão" in captured.err
    assert "AccessDenied" in captured.err
    assert len(calls) == 1


def test_main_outside_a_space_exits_with_one(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Sem o arquivo de metadados, o script termina com 1, sem JSON, e não chama o DataZone."""
    calls: list[tuple[str, str, str, str | None]] = []
    double = fake_get_environment(tooling_environment(), calls)
    monkeypatch.setattr(space_values, "_get_environment", double)
    monkeypatch.setattr(space_values, "METADATA_PATH", tmp_path / "resource-metadata.json")
    assert space_values.main() == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "o script roda num espaço do projeto" in captured.err
    assert calls == []


# A chamada real ao DataZone, sobre um servidor local: precisa do boto3.


@dataclass
class FakeDataZone:
    """O que o servidor local responde a todo ``GET``, os pedidos que recebeu, com o caminho e a
    chave de acesso que assinou cada um, e o endereço do servidor."""

    status: int = 200
    body: dict[str, Any] = field(default_factory=tooling_environment)
    requests: list[dict[str, str]] = field(default_factory=list)
    url: str = ""


def handler_for(
    fake: FakeDataZone,
) -> type[http.server.BaseHTTPRequestHandler]:
    """A classe que atende os pedidos do servidor local com a resposta de ``fake``."""

    class Handler(http.server.BaseHTTPRequestHandler):
        """Grava cada pedido em ``fake`` e responde com o status e o corpo dele."""

        def do_GET(self) -> None:
            """Grava o pedido e responde."""
            authorization = self.headers.get("Authorization", "")
            access_key = authorization.split("Credential=")[-1].split("/")[0]
            fake.requests.append({"path": self.path, "access_key": access_key})
            content = json.dumps(fake.body).encode("utf-8")
            self.send_response(fake.status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def log_message(
            self,
            *args: object,
        ) -> None:
            """Não imprime o log de cada pedido."""

    return Handler


@pytest.fixture
def datazone(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[FakeDataZone]:
    """Um servidor local no lugar do endpoint do DataZone, e as credenciais do espaço por
    variáveis, sem configuração do ``aws``."""
    pytest.importorskip("boto3")
    fake = FakeDataZone()
    server = http.server.HTTPServer(("127.0.0.1", 0), handler_for(fake))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    fake.url = f"http://127.0.0.1:{server.server_port}"

    # Nenhuma variável AWS_ de fora entra na chamada, e o servidor local fica fora do proxy.
    for name in [name for name in os.environ if name.startswith("AWS_")]:
        monkeypatch.delenv(name)
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIDESPACO")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "segredo")
    monkeypatch.setenv("AWS_CONFIG_FILE", str(tmp_path / "config"))
    monkeypatch.setenv("AWS_SHARED_CREDENTIALS_FILE", str(tmp_path / "credentials"))
    monkeypatch.setenv("AWS_ENDPOINT_URL_DATAZONE", fake.url)
    monkeypatch.setenv("NO_PROXY", "127.0.0.1")
    monkeypatch.setenv("no_proxy", "127.0.0.1")
    yield fake
    server.shutdown()
    thread.join(timeout=5)


def test_the_call_signs_with_the_space_credentials_without_the_sdk_profile(
    datazone: FakeDataZone,
) -> None:
    """Sem o perfil do SDK, a chamada assina com as credenciais do espaço e pede o ambiente pelo
    caminho do ``GetEnvironment``."""
    response = space_values._get_environment("dzd_exemplo", "env456", "us-west-2", None)
    assert response["provisionedResources"][1]["value"] == KEY_ARN
    assert datazone.requests == [
        {"path": "/v2/domains/dzd_exemplo/environments/env456", "access_key": "AKIDESPACO"}
    ]


def test_the_call_signs_with_the_sdk_profile_when_the_space_has_it(
    datazone: FakeDataZone,
    tmp_path: Path,
) -> None:
    """Com o perfil ``DomainExecutionRoleCreds`` na configuração, a chamada assina com as
    credenciais dele."""
    credentials = {"Version": 1, "AccessKeyId": "AKIDDOMINIO", "SecretAccessKey": "s"}
    program = tmp_path / "credenciais.py"
    program.write_text(f"print({json.dumps(json.dumps(credentials))})\n", encoding="utf-8")
    (tmp_path / "config").write_text(
        f"[profile DomainExecutionRoleCreds]\ncredential_process = {sys.executable} {program}\n",
        encoding="utf-8",
    )
    space_values._get_environment("dzd_exemplo", "env456", "us-west-2", None)
    assert [request["access_key"] for request in datazone.requests] == ["AKIDDOMINIO"]


def test_a_failed_call_is_not_repeated(
    datazone: FakeDataZone,
) -> None:
    """Uma resposta 503, que o boto3 repetiria, chega ao script na primeira tentativa."""
    datazone.status = 503
    datazone.body = {"message": "indisponível"}
    with pytest.raises(space_values.KeyNotReadError, match="recusou ou não respondeu"):
        space_values._get_environment("dzd_exemplo", "env456", "us-west-2", None)
    assert len(datazone.requests) == 1


def test_the_call_goes_to_the_endpoint_it_is_given(
    datazone: FakeDataZone,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """O endpoint dado vale mais que o do ``boto3``, aqui uma porta fechada."""
    monkeypatch.setenv("AWS_ENDPOINT_URL_DATAZONE", "http://127.0.0.1:9")
    space_values._get_environment("dzd_exemplo", "env456", "us-west-2", datazone.url)
    assert len(datazone.requests) == 1
