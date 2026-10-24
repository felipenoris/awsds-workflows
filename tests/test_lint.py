"""O lint das aplicações da CLI de CI/CD: cada regra do módulo tem um caso que falha, e a recusa
nomeia a regra e o motivo; uma definição e uma aplicação fabricadas passam; cada aplicação de
``examples/`` passa no modo de autoria, com o manifest, a definição e os scripts copiados como os
arquivos lidos; e a cópia promovida de um exemplo, renderizada com valores fabricados, recusa só o
que a tradução por conta tem de trocar.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from awsds_workflows import lint, render
from awsds_workflows.errors import RefusalError
from test_examples import SPACE_VALUES, TO_FILL, extra_values_of

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
# As aplicações de examples/, as pastas com um manifest.yaml.
APPLICATIONS = sorted(path.parent for path in EXAMPLES.glob("*/manifest.yaml"))
APPLICATION_IDS = [application.name for application in APPLICATIONS]

# A variável da CLI com que todo caminho no bucket do projeto começa, e o prefixo da aplicação
# fabricada.
SHARED = "{proj.connection.default.s3_shared.s3Uri}"
PREFIX = f"{SHARED}exemplos/meu-workflow/"
# Um URI de imagem com digest, da conta de exemplo da AWS.
DIGEST = "sha256:" + "0" * 64
IMAGE_URI = f"111122223333.dkr.ecr.us-west-2.amazonaws.com/minha-imagem@{DIGEST}"
# O carimbo por execução que o serviço renderiza (laboratório, 2026-10-11).
STAMP = "{{ macros.time.strftime('%Y%m%dT%H%M%S', macros.time.gmtime()) }}"


def python_task() -> dict[str, Any]:
    """Uma task Python como a de ``demo-python-operator``, que passa na autoria."""
    return {
        "operator": "airflow.providers.standard.operators.python.PythonOperator",
        "python_callable": "tasks.run",
        "op_kwargs": {"inbox": f"{PREFIX}inbox/"},
        "retries": 0,
    }


def sensor_task() -> dict[str, Any]:
    """Um sensor de arquivo como o dos exemplos."""
    return {
        "operator": "airflow.providers.amazon.aws.sensors.s3.S3KeySensor",
        "bucket_key": f"{PREFIX}inbox/?*",
        "wildcard_match": True,
        "poke_interval": 30,
        "timeout": 600,
        "soft_fail": True,
        "retries": 0,
    }


def job_task() -> dict[str, Any]:
    """Uma task de processamento como a de ``demo-devenv-job``, que passa na autoria."""
    return {
        "operator": "airflow.providers.amazon.aws.operators.sagemaker.SageMakerProcessingOperator",
        "retries": 0,
        "config": {
            "ProcessingJobName": f"meu-job-{STAMP}",
            "RoleArn": "{proj.iam_role_arn}",
            "AppSpecification": {
                "ImageUri": "{env.JOB_IMAGE_URI}",
                "ContainerEntrypoint": ["/bin/bash", "-c"],
                "ContainerArguments": ["echo oi"],
            },
            "ProcessingResources": {
                "ClusterConfig": {
                    "InstanceCount": 1,
                    "InstanceType": "ml.t3.medium",
                    "VolumeSizeInGB": 10,
                }
            },
            "NetworkConfig": {
                "EnableNetworkIsolation": True,
                "EnableInterContainerTrafficEncryption": True,
                "VpcConfig": {
                    "Subnets": ["{env.SUBNET_AZ1}", "{env.SUBNET_AZ2}"],
                    "SecurityGroupIds": ["{env.PROJECT_SG}"],
                },
            },
            "ProcessingInputs": [
                {
                    "InputName": "code",
                    "S3Input": {"S3Uri": f"{PREFIX}src/", "LocalPath": "/opt/ml/processing/code"},
                }
            ],
            "StoppingCondition": {"MaxRuntimeInSeconds": 1800},
            "Tags": [{"Key": "AmazonDataZoneProject", "Value": "{proj.id}"}],
        },
    }


def glue_task() -> dict[str, Any]:
    """Uma task do Glue como a de ``houseprice-etl``, que passa na autoria."""
    return {
        "operator": "airflow.providers.amazon.aws.operators.glue.GlueJobOperator",
        "job_name": "meu-workflow-{proj.id}",
        "script_location": f"{PREFIX}glue/etl.py",
        "iam_role_arn": "{proj.iam_role_arn}",
        "script_args": {"--SOURCE_PATH": f"{PREFIX}entrada/"},
        "create_job_kwargs": {
            "Command": {"Name": "glueetl", "ScriptLocation": f"{PREFIX}glue/etl.py"},
            "DefaultArguments": {"--extra-py-files": f"{PREFIX}glue/lib.py,{PREFIX}glue/util.py"},
            "Tags": {"AmazonDataZoneProject": "{proj.id}"},
        },
        "retries": 0,
    }


def definition_text(
    tasks: dict[str, Any],
    **dag_keys: Any,
) -> str:
    """O YAML de uma definição com as tasks, o comentário de layout do editor na primeira linha
    e as chaves a mais no DAG."""
    document = {"meu-workflow": {"dag_id": "meu-workflow", **dag_keys, "tasks": tasks}}
    return '# {"run":{"x":120,"y":200}}\n' + yaml.safe_dump(document, sort_keys=False)


def lint_text(
    tmp_path: Path,
    text: str,
    **options: Any,
) -> list[lint.Finding]:
    """As recusas de ``lint_definition`` sobre o texto gravado em ``meu-workflow.yaml``."""
    path = tmp_path / "meu-workflow.yaml"
    path.write_text(text, encoding="utf-8")
    return lint.lint_definition(path, **options)


def lint_tasks(
    tmp_path: Path,
    tasks: dict[str, Any],
    **options: Any,
) -> list[lint.Finding]:
    """As recusas de uma definição com as tasks."""
    return lint_text(tmp_path, definition_text(tasks), **options)


def rules_of(
    findings: list[lint.Finding],
) -> list[str]:
    """As regras das recusas, na ordem."""
    return [finding.rule for finding in findings]


def test_a_python_task_and_a_sensor_pass(
    tmp_path: Path,
) -> None:
    """Uma definição como a dos exemplos passa sem recusa."""
    tasks = {"wait_for_file": sensor_task(), "run": python_task()}
    assert lint_tasks(tmp_path, tasks, prefixes=[PREFIX]) == []


def test_a_finding_prints_the_file_the_rule_and_the_reason(
    tmp_path: Path,
) -> None:
    """Uma recusa imprime ``arquivo: regra: motivo``."""
    task = python_task()
    del task["retries"]
    findings = lint_tasks(tmp_path, {"run": task})
    assert str(findings[0]) == f"{tmp_path / 'meu-workflow.yaml'}: limites: {findings[0].message}"


def test_a_missing_file_is_refused(
    tmp_path: Path,
) -> None:
    """Um arquivo que não existe é uma recusa, e não um achado."""
    with pytest.raises(RefusalError, match="não existe"):
        lint.lint_definition(tmp_path / "nada.yaml")


def test_a_text_that_is_not_yaml_fails_the_form(
    tmp_path: Path,
) -> None:
    """Um texto que o YAML não lê falha em ``forma``, com o erro do YAML."""
    findings = lint_text(tmp_path, "meu-workflow: [\n")
    assert rules_of(findings) == ["forma"]
    assert "não é YAML" in findings[0].message


def test_a_list_fails_the_form(
    tmp_path: Path,
) -> None:
    """Um YAML que não é um mapeamento falha em ``forma``."""
    findings = lint_text(tmp_path, "- a\n- b\n")
    assert rules_of(findings) == ["forma"]
    assert "não é um mapeamento" in findings[0].message


def test_two_top_keys_fail_the_form(
    tmp_path: Path,
) -> None:
    """O topo tem uma chave só, o nome do workflow."""
    findings = lint_text(tmp_path, "a:\n  tasks: {}\nb:\n  tasks: {}\n")
    assert rules_of(findings) == ["forma"]
    assert "tem 2: a, b" in findings[0].message


def test_a_workflow_without_tasks_fails_the_form(
    tmp_path: Path,
) -> None:
    """O workflow tem ``tasks``, um mapeamento com algo dentro."""
    findings = lint_text(tmp_path, "meu-workflow:\n  dag_id: meu-workflow\n  tasks: {}\n")
    assert rules_of(findings) == ["forma"]
    assert "não tem tasks" in findings[0].message


def test_a_task_that_is_not_a_mapping_fails_the_form(
    tmp_path: Path,
) -> None:
    """Cada task é um mapeamento."""
    findings = lint_text(tmp_path, "meu-workflow:\n  tasks:\n    run: oi\n")
    assert rules_of(findings) == ["forma"]
    assert "task run: não é um mapeamento" in findings[0].message


def test_a_task_without_an_operator_fails_the_form(
    tmp_path: Path,
) -> None:
    """Cada task tem ``operator``."""
    task = python_task()
    del task["operator"]
    findings = lint_tasks(tmp_path, {"run": task})
    assert rules_of(findings) == ["forma"]
    assert "task run: sem operator" in findings[0].message


def test_a_cli_variable_outside_the_table_fails_the_project_rule(
    tmp_path: Path,
) -> None:
    """Uma variável da CLI que o ``render`` não traduz é uma recusa ``projeto``."""
    task = python_task()
    task["op_kwargs"]["name"] = "{proj.name}"
    findings = lint_tasks(tmp_path, {"run": task})
    assert rules_of(findings) == ["projeto"]
    assert "sem tradução: {proj.name}" in findings[0].message


@pytest.mark.parametrize(
    ("value", "description"),
    [
        ("dzd_abc123", "um id de domínio"),
        ("datazone_usr_role_abc_def", "um papel de projeto"),
        ("arn:aws:s3:::smus-projects/x", "smus-projects"),
        ("dev/operatorFiles/x.zip", "a cópia do código que a CLI faz"),
        ("DataZoneProjectId", "uma variável DataZone*"),
        ("ProjectS3Path", "a variável ProjectS3Path"),
        ("alias/meu-project", "o alias de uma chave de projeto"),
    ],
)
def test_a_value_of_the_authoring_project_fails_the_project_rule(
    tmp_path: Path,
    value: str,
    description: str,
) -> None:
    """Um valor que só existe no projeto de autoria é uma recusa ``projeto``, com a linha."""
    task = python_task()
    task["op_kwargs"]["value"] = value
    findings = lint_tasks(tmp_path, {"run": task})
    assert rules_of(findings) == ["projeto"]
    assert description in findings[0].message
    assert findings[0].message.startswith("linha ")


def test_a_project_id_key_fails_the_project_rule(
    tmp_path: Path,
) -> None:
    """As chaves ``domain_id`` e ``project_id`` são do projeto de autoria."""
    findings = lint_tasks(tmp_path, {"run": python_task(), "project_id": {"operator": "x"}})
    assert "projeto" in rules_of(findings)


def test_the_project_tag_passes_in_authoring(
    tmp_path: Path,
) -> None:
    """A etiqueta ``AmazonDataZoneProject`` e a conexão de rede do projeto passam na autoria, onde
    os exemplos as levam."""
    assert lint_tasks(tmp_path, {"run": job_task(), "glue": glue_task()}) == []


def rendered_job(
    **cluster: Any,
) -> dict[str, Any]:
    """A task de processamento como uma cópia promovida a leva: valores literais, a imagem por
    digest e a chave do volume, com o que ``cluster`` muda em ``ClusterConfig``."""
    task = job_task()
    config = task["config"]
    config["RoleArn"] = "arn:aws:iam::111122223333:role/meu-papel"
    config["AppSpecification"]["ImageUri"] = IMAGE_URI
    config["NetworkConfig"]["VpcConfig"] = {
        "Subnets": ["subnet-0123456789abcdef0"],
        "SecurityGroupIds": ["sg-0123456789abcdef0"],
    }
    config["ProcessingInputs"][0]["S3Input"]["S3Uri"] = "s3://meu-bucket/meu-workflow/v1/src/"
    config["ProcessingResources"]["ClusterConfig"]["VolumeKmsKeyId"] = "alias/minha-chave"
    config["ProcessingResources"]["ClusterConfig"].update(cluster)
    del config["Tags"]
    return task


def test_a_promoted_copy_passes(
    tmp_path: Path,
) -> None:
    """Uma cópia promovida com valores literais passa, com o prefixo da versão."""
    findings = lint_tasks(
        tmp_path,
        {"run": rendered_job()},
        promoted=True,
        prefixes=["s3://meu-bucket/meu-workflow/v1/"],
        instance_types=["ml.t3.medium"],
        image_repository="minha-imagem",
    )
    assert findings == []


def test_a_cli_variable_left_in_a_promoted_copy_fails_the_project_rule(
    tmp_path: Path,
) -> None:
    """Uma variável da CLI numa cópia promovida está por renderizar."""
    task = rendered_job()
    task["config"]["RoleArn"] = "{proj.iam_role_arn}"
    findings = lint_tasks(tmp_path, {"run": task}, promoted=True)
    assert rules_of(findings) == ["projeto"]
    assert "variável da CLI por renderizar: {proj.iam_role_arn}" in findings[0].message


def test_a_placeholder_left_in_a_promoted_copy_fails_the_project_rule(
    tmp_path: Path,
) -> None:
    """Um placeholder numa cópia promovida está por preencher."""
    task = rendered_job()
    task["config"]["RoleArn"] = "<PROJECT_ROLE_ARN>"
    findings = lint_tasks(tmp_path, {"run": task}, promoted=True)
    assert rules_of(findings) == ["projeto"]
    assert "placeholder por preencher: <PROJECT_ROLE_ARN>" in findings[0].message


@pytest.mark.parametrize(
    ("value", "description"),
    [
        ("AmazonDataZoneProject", "a etiqueta AmazonDataZoneProject"),
        ("datazone-glue-network-connection-subnet-1-abc-dev", "uma conexão de rede do projeto"),
        ("datazone-abc123-dev", "um prefixo datazone-<projeto>-dev"),
    ],
)
def test_what_only_the_project_has_fails_a_promoted_copy(
    tmp_path: Path,
    value: str,
    description: str,
) -> None:
    """A etiqueta, a conexão de rede e o prefixo de logs do projeto não cabem numa cópia
    promovida."""
    task = rendered_job()
    task["config"]["Environment"] = {"VALUE": value}
    findings = lint_tasks(tmp_path, {"run": task}, promoted=True)
    assert rules_of(findings) == ["projeto"]
    assert description in findings[0].message


@pytest.mark.parametrize(
    ("dag_keys", "where"),
    [
        ({"start_date": "2026-10-17"}, "start_date no DAG"),
        ({"default_args": {"start_date": "2026-10-17"}}, "start_date em default_args"),
        ({"schedule": "0 6 * * *"}, "schedule no DAG"),
        ({"schedule_interval": "@daily"}, "schedule_interval no DAG"),
    ],
)
def test_a_date_or_a_schedule_fails_the_dates_rule(
    tmp_path: Path,
    dag_keys: dict[str, Any],
    where: str,
) -> None:
    """``start_date``, no DAG ou em ``default_args``, e ``schedule`` são recusas ``datas``."""
    findings = lint_text(tmp_path, definition_text({"run": python_task()}, **dag_keys))
    assert rules_of(findings) == ["datas"]
    assert where in findings[0].message


@pytest.mark.parametrize(
    "operator",
    [
        "airflow.providers.standard.operators.empty.EmptyOperator",
        "PythonOperator",
        "meu_modulo.MeuOperator",
    ],
)
def test_an_operator_the_service_does_not_run_fails_the_operator_rule(
    tmp_path: Path,
    operator: str,
) -> None:
    """Um operador fora do provedor Amazon que não é o Python nem o Bash do provedor standard,
    ou um nome sem módulo, é uma recusa ``operador``."""
    task = python_task()
    task["operator"] = operator
    findings = lint_tasks(tmp_path, {"run": task})
    assert rules_of(findings) == ["operador"]
    assert f"{operator} não é uma classe" in findings[0].message


def test_any_class_of_the_amazon_provider_passes(
    tmp_path: Path,
) -> None:
    """Qualquer classe de ``airflow.providers.amazon.aws.`` passa, sem tabela de nomes."""
    task = {
        "operator": "airflow.providers.amazon.aws.operators.athena.AthenaOperator",
        "query": "select 1",
        "retries": 0,
    }
    assert lint_tasks(tmp_path, {"run": task}) == []


def test_the_notebook_operator_is_refused_by_name(
    tmp_path: Path,
) -> None:
    """``SageMakerNotebookOperator`` é recusado pelo nome, com o motivo."""
    task = python_task()
    task["operator"] = "airflow.providers.amazon.aws.operators.sagemaker.SageMakerNotebookOperator"
    findings = lint_tasks(tmp_path, {"run": task})
    assert rules_of(findings) == ["operador"]
    assert "SageMakerNotebookOperator: uma task de notebook" in findings[0].message


def test_retries_absent_fails_the_limits_rule(
    tmp_path: Path,
) -> None:
    """``retries`` escrito em cada task, porque o serviço assume 1."""
    task = python_task()
    del task["retries"]
    findings = lint_tasks(tmp_path, {"run": task})
    assert rules_of(findings) == ["limites"]
    assert "retries ausente" in findings[0].message


@pytest.mark.parametrize("retries", [4, -1, True, "0"])
def test_retries_outside_zero_to_three_fails_the_limits_rule(
    tmp_path: Path,
    retries: Any,
) -> None:
    """``retries`` é um número de 0 a 3; um ``bool`` ou um texto não conta."""
    task = python_task()
    task["retries"] = retries
    findings = lint_tasks(tmp_path, {"run": task})
    assert rules_of(findings) == ["limites"]
    assert f"retries {retries!r} fora de 0 a 3" in findings[0].message


@pytest.mark.parametrize(
    ("key", "value", "limit"),
    [
        ("retry_delay", 301, 300),
        ("retry_delay_sec", 301, 300),
        ("execution_timeout", 3601, 3600),
        ("execution_timeout_secs", 3601, 3600),
        ("timeout", 3601, 3600),
    ],
)
def test_a_time_above_the_service_limit_fails_the_limits_rule(
    tmp_path: Path,
    key: str,
    value: int,
    limit: int,
) -> None:
    """``retry_delay`` até 300 s e ``execution_timeout`` e o ``timeout`` de um sensor até 3.600 s,
    nas grafias do Airflow e do dag-factory."""
    task = sensor_task()
    task[key] = value
    findings = lint_tasks(tmp_path, {"wait": task})
    assert rules_of(findings) == ["limites"]
    assert f"{key} {value} acima dos {limit} s" in findings[0].message


def test_a_definition_above_the_quota_fails_the_limits_rule(
    tmp_path: Path,
) -> None:
    """Uma definição acima de 50.000 bytes, a cota do serviço, é uma recusa ``limites``."""
    text = "# " + "x" * 50_000 + "\n" + definition_text({"run": python_task()})
    findings = lint_text(tmp_path, text)
    assert rules_of(findings) == ["limites"]
    assert "acima dos 50000 da cota" in findings[0].message


@pytest.mark.parametrize(
    "image",
    [
        "111122223333.dkr.ecr.us-west-2.amazonaws.com/minha-imagem:v1",
        "111122223333.dkr.ecr.us-west-2.amazonaws.com/minha-imagem",
        "public.ecr.aws/sagemaker/sagemaker-distribution:4.5.2-cpu",
    ],
)
def test_an_image_without_a_digest_fails_the_image_rule(
    tmp_path: Path,
    image: str,
) -> None:
    """Um ``ImageUri`` literal é um URI do ECR com digest."""
    task = job_task()
    task["config"]["AppSpecification"]["ImageUri"] = image
    findings = lint_tasks(tmp_path, {"run": task})
    assert rules_of(findings) == ["imagem"]
    assert f"ImageUri {image} não é um URI do ECR com digest" in findings[0].message


def test_an_image_of_another_repository_fails_the_image_rule(
    tmp_path: Path,
) -> None:
    """Com ``image_repository``, a imagem é desse repositório."""
    task = job_task()
    task["config"]["AppSpecification"]["ImageUri"] = IMAGE_URI
    findings = lint_tasks(tmp_path, {"run": task}, image_repository="outra-imagem")
    assert rules_of(findings) == ["imagem"]
    assert "do repositório minha-imagem, e não de outra-imagem" in findings[0].message


def test_an_image_placeholder_passes_only_in_authoring(
    tmp_path: Path,
) -> None:
    """``{env.JOB_IMAGE_URI}`` passa na autoria e falha no modo promovido, por renderizar e sem
    digest."""
    assert lint_tasks(tmp_path, {"run": job_task()}) == []
    task = rendered_job()
    task["config"]["AppSpecification"]["ImageUri"] = "<JOB_IMAGE_URI>"
    findings = lint_tasks(tmp_path, {"run": task}, promoted=True)
    assert rules_of(findings) == ["projeto", "imagem"]


def test_a_job_without_config_fails_the_job_rule(
    tmp_path: Path,
) -> None:
    """Uma task de processamento tem ``config``, a chamada ``CreateProcessingJob``."""
    task = job_task()
    del task["config"]
    findings = lint_tasks(tmp_path, {"run": task})
    assert rules_of(findings) == ["job"]
    assert "sem config" in findings[0].message


@pytest.mark.parametrize("key", ["Subnets", "SecurityGroupIds"])
def test_a_job_without_the_vpc_fails_the_job_rule(
    tmp_path: Path,
    key: str,
) -> None:
    """``NetworkConfig.VpcConfig`` tem ``Subnets`` e ``SecurityGroupIds`` com algo dentro."""
    task = job_task()
    task["config"]["NetworkConfig"]["VpcConfig"][key] = []
    findings = lint_tasks(tmp_path, {"run": task})
    assert rules_of(findings) == ["job"]
    assert f"VpcConfig.{key} ausente ou vazio" in findings[0].message


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("EnableNetworkIsolation", False),
        ("EnableNetworkIsolation", "true"),
        ("EnableInterContainerTrafficEncryption", None),
    ],
)
def test_a_job_without_isolation_or_encryption_fails_the_job_rule(
    tmp_path: Path,
    key: str,
    value: Any,
) -> None:
    """O isolamento de rede e a cifra entre contêineres são ``true``, o booleano."""
    task = job_task()
    if value is None:
        del task["config"]["NetworkConfig"][key]
    else:
        task["config"]["NetworkConfig"][key] = value
    findings = lint_tasks(tmp_path, {"run": task})
    assert rules_of(findings) == ["job"]
    assert f"NetworkConfig.{key} tem de ser true" in findings[0].message


def test_a_job_without_a_runtime_limit_fails_the_job_rule(
    tmp_path: Path,
) -> None:
    """``StoppingCondition.MaxRuntimeInSeconds`` está escrito."""
    task = job_task()
    del task["config"]["StoppingCondition"]
    findings = lint_tasks(tmp_path, {"run": task})
    assert rules_of(findings) == ["job"]
    assert "MaxRuntimeInSeconds ausente" in findings[0].message


def test_a_job_above_the_task_ceiling_fails_the_job_rule(
    tmp_path: Path,
) -> None:
    """``MaxRuntimeInSeconds`` até 2.820 s, o que cabe nos 3.600 s da task."""
    task = job_task()
    task["config"]["StoppingCondition"]["MaxRuntimeInSeconds"] = 2821
    findings = lint_tasks(tmp_path, {"run": task})
    assert rules_of(findings) == ["job"]
    assert "MaxRuntimeInSeconds 2821 acima dos 2820 s" in findings[0].message


def test_an_instance_type_outside_the_list_fails_the_job_rule(
    tmp_path: Path,
) -> None:
    """Com ``instance_types``, o job pede um deles."""
    findings = lint_tasks(tmp_path, {"run": job_task()}, instance_types=["ml.m5.xlarge"])
    assert rules_of(findings) == ["job"]
    assert "InstanceType ml.t3.medium fora de ml.m5.xlarge" in findings[0].message


def test_the_volume_key_is_required_only_in_a_promoted_copy(
    tmp_path: Path,
) -> None:
    """``VolumeKmsKeyId`` falta sem recusa na autoria e é uma recusa ``job`` no modo
    promovido."""
    task = rendered_job(VolumeKmsKeyId=None)
    del task["config"]["ProcessingResources"]["ClusterConfig"]["VolumeKmsKeyId"]
    assert lint_tasks(tmp_path, {"run": task}) == []
    findings = lint_tasks(tmp_path, {"run": task}, promoted=True)
    assert rules_of(findings) == ["job"]
    assert "VolumeKmsKeyId ausente" in findings[0].message


@pytest.mark.parametrize(
    "template",
    [
        "{{ dag_run.run_id }}",
        "{{ run_id }}",
        "{{ logical_date }}",
        "{{ macros.datetime.utcnow().strftime('%Y') }}",
    ],
)
def test_a_template_the_service_does_not_render_fails_the_templates_rule(
    tmp_path: Path,
    template: str,
) -> None:
    """Um nome fora dos que o serviço renderiza, ou um método sobre o que uma macro devolveu, é
    uma recusa ``templates``."""
    task = python_task()
    task["op_kwargs"]["stamp"] = f"saida/{template}/"
    findings = lint_tasks(tmp_path, {"run": task})
    assert rules_of(findings) == ["templates"]
    assert template in findings[0].message


@pytest.mark.parametrize("template", [STAMP, "{{ ds }}", "{{ ts_nodash }}", "{{ params.x }}"])
def test_a_template_the_service_renders_passes(
    tmp_path: Path,
    template: str,
) -> None:
    """O carimbo por execução e os nomes que o serviço renderiza passam."""
    task = python_task()
    task["op_kwargs"]["stamp"] = f"saida/{template}/"
    assert lint_tasks(tmp_path, {"run": task}) == []


def test_a_code_input_outside_the_prefixes_fails_the_code_rule(
    tmp_path: Path,
) -> None:
    """A entrada de código do job está sob um dos prefixos, e nada é conferido sem prefixos."""
    task = job_task()
    task["config"]["ProcessingInputs"][0]["S3Input"]["S3Uri"] = f"{SHARED}exemplos/outro/src/"
    assert lint_tasks(tmp_path, {"run": task}) == []
    findings = lint_tasks(tmp_path, {"run": task}, prefixes=[PREFIX])
    assert rules_of(findings) == ["codigo"]
    assert "a entrada de código" in findings[0].message


def test_the_code_input_is_found_by_its_local_path(
    tmp_path: Path,
) -> None:
    """A entrada de código é a de ``LocalPath`` ``/opt/ml/processing/code`` mesmo com outro
    nome."""
    task = job_task()
    code_input = task["config"]["ProcessingInputs"][0]
    code_input["InputName"] = "fontes"
    code_input["S3Input"]["S3Uri"] = f"{SHARED}exemplos/outro/src/"
    findings = lint_tasks(tmp_path, {"run": task}, prefixes=[PREFIX])
    assert rules_of(findings) == ["codigo"]


def test_a_glue_script_outside_the_prefixes_fails_the_glue_rule(
    tmp_path: Path,
) -> None:
    """O script do job do Glue, em ``script_location`` e em ``Command.ScriptLocation``, está sob
    um dos prefixos."""
    task = glue_task()
    task["create_job_kwargs"]["Command"]["ScriptLocation"] = f"{SHARED}exemplos/outro/etl.py"
    assert lint_tasks(tmp_path, {"run": task}) == []
    findings = lint_tasks(tmp_path, {"run": task}, prefixes=[PREFIX])
    assert rules_of(findings) == ["glue"]
    assert "exemplos/outro/etl.py está fora de" in findings[0].message


def test_a_glue_extra_file_outside_the_prefixes_fails_the_glue_rule(
    tmp_path: Path,
) -> None:
    """Cada arquivo de ``--extra-py-files``, separado por vírgula, está sob um dos prefixos."""
    task = glue_task()
    arguments = task["create_job_kwargs"]["DefaultArguments"]
    arguments["--extra-py-files"] = f"{PREFIX}glue/lib.py,{SHARED}exemplos/outro/util.py"
    findings = lint_tasks(tmp_path, {"run": task}, prefixes=[PREFIX])
    assert rules_of(findings) == ["glue"]
    assert "exemplos/outro/util.py está fora de" in findings[0].message


def rendered_glue() -> dict[str, Any]:
    """A task do Glue como uma cópia promovida a leva: o nome do job, que o Terraform da
    aplicação cria na conta, e os argumentos da execução."""
    return {
        "operator": "airflow.providers.amazon.aws.operators.glue.GlueJobOperator",
        "job_name": "meu-workflow-glue",
        "script_args": {"--SOURCE_PATH": "s3://meu-bucket/meu-workflow/v1/entrada/"},
        "retries": 0,
    }


def test_a_promoted_glue_task_that_only_starts_the_job_passes(
    tmp_path: Path,
) -> None:
    """Uma task do Glue que só nomeia o job e os argumentos da execução passa no modo
    promovido."""
    findings = lint_tasks(
        tmp_path,
        {"glue": rendered_glue()},
        promoted=True,
        prefixes=["s3://meu-bucket/meu-workflow/v1/"],
    )
    assert findings == []


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("create_job_kwargs", {"GlueVersion": "5.0"}),
        ("script_location", "s3://meu-bucket/meu-workflow/v1/glue/etl.py"),
        ("iam_role_arn", "arn:aws:iam::111122223333:role/meu-papel"),
        ("update_config", True),
        ("job_desc", "o job da aplicação"),
    ],
)
def test_a_glue_task_that_creates_the_job_fails_a_promoted_copy(
    tmp_path: Path,
    key: str,
    value: Any,
) -> None:
    """Numa cópia promovida, o job do Glue é do Terraform da aplicação: cada chave com que o
    operador cria ou atualiza o job é uma recusa ``glue``; na autoria, onde o operador cria o
    job no projeto, ela passa."""
    task = rendered_glue()
    task[key] = value
    assert lint_tasks(tmp_path, {"glue": task}) == []
    findings = lint_tasks(
        tmp_path,
        {"glue": task},
        promoted=True,
        prefixes=["s3://meu-bucket/meu-workflow/v1/"],
    )
    assert rules_of(findings) == ["glue"]
    assert f"task glue: {key} numa cópia promovida" in findings[0].message


# O prefixo da pasta glue/ de uma versão no bucket, sob o qual o job do plano lê os arquivos.
GLUE_PREFIX = "s3://meu-bucket/applications/meu-app/v1.0.0/glue/"


def glue_job_change(
    address: str = "aws_glue_job.this[0]",
    actions: tuple[str, ...] = ("create",),
    **job: Any,
) -> dict[str, Any]:
    """Uma mudança de ``aws_glue_job`` como o ``terraform show -json`` do Terraform 1.15.8 com o
    provedor AWS 6.60.0 a imprimiu (2026-10-23): o ``command`` é uma lista de um bloco, e os
    mapeamentos de argumentos, ``null`` quando o job não os tem; ``job`` troca os valores do job
    depois do ``apply``."""
    after = {
        "name": "meu-app",
        "command": [
            {"name": "glueetl", "python_version": "3", "script_location": f"{GLUE_PREFIX}etl.py"}
        ],
        "default_arguments": None,
        "non_overridable_arguments": None,
        **job,
    }
    return {
        "address": address,
        "mode": "managed",
        "type": "aws_glue_job",
        "name": address.rpartition(".")[2],
        "change": {"actions": list(actions), "after": after},
    }


def plan_document(
    *changes: dict[str, Any],
) -> dict[str, Any]:
    """O JSON de um plano com as mudanças; sem mudança, sem ``resource_changes``, como o
    Terraform 1.15.8 imprime um plano sem recursos (2026-10-23)."""
    document: dict[str, Any] = {
        "format_version": "1.2",
        "terraform_version": "1.15.8",
        "planned_values": {"root_module": {}},
    }
    if changes:
        document["resource_changes"] = list(changes)
    return document


def lint_plan_of(
    tmp_path: Path,
    document: Any,
) -> lint.PlanReport:
    """O ``lint_plan`` do documento gravado em ``plano.json``, com o prefixo da pasta glue/."""
    path = tmp_path / "plano.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return lint.lint_plan(path, prefixes=[GLUE_PREFIX])


def test_a_plan_whose_glue_job_lies_under_the_prefix_passes(
    tmp_path: Path,
) -> None:
    """Um job com o script, os arquivos e uma roda sob o prefixo passa, e o relatório traz o
    endereço do job; um recurso de outro tipo fica de fora."""
    job = glue_job_change(
        default_arguments={
            "--extra-py-files": f"{GLUE_PREFIX}lib.py,{GLUE_PREFIX}util.py",
            "--additional-python-modules": f"{GLUE_PREFIX}minha_lib-1.0-py3-none-any.whl",
            "--SOURCE_PATH": "s3://meu-bucket/entrada/",
        }
    )
    other = {
        "address": "terraform_data.keep",
        "mode": "managed",
        "type": "terraform_data",
        "change": {"actions": ["create"], "after": {"input": "s3://outro-bucket/x.py"}},
    }
    report = lint_plan_of(tmp_path, plan_document(job, other))
    assert report.findings == []
    assert report.jobs == ["aws_glue_job.this[0]"]


def test_a_plan_without_resources_reads_no_job(
    tmp_path: Path,
) -> None:
    """Um plano sem recursos, sem ``resource_changes``, passa sem job lido."""
    report = lint_plan_of(tmp_path, plan_document())
    assert report.findings == []
    assert report.jobs == []


def test_a_glue_script_outside_the_prefix_fails_the_plan(
    tmp_path: Path,
) -> None:
    """O ``command.script_location`` do job está sob um dos prefixos."""
    command = [{"name": "glueetl", "script_location": "s3://outro-bucket/etl.py"}]
    report = lint_plan_of(tmp_path, plan_document(glue_job_change(command=command)))
    assert rules_of(report.findings) == ["glue"]
    assert report.findings[0].message == (
        f"aws_glue_job.this[0]: o script s3://outro-bucket/etl.py está fora de {GLUE_PREFIX}"
    )


@pytest.mark.parametrize(
    ("field", "key"),
    [
        ("default_arguments", "--extra-py-files"),
        ("default_arguments", "--extra-jars"),
        ("default_arguments", "--extra-files"),
        ("default_arguments", "--additional-python-modules"),
        ("non_overridable_arguments", "--extra-files"),
    ],
)
def test_a_glue_file_outside_the_prefix_fails_the_plan(
    tmp_path: Path,
    field: str,
    key: str,
) -> None:
    """Cada arquivo dos argumentos do job, separado por vírgula, nos dois mapeamentos, está sob
    um dos prefixos."""
    arguments = {key: f"{GLUE_PREFIX}bom.py, s3://outro-bucket/ruim.py"}
    report = lint_plan_of(tmp_path, plan_document(glue_job_change(**{field: arguments})))
    assert rules_of(report.findings) == ["glue"]
    assert report.findings[0].message == (
        f"aws_glue_job.this[0]: {key} s3://outro-bucket/ruim.py está fora de {GLUE_PREFIX}"
    )


def test_a_pypi_module_fails_the_plan(
    tmp_path: Path,
) -> None:
    """Um item de ``--additional-python-modules`` que não é ``s3://`` é um nome do PyPI, que o
    job baixaria pela internet."""
    arguments = {"--additional-python-modules": "pandas==2.2.3"}
    report = lint_plan_of(tmp_path, plan_document(glue_job_change(default_arguments=arguments)))
    assert rules_of(report.findings) == ["glue"]
    assert "--additional-python-modules pandas==2.2.3 não é um s3://" in report.findings[0].message


def test_a_script_the_plan_does_not_know_yet_fails_the_plan(
    tmp_path: Path,
) -> None:
    """Um ``script_location`` calculado no ``apply`` falta no ``command`` do plano, como o
    Terraform 1.15.8 o imprime (2026-10-23), e não se confere."""
    report = lint_plan_of(tmp_path, plan_document(glue_job_change(command=[{"name": "glueetl"}])))
    assert rules_of(report.findings) == ["glue"]
    assert "command.script_location desconhecido no plano" in report.findings[0].message


def test_a_glue_job_in_a_module_left_unchanged_is_read(
    tmp_path: Path,
) -> None:
    """Um job de um módulo, que o plano mantém (``no-op``), existe depois do ``apply`` e é
    conferido."""
    change = glue_job_change(
        address="module.app.aws_glue_job.etl",
        actions=("no-op",),
        command=[{"name": "glueetl", "script_location": "s3://outro-bucket/etl.py"}],
    )
    report = lint_plan_of(tmp_path, plan_document(change))
    assert report.jobs == ["module.app.aws_glue_job.etl"]
    assert rules_of(report.findings) == ["glue"]


def test_a_glue_job_the_plan_deletes_is_not_read(
    tmp_path: Path,
) -> None:
    """Um job que o plano apaga, com ``after`` nulo, não existe depois do ``apply``."""
    change = glue_job_change(actions=("delete",))
    change["change"]["after"] = None
    report = lint_plan_of(tmp_path, plan_document(change))
    assert report.jobs == []
    assert report.findings == []


@pytest.mark.parametrize(
    ("document", "reason"),
    [
        ("não é json", "não é JSON"),
        (["uma", "lista"], "sem planned_values"),
        ({"format_version": "1.0", "values": {"root_module": {}}}, "sem planned_values"),
    ],
)
def test_a_file_that_is_not_a_plan_fails_the_form(
    tmp_path: Path,
    document: Any,
    reason: str,
) -> None:
    """Um texto que não é JSON, ou um JSON sem ``planned_values``, como o de um state, falha em
    ``forma``."""
    path = tmp_path / "plano.json"
    if isinstance(document, str):
        path.write_text(document, encoding="utf-8")
    else:
        path.write_text(json.dumps(document), encoding="utf-8")
    report = lint.lint_plan(path, prefixes=[GLUE_PREFIX])
    assert rules_of(report.findings) == ["forma"]
    assert reason in report.findings[0].message
    assert report.jobs == []


def test_a_missing_plan_is_refused(
    tmp_path: Path,
) -> None:
    """Um plano que não existe é uma recusa, e não um achado."""
    with pytest.raises(RefusalError, match="não existe"):
        lint.lint_plan(tmp_path / "nada.json", prefixes=[GLUE_PREFIX])


def manifest_document(
    name: str = "meu-workflow",
    code: str | None = None,
) -> dict[str, Any]:
    """O manifest de uma aplicação fabricada como as de ``examples/``: ``code/tasks.zip``
    (quando há ``code``), ``src/meu-workflow.tar.gz``, ``glue/`` e ``workflows/`` copiados sob
    ``exemplos/<nome>/`` nos dois stages."""
    storage = [
        {"name": "src", "include": ["src/meu-workflow.tar.gz"]},
        {"name": "glue", "include": ["glue/"], "exclude": ["__pycache__/", "*.pyc"]},
        {"name": "workflows", "include": ["workflows/"]},
    ]
    workflow: dict[str, Any] = {
        "workflowName": name,
        "connectionName": "default.workflow_serverless",
    }
    if code is not None:
        storage.insert(0, {"name": "code", "include": ["code/tasks.zip"]})
        workflow["code"] = code
    stages = {}
    for stage in ("dev", "test"):
        actions: list[dict[str, Any]] = [{"type": "workflow.create", "workflowName": name}]
        if stage == "test":
            actions.append({"type": "workflow.run", "workflowName": name, "trailLogs": True})
        targets = []
        for item in storage:
            target = f"exemplos/{name}/{item['name']}"
            targets.append(
                {
                    "name": item["name"],
                    "connectionName": "default.s3_shared",
                    "targetDirectory": target,
                }
            )
        stages[stage] = {
            "stage": stage.upper(),
            "domain": {"id": "${DOMAIN_ID}", "region": "${DOMAIN_REGION}"},
            "project": {"name": "${PROJECT_NAME}"},
            "environment_variables": {
                "SUBNET_AZ1": "${SUBNET_AZ1}",
                "SUBNET_AZ2": "${SUBNET_AZ2}",
                "PROJECT_SG": "${PROJECT_SG}",
                "JOB_IMAGE_URI": "${JOB_IMAGE_URI}",
            },
            "bootstrap": {"actions": actions},
            "deployment_configuration": {"storage": targets},
        }
    return {
        "applicationName": name,
        "content": {"storage": storage, "workflows": [workflow]},
        "stages": stages,
    }


def write_application(
    folder: Path,
    manifest: dict[str, Any],
    tasks: dict[str, Any],
) -> Path:
    """Grava uma aplicação fabricada: o manifest, a definição em ``workflows/`` e um script em
    ``glue/``, e devolve a pasta."""
    folder.mkdir()
    (folder / "manifest.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
    )
    (folder / "workflows").mkdir()
    (folder / "workflows" / "meu-workflow.yaml").write_text(
        definition_text(tasks), encoding="utf-8"
    )
    (folder / "glue").mkdir()
    (folder / "glue" / "etl.py").write_text("print('oi')\n", encoding="utf-8")
    return folder


def test_an_application_passes_with_its_files_read(
    tmp_path: Path,
) -> None:
    """Uma aplicação fabricada passa, e os arquivos lidos são o manifest, a definição e o
    script copiado."""
    folder = write_application(tmp_path / "app", manifest_document(), {"run": job_task()})
    report = lint.lint_application(folder)
    assert report.findings == []
    assert report.files == [
        folder / "manifest.yaml",
        folder / "workflows" / "meu-workflow.yaml",
        folder / "glue" / "etl.py",
    ]


def test_a_missing_folder_or_manifest_is_refused(
    tmp_path: Path,
) -> None:
    """Uma pasta que não existe, ou sem ``manifest.yaml``, não é uma aplicação."""
    with pytest.raises(RefusalError, match="não existe"):
        lint.lint_application(tmp_path / "nada")
    with pytest.raises(RefusalError, match="não tem manifest.yaml"):
        lint.lint_application(tmp_path)


def test_a_manifest_without_its_keys_fails_the_form(
    tmp_path: Path,
) -> None:
    """O manifest tem ``applicationName``, ``content`` e ``stages``."""
    folder = tmp_path / "app"
    folder.mkdir()
    (folder / "manifest.yaml").write_text("applicationName: x\n", encoding="utf-8")
    report = lint.lint_application(folder)
    assert rules_of(report.findings) == ["forma", "forma"]
    assert [finding.message for finding in report.findings] == ["sem content", "sem stages"]


def test_an_excluded_file_is_not_read(
    tmp_path: Path,
) -> None:
    """Um ``exclude`` por pasta ou por nome deixa o arquivo fora dos lidos."""
    folder = write_application(tmp_path / "app", manifest_document(), {"run": job_task()})
    (folder / "glue" / "__pycache__").mkdir()
    (folder / "glue" / "__pycache__" / "etl.py").write_text("dzd_abc\n", encoding="utf-8")
    (folder / "glue" / "etl.pyc").write_text("dzd_abc\n", encoding="utf-8")
    report = lint.lint_application(folder)
    assert report.findings == []
    assert folder / "glue" / "etl.py" in report.files


def test_a_project_value_in_a_copied_script_fails_the_project_rule(
    tmp_path: Path,
) -> None:
    """Um script de uma pasta copiada passa pelos padrões de projeto, com o arquivo na recusa."""
    folder = write_application(tmp_path / "app", manifest_document(), {"run": job_task()})
    script = folder / "glue" / "etl.py"
    script.write_text("ROLE = 'datazone_usr_role_abc_def'\n", encoding="utf-8")
    report = lint.lint_application(folder)
    assert rules_of(report.findings) == ["projeto"]
    assert report.findings[0].path == script


def test_the_prefixes_of_an_application_are_the_folders_every_stage_copies(
    tmp_path: Path,
) -> None:
    """A entrada de código fora das pastas que o manifest copia, ou numa que só um stage copia,
    é uma recusa ``codigo``."""
    task = job_task()
    task["config"]["ProcessingInputs"][0]["S3Input"]["S3Uri"] = f"{SHARED}exemplos/outro/src/"
    folder = write_application(tmp_path / "app", manifest_document(), {"run": task})
    report = lint.lint_application(folder)
    assert rules_of(report.findings) == ["codigo"]

    manifest = manifest_document()
    del manifest["stages"]["test"]["deployment_configuration"]["storage"][0]
    folder = write_application(tmp_path / "outra", manifest, {"run": job_task()})
    report = lint.lint_application(folder)
    assert rules_of(report.findings) == ["codigo"]


def test_a_storage_item_with_a_connection_fails_the_manifest_rule(
    tmp_path: Path,
) -> None:
    """Um item de ``content.storage`` com ``connectionName`` faz o bundle ler o projeto."""
    manifest = manifest_document()
    manifest["content"]["storage"][0]["connectionName"] = "default.s3_shared"
    folder = write_application(tmp_path / "app", manifest, {"run": job_task()})
    report = lint.lint_application(folder)
    assert rules_of(report.findings) == ["manifest"]
    assert "content.storage src: com connectionName" in report.findings[0].message


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ({"git": {"repository": "x"}}, "content.git"),
        ({"catalog": {"enabled": True}}, "content.catalog.enabled"),
        ({"notebooks": {"enabled": True}}, "content.notebooks.enabled"),
        ({"quicksight": [{"name": "painel"}]}, "content.quicksight painel: assetBundle ausente"),
        ({"quicksight": [{"name": "p", "assetBundle": "export"}]}, "content.quicksight p"),
    ],
)
def test_content_read_from_outside_the_tag_fails_the_manifest_rule(
    tmp_path: Path,
    content: dict[str, Any],
    message: str,
) -> None:
    """``git``, o catálogo e os notebooks ligados e um painel exportado do serviço levam ao
    bundle o que não está na tag."""
    manifest = manifest_document()
    manifest["content"].update(content)
    folder = write_application(tmp_path / "app", manifest, {"run": job_task()})
    report = lint.lint_application(folder)
    assert rules_of(report.findings) == ["manifest"]
    assert message in report.findings[0].message


@pytest.mark.parametrize("pattern", ["src/*.tar.gz", "src/meu-workflow.tar.g?", "src/[ab].tar.gz"])
def test_a_glob_include_fails_the_manifest_rule(
    tmp_path: Path,
    pattern: str,
) -> None:
    """Um ``include`` com glob fica fora do bundle: o ``bundle`` da CLI 1.0.9 lê um ``include``
    como arquivo ou pasta, e um glob imprime ``Warning: Pattern not found`` e termina com 0
    (2026-10-23)."""
    manifest = manifest_document()
    manifest["content"]["storage"][0]["include"] = [pattern]
    folder = write_application(tmp_path / "app", manifest, {"run": job_task()})
    report = lint.lint_application(folder)
    assert rules_of(report.findings) == ["manifest"]
    assert f"content.storage src: include {pattern} é um glob" in report.findings[0].message


def test_an_undeclared_stage_variable_fails_the_manifest_rule(
    tmp_path: Path,
) -> None:
    """Cada ``{env.NOME}`` dos workflows é declarado em todos os stages."""
    manifest = manifest_document()
    del manifest["stages"]["test"]["environment_variables"]["PROJECT_SG"]
    folder = write_application(tmp_path / "app", manifest, {"run": job_task()})
    report = lint.lint_application(folder)
    assert rules_of(report.findings) == ["manifest"]
    assert "stage test: sem PROJECT_SG em environment_variables" in report.findings[0].message


def test_a_workflow_no_definition_exposes_fails_the_manifest_rule(
    tmp_path: Path,
) -> None:
    """Cada ``workflowName`` do manifest é a chave do topo ou o ``dag_id`` de um YAML copiado."""
    manifest = manifest_document(name="outro-nome")
    folder = write_application(tmp_path / "app", manifest, {"run": python_task()})
    report = lint.lint_application(folder)
    assert rules_of(report.findings) == ["manifest"] * 4
    assert "content.workflows: nenhum YAML" in report.findings[0].message
    assert "stage test: nenhum YAML" in report.findings[3].message


def test_a_code_with_another_suffix_or_outside_the_includes_fails_the_manifest_rule(
    tmp_path: Path,
) -> None:
    """O ``code`` de um workflow é um ``.py``, ``.sh`` ou ``.zip`` sob um ``include``."""
    folder = write_application(
        tmp_path / "app", manifest_document(code="code/tasks.tar.gz"), {"run": python_task()}
    )
    report = lint.lint_application(folder)
    assert rules_of(report.findings) == ["manifest", "manifest"]
    assert "não é .py, .sh nem .zip" in report.findings[0].message
    assert "fora dos include" in report.findings[1].message
    folder = write_application(
        tmp_path / "outra", manifest_document(code="code/tasks.zip"), {"run": python_task()}
    )
    assert lint.lint_application(folder).findings == []


@pytest.mark.parametrize("application", APPLICATIONS, ids=APPLICATION_IDS)
def test_every_example_passes_the_lint(
    application: Path,
) -> None:
    """Cada aplicação de ``examples/`` passa no modo de autoria, com o manifest, a definição e os
    scripts das pastas copiadas lidos."""
    report = lint.lint_application(application)
    assert report.findings == []
    expected = [application / "manifest.yaml", *sorted(application.glob("workflows/*.yaml"))]
    expected.extend(sorted(application.glob("glue/*.py")))
    assert report.files == expected


def test_the_promoted_lint_of_a_rendered_example_names_what_the_translation_changes(
    tmp_path: Path,
) -> None:
    """A cópia de ``demo-devenv-job`` renderizada com os valores do projeto falha no modo
    promovido só no que a tradução por conta troca: o papel do projeto, o id do domínio, a
    etiqueta do projeto, a imagem por tag e a chave do volume."""
    definition = EXAMPLES / "demo-devenv-job" / "workflows" / "demo-devenv-job.yaml"
    values = {**SPACE_VALUES, **extra_values_of(definition), **TO_FILL["demo-devenv-job"]}
    text = render.translate_cli_variables(definition.read_text(encoding="utf-8"))
    findings = lint_text(tmp_path, render.fill_placeholders(text, values), promoted=True)
    assert rules_of(findings) == ["projeto", "projeto", "projeto", "imagem", "job"]
    found = [finding.message.split(": ")[1] for finding in findings]
    assert found == [
        "um papel de projeto, datazone_usr_role_, um valor do projeto de autoria",
        "um id de domínio, dzd_, um valor do projeto de autoria",
        "a etiqueta AmazonDataZoneProject, um valor do projeto de autoria",
        "ImageUri 111122223333.dkr.ecr.us-west-2.amazonaws.com/sagemaker-distribution-prod"
        ":4.5.2-cpu não é um URI do ECR com digest, "
        "<conta>.dkr.ecr.<região>.amazonaws.com/<repositório>@sha256:<digest>",
        "ProcessingResources.ClusterConfig.VolumeKmsKeyId ausente",
    ]


def training_task() -> dict[str, Any]:
    """Uma task de treinamento como a de ``app-etl-train``, que passa na autoria."""
    return {
        "operator": "airflow.providers.amazon.aws.operators.sagemaker.SageMakerTrainingOperator",
        "action_if_job_exists": "fail",
        "retries": 0,
        "config": {
            "TrainingJobName": "meu-treino-{{ ts_nodash }}",
            "RoleArn": "{proj.iam_role_arn}",
            "AlgorithmSpecification": {
                "TrainingImage": "{env.TRAINING_IMAGE_URI}",
                "TrainingInputMode": "File",
            },
            "InputDataConfig": [
                {
                    "ChannelName": "train",
                    "ContentType": "text/csv",
                    "DataSource": {
                        "S3DataSource": {"S3DataType": "S3Prefix", "S3Uri": f"{PREFIX}work/train/"}
                    },
                }
            ],
            "OutputDataConfig": {"S3OutputPath": f"{PREFIX}models/"},
            "ResourceConfig": {
                "InstanceType": "ml.m5.large",
                "InstanceCount": 1,
                "VolumeSizeInGB": 10,
            },
            "VpcConfig": {
                "Subnets": ["{env.SUBNET_AZ1}", "{env.SUBNET_AZ2}"],
                "SecurityGroupIds": ["{env.PROJECT_SG}"],
            },
            "EnableNetworkIsolation": True,
            "EnableInterContainerTrafficEncryption": True,
            "StoppingCondition": {"MaxRuntimeInSeconds": 1800},
        },
    }


# A imagem de um algoritmo da AWS, por digest, da conta de exemplo da AWS.
ALGORITHM_URI = f"111122223333.dkr.ecr.us-west-2.amazonaws.com/sagemaker-xgboost@{DIGEST}"


def rendered_training() -> dict[str, Any]:
    """A task de treinamento como uma cópia promovida a leva: valores literais, a imagem do
    algoritmo por digest, as duas chaves e a saída sob ``models/``."""
    task = training_task()
    config = task["config"]
    config["RoleArn"] = "arn:aws:iam::111122223333:role/meu-papel"
    config["AlgorithmSpecification"]["TrainingImage"] = ALGORITHM_URI
    config["InputDataConfig"][0]["DataSource"]["S3DataSource"]["S3Uri"] = (
        "s3://meu-bucket/meu-workflow/work/train/"
    )
    config["OutputDataConfig"] = {
        "S3OutputPath": "s3://meu-bucket/models/meu-workflow/",
        "KmsKeyId": "alias/minha-chave",
    }
    config["ResourceConfig"]["VolumeKmsKeyId"] = "alias/minha-chave"
    config["VpcConfig"] = {
        "Subnets": ["subnet-0123456789abcdef0"],
        "SecurityGroupIds": ["sg-0123456789abcdef0"],
    }
    return task


def test_a_training_task_passes_in_authoring(
    tmp_path: Path,
) -> None:
    """Uma task de treinamento como a dos exemplos passa sem recusa, com a lista de tipos."""
    assert lint_tasks(tmp_path, {"train": training_task()}, instance_types=["ml.m5.large"]) == []


def test_a_promoted_training_task_passes_with_its_algorithm_repository(
    tmp_path: Path,
) -> None:
    """A cópia promovida passa com o repositório do algoritmo admitido ao lado do da aplicação."""
    findings = lint_tasks(
        tmp_path,
        {"train": rendered_training()},
        promoted=True,
        prefixes=["s3://meu-bucket/meu-workflow/v1/"],
        instance_types=["ml.m5.large"],
        image_repository="minha-imagem",
        algorithm_repositories=["sagemaker-xgboost"],
    )
    assert findings == []


def test_a_training_image_outside_the_repositories_fails_the_image_rule(
    tmp_path: Path,
) -> None:
    """Sem o repositório do algoritmo admitido, a imagem de treinamento é recusada pelo nome."""
    findings = lint_tasks(
        tmp_path,
        {"train": rendered_training()},
        promoted=True,
        prefixes=["s3://meu-bucket/meu-workflow/v1/"],
        image_repository="minha-imagem",
    )
    assert rules_of(findings) == ["imagem"]
    assert "TrainingImage do repositório sagemaker-xgboost, e não de minha-imagem" in (
        findings[0].message
    )


def test_a_training_image_without_a_digest_fails_the_image_rule(
    tmp_path: Path,
) -> None:
    """Uma ``TrainingImage`` literal por tag, como o SDK a devolve, é recusada."""
    task = training_task()
    image = "111122223333.dkr.ecr.us-west-2.amazonaws.com/sagemaker-xgboost:3.0-5"
    task["config"]["AlgorithmSpecification"]["TrainingImage"] = image
    findings = lint_tasks(tmp_path, {"train": task})
    assert rules_of(findings) == ["imagem"]
    assert f"TrainingImage {image} não é um URI do ECR com digest" in findings[0].message


def test_a_training_task_without_fail_on_an_existing_job_fails_the_training_rule(
    tmp_path: Path,
) -> None:
    """A task leva ``action_if_job_exists: fail``."""
    task = training_task()
    del task["action_if_job_exists"]
    findings = lint_tasks(tmp_path, {"train": task})
    assert rules_of(findings) == ["treino"]
    assert "action_if_job_exists tem de ser fail" in findings[0].message


def test_a_training_task_without_config_fails_the_training_rule(
    tmp_path: Path,
) -> None:
    """Uma task de treinamento tem ``config``, a chamada ``CreateTrainingJob``."""
    task = training_task()
    del task["config"]
    findings = lint_tasks(tmp_path, {"train": task})
    assert rules_of(findings) == ["treino"]
    assert "sem config" in findings[0].message


@pytest.mark.parametrize("key", ["Subnets", "SecurityGroupIds"])
def test_a_training_task_without_the_vpc_fails_the_training_rule(
    tmp_path: Path,
    key: str,
) -> None:
    """``VpcConfig`` tem ``Subnets`` e ``SecurityGroupIds`` com algo dentro."""
    task = training_task()
    task["config"]["VpcConfig"][key] = []
    findings = lint_tasks(tmp_path, {"train": task})
    assert rules_of(findings) == ["treino"]
    assert f"VpcConfig.{key} ausente ou vazio" in findings[0].message


@pytest.mark.parametrize("key", ["EnableNetworkIsolation", "EnableInterContainerTrafficEncryption"])
def test_a_training_task_without_isolation_or_encryption_fails_the_training_rule(
    tmp_path: Path,
    key: str,
) -> None:
    """O isolamento de rede e a cifra entre contêineres são ``true``, no topo do ``config``."""
    task = training_task()
    task["config"][key] = False
    findings = lint_tasks(tmp_path, {"train": task})
    assert rules_of(findings) == ["treino"]
    assert f"{key} tem de ser true" in findings[0].message


def test_a_training_task_above_the_task_ceiling_fails_the_training_rule(
    tmp_path: Path,
) -> None:
    """``MaxRuntimeInSeconds`` até 2.820 s, como num job de processamento."""
    task = training_task()
    task["config"]["StoppingCondition"]["MaxRuntimeInSeconds"] = 2821
    findings = lint_tasks(tmp_path, {"train": task})
    assert rules_of(findings) == ["treino"]
    assert "2821 acima dos 2820 s" in findings[0].message


def test_a_training_instance_outside_the_list_fails_the_training_rule(
    tmp_path: Path,
) -> None:
    """Com ``instance_types``, o ``ResourceConfig.InstanceType`` é um deles."""
    task = training_task()
    task["config"]["ResourceConfig"]["InstanceType"] = "ml.m5.2xlarge"
    findings = lint_tasks(tmp_path, {"train": task}, instance_types=["ml.m5.large"])
    assert rules_of(findings) == ["treino"]
    assert "InstanceType ml.m5.2xlarge fora de ml.m5.large" in findings[0].message


def test_a_channel_in_another_bucket_fails_the_training_rule(
    tmp_path: Path,
) -> None:
    """Cada canal lê do bucket da saída, e não de outro, como um da lake."""
    task = rendered_training()
    channel = task["config"]["InputDataConfig"][0]
    channel["DataSource"]["S3DataSource"]["S3Uri"] = "s3://um-bucket-da-lake/curated/"
    findings = lint_tasks(tmp_path, {"train": task}, promoted=True, prefixes=["s3://meu-bucket/"])
    assert rules_of(findings) == ["treino"]
    assert "o canal train lê s3://um-bucket-da-lake/curated/, fora do bucket da saída" in (
        findings[0].message
    )


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        (lambda c: c["ResourceConfig"].pop("VolumeKmsKeyId"), "VolumeKmsKeyId ausente"),
        (lambda c: c["OutputDataConfig"].pop("KmsKeyId"), "OutputDataConfig.KmsKeyId ausente"),
        (
            lambda c: c["OutputDataConfig"].update(S3OutputPath="s3://meu-bucket/work/modelo/"),
            "fora de models/ do bucket",
        ),
    ],
)
def test_a_promoted_training_task_without_its_keys_or_its_prefix_fails_the_training_rule(
    tmp_path: Path,
    change: Any,
    expected: str,
) -> None:
    """No modo promovido, as duas chaves estão escritas e o modelo vai para ``models/``."""
    task = rendered_training()
    change(task["config"])
    findings = lint_tasks(tmp_path, {"train": task}, promoted=True, prefixes=["s3://meu-bucket/"])
    assert rules_of(findings) == ["treino"]
    assert expected in findings[0].message
