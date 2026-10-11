"""Imprime, de dentro de um espaço do projeto, os valores de uma definição de workflow em JSON.

O script roda num espaço do projeto do SageMaker Unified Studio, no Python do próprio espaço, e
imprime o JSON de ``awsds-workflows values``, o formato de ``--values-file``. Ele não usa o pacote
nem o ``aws`` e não pede as permissões de IAM e EC2 que ``values`` pede: o espaço grava os dados do
projeto em ``/opt/ml/metadata/resource-metadata.json``, e só a chave KMS vem de uma chamada à AWS,
ao DataZone.

Os valores e de onde vêm:

- ``REGION``: a região do espaço, de ``AWS_REGION`` ou ``AWS_DEFAULT_REGION``;
- ``ACCOUNT_ID`` e ``PROJECT_ROLE_NAME``: o papel do espaço, ``ExecutionRoleArn``, que é o papel
  do projeto;
- ``PROJECT_ID`` e ``DOMAIN_ID``: ``DataZoneProjectId`` e ``DataZoneDomainId``;
- ``PROJECTS_BUCKET``: o bucket de ``ProjectS3Path``;
- ``PROJECT_SG``: ``SecurityGroup``;
- ``SUBNET_AZ1`` e ``SUBNET_AZ2``: as duas primeiras sub-redes de ``PrivateSubnets``, na ordem do
  arquivo; ``values`` as ordena pela zona, que só o EC2 informa;
- ``PROJECT_KEY_ID``: o id da chave do ``kmsKeyArn`` que o ``GetEnvironment`` do DataZone devolve
  para o ambiente do espaço, ``DataZoneEnvironmentId``. O SDK ``sagemaker-studio`` lê o mesmo
  recurso no ambiente Tooling padrão do projeto, que acha por mais duas listagens; o script supõe
  que o espaço roda nesse ambiente. Como no SDK, a chamada vai ao ``DataZoneEndpoint`` do arquivo,
  quando há, e assina com o perfil ``DomainExecutionRoleCreds``, quando o espaço o tem; sem eles,
  vai ao endpoint do ``boto3`` e assina com as credenciais do espaço.

Os nomes dos campos vêm do SDK ``sagemaker-studio`` 1.1.35 (2026-10-11): o código dele lê os do
DataZone, ``ExecutionRoleArn`` e ``ProjectS3Path``, na raiz do JSON ou em ``AdditionalMetadata``, e
``PrivateSubnets`` e ``SecurityGroup`` só aparecem nos dados de teste dele. ``JOB_IMAGE_URI`` e
``JOB_PYTHON`` não saem daqui: com a imagem padrão do SageMaker, eles entram no arquivo de valores.

Um campo que falta no arquivo termina com 1 e o motivo na saída de erro, sem JSON. Uma falha na
leitura da chave imprime o JSON sem ``PROJECT_KEY_ID``, com o motivo na saída de erro, e termina
com 0: a chave entra à mão no arquivo.

Uso, num terminal do espaço, com este arquivo copiado para lá:

    python space_values.py > valores.json
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

METADATA_PATH = Path("/opt/ml/metadata/resource-metadata.json")
"""O arquivo em que o espaço grava os dados do projeto."""

DOMAIN_PROFILE = "DomainExecutionRoleCreds"
"""O perfil do ``aws`` com que o SDK ``sagemaker-studio`` chama o DataZone, quando o espaço o
tem."""

# Os campos de que os valores saem, menos a chave KMS.
VALUE_FIELDS = (
    "DataZoneDomainId",
    "DataZoneProjectId",
    "ExecutionRoleArn",
    "PrivateSubnets",
    "ProjectS3Path",
    "SecurityGroup",
)

# Os campos da chamada ao DataZone que lê a chave KMS.
KEY_FIELDS = (
    "DataZoneDomainId",
    "DataZoneDomainRegion",
    "DataZoneEnvironmentId",
)


class MetadataError(Exception):
    """O motivo por que o arquivo de metadados não dá os valores."""


class KeyNotReadError(Exception):
    """O motivo por que a chave KMS do projeto não foi lida."""


def load_metadata(
    path: Path,
) -> dict[str, Any]:
    """Lê o arquivo de metadados do espaço, um objeto JSON."""
    if not path.is_file():
        raise MetadataError(f"{path} não existe: o script roda num espaço do projeto")
    try:
        metadata = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise MetadataError(f"{path} não é JSON: {error}") from error
    if not isinstance(metadata, dict):
        raise MetadataError(f"{path} não é um objeto JSON")
    return metadata


def metadata_fields(
    metadata: Mapping[str, Any],
    names: tuple[str, ...],
) -> dict[str, str]:
    """O texto de cada campo pedido, lido na raiz do JSON ou em ``AdditionalMetadata``; devolve
    só os campos presentes e não vazios."""
    additional = metadata.get("AdditionalMetadata") or {}
    found: dict[str, str] = {}
    for name in names:
        value = metadata.get(name) or additional.get(name)
        if isinstance(value, str) and value.strip():
            found[name] = value.strip()
    return found


def split_list(
    text: str,
) -> list[str]:
    """Os itens de uma lista separada por vírgulas, sem espaços nem itens vazios."""
    items = []
    for item in text.split(","):
        if item.strip():
            items.append(item.strip())
    return items


def role_from_arn(
    arn: str,
) -> tuple[str, str]:
    """A conta e o nome do papel de um ARN ``arn:aws:iam::<conta>:role/<nome>``; o caminho do
    papel, quando há, fica fora do nome."""
    parts = arn.split(":", 5)
    is_role = len(parts) == 6 and parts[2] == "iam" and parts[5].startswith("role/")
    if not is_role:
        raise MetadataError(f"ExecutionRoleArn não é o ARN de um papel do IAM: {arn}")
    role_name = parts[5].rsplit("/", 1)[-1]
    return parts[4], role_name


def bucket_from_path(
    path: str,
) -> str:
    """O bucket de um caminho ``s3://<bucket>/<prefixo>``."""
    parsed = urlparse(path)
    if parsed.scheme != "s3" or not parsed.netloc:
        raise MetadataError(f"ProjectS3Path não é um caminho s3://: {path}")
    return parsed.netloc


def space_region(
    environ: Mapping[str, str],
) -> str:
    """A região do espaço, de ``AWS_REGION`` ou, sem ela, de ``AWS_DEFAULT_REGION``."""
    region = environ.get("AWS_REGION") or environ.get("AWS_DEFAULT_REGION")
    if not region:
        raise MetadataError("o espaço não define AWS_REGION nem AWS_DEFAULT_REGION")
    return region


def values_from_metadata(
    metadata: Mapping[str, Any],
    environ: Mapping[str, str],
) -> dict[str, str]:
    """Os valores que o arquivo de metadados e a região do espaço dão: todos menos a chave KMS."""
    # Os campos que faltam vão todos na mensagem, com os que o arquivo tem, para comparar.
    fields = metadata_fields(metadata, VALUE_FIELDS)
    missing = [name for name in VALUE_FIELDS if name not in fields]
    if missing:
        present = set(metadata) | set(metadata.get("AdditionalMetadata") or {})
        raise MetadataError(
            f"campos ausentes nos metadados: {', '.join(missing)} "
            f"(o arquivo tem: {', '.join(sorted(present)) or 'nenhum'})"
        )

    account, role_name = role_from_arn(fields["ExecutionRoleArn"])
    groups = split_list(fields["SecurityGroup"])
    if len(groups) != 1:
        raise MetadataError(f"SecurityGroup não nomeia um só grupo: {fields['SecurityGroup']}")
    subnets = split_list(fields["PrivateSubnets"])
    if len(subnets) < 2:
        raise MetadataError(
            f"PrivateSubnets nomeia {len(subnets)} sub-redes, e o job pede duas zonas: "
            f"{fields['PrivateSubnets']}"
        )

    return {
        "REGION": space_region(environ),
        "ACCOUNT_ID": account,
        "PROJECT_ROLE_NAME": role_name,
        "PROJECT_ID": fields["DataZoneProjectId"],
        "DOMAIN_ID": fields["DataZoneDomainId"],
        "PROJECTS_BUCKET": bucket_from_path(fields["ProjectS3Path"]),
        "PROJECT_SG": groups[0],
        "SUBNET_AZ1": subnets[0],
        "SUBNET_AZ2": subnets[1],
    }


def _get_environment(
    domain_id: str,
    environment_id: str,
    region: str,
    endpoint_url: str | None,
) -> dict[str, Any]:
    """O ambiente do DataZone, por ``GetEnvironment``; é o ponto que os testes trocam.

    O ``boto3`` é importado aqui para o resto do script rodar num Python sem ele. A conexão espera
    5 segundos, sem nova tentativa: no espaço sem rota para o DataZone, a chamada falha logo. Sem
    ``endpoint_url``, o ``boto3`` chama ``https://datazone.<região>.api.aws``, o padrão do SDK.
    """
    try:
        import boto3
        from botocore.config import Config
        from botocore.exceptions import BotoCoreError, ClientError
    except ImportError as error:
        raise KeyNotReadError(f"o boto3 não está neste Python ({sys.executable})") from error

    config = Config(connect_timeout=5, read_timeout=20, retries={"total_max_attempts": 1})
    try:
        # O perfil do SDK, quando o arquivo de configuração que o boto3 lê o tem.
        session = boto3.session.Session()
        if DOMAIN_PROFILE in session.available_profiles:
            session = boto3.session.Session(profile_name=DOMAIN_PROFILE)
        client = session.client(
            "datazone",
            region_name=region,
            endpoint_url=endpoint_url,
            config=config,
        )
        return client.get_environment(domainIdentifier=domain_id, identifier=environment_id)
    except (BotoCoreError, ClientError) as error:
        raise KeyNotReadError(f"o DataZone recusou ou não respondeu: {error}") from error


def project_key_id(
    metadata: Mapping[str, Any],
) -> str:
    """O id da chave KMS do projeto, do ``kmsKeyArn`` do ambiente do espaço no DataZone."""
    fields = metadata_fields(metadata, KEY_FIELDS)
    missing = [name for name in KEY_FIELDS if name not in fields]
    if missing:
        raise KeyNotReadError(f"campos ausentes nos metadados: {', '.join(missing)}")

    # O endpoint que o espaço grava, quando grava, é o que o SDK chama.
    endpoint = metadata_fields(metadata, ("DataZoneEndpoint",)).get("DataZoneEndpoint")
    environment = _get_environment(
        fields["DataZoneDomainId"],
        fields["DataZoneEnvironmentId"],
        fields["DataZoneDomainRegion"],
        endpoint,
    )
    resources = environment.get("provisionedResources") or []
    arns = [item.get("value", "") for item in resources if item.get("name") == "kmsKeyArn"]
    if not arns:
        names = ", ".join(str(item.get("name")) for item in resources) or "nenhum"
        raise KeyNotReadError(
            f"o ambiente {fields['DataZoneEnvironmentId']} não tem kmsKeyArn "
            f"(os recursos provisionados: {names})"
        )

    # O id é o que vem depois de key/ no ARN da chave.
    resource = arns[0].split(":", 5)[-1]
    if not resource.startswith("key/"):
        raise KeyNotReadError(f"kmsKeyArn não é o ARN de uma chave: {arns[0]}")
    return resource.removeprefix("key/")


def main() -> int:
    """Imprime os valores em JSON e devolve o código de saída: 1 quando os metadados não dão os
    valores, 0 nos outros casos, com ou sem a chave KMS."""
    try:
        metadata = load_metadata(METADATA_PATH)
        values = values_from_metadata(metadata, os.environ)
    except MetadataError as error:
        print(error, file=sys.stderr)
        return 1

    # Uma falha na leitura da chave deixa o resto do JSON valendo.
    try:
        values["PROJECT_KEY_ID"] = project_key_id(metadata)
    except KeyNotReadError as error:
        print(f"PROJECT_KEY_ID fora do JSON, para entrar à mão: {error}", file=sys.stderr)

    print(json.dumps(values, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
