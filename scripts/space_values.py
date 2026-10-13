"""Imprime, de dentro de um espaço do projeto, os valores de uma definição de workflow em JSON.

O script roda num espaço do projeto do SageMaker Unified Studio, no Python do próprio espaço, e
imprime o JSON de ``awsds-workflows values``, o formato de ``--values-file``. Ele não usa o pacote
nem o ``aws`` e não pede as permissões de IAM e EC2 que ``values`` pede: lê tudo pelo SDK
``sagemaker-studio`` do espaço, que escolhe sozinho o endpoint do DataZone e as credenciais.

O ``Project()`` do SDK dá o projeto e o domínio. Os outros valores vêm do ambiente Tooling padrão
do projeto, que o SDK acha (``get_project_default_environment``) e o DataZone descreve
(``GetEnvironment``). Desse ambiente o SDK tira o papel, o grupo de segurança, as sub-redes e a
chave de um job que ele cria, a chave de ``project.kms_key_arn`` e o caminho de
``project.s3.root``.

Os valores e de onde vêm:

- ``PROJECT_ID`` e ``DOMAIN_ID``: ``project.id`` e ``project.domain_id``;
- ``ACCOUNT_ID`` e ``REGION``: ``awsAccountId`` e ``awsAccountRegion`` do ambiente;
- ``PROJECT_ROLE_NAME``: o nome do papel de ``userRoleArn``;
- ``PROJECTS_BUCKET``: o bucket de ``s3BucketPath``;
- ``PROJECT_KEY_ID``: o id da chave de ``kmsKeyArn``, quando o ambiente tem esse recurso;
- ``PROJECT_SG``: ``securityGroup``;
- ``SUBNET_AZ1`` e ``SUBNET_AZ2``: as duas primeiras sub-redes de ``privateSubnets``, uma lista
  separada por vírgulas, na ordem do ambiente; ``values`` as ordena pela zona, que só o EC2
  informa.

Os nomes dos recursos vêm do código do SDK ``sagemaker-studio`` 1.1.35, igual ao da 1.1.32 nesse
ponto (lidos em 2026-10-11). Num espaço do laboratório, em 2026-10-11, o ambiente Tooling trouxe os
cinco recursos, e o JSON saiu igual, byte a byte, ao de ``values --profile`` na mesma conta, com as
sub-redes na ordem das zonas.
``JOB_IMAGE_URI`` e ``JOB_PYTHON`` não saem daqui: com a imagem padrão do SageMaker, eles entram
no arquivo de valores.

Só um projeto com chave KMS própria tem o ``kmsKeyArn``: o ambiente Tooling lido num espaço do
ambiente alvo em 2026-10-12 não o tinha. Sem ele, o JSON sai sem ``PROJECT_KEY_ID``, com um aviso
na saída de erro, e o SDK cria o job dele sem ``KmsKeyId`` e sem ``VolumeKmsKeyId``, dois campos
opcionais do ``CreateProcessingJob``.

Outro valor que o ambiente não dá termina com 1 e o motivo na saída de erro, sem JSON. Uma recusa
do DataZone ou outra falha do SDK também termina sem JSON, com o rastro do Python na saída de erro.

Uso, num terminal do espaço, com este arquivo copiado para lá:

    python space_values.py > space_values.json
"""

from __future__ import annotations

import json
import sys
from typing import Any
from urllib.parse import urlparse

# Os campos do ambiente que dão a conta e a região.
ENVIRONMENT_FIELDS = ("awsAccountId", "awsAccountRegion")

# Os recursos provisionados do ambiente que dão os outros valores.
RESOURCE_NAMES = ("privateSubnets", "s3BucketPath", "securityGroup", "userRoleArn")

# O recurso da chave KMS do projeto, que só um projeto com chave própria tem.
KEY_RESOURCE = "kmsKeyArn"

# O aviso, na saída de erro, de um ambiente sem a chave.
NO_KEY_WARNING = (
    "o ambiente Tooling não tem kmsKeyArn, a chave KMS do projeto: o JSON sai sem PROJECT_KEY_ID"
)


class ValuesError(Exception):
    """O motivo por que o ambiente Tooling do projeto não dá os valores."""


def _read_tooling_environment() -> tuple[str, str, dict[str, Any]]:
    """O id do projeto, o do domínio e o ambiente Tooling padrão do projeto, lidos pelo SDK
    ``sagemaker-studio``; é o ponto que os testes trocam.

    O SDK é importado aqui para uma falta dele virar uma mensagem em vez de um rastro.
    """
    try:
        from sagemaker_studio import Project, SageMakerStudioAPI
    except ImportError as error:
        raise ValuesError(
            f"o SDK sagemaker-studio não está neste Python ({sys.executable}): rode o script com "
            "o Python do espaço"
        ) from error

    # O SageMakerStudioAPI é um singleton: a chamada devolve a instância que o Project() usa,
    # refeita com a mesma configuração.
    project = Project()
    api = SageMakerStudioAPI()

    # O ambiente é achado e lido como em project.kms_key_arn.
    summary = api.project_api.get_project_default_environment(project.domain_id, project.id)
    environment = api.datazone_api.get_environment(
        domainIdentifier=project.domain_id,
        identifier=summary["id"],
    )
    return project.id, project.domain_id, environment


def provisioned_resources(
    environment: dict[str, Any],
) -> dict[str, str]:
    """O valor de cada recurso provisionado do ambiente, pelo nome; um recurso sem nome fica de
    fora."""
    resources = {}
    for resource in environment.get("provisionedResources", []):
        if resource.get("name"):
            resources[resource["name"]] = resource["value"]
    return resources


def split_list(
    text: str,
) -> list[str]:
    """Os itens de uma lista separada por vírgulas, sem espaços nem itens vazios."""
    items = []
    for item in text.split(","):
        if item.strip():
            items.append(item.strip())
    return items


def role_name_from_arn(
    arn: str,
) -> str:
    """O nome do papel de um ARN ``arn:aws:iam::<conta>:role/<nome>``; o caminho do papel, quando
    há, fica fora do nome."""
    parts = arn.split(":", 5)
    is_role = len(parts) == 6 and parts[2] == "iam" and parts[5].startswith("role/")
    if not is_role:
        raise ValuesError(f"userRoleArn não é o ARN de um papel do IAM: {arn}")
    return parts[5].rsplit("/", 1)[-1]


def bucket_from_path(
    path: str,
) -> str:
    """O bucket de um caminho ``s3://<bucket>/<prefixo>``."""
    parsed = urlparse(path)
    if parsed.scheme != "s3" or not parsed.netloc:
        raise ValuesError(f"s3BucketPath não é um caminho s3://: {path}")
    return parsed.netloc


def key_id_from_arn(
    arn: str,
) -> str:
    """O id da chave de um ARN ``arn:aws:kms:<região>:<conta>:key/<id>``."""
    resource = arn.split(":", 5)[-1]
    if not resource.startswith("key/"):
        raise ValuesError(f"kmsKeyArn não é o ARN de uma chave: {arn}")
    return resource.removeprefix("key/")


def values_from_environment(
    project_id: str,
    domain_id: str,
    environment: dict[str, Any],
) -> dict[str, str]:
    """Os valores da definição, dos ids do projeto e do domínio e do ambiente Tooling;
    ``PROJECT_KEY_ID`` só quando o ambiente tem ``kmsKeyArn``."""
    # O que falta vai todo na mensagem, com os recursos que o ambiente tem, para comparar.
    resources = provisioned_resources(environment)
    missing = [name for name in ENVIRONMENT_FIELDS if not environment.get(name)]
    missing += [name for name in RESOURCE_NAMES if not resources.get(name)]
    if missing:
        found = ", ".join(sorted(resources)) or "nenhum"
        raise ValuesError(
            f"o ambiente {environment.get('id')} não tem {', '.join(missing)} "
            f"(os recursos provisionados: {found})"
        )

    subnets = split_list(resources["privateSubnets"])
    if len(subnets) < 2:
        raise ValuesError(
            f"privateSubnets nomeia {len(subnets)} sub-redes, e o job pede duas zonas: "
            f"{resources['privateSubnets']}"
        )

    values = {
        "REGION": environment["awsAccountRegion"],
        "ACCOUNT_ID": environment["awsAccountId"],
        "PROJECT_ROLE_NAME": role_name_from_arn(resources["userRoleArn"]),
        "PROJECT_ID": project_id,
        "DOMAIN_ID": domain_id,
        "PROJECTS_BUCKET": bucket_from_path(resources["s3BucketPath"]),
        "PROJECT_SG": resources["securityGroup"],
        "SUBNET_AZ1": subnets[0],
        "SUBNET_AZ2": subnets[1],
    }

    # A chave entra só quando o projeto tem uma própria.
    if resources.get(KEY_RESOURCE):
        values["PROJECT_KEY_ID"] = key_id_from_arn(resources[KEY_RESOURCE])
    return values


def main() -> int:
    """Imprime os valores em JSON e devolve o código de saída: 1 quando o ambiente não dá os
    valores, 0 quando os imprime."""
    try:
        project_id, domain_id, environment = _read_tooling_environment()
        values = values_from_environment(project_id, domain_id, environment)
    except ValuesError as error:
        print(error, file=sys.stderr)
        return 1

    if "PROJECT_KEY_ID" not in values:
        print(NO_KEY_WARNING, file=sys.stderr)
    print(json.dumps(values, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
