"""``awsds_workflows.compare``: a comparação de duas definições de workflow pelo conteúdo do YAML.

``SAVED`` repete o que o portal fez com uma definição importada no laboratório (2026-10-10 e
2026-10-11): as chaves reordenadas, os textos longos dobrados em ``>-``, um deles no meio de um
template, as listas em bloco, o ``-c`` entre aspas, o layout do editor mantido e
``is_paused_upon_creation: false`` acrescentado. Os testes gravam os arquivos em ``tmp_path``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from awsds_workflows import compare
from awsds_workflows.errors import RefusalError

IMPORTED = """\
# {"wait_for_file":{"x":120,"y":200},"run_project":{"x":420,"y":200}}
meu-job:
  dag_id: meu-job
  tasks:
    wait_for_file:
      operator: airflow.providers.amazon.aws.sensors.s3.S3KeySensor
      bucket_key: s3://<PROJECTS_BUCKET>/<DOMAIN_ID>/<PROJECT_ID>/shared/meu-job/inbox/*
      wildcard_match: true
      retries: 0
    run_project:
      operator: airflow.providers.amazon.aws.operators.sagemaker.SageMakerProcessingOperator
      dependencies: [wait_for_file]
      retries: 0
      config:
        ProcessingJobName: "job-{{ macros.time.strftime('%Y%m%dT%H%M%S', macros.time.gmtime()) }}"
        RoleArn: arn:aws:iam::<ACCOUNT_ID>:role/<PROJECT_ROLE_NAME>
        AppSpecification:
          ImageUri: <JOB_IMAGE_URI>
          ContainerEntrypoint: [/bin/bash, -c]
          ContainerArguments:
            - 'exec <JOB_PYTHON> -m meu_pacote --input /opt/ml/processing/inbox --output out'
        ProcessingResources:
          ClusterConfig:
            InstanceCount: 1
            InstanceType: ml.t3.medium
            VolumeSizeInGB: 10
        NetworkConfig:
          EnableNetworkIsolation: true
          VpcConfig:
            Subnets: [<SUBNET_AZ1>, <SUBNET_AZ2>]
            SecurityGroupIds: [<PROJECT_SG>]
"""

SAVED = """\
# {"wait_for_file":{"x":120,"y":200},"run_project":{"x":420,"y":200}}
meu-job:
  dag_id: meu-job
  is_paused_upon_creation: false
  tasks:
    wait_for_file:
      operator: airflow.providers.amazon.aws.sensors.s3.S3KeySensor
      bucket_key: >-
        s3://<PROJECTS_BUCKET>/<DOMAIN_ID>/<PROJECT_ID>/shared/meu-job/inbox/*
      wildcard_match: true
      retries: 0
    run_project:
      dependencies:
        - wait_for_file
      operator: >-
        airflow.providers.amazon.aws.operators.sagemaker.SageMakerProcessingOperator
      retries: 0
      config:
        ProcessingJobName: >-
          job-{{ macros.time.strftime('%Y%m%dT%H%M%S',
          macros.time.gmtime()) }}
        AppSpecification:
          ImageUri: <JOB_IMAGE_URI>
          ContainerEntrypoint:
            - /bin/bash
            - "-c"
          ContainerArguments:
            - >-
              exec <JOB_PYTHON> -m meu_pacote --input
              /opt/ml/processing/inbox --output out
        ProcessingResources:
          ClusterConfig:
            InstanceType: ml.t3.medium
            InstanceCount: 1
            VolumeSizeInGB: 10
        RoleArn: >-
          arn:aws:iam::<ACCOUNT_ID>:role/<PROJECT_ROLE_NAME>
        NetworkConfig:
          EnableNetworkIsolation: true
          VpcConfig:
            Subnets:
              - <SUBNET_AZ1>
              - <SUBNET_AZ2>
            SecurityGroupIds:
              - <PROJECT_SG>
"""

INSTANCE_TYPE = "meu-job.tasks.run_project.config.ProcessingResources.ClusterConfig.InstanceType"


def compare_texts(
    tmp_path: Path,
    first: str,
    second: str,
) -> list[str]:
    """Grava os dois textos em ``tmp_path`` e compara os arquivos."""
    first_path = tmp_path / "primeiro.yaml"
    second_path = tmp_path / "segundo.yaml"
    first_path.write_text(first, encoding="utf-8")
    second_path.write_text(second, encoding="utf-8")
    return compare.compare_definitions(first_path, second_path)


def test_the_saved_definition_differs_only_by_the_pause_key(
    tmp_path: Path,
) -> None:
    """A ordem das chaves, as dobras, as aspas, a forma das listas e os comentários não contam, e
    sobra só a chave que o portal acrescenta."""
    differences = compare_texts(tmp_path, IMPORTED, SAVED)
    assert differences == ["+ meu-job.is_paused_upon_creation: false"]


def test_equal_definitions_have_no_difference(
    tmp_path: Path,
) -> None:
    """Uma definição comparada com ela mesma, com outro comentário, não tem diferença."""
    other_layout = IMPORTED.replace('"x":120', '"x":300')
    assert compare_texts(tmp_path, IMPORTED, other_layout) == []


def test_a_changed_value_gives_both_lines(
    tmp_path: Path,
) -> None:
    """Um valor que muda sai com ``-`` e o valor da primeira, e com ``+`` e o da segunda, pelo
    caminho de chaves."""
    changed = SAVED.replace("InstanceType: ml.t3.medium", "InstanceType: ml.m5.large")
    differences = compare_texts(tmp_path, IMPORTED, changed)
    assert differences == [
        f'- {INSTANCE_TYPE}: "ml.t3.medium"',
        f'+ {INSTANCE_TYPE}: "ml.m5.large"',
        "+ meu-job.is_paused_upon_creation: false",
    ]


@pytest.mark.parametrize(
    ("first", "second"),
    [("0", '"0"'), ("true", "1"), ("1", "1.0")],
)
def test_the_values_compare_with_their_type(
    tmp_path: Path,
    first: str,
    second: str,
) -> None:
    """Valores que o Python iguala, mas que o YAML escreve com tipos diferentes, diferem."""
    differences = compare_texts(tmp_path, f"retries: {first}\n", f"retries: {second}\n")
    assert differences == [f"- retries: {first}", f"+ retries: {second}"]


def test_the_lists_compare_position_by_position(
    tmp_path: Path,
) -> None:
    """As listas se comparam posição a posição, e o item além do fim da mais curta sai só de um
    lado."""
    differences = compare_texts(tmp_path, "dependencies: [a, b]\n", "dependencies: [b]\n")
    assert differences == [
        '- dependencies[0]: "a"',
        '+ dependencies[0]: "b"',
        '- dependencies[1]: "b"',
    ]


def test_the_differences_follow_the_key_order_of_the_first_definition(
    tmp_path: Path,
) -> None:
    """As diferenças seguem a ordem das chaves da primeira definição, e as chaves que só a segunda
    tem vêm no fim, na ordem dela."""
    first = "zeta: 1\nalfa: 1\n"
    second = "gama: 3\nalfa: 2\nbeta: 3\nzeta: 2\n"
    assert compare_texts(tmp_path, first, second) == [
        "- zeta: 1",
        "+ zeta: 2",
        "- alfa: 1",
        "+ alfa: 2",
        "+ gama: 3",
        "+ beta: 3",
    ]


def test_a_key_only_in_one_definition_shows_its_whole_value(
    tmp_path: Path,
) -> None:
    """Uma task que só a primeira tem sai inteira, em JSON numa linha, na ordem do arquivo."""
    first = "tasks:\n  remove_source:\n    retries: 0\n    bucket: <PROJECTS_BUCKET>\n"
    differences = compare_texts(tmp_path, first, "tasks: {}\n")
    assert differences == ['- tasks.remove_source: {"retries": 0, "bucket": "<PROJECTS_BUCKET>"}']


def test_a_date_is_written_as_text(
    tmp_path: Path,
) -> None:
    """Uma data, que o YAML lê como data e o JSON não representa, sai como texto."""
    differences = compare_texts(tmp_path, "dag_id: meu-job\n", "start_date: 2026-10-11\n")
    assert differences == ['- dag_id: "meu-job"', '+ start_date: "2026-10-11"']


def test_a_missing_file_is_refused(
    tmp_path: Path,
) -> None:
    """Um arquivo que não existe é recusado com o caminho na mensagem."""
    existing = tmp_path / "existe.yaml"
    existing.write_text("a: 1\n", encoding="utf-8")
    with pytest.raises(RefusalError, match="o arquivo .*falta.yaml não existe"):
        compare.compare_definitions(existing, tmp_path / "falta.yaml")


def test_invalid_yaml_is_refused_with_the_file_and_the_line(
    tmp_path: Path,
) -> None:
    """Um arquivo que não é YAML é recusado com o arquivo e a linha do erro."""
    with pytest.raises(RefusalError, match=r"segundo\.yaml não é YAML") as refusal:
        compare_texts(tmp_path, "a: 1\n", "a: 1\nb: [1\n")
    assert 'segundo.yaml", line 2' in str(refusal.value)


@pytest.mark.parametrize("content", ["- a\n- b\n", "", "# só um comentário\n"])
def test_a_definition_that_is_not_a_mapping_is_refused(
    tmp_path: Path,
    content: str,
) -> None:
    """Uma lista, um arquivo vazio ou só de comentários não são uma definição de workflow."""
    with pytest.raises(RefusalError, match="segundo.yaml não é uma definição de workflow"):
        compare_texts(tmp_path, "a: 1\n", content)
