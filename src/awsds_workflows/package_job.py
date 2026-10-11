"""[public] A pasta de código de um job de processamento do SageMaker, para a imagem que o job
nomeia.

O job roda o interpretador da imagem sem rede, então cada dependência do projeto ou já está no
ambiente da imagem ou viaja na entrada de código; nada é instalado na execução. Três regras
separam essa entrada do ``.zip`` de uma task (``awsds_workflows.package_task``):

- O interpretador é o da imagem do job, e não o do worker: o da SageMaker Distribution na imagem
  padrão, ou o ambiente que uma imagem customizada traz.
- A entrada é uma pasta, e não um arquivo: um ``ProcessingInput`` baixa um prefixo do S3, e um
  módulo de extensão não é importado de um ``.zip`` no ``sys.path``.
- A precedência é a inversa da do worker: o ``PYTHONPATH`` vem antes do ``site-packages`` da
  imagem, e um pacote presente nos dois esconderia a cópia da imagem. Por isso a pasta leva só o
  que a imagem não tem, e as versões do projeto têm de ser iguais às da imagem em tudo o que os
  dois compartilham.

O ambiente da imagem chega num arquivo de requisitos, uma linha ``nome==versão`` por pacote, com um
marcador PEP 508 opcional. Num space que roda a imagem do job, sem internet, com o interpretador
que o job vai chamar:

.. code-block:: shell

    uv pip list --format freeze --python /opt/conda/bin/python > ambiente.txt

Para uma imagem construída de um projeto uv, o ``uv export --frozen --no-dev --no-emit-project
--no-hashes`` desse projeto também serve. Os marcadores são avaliados aqui para o interpretador e a
plataforma do job, sem um resolvedor, porque o ambiente de uma imagem pode ter pacotes de um índice
próprio (o do PyTorch) ou sem wheel para todo Python, que um resolvedor recusaria. Uma linha que não
é ``nome==versão``, como o ``nome @ file:///...`` que o ``pip freeze`` escreve para um pacote do
conda, é recusada: ignorada, ela faria o pacote parecer ausente da imagem e entrar na pasta.

A plataforma padrão, ``x86_64-manylinux_2_28``, pede glibc 2.28 ou mais nova na imagem. A imagem do
laboratório tem o ``onnxruntime`` 1.30.0, que não publica wheel anterior a ``manylinux_2_28``
(medido em 2026-10-11), então ``manylinux2014`` não a descreve; numa outra imagem, ``ldd --version``
no space diz a glibc.

Medido em 2026-10-11 sobre a imagem do laboratório, ``awsds-sandbox-dev-env``, e um projeto que
dependia de ``petl``, ``requests``, ``boto3`` e ``pyyaml``: o lock novo discordou da imagem em
``boto3``, ``botocore``, ``charset-normalizer``, ``idna`` e ``urllib3``; com o bloco de restrições
impresso e um novo ``uv lock``, 12 pacotes vieram da imagem e só o ``petl`` entrou na pasta,
de 1,2 MB.

Exemplo:

.. code-block:: python

    from pathlib import Path

    from awsds_workflows import package_job

    folder = package_job.build_folder(
        Path("/home/usuario/src/meu-projeto"),
        Path("/tmp/meu-projeto-0.2.0"),
        environment=Path("ambiente.txt"),
        python="3.12",
    )
    print(folder.vendored, folder.top_level)
"""

from __future__ import annotations

import re
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from packaging.markers import Marker

from awsds_workflows import _uv
from awsds_workflows.errors import RefusalError

__all__ = [
    "JOB_PLATFORM",
    "JobFolder",
    "build_folder",
    "environment_versions",
]

JOB_PLATFORM = "x86_64-manylinux_2_28"
"""[public] A plataforma padrão do job, Linux x86_64 com glibc 2.28 ou mais nova, no formato do
``--python-platform`` do ``uv``."""

_PIN = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([^\s;\\]+)(?:\s*;\s*([^\\]+?))?\s*\\?$")


@dataclass(frozen=True)
class JobFolder:
    """[public] A pasta que ``build_folder`` gravou, com o que a linha de comando imprime.

    Exemplo:

    .. code-block:: python

        folder = build_folder(project, output, environment=Path("ambiente.txt"), python="3.12")
        print(folder.from_environment)  # {'boto3': '1.43.92', ...}
        print(folder.vendored)  # {'petl': '1.7.29'}
    """

    path: Path
    """[public] O caminho absoluto da pasta."""

    size_bytes: int
    """[public] A soma dos tamanhos dos arquivos da pasta, em bytes."""

    from_environment: dict[str, str]
    """[public] Os pacotes do fechamento que a imagem já tem, nome normalizado e versão."""

    vendored: dict[str, str]
    """[public] Os pacotes do fechamento que a pasta leva, nome normalizado e versão."""

    top_level: list[str]
    """[public] Os nomes na raiz da pasta, em ordem alfabética."""

    python: str
    """[public] A versão do CPython para a qual os wheels foram escolhidos."""

    platform: str
    """[public] A plataforma para a qual os wheels foram escolhidos."""


@dataclass
class _Pin:
    """[private] Um requisito ``nome==versão`` de um arquivo de requisitos, com o marcador e as
    linhas de continuação que o seguem (os hashes)."""

    name: str
    """[private] O nome normalizado, como o PEP 503 o escreve."""

    version: str
    """[private] A versão fixada."""

    marker: str | None
    """[private] O marcador PEP 508 depois do ``;``; ``None`` quando a linha não tem um."""

    lines: list[str] = field(default_factory=list)
    """[private] A linha do requisito e as de continuação, como estão no arquivo."""


def environment_versions(
    environment: Path,
    python: str,
    platform: str = JOB_PLATFORM,
) -> dict[str, str]:
    """[public] Os pacotes do ambiente da imagem do job que valem para o interpretador e a
    plataforma do job.

    Serve também para restringir o lock do projeto às versões da imagem, com
    ``uv pip compile -c`` ou ``uv add -c``.

    Exemplo:

    .. code-block:: python

        versions = environment_versions(Path("ambiente.txt"), python="3.12")
        print(versions["boto3"])

    :param environment: o arquivo de requisitos do ambiente da imagem, uma linha ``nome==versão``
        por pacote, com um marcador PEP 508 opcional.
    :param python: a versão do CPython do interpretador que o job chama, como ``3.12``.
    :param platform: a plataforma do job no formato do ``--python-platform`` do ``uv``.
    :return: a versão de cada pacote, pelo nome normalizado (``charset-normalizer``), em ordem de
        nome.
    :raises awsds_workflows.errors.RefusalError: quando o arquivo não existe ou tem uma linha que
        não é ``nome==versão``.
    """
    if not environment.is_file():
        raise RefusalError(f"o arquivo de ambiente {environment} não existe")
    pins = _read_pins(environment.read_text(encoding="utf-8"), str(environment))
    applicable = _applicable(pins, _marker_environment(python, platform))
    return {name: applicable[name].version for name in sorted(applicable)}


def build_folder(
    project: Path,
    output: Path,
    environment: Path,
    python: str,
    platform: str = JOB_PLATFORM,
) -> JobFolder:
    """[public] Grava a pasta de código de um job de processamento a partir de um projeto uv.

    A pasta leva o pacote do projeto e os pacotes do fechamento do ``uv.lock`` que o ambiente da
    imagem não tem, construídos para ``python`` e ``platform``. O projeto precisa de um
    ``uv.lock`` em dia, de um ``requires-python`` que admita ``python`` e de código próprio em
    Python puro; o job o chama como ``python -m <pacote>`` com o ``PYTHONPATH`` na pasta.

    Exemplo:

    .. code-block:: python

        folder = build_folder(
            Path("meu-projeto"),
            Path("/tmp/meu-projeto-0.2.0"),
            environment=Path("ambiente.txt"),
            python="3.12",
        )

    :param project: a pasta do projeto uv, com ``pyproject.toml`` e ``uv.lock``.
    :param output: a pasta a gravar, que ainda não pode existir.
    :param environment: o arquivo de requisitos do ambiente da imagem do job
        (``environment_versions``).
    :param python: a versão do CPython do interpretador que o job chama, como ``3.12``.
    :param platform: a plataforma do job no formato do ``--python-platform`` do ``uv``.
    :return: a pasta gravada, com o que veio da imagem e o que ela leva.
    :raises awsds_workflows.errors.RefusalError: quando falta o ``uv.lock`` ou o arquivo de
        ambiente, quando a pasta de saída já existe, quando o lock e a imagem discordam numa
        versão (a mensagem traz o bloco ``[tool.uv] constraint-dependencies`` que alinha o
        projeto à imagem), quando o ``uv`` recusa o lock ou uma dependência sem wheel para o alvo
        e quando o projeto não é Python puro.
    """
    # Os caminhos absolutos, porque o uv roda dentro da pasta do projeto.
    project = project.resolve()
    output = output.resolve()
    if not (project / "uv.lock").is_file():
        raise RefusalError(f"não há uv.lock em {project}: rode uv lock lá antes")
    if output.exists():
        raise RefusalError(f"{output} já existe: nomeie uma pasta nova, e nada é sobrescrito")
    in_environment = environment_versions(environment, python, platform)

    # O fechamento travado do projeto, com os hashes, e a parte dele que vale para o job.
    exported = _uv.run(
        ["export", "--locked", "--no-dev", "--no-emit-project", "--no-header", "--quiet"],
        cwd=project,
    )
    closure = _applicable(_read_pins(exported, "uv export"), _marker_environment(python, platform))
    from_environment, conflicts, vendored = _compare(closure, in_environment)
    if conflicts:
        raise RefusalError(_conflict_message(conflicts, from_environment, in_environment))

    with tempfile.TemporaryDirectory() as temporary:
        stage = Path(temporary) / "stage"

        # Os pacotes que a imagem não tem, em wheels do job, com os hashes do lock.
        if vendored:
            requirements = Path(temporary) / "vendored.txt"
            blocks = ["\n".join(vendored[name].lines) for name in sorted(vendored)]
            requirements.write_text("\n".join(blocks) + "\n", encoding="utf-8")
            _uv.install_requirements(requirements, stage, python, platform)

        # O pacote do projeto, de um wheel construído a partir do pyproject.toml.
        wheels = _uv.build_pure_wheel(project, Path(temporary) / "dist")
        _uv.install_wheels(wheels, stage, python, platform)
        _uv.remove_leftovers(stage)
        shutil.copytree(stage, output)

    files = [path for path in output.rglob("*") if path.is_file()]
    return JobFolder(
        path=output,
        size_bytes=sum(path.stat().st_size for path in files),
        from_environment=from_environment,
        vendored={name: vendored[name].version for name in sorted(vendored)},
        top_level=sorted(path.name for path in output.iterdir()),
        python=python,
        platform=platform,
    )


def _normalize(
    name: str,
) -> str:
    """[private] O nome de um pacote como o PEP 503 o normaliza: minúsculas, e ``-`` no lugar de
    cada sequência de ``-``, ``_`` e ``.``."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _read_pins(
    text: str,
    source: str,
) -> list[_Pin]:
    """[private] Os requisitos ``nome==versão`` de um arquivo de requisitos, cada um com as linhas
    de continuação que o seguem.

    Uma linha em branco ou de comentário é pulada, e uma linha recuada continua o requisito
    anterior (um hash, uma anotação ``# via``). Qualquer outra linha recusa o arquivo, com
    ``source`` na mensagem.
    """
    pins: list[_Pin] = []
    for number, line in enumerate(text.splitlines(), start=1):
        # Uma linha recuada pertence ao requisito anterior.
        if line[:1] in (" ", "\t"):
            if pins and line.strip():
                pins[-1].lines.append(line)
            continue
        if not line.strip() or line.startswith("#"):
            continue

        match = _PIN.match(line)
        if match is None:
            raise RefusalError(
                f"{source}, linha {number}: {line.strip()!r} não é nome==versão; gere o arquivo "
                "com uv pip list --format freeze, que escreve só nome==versão"
            )
        name, version, marker = match.groups()
        pins.append(_Pin(name=_normalize(name), version=version, marker=marker, lines=[line]))
    return pins


def _marker_environment(
    python: str,
    platform: str,
) -> dict[str, str]:
    """[private] O ambiente de marcadores PEP 508 do CPython ``python`` em Linux, com a arquitetura
    de ``platform`` (``x86_64-manylinux_2_28`` dá ``x86_64``)."""
    full_version = python if python.count(".") >= 2 else f"{python}.0"
    return {
        "implementation_name": "cpython",
        "implementation_version": full_version,
        "os_name": "posix",
        "platform_machine": platform.split("-")[0],
        "platform_python_implementation": "CPython",
        "platform_release": "",
        "platform_system": "Linux",
        "platform_version": "",
        "python_full_version": full_version,
        "python_version": ".".join(full_version.split(".")[:2]),
        "sys_platform": "linux",
    }


def _applicable(
    pins: list[_Pin],
    marker_environment: dict[str, str],
) -> dict[str, _Pin]:
    """[private] Os requisitos cujo marcador vale no ambiente dado, ou que não têm marcador, pelo
    nome normalizado."""
    applicable: dict[str, _Pin] = {}
    for pin in pins:
        if pin.marker is not None and not Marker(pin.marker).evaluate(marker_environment):
            continue
        applicable[pin.name] = pin
    return applicable


def _compare(
    closure: dict[str, _Pin],
    in_environment: dict[str, str],
) -> tuple[dict[str, str], dict[str, tuple[str, str]], dict[str, _Pin]]:
    """[private] Separa o fechamento do projeto no que a imagem já tem na mesma versão, no que ela
    tem em outra versão e no que ela não tem."""
    from_environment: dict[str, str] = {}
    conflicts: dict[str, tuple[str, str]] = {}
    vendored: dict[str, _Pin] = {}
    for name in sorted(closure):
        pin = closure[name]
        environment_version = in_environment.get(name)
        if environment_version is None:
            vendored[name] = pin
        elif environment_version == pin.version:
            from_environment[name] = pin.version
        else:
            conflicts[name] = (pin.version, environment_version)
    return from_environment, conflicts, vendored


def _conflict_message(
    conflicts: dict[str, tuple[str, str]],
    from_environment: dict[str, str],
    in_environment: dict[str, str],
) -> str:
    """[private] A recusa de um lock que discorda da imagem, com o bloco que alinha o projeto às
    versões da imagem em cada pacote que os dois compartilham."""
    lines = ["o lock do projeto e o ambiente da imagem discordam:"]
    for name in sorted(conflicts):
        locked, image = conflicts[name]
        lines.append(f"  {name}: {locked} no lock, {image} na imagem")

    # O bloco fixa cada pacote compartilhado na versão da imagem, os que já concordam incluídos.
    shared = sorted(set(from_environment) | set(conflicts))
    lines.append("")
    lines.append("acrescente ao pyproject.toml do projeto e rode uv lock; quando um limite")
    lines.append("inferior do projeto passa da versão da imagem, esse lock falha, e a dependência")
    lines.append("não serve a esta imagem:")
    lines.append("")
    lines.append("[tool.uv]")
    lines.append("constraint-dependencies = [")
    for name in shared:
        lines.append(f'  "{name}=={in_environment[name]}",')
    lines.append("]")
    return "\n".join(lines)
