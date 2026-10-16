"""[public] O lint de uma aplicação da CLI de CI/CD: as regras que uma definição de workflow do MWAA
Serverless e o ``manifest.yaml`` obedecem, conferidas antes do ``deploy``, sem AWS.

Uma pasta é uma aplicação: o ``manifest.yaml`` e cada YAML sob uma pasta que os itens de
``content.storage`` copiam é uma definição, como a CLI de CI/CD as encontra (código da 1.0.9).
Um arquivo é uma definição sozinha, sem as regras que dependem do manifest. O lint tem dois modos:

- **autoria**, o padrão: lê os arquivos do repositório, na notação da CLI (``{proj.*}``,
  ``{domain.*}``, ``{env.*}``), e aceita as variáveis da tabela
  ``awsds_workflows.render.CLI_VARIABLES``;
- **promovido** (``promoted=True``): lê uma cópia renderizada por conta, onde não pode sobrar
  variável da CLI, placeholder nem valor do projeto, a imagem é nomeada por digest e o job de
  processamento leva a chave do volume.

As regras, pelo nome que uma recusa traz:

- ``forma``: YAML válido, um mapeamento com uma chave, o nome do workflow, cujo valor tem ``tasks``,
  um mapeamento de tasks, cada uma com ``operator``.
- ``projeto``: nenhuma variável da CLI fora da tabela, e nenhum valor que só existe no projeto de
  autoria, como ``datazone_usr_role_``, um id de domínio ``dzd_``, ``smus-projects``,
  ``dev/operatorFiles/``, uma variável ``DataZone*`` ou ``ProjectS3Path``, um alias de chave
  ``-project`` e as chaves ``domain_id`` e ``project_id``; no modo promovido, também nenhuma
  variável da CLI ou placeholder por preencher, nenhuma etiqueta ``AmazonDataZoneProject``,
  conexão ``datazone-glue-network-connection-`` ou prefixo ``datazone-<projeto>-dev``.
- ``datas``: sem ``start_date`` (o serviço exige uma data futura, e a esteira a escreve), no DAG ou
  em ``default_args``, e sem ``schedule`` nem ``schedule_interval`` (uma máquina de estados inicia
  cada workflow promovido, e um exemplo roda por ``run``).
- ``operador``: o ``operator`` é uma classe do provedor Amazon
  (``airflow.providers.amazon.aws.``) ou o ``PythonOperator`` ou ``BashOperator`` de
  ``airflow.providers.standard.operators.``; ``SageMakerNotebookOperator`` é recusado pelo nome.
- ``limites``: ``retries`` escrito em cada task, entre 0 e 3 (o serviço assume 1); ``retry_delay``
  até 300 s; ``execution_timeout`` e o ``timeout`` de um sensor até 3.600 s, o teto de uma task;
  o arquivo até 50.000 bytes (a cota de uma definição). As grafias ``retry_delay_sec`` e
  ``execution_timeout_secs`` do dag-factory contam.
- ``imagem``: um ``ImageUri`` literal é um URI do ECR com digest,
  ``<conta>.dkr.ecr.<região>.amazonaws.com/<repositório>@sha256:<64 hex>``, e do repositório
  pedido, quando há um; um placeholder passa na autoria.
- ``job``: o ``config`` de um ``SageMakerProcessingOperator`` tem ``NetworkConfig.VpcConfig`` com
  ``Subnets`` e ``SecurityGroupIds``, ``EnableNetworkIsolation`` e
  ``EnableInterContainerTrafficEncryption`` verdadeiros, ``StoppingCondition.MaxRuntimeInSeconds``
  até 2.820 s (os 3.600 s da task menos uns 13 minutos de provisionamento e encerramento), um
  ``InstanceType`` da lista pedida, quando há uma, e, no modo promovido, ``VolumeKmsKeyId``.
- ``templates``: o primeiro nome de cada ``{{ }}`` é um dos que o serviço renderiza (``macros``,
  ``ti``, ``task_instance``, ``params``, ``ds``, ``ds_nodash``, ``ts``, ``ts_nodash``), e nenhum
  método é chamado sobre o que uma macro devolveu (laboratório, 2026-10-11).
- ``codigo``: a entrada de código do job, a de ``LocalPath`` ``/opt/ml/processing/code`` ou
  ``InputName`` ``code``, está sob um prefixo permitido: numa aplicação, uma pasta que o manifest
  copia em todos os stages; numa definição sozinha, os ``prefixes`` dados, ou nada é conferido.
- ``glue``: o script de um ``GlueJobOperator`` (``script_location`` ou
  ``Command.ScriptLocation``) e cada arquivo de ``--extra-py-files``, ``--extra-jars`` e
  ``--extra-files`` estão sob um prefixo permitido, como a entrada de código; os scripts das pastas
  copiadas passam pelos padrões da regra ``projeto``.
- ``manifest``: nenhum item de ``content.storage`` com ``connectionName``, nenhum ``content.git``,
  ``content.catalog`` e ``content.notebooks`` desligados e nenhum painel de ``content.quicksight``
  exportado do serviço (``assetBundle`` ausente ou ``export``), porque com eles o ``bundle`` leva o
  que um projeto, um repositório ou uma conta tem no lugar dos arquivos da tag; cada ``{env.NOME}``
  dos workflows declarado em ``environment_variables`` de todos os stages; cada ``workflowName``
  exposto por um YAML copiado (a chave do topo ou ``dag_id``); e o ``code`` de um workflow um
  ``.py``, ``.sh`` ou ``.zip`` sob um item de storage.

Exemplo:

.. code-block:: python

    from pathlib import Path

    from awsds_workflows import lint

    report = lint.lint_application(Path("examples/demo-devenv-job"))
    for finding in report.findings:
        print(finding)  # examples/demo-devenv-job/workflows/demo-devenv-job.yaml: job: ...
    findings = lint.lint_definition(
        Path("/tmp/app-etl.yaml"),
        promoted=True,
        prefixes=["s3://meu-bucket/workflows/app-etl/v1.0.0/"],
    )
"""

from __future__ import annotations

import fnmatch
import io
import re
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from awsds_workflows import render
from awsds_workflows.errors import RefusalError

__all__ = ["Finding", "Report", "lint_application", "lint_definition"]

# A cota de uma definição, 50 KB na página de cotas do MWAA Serverless (lida em 2026-10-16).
_DEFINITION_LIMIT_BYTES = 50_000
# Os limites de uma task, da página dos parâmetros que o serviço valida (lida em 2026-10-16).
_RETRIES_LIMIT = 3
_RETRY_DELAY_LIMIT_SECONDS = 300
_TASK_TIMEOUT_LIMIT_SECONDS = 3_600
# O teto de um job de processamento: a task espera o job, e o provisionamento, o download da
# imagem e o encerramento tomam uns 13 minutos dos 3.600 s dela.
_JOB_RUNTIME_LIMIT_SECONDS = 2_820

# Os módulos de onde um operador pode vir, e as classes do segundo que o serviço roda.
_AMAZON_PROVIDER = "airflow.providers.amazon.aws."
_STANDARD_OPERATORS = "airflow.providers.standard.operators."
_CORE_OPERATORS = frozenset({"PythonOperator", "BashOperator"})
# Os operadores recusados pelo nome, com o motivo.
_REFUSED_OPERATORS = {
    "SageMakerNotebookOperator": "uma task de notebook roda um job de treinamento cuja rede e "
    "chave a definição não controla; use PythonOperator, BashOperator ou "
    "SageMakerProcessingOperator",
}

# Os nomes que o serviço renderiza num template (laboratório, 2026-10-11).
_TEMPLATE_NAMES = frozenset(
    {"macros", "ti", "task_instance", "params", "ds", "ds_nodash", "ts", "ts_nodash"}
)
_TEMPLATE = re.compile(r"\{\{(.+?)\}\}", re.DOTALL)
_TEMPLATE_FIRST_NAME = re.compile(r"\s*([A-Za-z_][A-Za-z0-9_]*)")
# Um método chamado sobre o que uma macro devolveu: macros.x.y(...).z(...).
_MACRO_RESULT_METHOD = re.compile(r"macros\.[\w.]+\([^)]*\)\s*\.\s*\w+\s*\(")

# Os valores que só existem no projeto de autoria, em qualquer modo.
_PROJECT_PATTERNS = [
    (re.compile(r"datazone_usr_role_"), "um papel de projeto, datazone_usr_role_"),
    (re.compile(r"\bdzd[_-][a-z0-9]+"), "um id de domínio, dzd_"),
    (re.compile(r"smus-projects"), "smus-projects"),
    (re.compile(r"dev/operatorFiles/"), "a cópia do código que a CLI faz, dev/operatorFiles/"),
    (re.compile(r"\bDataZone[A-Za-z]+\b"), "uma variável DataZone*"),
    (re.compile(r"\bProjectS3Path\b"), "a variável ProjectS3Path"),
    (re.compile(r"alias/\S*-project\b"), "o alias de uma chave de projeto"),
    (
        re.compile(r"^\s*(domain_id|project_id)\s*:", re.MULTILINE),
        "uma chave domain_id ou project_id",
    ),
]
# O que só o projeto tem e uma cópia promovida não pode levar.
_PROMOTED_PATTERNS = [
    (re.compile(r"AmazonDataZoneProject"), "a etiqueta AmazonDataZoneProject"),
    (re.compile(r"datazone-glue-network-connection-"), "uma conexão de rede do projeto"),
    (re.compile(r"\bdatazone-[a-z0-9]+-dev\b"), "um prefixo datazone-<projeto>-dev"),
]

# Um URI de imagem do ECR com digest; o grupo é o repositório.
_IMAGE_URI = re.compile(
    r"\d{12}\.dkr\.ecr\.[a-z0-9-]+\.amazonaws\.com/([^@:\s]+)@sha256:[0-9a-f]{64}"
)
# A entrada de código de um job de processamento, pelo LocalPath ou pelo nome.
_CODE_LOCAL_PATH = "/opt/ml/processing/code"
_CODE_INPUT_NAME = "code"
# Os argumentos de um job do Glue que nomeiam arquivos, separados por vírgula.
_GLUE_FILE_ARGUMENTS = ("--extra-py-files", "--extra-jars", "--extra-files")
# Os sufixos que o code de um workflow pode ter.
_CODE_SUFFIXES = (".py", ".sh", ".zip")
# Os sufixos dos scripts das pastas copiadas que passam pelos padrões de projeto.
_SCRIPT_SUFFIXES = (".py", ".sh", ".sql")
# A variável da CLI com que todo caminho de uma aplicação no bucket começa: a pasta shared/ do
# projeto, a conexão que os itens de storage de um stage nomeiam.
_SHARED_CONNECTION = "default.s3_shared"
_SHARED_URI = "{proj.connection.default.s3_shared.s3Uri}"


@dataclass(frozen=True)
class Finding:
    """[public] Uma recusa do lint: o arquivo, a regra e o motivo, impressa como
    ``arquivo: regra: motivo``.

    Exemplo:

    .. code-block:: python

        for finding in lint_definition(Path("meu-workflow.yaml")):
            print(finding)  # meu-workflow.yaml: limites: task run_project: retries ausente ...
    """

    path: Path
    """[public] O arquivo em que a regra falhou."""

    rule: str
    """[public] O nome da regra, um dos da lista do módulo: ``forma``, ``projeto``, ``datas``,
    ``operador``, ``limites``, ``imagem``, ``job``, ``templates``, ``codigo``, ``glue`` ou
    ``manifest``."""

    message: str
    """[public] O motivo, numa linha, com a task ou a linha em que a regra falhou."""

    def __str__(self) -> str:
        """[public] ``arquivo: regra: motivo``."""
        return f"{self.path}: {self.rule}: {self.message}"


@dataclass(frozen=True)
class Report:
    """[public] O resultado do lint de uma aplicação: os arquivos lidos e as recusas.

    Exemplo:

    .. code-block:: python

        report = lint_application(Path("examples/houseprice-etl"))
        print(len(report.files), len(report.findings))  # 3 0
    """

    files: list[Path]
    """[public] Os arquivos lidos, o manifest primeiro, depois as definições e os scripts das
    pastas copiadas, em ordem de caminho."""

    findings: list[Finding]
    """[public] As recusas, na ordem dos arquivos; vazia quando a aplicação passa."""


@dataclass(frozen=True)
class _Definition:
    """[private] Uma definição lida: o arquivo, o texto conferido (traduzido na autoria), o nome do
    workflow e o mapeamento dele."""

    path: Path
    text: str
    name: str
    dag: dict[str, Any]


def lint_definition(
    path: Path,
    *,
    promoted: bool = False,
    prefixes: Sequence[str] = (),
    instance_types: Sequence[str] = (),
    image_repository: str | None = None,
) -> list[Finding]:
    """[public] Confere uma definição de workflow contra as regras do módulo.

    Exemplo:

    .. code-block:: python

        findings = lint_definition(Path("workflows/meu-workflow.yaml"))
        findings = lint_definition(
            Path("/tmp/meu-workflow.yaml"),
            promoted=True,
            prefixes=["s3://meu-bucket/workflows/meu-workflow/v1.0.0/"],
            instance_types=["ml.m5.xlarge"],
            image_repository="minha-imagem",
        )

    :param path: o arquivo YAML da definição, na notação da CLI de CI/CD na autoria, ou a cópia
        renderizada no modo promovido.
    :param promoted: ``True`` para o modo promovido, descrito no módulo; ``False``, o padrão, para
        a autoria, onde as variáveis da CLI são traduzidas antes das regras.
    :param prefixes: os prefixos S3 sob os quais a entrada de código do job e o script do Glue
        têm de estar, na mesma notação do arquivo; vazio, o padrão, não confere as regras
        ``codigo`` e ``glue``.
    :param instance_types: os tipos de instância que um job de processamento pode pedir; vazio,
        o padrão, aceita qualquer um.
    :param image_repository: o repositório ECR que um ``ImageUri`` literal tem de nomear;
        ``None``, o padrão, aceita qualquer repositório.
    :return: as recusas, na ordem das regras do módulo; vazia quando a definição passa.
    :raises awsds_workflows.errors.RefusalError: quando o arquivo não existe.
    """
    definition, findings = _read_definition(path, promoted)
    if definition is None:
        return findings

    allowed = [_translated(prefix, promoted) for prefix in prefixes]
    findings.extend(_check_project_values(definition, promoted))
    findings.extend(_check_dates(definition))
    for task_name, task in definition.dag["tasks"].items():
        findings.extend(_check_operator(definition, task_name, task))
        findings.extend(_check_limits(definition, task_name, task))
        findings.extend(_check_images(definition, task_name, task, promoted, image_repository))
        findings.extend(_check_processing(definition, task_name, task, promoted, instance_types))
        findings.extend(_check_code_input(definition, task_name, task, allowed))
        findings.extend(_check_glue(definition, task_name, task, allowed))
    findings.extend(_check_templates(definition))
    return findings


def lint_application(
    folder: Path,
    *,
    instance_types: Sequence[str] = (),
    image_repository: str | None = None,
) -> Report:
    """[public] Confere uma aplicação da CLI de CI/CD, a pasta com o ``manifest.yaml``, no modo de
    autoria.

    Cada YAML sob uma pasta que ``content.storage`` copia é uma definição, conferida com os
    prefixos das pastas que todos os stages copiam; os scripts dessas pastas passam pelos padrões
    de projeto; e o manifest passa pelas regras ``manifest``.

    Exemplo:

    .. code-block:: python

        report = lint_application(Path("examples/demo-devenv-job"), instance_types=["ml.t3.medium"])
        for finding in report.findings:
            print(finding)

    :param folder: a pasta da aplicação, onde o ``manifest.yaml`` está.
    :param instance_types: os tipos de instância que um job de processamento pode pedir; vazio,
        o padrão, aceita qualquer um.
    :param image_repository: o repositório ECR que um ``ImageUri`` literal tem de nomear;
        ``None``, o padrão, aceita qualquer repositório.
    :return: os arquivos lidos e as recusas.
    :raises awsds_workflows.errors.RefusalError: quando a pasta ou o ``manifest.yaml`` não existe.
    """
    manifest_path = folder / "manifest.yaml"
    if not folder.is_dir():
        raise RefusalError(f"a pasta {folder} não existe")
    if not manifest_path.is_file():
        raise RefusalError(f"a pasta {folder} não tem manifest.yaml, então não é uma aplicação")

    manifest, findings = _read_manifest(manifest_path)
    if manifest is None:
        return Report(files=[manifest_path], findings=findings)

    copied = _copied_files(folder, manifest)
    definitions = [path for path in copied if path.suffix in (".yaml", ".yml")]
    scripts = [path for path in copied if path.suffix in _SCRIPT_SUFFIXES]
    prefixes = _shared_prefixes(manifest)

    for definition in definitions:
        findings.extend(
            lint_definition(
                definition,
                prefixes=prefixes,
                instance_types=instance_types,
                image_repository=image_repository,
            )
        )
    for script in scripts:
        findings.extend(_check_script(script))
    findings.extend(_check_manifest(manifest_path, manifest, folder, definitions))
    return Report(files=[manifest_path, *definitions, *scripts], findings=findings)


def _read_definition(
    path: Path,
    promoted: bool,
) -> tuple[_Definition | None, list[Finding]]:
    """[private] Lê a definição: o tamanho, as variáveis da CLI (traduzidas na autoria, recusadas
    no modo promovido), o YAML e a forma. ``None`` com as recusas quando a forma impede as outras
    regras."""
    if not path.is_file():
        raise RefusalError(f"o arquivo {path} não existe")

    findings: list[Finding] = []
    size = path.stat().st_size
    if size > _DEFINITION_LIMIT_BYTES:
        message = f"{size} bytes, acima dos {_DEFINITION_LIMIT_BYTES} da cota de uma definição"
        findings.append(Finding(path, "limites", message))

    text = path.read_text(encoding="utf-8")
    if promoted:
        findings.extend(_unrendered_values(path, text))
    else:
        try:
            text = render.translate_cli_variables(text)
        except RefusalError as error:
            findings.append(Finding(path, "projeto", str(error)))

    document = _parse_yaml(path, text, findings)
    if document is None:
        return None, findings

    # A forma: uma chave no topo, o nome do workflow, com as tasks como mapeamentos.
    if len(document) != 1:
        keys = ", ".join(str(key) for key in document)
        message = f"o topo tem de ser uma chave só, o nome do workflow; tem {len(document)}: {keys}"
        findings.append(Finding(path, "forma", message))
        return None, findings
    name = str(next(iter(document)))
    dag = document[name]
    if not isinstance(dag, dict):
        findings.append(Finding(path, "forma", f"{name} não é um mapeamento"))
        return None, findings
    tasks = dag.get("tasks")
    if not isinstance(tasks, dict) or not tasks:
        findings.append(Finding(path, "forma", f"{name} não tem tasks, um mapeamento de tasks"))
        return None, findings
    for task_name, task in tasks.items():
        if not isinstance(task, dict):
            findings.append(Finding(path, "forma", f"task {task_name}: não é um mapeamento"))
            return None, findings
    return _Definition(path=path, text=text, name=name, dag=dag), findings


def _parse_yaml(
    path: Path,
    text: str,
    findings: list[Finding],
) -> dict[Any, Any] | None:
    """[private] O conteúdo do YAML, ou ``None`` com a recusa ``forma`` juntada quando o texto não
    é YAML ou não é um mapeamento."""
    # O stream leva o nome do arquivo, para que o erro do YAML nomeie o arquivo e a linha.
    stream = io.StringIO(text)
    stream.name = str(path)
    try:
        content = yaml.safe_load(stream)
    except yaml.YAMLError as error:
        findings.append(Finding(path, "forma", f"não é YAML: {error}"))
        return None
    if not isinstance(content, dict):
        findings.append(Finding(path, "forma", "o YAML não é um mapeamento"))
        return None
    return content


def _unrendered_values(
    path: Path,
    text: str,
) -> list[Finding]:
    """[private] As variáveis da CLI e os placeholders que sobraram numa cópia promovida, uma recusa
    por nome."""
    findings: list[Finding] = []
    for variable in sorted({match.group(0) for match in render.CLI_VARIABLE.finditer(text)}):
        line = _line_of(text, variable)
        message = f"linha {line}: variável da CLI por renderizar: {variable}"
        findings.append(Finding(path, "projeto", message))
    for name in sorted(set(render.PLACEHOLDER.findall(text))):
        line = _line_of(text, f"<{name}>")
        message = f"linha {line}: placeholder por preencher: <{name}>"
        findings.append(Finding(path, "projeto", message))
    return findings


def _translated(
    prefix: str,
    promoted: bool,
) -> str:
    """[private] O prefixo na notação do texto conferido: traduzido na autoria, como o texto da
    definição; como veio no modo promovido."""
    if promoted:
        return prefix
    return render.translate_cli_variables(prefix)


def _check_project_values(
    definition: _Definition,
    promoted: bool,
) -> list[Finding]:
    """[private] Os valores que só existem no projeto de autoria, no texto; no modo promovido,
    também os que só o projeto tem."""
    patterns = list(_PROJECT_PATTERNS)
    if promoted:
        patterns.extend(_PROMOTED_PATTERNS)
    return _matches_of(definition.path, definition.text, patterns)


def _check_script(
    path: Path,
) -> list[Finding]:
    """[private] Os valores de projeto no texto de um script de uma pasta copiada."""
    text = path.read_text(encoding="utf-8", errors="replace")
    return _matches_of(path, text, _PROJECT_PATTERNS)


def _matches_of(
    path: Path,
    text: str,
    patterns: list[tuple[re.Pattern[str], str]],
) -> list[Finding]:
    """[private] Uma recusa ``projeto`` por padrão encontrado, com a linha e o texto da primeira
    ocorrência."""
    findings: list[Finding] = []
    for pattern, description in patterns:
        match = pattern.search(text)
        if match is None:
            continue
        line = text.count("\n", 0, match.start()) + 1
        found = match.group(0).strip()
        message = f"linha {line}: {description}, um valor do projeto de autoria: {found}"
        findings.append(Finding(path, "projeto", message))
    return findings


def _check_dates(
    definition: _Definition,
) -> list[Finding]:
    """[private] ``start_date`` no DAG ou em ``default_args``, e ``schedule`` ou
    ``schedule_interval``."""
    findings: list[Finding] = []
    dag = definition.dag
    if "start_date" in dag:
        message = "start_date no DAG: o serviço exige uma data futura, e a esteira a escreve"
        findings.append(Finding(definition.path, "datas", message))
    default_args = dag.get("default_args")
    if isinstance(default_args, dict) and "start_date" in default_args:
        message = (
            "start_date em default_args: o serviço exige uma data futura, e a esteira a escreve"
        )
        findings.append(Finding(definition.path, "datas", message))
    for key in ("schedule", "schedule_interval"):
        if key in dag:
            message = f"{key} no DAG: um workflow é iniciado por run ou por uma máquina de estados"
            findings.append(Finding(definition.path, "datas", message))
    return findings


def _check_operator(
    definition: _Definition,
    task_name: str,
    task: dict[str, Any],
) -> list[Finding]:
    """[private] O ``operator`` da task: uma classe do provedor Amazon, ou o Python ou o Bash do
    provedor standard, e nenhum dos recusados pelo nome."""
    operator = task.get("operator")
    if not isinstance(operator, str) or not operator:
        return [Finding(definition.path, "forma", f"task {task_name}: sem operator")]

    module, _, class_name = operator.rpartition(".")
    module_prefix = f"{module}."
    if class_name in _REFUSED_OPERATORS:
        message = f"task {task_name}: {class_name}: {_REFUSED_OPERATORS[class_name]}"
        return [Finding(definition.path, "operador", message)]
    if module_prefix.startswith(_AMAZON_PROVIDER):
        return []
    if module_prefix.startswith(_STANDARD_OPERATORS) and class_name in _CORE_OPERATORS:
        return []
    message = (
        f"task {task_name}: {operator} não é uma classe de {_AMAZON_PROVIDER} nem o "
        f"PythonOperator ou o BashOperator de {_STANDARD_OPERATORS}, os que o serviço roda"
    )
    return [Finding(definition.path, "operador", message)]


def _check_limits(
    definition: _Definition,
    task_name: str,
    task: dict[str, Any],
) -> list[Finding]:
    """[private] ``retries`` escrito e entre 0 e 3, ``retry_delay`` até 300 s, ``execution_timeout``
    e o ``timeout`` de um sensor até 3.600 s, nas grafias do Airflow e do dag-factory."""
    findings: list[Finding] = []
    path = definition.path
    retries = task.get("retries")
    if retries is None:
        message = f"task {task_name}: retries ausente; o serviço assume 1, escreva 0 a 3"
        findings.append(Finding(path, "limites", message))
    elif not _is_number(retries) or not 0 <= retries <= _RETRIES_LIMIT:
        message = f"task {task_name}: retries {retries!r} fora de 0 a {_RETRIES_LIMIT}"
        findings.append(Finding(path, "limites", message))

    limits = [
        ("retry_delay", _RETRY_DELAY_LIMIT_SECONDS),
        ("retry_delay_sec", _RETRY_DELAY_LIMIT_SECONDS),
        ("execution_timeout", _TASK_TIMEOUT_LIMIT_SECONDS),
        ("execution_timeout_secs", _TASK_TIMEOUT_LIMIT_SECONDS),
        ("timeout", _TASK_TIMEOUT_LIMIT_SECONDS),
    ]
    for key, limit in limits:
        value = task.get(key)
        if _is_number(value) and value > limit:
            message = f"task {task_name}: {key} {value} acima dos {limit} s do serviço"
            findings.append(Finding(path, "limites", message))
    return findings


def _check_images(
    definition: _Definition,
    task_name: str,
    task: dict[str, Any],
    promoted: bool,
    image_repository: str | None,
) -> list[Finding]:
    """[private] Cada ``ImageUri`` da task: um placeholder passa na autoria; um literal é um URI do
    ECR com digest, do repositório pedido."""
    findings: list[Finding] = []
    for image in _values_of_key(task, "ImageUri"):
        if not isinstance(image, str):
            continue
        if not promoted and render.PLACEHOLDER.search(image):
            continue
        match = _IMAGE_URI.fullmatch(image)
        if match is None:
            message = (
                f"task {task_name}: ImageUri {image} não é um URI do ECR com digest, "
                "<conta>.dkr.ecr.<região>.amazonaws.com/<repositório>@sha256:<digest>"
            )
            findings.append(Finding(definition.path, "imagem", message))
        elif image_repository is not None and match.group(1) != image_repository:
            message = (
                f"task {task_name}: ImageUri do repositório {match.group(1)}, e não de "
                f"{image_repository}"
            )
            findings.append(Finding(definition.path, "imagem", message))
    return findings


def _check_processing(
    definition: _Definition,
    task_name: str,
    task: dict[str, Any],
    promoted: bool,
    instance_types: Sequence[str],
) -> list[Finding]:
    """[private] O ``config`` de um ``SageMakerProcessingOperator``: a rede, o isolamento, a
    cifra, o teto de tempo, o tipo de instância e, no modo promovido, a chave do volume."""
    if not _is_operator(task, "SageMakerProcessingOperator"):
        return []
    path = definition.path
    config = task.get("config")
    if not isinstance(config, dict):
        message = f"task {task_name}: sem config, a chamada CreateProcessingJob"
        return [Finding(path, "job", message)]

    findings: list[Finding] = []
    network = _mapping_at(config, "NetworkConfig")
    vpc = _mapping_at(network, "VpcConfig")
    for key in ("Subnets", "SecurityGroupIds"):
        if not _is_nonempty_list(vpc.get(key)):
            message = f"task {task_name}: NetworkConfig.VpcConfig.{key} ausente ou vazio"
            findings.append(Finding(path, "job", message))
    for key in ("EnableNetworkIsolation", "EnableInterContainerTrafficEncryption"):
        if network.get(key) is not True:
            message = f"task {task_name}: NetworkConfig.{key} tem de ser true"
            findings.append(Finding(path, "job", message))

    runtime = _mapping_at(config, "StoppingCondition").get("MaxRuntimeInSeconds")
    if runtime is None:
        message = (
            f"task {task_name}: StoppingCondition.MaxRuntimeInSeconds ausente; "
            f"até {_JOB_RUNTIME_LIMIT_SECONDS} s"
        )
        findings.append(Finding(path, "job", message))
    elif _is_number(runtime) and runtime > _JOB_RUNTIME_LIMIT_SECONDS:
        message = (
            f"task {task_name}: StoppingCondition.MaxRuntimeInSeconds {runtime} acima dos "
            f"{_JOB_RUNTIME_LIMIT_SECONDS} s que cabem nos 3600 s da task"
        )
        findings.append(Finding(path, "job", message))

    cluster = _mapping_at(_mapping_at(config, "ProcessingResources"), "ClusterConfig")
    instance_type = cluster.get("InstanceType")
    if instance_types and instance_type not in instance_types:
        message = (
            f"task {task_name}: InstanceType {instance_type} fora de {', '.join(instance_types)}"
        )
        findings.append(Finding(path, "job", message))
    if promoted and not cluster.get("VolumeKmsKeyId"):
        message = f"task {task_name}: ProcessingResources.ClusterConfig.VolumeKmsKeyId ausente"
        findings.append(Finding(path, "job", message))
    return findings


def _check_code_input(
    definition: _Definition,
    task_name: str,
    task: dict[str, Any],
    prefixes: Sequence[str],
) -> list[Finding]:
    """[private] A entrada de código de um job de processamento sob um dos prefixos; nada sem
    prefixos."""
    if not prefixes or not _is_operator(task, "SageMakerProcessingOperator"):
        return []
    findings: list[Finding] = []
    inputs = _mapping_at(task, "config").get("ProcessingInputs")
    if not isinstance(inputs, list):
        return []
    for item in inputs:
        if not isinstance(item, dict):
            continue
        s3_input = _mapping_at(item, "S3Input")
        is_code = item.get("InputName") == _CODE_INPUT_NAME
        is_code = is_code or s3_input.get("LocalPath") == _CODE_LOCAL_PATH
        uri = s3_input.get("S3Uri")
        if is_code and isinstance(uri, str) and _outside(uri, prefixes):
            message = (
                f"task {task_name}: a entrada de código {uri} está fora de {', '.join(prefixes)}"
            )
            findings.append(Finding(definition.path, "codigo", message))
    return findings


def _check_glue(
    definition: _Definition,
    task_name: str,
    task: dict[str, Any],
    prefixes: Sequence[str],
) -> list[Finding]:
    """[private] O script de um ``GlueJobOperator`` e os arquivos dos argumentos ``--extra-*`` sob
    um dos prefixos; nada sem prefixos."""
    if not prefixes or not _is_operator(task, "GlueJobOperator"):
        return []
    create_kwargs = _mapping_at(task, "create_job_kwargs")
    locations = [
        task.get("script_location"),
        _mapping_at(create_kwargs, "Command").get("ScriptLocation"),
    ]
    arguments = {}
    arguments.update(_mapping_at(task, "script_args"))
    arguments.update(_mapping_at(create_kwargs, "DefaultArguments"))
    for key in _GLUE_FILE_ARGUMENTS:
        value = arguments.get(key)
        if isinstance(value, str):
            locations.extend(part.strip() for part in value.split(","))

    findings: list[Finding] = []
    for location in locations:
        if isinstance(location, str) and location and _outside(location, prefixes):
            message = f"task {task_name}: {location} está fora de {', '.join(prefixes)}"
            findings.append(Finding(definition.path, "glue", message))
    return findings


def _check_templates(
    definition: _Definition,
) -> list[Finding]:
    """[private] Cada ``{{ }}`` dos textos da definição: o primeiro nome é um dos que o serviço
    renderiza, e nenhum método é chamado sobre o que uma macro devolveu."""
    findings: list[Finding] = []
    seen: set[str] = set()
    for text in _strings_of(definition.dag):
        for match in _TEMPLATE.finditer(text):
            body = match.group(1).strip()
            if body in seen:
                continue
            seen.add(body)
            first = _TEMPLATE_FIRST_NAME.match(body)
            if first is None or first.group(1) not in _TEMPLATE_NAMES:
                message = (
                    f"{{{{ {body} }}}}: o serviço renderiza só {', '.join(sorted(_TEMPLATE_NAMES))}"
                )
                findings.append(Finding(definition.path, "templates", message))
            if _MACRO_RESULT_METHOD.search(body):
                message = (
                    f"{{{{ {body} }}}}: um método sobre o que uma macro devolveu não renderiza; "
                    "chame só funções de um módulo, como "
                    "macros.time.strftime(..., macros.time.gmtime())"
                )
                findings.append(Finding(definition.path, "templates", message))
    return findings


def _read_manifest(
    path: Path,
) -> tuple[dict[str, Any] | None, list[Finding]]:
    """[private] O manifest lido, com a forma conferida: ``applicationName``, ``content`` e
    ``stages``. ``None`` com as recusas quando a forma impede as outras regras."""
    findings: list[Finding] = []
    text = path.read_text(encoding="utf-8")
    manifest = _parse_yaml(path, text, findings)
    if manifest is None:
        return None, findings
    for key in ("applicationName", "content", "stages"):
        if key not in manifest:
            findings.append(Finding(path, "forma", f"sem {key}"))
    if findings:
        return None, findings
    if not isinstance(manifest["content"], dict) or not isinstance(manifest["stages"], dict):
        findings.append(Finding(path, "forma", "content e stages têm de ser mapeamentos"))
        return None, findings
    return manifest, findings


def _copied_files(
    folder: Path,
    manifest: dict[str, Any],
) -> list[Path]:
    """[private] Os arquivos que os itens de ``content.storage`` incluem, em ordem de caminho: cada
    ``include`` é uma pasta, com a barra no fim, ou um padrão de ``glob``; um ``exclude`` casa com
    o caminho relativo ou com o nome do arquivo."""
    files: set[Path] = set()
    for item in _storage_items(manifest):
        excludes = item.get("exclude") or []
        for pattern in item.get("include") or []:
            for path in _included(folder, str(pattern)):
                relative = path.relative_to(folder).as_posix()
                if any(_excluded(relative, str(exclude)) for exclude in excludes):
                    continue
                files.add(path)
    return sorted(files)


def _included(
    folder: Path,
    pattern: str,
) -> Iterator[Path]:
    """[private] Os arquivos de uma pasta, quando o padrão termina em ``/``, ou os que o padrão
    casa como ``glob``."""
    if pattern.endswith("/"):
        root = folder / pattern.rstrip("/")
        if root.is_dir():
            yield from (path for path in root.rglob("*") if path.is_file())
        return
    yield from (path for path in folder.glob(pattern) if path.is_file())


def _excluded(
    relative: str,
    pattern: str,
) -> bool:
    """[private] Se um ``exclude`` casa com o caminho relativo, com uma pasta dele
    (``__pycache__/``) ou com o nome do arquivo (``*.pyc``)."""
    parts = relative.split("/")
    if pattern.endswith("/"):
        return pattern.rstrip("/") in parts[:-1]
    return fnmatch.fnmatch(relative, pattern) or fnmatch.fnmatch(parts[-1], pattern)


def _shared_prefixes(
    manifest: dict[str, Any],
) -> list[str]:
    """[private] Os prefixos, na notação traduzida, das pastas que todos os stages copiam para a
    conexão ``default.s3_shared``: a interseção dos ``targetDirectory`` dos stages."""
    common: set[str] | None = None
    for stage in manifest["stages"].values():
        if not isinstance(stage, dict):
            continue
        targets: set[str] = set()
        deployment = _mapping_at(stage, "deployment_configuration")
        for item in deployment.get("storage") or []:
            if not isinstance(item, dict) or item.get("connectionName") != _SHARED_CONNECTION:
                continue
            target = item.get("targetDirectory")
            if isinstance(target, str) and target:
                targets.add(f"{_SHARED_URI}{target.strip('/')}/")
        if common is None:
            common = targets
        else:
            common &= targets
    if not common:
        return []
    return [render.translate_cli_variables(prefix) for prefix in sorted(common)]


def _check_manifest(
    path: Path,
    manifest: dict[str, Any],
    folder: Path,
    definitions: list[Path],
) -> list[Finding]:
    """[private] As regras ``manifest``: o conteúdo só da tag, as variáveis de stage declaradas,
    cada ``workflowName`` exposto por uma definição copiada e o ``code`` de cada workflow."""
    findings: list[Finding] = []
    content = manifest["content"]
    findings.extend(_check_content_from_the_tag(path, content))
    findings.extend(_check_stage_variables(path, manifest, definitions))
    findings.extend(_check_workflow_names(path, manifest, definitions))
    findings.extend(_check_codes(path, manifest))
    return findings


def _check_content_from_the_tag(
    path: Path,
    content: dict[str, Any],
) -> list[Finding]:
    """[private] O ``content`` que o ``bundle`` leria de fora da tag: um storage com conexão, um
    ``git``, o catálogo ou os notebooks ligados, um painel exportado do serviço."""
    findings: list[Finding] = []
    for item in content.get("storage") or []:
        if isinstance(item, dict) and item.get("connectionName"):
            message = (
                f"content.storage {item.get('name')}: com connectionName, o bundle lê o projeto, "
                "e não a pasta ao lado do manifest"
            )
            findings.append(Finding(path, "manifest", message))
    if content.get("git"):
        message = "content.git: o bundle clonaria um repositório no lugar dos arquivos da tag"
        findings.append(Finding(path, "manifest", message))
    for key in ("catalog", "notebooks"):
        if _mapping_at(content, key).get("enabled") is True:
            message = f"content.{key}.enabled: o bundle levaria o que o projeto tem, e não a tag"
            findings.append(Finding(path, "manifest", message))
    for item in content.get("quicksight") or []:
        if isinstance(item, dict) and item.get("assetBundle", "export") == "export":
            message = (
                f"content.quicksight {item.get('name')}: assetBundle ausente ou export, o painel "
                "exportado do serviço no lugar de um arquivo da tag"
            )
            findings.append(Finding(path, "manifest", message))
    return findings


def _check_stage_variables(
    path: Path,
    manifest: dict[str, Any],
    definitions: list[Path],
) -> list[Finding]:
    """[private] Cada ``{env.NOME}`` das definições declarado em ``environment_variables`` de todos
    os stages, ou o ``deploy`` para em ``Failed to resolve variables``."""
    used: set[str] = set()
    for definition in definitions:
        text = definition.read_text(encoding="utf-8")
        for match in render.CLI_VARIABLE.finditer(text):
            if match.group(1) == "env":
                used.add(match.group(2))

    findings: list[Finding] = []
    for stage_name, stage in manifest["stages"].items():
        declared = _mapping_at(stage, "environment_variables") if isinstance(stage, dict) else {}
        missing = sorted(used - set(declared))
        if missing:
            message = (
                f"stage {stage_name}: sem {', '.join(missing)} em environment_variables, que os "
                "workflows usam"
            )
            findings.append(Finding(path, "manifest", message))
    return findings


def _check_workflow_names(
    path: Path,
    manifest: dict[str, Any],
    definitions: list[Path],
) -> list[Finding]:
    """[private] Cada ``workflowName`` de ``content.workflows`` e das ações de ``bootstrap`` exposto
    por uma definição copiada, pela chave do topo ou pelo ``dag_id``."""
    exposed: set[str] = set()
    for definition in definitions:
        document = yaml.safe_load(definition.read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            continue
        for key, value in document.items():
            exposed.add(str(key))
            if isinstance(value, dict) and isinstance(value.get("dag_id"), str):
                exposed.add(value["dag_id"])

    named: list[tuple[str, str]] = []
    for item in manifest["content"].get("workflows") or []:
        if isinstance(item, dict) and isinstance(item.get("workflowName"), str):
            named.append(("content.workflows", item["workflowName"]))
    for stage_name, stage in manifest["stages"].items():
        actions = _mapping_at(stage, "bootstrap").get("actions") if isinstance(stage, dict) else []
        for action in actions or []:
            if isinstance(action, dict) and isinstance(action.get("workflowName"), str):
                named.append((f"stage {stage_name}", action["workflowName"]))

    findings: list[Finding] = []
    for where, name in named:
        if name not in exposed:
            message = f"{where}: nenhum YAML das pastas copiadas expõe o workflow {name}"
            findings.append(Finding(path, "manifest", message))
    return findings


def _check_codes(
    path: Path,
    manifest: dict[str, Any],
) -> list[Finding]:
    """[private] O ``code`` de cada workflow: um ``.py``, ``.sh`` ou ``.zip`` que um ``include`` de
    ``content.storage`` cobre."""
    findings: list[Finding] = []
    includes: list[str] = []
    for item in _storage_items(manifest):
        includes.extend(str(pattern) for pattern in item.get("include") or [])
    for item in manifest["content"].get("workflows") or []:
        if not isinstance(item, dict) or "code" not in item:
            continue
        code = str(item["code"])
        name = item.get("workflowName")
        if not code.endswith(_CODE_SUFFIXES):
            message = f"workflow {name}: code {code} não é .py, .sh nem .zip"
            findings.append(Finding(path, "manifest", message))
        if not any(_covers(pattern, code) for pattern in includes):
            message = f"workflow {name}: code {code} fora dos include de content.storage"
            findings.append(Finding(path, "manifest", message))
    return findings


def _covers(
    pattern: str,
    code: str,
) -> bool:
    """[private] Se um ``include`` cobre o caminho do ``code``: a pasta é um prefixo, ou o padrão
    casa como ``glob``."""
    if pattern.endswith("/"):
        return code.startswith(pattern)
    return fnmatch.fnmatch(code, pattern)


def _storage_items(
    manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    """[private] Os itens de ``content.storage`` que são mapeamentos."""
    items = manifest["content"].get("storage") or []
    return [item for item in items if isinstance(item, dict)]


def _is_operator(
    task: dict[str, Any],
    class_name: str,
) -> bool:
    """[private] Se o ``operator`` da task termina na classe."""
    operator = task.get("operator")
    return isinstance(operator, str) and operator.rpartition(".")[2] == class_name


def _is_number(
    value: Any,
) -> bool:
    """[private] Se o valor é um número, e não um ``bool``, que o Python também conta."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_nonempty_list(
    value: Any,
) -> bool:
    """[private] Se o valor é uma lista com algo dentro."""
    return isinstance(value, list) and len(value) > 0


def _mapping_at(
    container: Any,
    key: str,
) -> dict[str, Any]:
    """[private] O mapeamento sob a chave, ou um vazio quando a chave falta ou não é um
    mapeamento."""
    if not isinstance(container, dict):
        return {}
    value = container.get(key)
    if isinstance(value, dict):
        return value
    return {}


def _outside(
    uri: str,
    prefixes: Sequence[str],
) -> bool:
    """[private] Se o URI não começa por nenhum dos prefixos."""
    return not any(uri.startswith(prefix) for prefix in prefixes)


def _line_of(
    text: str,
    needle: str,
) -> int:
    """[private] A linha da primeira ocorrência do trecho no texto, a partir de 1."""
    return text.count("\n", 0, text.index(needle)) + 1


def _values_of_key(
    value: Any,
    key: str,
) -> Iterator[Any]:
    """[private] Cada valor sob a chave, em qualquer nível dos mapeamentos e das listas."""
    if isinstance(value, dict):
        for inner_key, inner in value.items():
            if inner_key == key:
                yield inner
            yield from _values_of_key(inner, key)
    elif isinstance(value, list):
        for inner in value:
            yield from _values_of_key(inner, key)


def _strings_of(
    value: Any,
) -> Iterator[str]:
    """[private] Cada texto dos mapeamentos e das listas, as chaves incluídas."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, inner in value.items():
            yield from _strings_of(key)
            yield from _strings_of(inner)
    elif isinstance(value, list):
        for inner in value:
            yield from _strings_of(inner)
