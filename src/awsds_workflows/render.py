"""[public] Os placeholders de uma definição de workflow, preenchidos com os valores do projeto, e
o caminho inverso.

Uma definição versionada guarda cada valor da conta como ``<PLACEHOLDER>``: um nome de maiúsculas,
dígitos e ``_`` entre ``<`` e ``>``. ``fill_placeholders`` troca cada um pelo seu valor e recusa um
placeholder sem valor; ``restore_placeholders`` faz o inverso numa definição que o portal salvou,
para que a cópia versionada se compare com o arquivo importado. O texto preenchido vai para a tela
e para o portal, nunca para o repositório.

Os valores vêm de um arquivo JSON (``load_values``), da conta pelo ``aws`` (``read_values``), ou dos
dois, e então os do arquivo completam e substituem os da conta. A leitura da conta chama o STS, o
IAM, o EC2 e, para uma imagem customizada, o SageMaker; onde essas APIs não respondem, como no
ambiente alvo, que não tem endpoint para o IAM nem para o SageMaker (leituras de 2026-09-21 e
2026-09-23, a partir de um espaço), os valores vêm só do arquivo. Os valores que dependem da imagem
do job, como ``JOB_IMAGE_URI`` e o interpretador, vêm do arquivo quando a imagem é a padrão.

Os nomes que ``read_values`` preenche:

- ``REGION`` e ``ACCOUNT_ID``: a região do perfil e a conta da credencial;
- ``PROJECT_ROLE_NAME``, ``PROJECT_ID``, ``DOMAIN_ID``, ``PROJECTS_BUCKET`` e ``PROJECT_KEY_ID``:
  o papel do projeto, ``datazone_usr_role_<projeto>_<ambiente>``, e as etiquetas que o SageMaker
  Unified Studio põe nele;
- ``PROJECT_SG``: o grupo de segurança ``datazone-<projeto>-<escopo>`` que o blueprint Tooling
  cria na VPC do projeto;
- ``SUBNET_AZ1`` e ``SUBNET_AZ2``: as sub-redes da VPC do projeto cujo nome casa com o padrão dado,
  em ordem de zona;
- ``JOB_IMAGE_URI``, só com ``image_name``: o URI da versão mais nova da imagem customizada
  registrada no SageMaker, fixado por digest.

Exemplo:

.. code-block:: python

    from pathlib import Path

    from awsds_workflows import render

    values = render.load_values(Path("valores.json"))
    text = Path("meu-workflow.yaml").read_text(encoding="utf-8")
    print(render.fill_placeholders(text, values))
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from awsds_workflows.errors import RefusalError

__all__ = [
    "PLACEHOLDER",
    "fill_placeholders",
    "load_values",
    "read_values",
    "restore_placeholders",
]

PLACEHOLDER = re.compile(r"<([A-Z][A-Z0-9_]+)>")
"""[public] O padrão de um placeholder: ``<`` e ``>`` em volta de um nome que começa por
maiúscula e segue com maiúsculas, dígitos e ``_``."""

_PROJECT_ROLE_PREFIX = "datazone_usr_role_"


def fill_placeholders(
    text: str,
    values: Mapping[str, str],
) -> str:
    """[public] Troca cada placeholder do texto pelo seu valor.

    Exemplo:

    .. code-block:: python

        fill_placeholders("bucket: <PROJECTS_BUCKET>", {"PROJECTS_BUCKET": "meu-bucket"})
        # 'bucket: meu-bucket'

    :param text: o texto com os placeholders, como uma definição de workflow.
    :param values: o valor de cada placeholder, pelo nome sem ``<`` e ``>``.
    :return: o texto com cada placeholder trocado.
    :raises awsds_workflows.errors.RefusalError: quando um placeholder do texto não tem valor, com
        todos os que faltam na mensagem.
    """
    found = {match.group(1) for match in PLACEHOLDER.finditer(text)}
    missing = sorted(found - set(values))
    if missing:
        raise RefusalError(f"nenhum valor para: {', '.join(missing)}")
    return PLACEHOLDER.sub(lambda match: values[match.group(1)], text)


def restore_placeholders(
    text: str,
    values: Mapping[str, str],
) -> str:
    """[public] Troca cada valor do texto pelo seu placeholder, o caminho inverso de
    ``fill_placeholders``.

    O valor mais longo é trocado primeiro, porque um valor pode conter outro: o id do projeto
    também está no nome do papel do projeto.

    Exemplo:

    .. code-block:: python

        restore_placeholders("bucket: meu-bucket", {"PROJECTS_BUCKET": "meu-bucket"})
        # 'bucket: <PROJECTS_BUCKET>'

    :param text: o texto com os valores, como uma definição que o portal salvou.
    :param values: o valor de cada placeholder, pelo nome sem ``<`` e ``>``.
    :return: o texto com cada valor trocado pelo seu placeholder.
    :raises awsds_workflows.errors.RefusalError: quando um valor é vazio, porque o texto inteiro
        casaria com ele.
    """
    empty = sorted(name for name, value in values.items() if value == "")
    if empty:
        raise RefusalError(f"valor vazio para: {', '.join(empty)}")

    by_length = sorted(values.items(), key=lambda item: len(item[1]), reverse=True)
    for name, value in by_length:
        text = text.replace(value, f"<{name}>")
    return text


def load_values(
    path: Path,
) -> dict[str, str]:
    """[public] Lê os valores de um arquivo JSON, um objeto de nome de placeholder para texto.

    Exemplo:

    .. code-block:: python

        # valores.json: {"PROJECTS_BUCKET": "meu-bucket", "PROJECT_ID": "abc123"}
        values = load_values(Path("valores.json"))

    :param path: o arquivo JSON.
    :return: o valor de cada placeholder, pelo nome sem ``<`` e ``>``.
    :raises awsds_workflows.errors.RefusalError: quando o arquivo não existe, não é JSON, não é um
        objeto ou tem um valor que não é texto.
    """
    if not path.is_file():
        raise RefusalError(f"o arquivo de valores {path} não existe")
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise RefusalError(f"{path} não é JSON: {error}") from error
    if not isinstance(loaded, dict):
        raise RefusalError(f"{path} não é um objeto JSON de nome para valor")

    not_text = sorted(name for name, value in loaded.items() if not isinstance(value, str))
    if not_text:
        raise RefusalError(f"{path}: valor que não é texto em {', '.join(not_text)}")
    return loaded


def read_values(
    profile: str,
    subnet_name: str,
    project: str | None = None,
    image_name: str | None = None,
) -> dict[str, str]:
    """[public] Lê da conta, pelo ``aws`` e só com chamadas de leitura, os valores do projeto.

    O papel do projeto é achado pelo prefixo ``datazone_usr_role_`` e, com ``project``, pela
    etiqueta ``AmazonDataZoneProject``. A VPC do projeto é a da etiqueta ``VpcId`` do papel.

    Exemplo:

    .. code-block:: python

        values = read_values(
            "awsds-infra-sandbox-1",
            subnet_name="awsds-sandbox-private-*",
            image_name="awsds-sandbox-dev-env",
        )

    :param profile: o perfil do ``aws`` com que a leitura roda; a região é a dele.
    :param subnet_name: o padrão da etiqueta ``Name`` das sub-redes privadas do projeto, com ``*``
        como curinga.
    :param project: o id do projeto; ``None`` quando a conta tem um só, e uma conta com mais de um
        pede o id.
    :param image_name: o nome da imagem customizada registrada no SageMaker, que dá
        ``JOB_IMAGE_URI``; ``None`` com a imagem padrão.
    :return: o valor de cada placeholder, pelo nome sem ``<`` e ``>``.
    :raises awsds_workflows.errors.RefusalError: quando o ``aws`` falta ou uma chamada falha, quando
        o perfil não tem região, quando não há exatamente um papel de projeto, um grupo de
        segurança ou ao menos duas sub-redes, e quando a imagem não está fixada por digest.
    """
    region = _profile_region(profile)
    account = _aws_json(profile, region, ["sts", "get-caller-identity"])["Account"]
    role_name, tags = _project_role(profile, region, project)
    project_id = tags["AmazonDataZoneProject"]
    vpc = tags["VpcId"]

    values = {
        "REGION": region,
        "ACCOUNT_ID": account,
        "PROJECT_ROLE_NAME": role_name,
        "PROJECT_ID": project_id,
        "DOMAIN_ID": tags["AmazonDataZoneDomain"],
        "PROJECTS_BUCKET": tags["DomainBucketName"],
        "PROJECT_KEY_ID": tags["KmsKeyId"],
        "PROJECT_SG": _project_security_group(profile, region, vpc, project_id, tags),
    }
    subnets = _project_subnets(profile, region, vpc, subnet_name)
    values["SUBNET_AZ1"] = subnets[0]
    values["SUBNET_AZ2"] = subnets[1]
    if image_name is not None:
        values["JOB_IMAGE_URI"] = _image_uri(profile, region, image_name)
    return values


def _run_aws(
    arguments: list[str],
) -> str:
    """[private] Roda o ``aws`` com os argumentos e devolve a saída padrão; é o ponto que os testes
    trocam."""
    executable = shutil.which("aws")
    if executable is None:
        raise RefusalError("o aws não está no PATH")
    completed = subprocess.run(
        [executable, *arguments],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        raise RefusalError(f"aws {' '.join(arguments[:4])} falhou: {completed.stderr.strip()}")
    return completed.stdout


def _profile_region(
    profile: str,
) -> str:
    """[private] A região do perfil, de ``aws configure get region``, que termina com 1 quando o
    perfil não nomeia uma."""
    try:
        region = _run_aws(["--profile", profile, "configure", "get", "region"]).strip()
    except RefusalError as error:
        raise RefusalError(f"o perfil {profile} não nomeia uma região ({error})") from error
    if not region:
        raise RefusalError(f"o perfil {profile} não nomeia uma região")
    return region


def _aws_json(
    profile: str,
    region: str,
    arguments: list[str],
) -> Any:
    """[private] Roda uma chamada de leitura do ``aws`` no perfil e na região dados e devolve o
    JSON."""
    output = _run_aws(["--profile", profile, "--region", region, *arguments, "--output", "json"])
    return json.loads(output or "null")


def _project_role(
    profile: str,
    region: str,
    project: str | None,
) -> tuple[str, dict[str, str]]:
    """[private] O nome e as etiquetas do único papel de projeto da conta, ou do de ``project``."""
    query = f"Roles[?starts_with(RoleName, '{_PROJECT_ROLE_PREFIX}')].RoleName"
    names = _aws_json(profile, region, ["iam", "list-roles", "--query", query]) or []

    # As etiquetas de cada papel de projeto, e só os do projeto pedido.
    found: dict[str, dict[str, str]] = {}
    for name in names:
        role = _aws_json(profile, region, ["iam", "get-role", "--role-name", name])["Role"]
        tags = {tag["Key"]: tag["Value"] for tag in role.get("Tags", [])}
        if project is None or tags.get("AmazonDataZoneProject") == project:
            found[name] = tags

    if len(found) != 1:
        listed = [tags.get("AmazonDataZoneProject", "?") for tags in found.values()]
        raise RefusalError(
            f"{len(found)} papéis de projeto casam: nomeie o projeto (--project na linha de "
            f"comando) ({', '.join(listed) or 'nenhum lido'})"
        )
    role_name = next(iter(found))
    return role_name, found[role_name]


def _project_security_group(
    profile: str,
    region: str,
    vpc: str,
    project_id: str,
    tags: dict[str, str],
) -> str:
    """[private] O id do grupo de segurança que o blueprint Tooling cria para o projeto."""
    scope = tags.get("AmazonDataZoneScopeName", "dev")
    group_name = f"datazone-{project_id}-{scope}"
    filters = [f"Name=vpc-id,Values={vpc}", f"Name=group-name,Values={group_name}"]
    arguments = ["ec2", "describe-security-groups", "--filters", *filters]
    groups = _aws_json(profile, region, arguments)["SecurityGroups"]
    if len(groups) != 1:
        raise RefusalError(f"{len(groups)} grupos de segurança chamados {group_name} em {vpc}")
    return groups[0]["GroupId"]


def _project_subnets(
    profile: str,
    region: str,
    vpc: str,
    subnet_name: str,
) -> list[str]:
    """[private] Os ids das sub-redes da VPC cujo nome casa com o padrão, em ordem de zona."""
    filters = [f"Name=vpc-id,Values={vpc}", f"Name=tag:Name,Values={subnet_name}"]
    arguments = ["ec2", "describe-subnets", "--filters", *filters]
    subnets = _aws_json(profile, region, arguments)["Subnets"]
    if len(subnets) < 2:
        raise RefusalError(
            f"{len(subnets)} sub-redes chamadas {subnet_name} em {vpc}: o job pede duas zonas"
        )
    by_zone = sorted(subnets, key=lambda subnet: subnet["AvailabilityZoneId"])
    return [subnet["SubnetId"] for subnet in by_zone]


def _image_uri(
    profile: str,
    region: str,
    image_name: str,
) -> str:
    """[private] O URI da versão mais nova da imagem customizada, recusado sem digest."""
    arguments = ["sagemaker", "describe-image-version", "--image-name", image_name]
    container = _aws_json(profile, region, arguments)["ContainerImage"]
    if "@" not in container:
        raise RefusalError(f"a imagem registrada não está fixada por digest: {container}")
    return container
