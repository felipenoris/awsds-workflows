"""``awsds_workflows.render``: o preenchimento e o caminho inverso, o arquivo de valores e a
leitura da conta sobre respostas fabricadas do ``aws``.

Nenhum teste chama a AWS: a leitura da conta roda sobre um dublê de ``render._run_aws`` que
responde a cada comando com o JSON que o ``aws`` daria. As contas e os ids são os de exemplo da
documentação da AWS.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from awsds_workflows import render
from awsds_workflows.errors import RefusalError

VALUES = {
    "PROJECTS_BUCKET": "meu-bucket",
    "PROJECT_ID": "abc123",
    "PROJECT_ROLE_NAME": "datazone_usr_role_abc123_env456",
}


def test_fill_replaces_every_placeholder() -> None:
    """Cada placeholder do texto vira o seu valor."""
    text = "s3://<PROJECTS_BUCKET>/<PROJECT_ID>/ e <PROJECT_ID>"
    assert render.fill_placeholders(text, VALUES) == "s3://meu-bucket/abc123/ e abc123"


def test_fill_refuses_a_placeholder_without_a_value() -> None:
    """Um placeholder sem valor recusa o texto, com todos os que faltam na mensagem."""
    with pytest.raises(RefusalError, match="nenhum valor para: IMAGE, SUBNET_AZ1"):
        render.fill_placeholders("<SUBNET_AZ1> <IMAGE> <PROJECT_ID>", VALUES)


def test_fill_leaves_text_that_is_not_a_placeholder() -> None:
    """Um ``<...>`` em minúsculas, como ``<função>`` num texto, não é placeholder."""
    text = "python_callable: tasks.<função> e <nome>"
    assert render.fill_placeholders(text, VALUES) == text


def test_restore_replaces_the_longest_value_first() -> None:
    """O id do projeto está no nome do papel, e o nome do papel volta inteiro."""
    text = "role/datazone_usr_role_abc123_env456 e projeto abc123"
    restored = render.restore_placeholders(text, VALUES)
    assert restored == "role/<PROJECT_ROLE_NAME> e projeto <PROJECT_ID>"


def test_restore_undoes_fill() -> None:
    """O caminho inverso devolve o texto original."""
    text = "bucket: <PROJECTS_BUCKET>\nrole: <PROJECT_ROLE_NAME>\nid: <PROJECT_ID>\n"
    filled = render.fill_placeholders(text, VALUES)
    assert render.restore_placeholders(filled, VALUES) == text


def test_restore_refuses_an_empty_value() -> None:
    """Um valor vazio casaria com o texto inteiro, e é recusado."""
    with pytest.raises(RefusalError, match="valor vazio para: PROJECT_SG"):
        render.restore_placeholders("texto", {"PROJECT_SG": ""})


def test_load_values_reads_a_json_object(
    tmp_path: Path,
) -> None:
    """Um objeto JSON de texto para texto volta como dicionário."""
    path = tmp_path / "valores.json"
    path.write_text(json.dumps(VALUES), encoding="utf-8")
    assert render.load_values(path) == VALUES


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("[1, 2]", "não é um objeto"),
        ('{"PROJECT_ID": 123}', "valor que não é texto em PROJECT_ID"),
        ("{", "não é JSON"),
    ],
)
def test_load_values_refuses_what_is_not_an_object_of_text(
    tmp_path: Path,
    content: str,
    message: str,
) -> None:
    """Uma lista, um valor que não é texto e um JSON inválido são recusados."""
    path = tmp_path / "valores.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(RefusalError, match=message):
        render.load_values(path)


def test_load_values_refuses_a_missing_file(
    tmp_path: Path,
) -> None:
    """Um arquivo de valores que não existe é recusado."""
    with pytest.raises(RefusalError, match="não existe"):
        render.load_values(tmp_path / "valores.json")


def fake_aws(
    responses: dict[str, object],
    calls: list[list[str]],
) -> Callable[[list[str]], str]:
    """Um dublê de ``render._run_aws`` que responde pelo primeiro subcomando que casa."""

    def run_aws(
        arguments: list[str],
    ) -> str:
        """Grava a chamada e devolve a resposta fabricada do comando."""
        calls.append(arguments)
        command = " ".join(arguments)
        for key, response in responses.items():
            if key in command:
                if isinstance(response, str):
                    return response
                return json.dumps(response)
        raise AssertionError(f"comando sem resposta fabricada: {command}")

    return run_aws


def project_responses(
    image: str = "111122223333.dkr.ecr.us-west-2.amazonaws.com/imagem@sha256:abcd",
    key_id: str | None = "chave-exemplo",
) -> dict[str, object]:
    """As respostas do ``aws`` para uma conta com um projeto; ``key_id`` ``None`` tira a etiqueta
    ``KmsKeyId`` do papel."""
    tags = [
        {"Key": "AmazonDataZoneProject", "Value": "abc123"},
        {"Key": "AmazonDataZoneDomain", "Value": "dzd_exemplo"},
        {"Key": "AmazonDataZoneScopeName", "Value": "dev"},
        {"Key": "DomainBucketName", "Value": "meu-bucket"},
        {"Key": "VpcId", "Value": "vpc-exemplo"},
    ]
    if key_id is not None:
        tags.append({"Key": "KmsKeyId", "Value": key_id})
    return {
        "configure get region": "us-west-2\n",
        "sts get-caller-identity": {"Account": "111122223333"},
        "iam list-roles": ["datazone_usr_role_abc123_env456"],
        "iam get-role": {"Role": {"Tags": tags}},
        "describe-security-groups": {"SecurityGroups": [{"GroupId": "sg-exemplo"}]},
        "describe-subnets": {
            "Subnets": [
                {"SubnetId": "subnet-b", "AvailabilityZoneId": "usw2-az2"},
                {"SubnetId": "subnet-a", "AvailabilityZoneId": "usw2-az1"},
            ]
        },
        "describe-image-version": {"ContainerImage": image},
    }


def test_read_values_reads_the_project_from_the_role_tags(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Os valores saem das etiquetas do papel, do grupo de segurança do projeto e das sub-redes
    em ordem de zona; sem ``image_name``, não há ``JOB_IMAGE_URI``."""
    calls: list[list[str]] = []
    monkeypatch.setattr(render, "_run_aws", fake_aws(project_responses(), calls))

    values = render.read_values("perfil", subnet_name="projeto-private-*")
    assert values == {
        "REGION": "us-west-2",
        "ACCOUNT_ID": "111122223333",
        "PROJECT_ROLE_NAME": "datazone_usr_role_abc123_env456",
        "PROJECT_ID": "abc123",
        "DOMAIN_ID": "dzd_exemplo",
        "PROJECTS_BUCKET": "meu-bucket",
        "PROJECT_KEY_ID": "chave-exemplo",
        "PROJECT_SG": "sg-exemplo",
        "SUBNET_AZ1": "subnet-a",
        "SUBNET_AZ2": "subnet-b",
    }
    commands = [" ".join(call) for call in calls]
    assert [command for command in commands if "describe-image-version" in command] == []
    assert [command for command in commands if "group-name,Values=datazone-abc123-dev" in command]


@pytest.mark.parametrize("key_id", [None, ""], ids=["sem etiqueta", "etiqueta vazia"])
def test_read_values_leaves_out_a_missing_project_key(
    key_id: str | None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Um papel sem a etiqueta ``KmsKeyId``, ou com ela vazia, dá os outros valores, sem
    ``PROJECT_KEY_ID``: um projeto pode não ter chave KMS própria, como o do ambiente alvo em
    2026-10-12."""
    responses = project_responses(key_id=key_id)
    monkeypatch.setattr(render, "_run_aws", fake_aws(responses, []))

    values = render.read_values("perfil", subnet_name="projeto-private-*")
    assert "PROJECT_KEY_ID" not in values
    assert values["PROJECT_SG"] == "sg-exemplo"


def test_read_values_reads_the_custom_image_uri(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Com ``image_name``, o URI da imagem registrada vira ``JOB_IMAGE_URI``."""
    calls: list[list[str]] = []
    monkeypatch.setattr(render, "_run_aws", fake_aws(project_responses(), calls))

    values = render.read_values("perfil", subnet_name="projeto-private-*", image_name="imagem")
    expected = "111122223333.dkr.ecr.us-west-2.amazonaws.com/imagem@sha256:abcd"
    assert values["JOB_IMAGE_URI"] == expected


def test_read_values_refuses_an_image_without_a_digest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Uma imagem registrada por etiqueta, e não por digest, é recusada."""
    responses = project_responses(image="111122223333.dkr.ecr.us-west-2.amazonaws.com/imagem:v1")
    monkeypatch.setattr(render, "_run_aws", fake_aws(responses, []))
    with pytest.raises(RefusalError, match="não está fixada por digest"):
        render.read_values("perfil", subnet_name="projeto-private-*", image_name="imagem")


def test_read_values_refuses_a_profile_without_a_region(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Um perfil sem região é recusado antes de qualquer outra chamada."""
    responses = project_responses()
    responses["configure get region"] = ""
    calls: list[list[str]] = []
    monkeypatch.setattr(render, "_run_aws", fake_aws(responses, calls))
    with pytest.raises(RefusalError, match="não nomeia uma região"):
        render.read_values("perfil", subnet_name="projeto-private-*")
    assert len(calls) == 1


def test_read_values_refuses_an_account_with_two_projects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Dois papéis de projeto sem ``project`` são recusados, com os ids na mensagem."""
    responses = project_responses()
    responses["iam list-roles"] = ["datazone_usr_role_abc123_env456", "datazone_usr_role_x_y"]
    monkeypatch.setattr(render, "_run_aws", fake_aws(responses, []))
    with pytest.raises(RefusalError, match="2 papéis de projeto casam"):
        render.read_values("perfil", subnet_name="projeto-private-*")


def test_read_values_refuses_a_single_subnet(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Uma só sub-rede é recusada: o job pede duas zonas."""
    responses = project_responses()
    responses["describe-subnets"] = {
        "Subnets": [{"SubnetId": "subnet-a", "AvailabilityZoneId": "usw2-az1"}]
    }
    monkeypatch.setattr(render, "_run_aws", fake_aws(responses, []))
    with pytest.raises(RefusalError, match="1 sub-redes"):
        render.read_values("perfil", subnet_name="projeto-private-*")
