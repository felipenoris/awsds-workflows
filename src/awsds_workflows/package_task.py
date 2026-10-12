"""[public] O ``.zip`` de código de uma task Python ou Bash de um workflow do MWAA Serverless.

Uma task Python ou Bash roda no worker, a máquina que o MWAA Serverless prepara para cada
execução, sem internet. O código dela chega num único ``.py``, ``.sh`` ou ``.zip``, que o worker
extrai em ``/usr/local/airflow/dags``, uma pasta do ``sys.path``. Por isso o ``.zip`` leva tudo na
raiz: o pacote do projeto, cada dependência que o ``uv.lock`` do projeto fixa, em wheels do
interpretador e da plataforma do worker, o módulo de entrada que o ``python_callable`` de uma task
Python nomeia e os arquivos que uma task Bash chama, como um script ou um binário. Os pacotes que
o worker já traz ficam de fora, com cada dependência que só eles usam.

``build_archive`` roda na máquina com internet, onde o ``uv`` alcança o PyPI; o ``.zip`` é enviado
depois ao workflow, em *Settings → Storage → Python/Bash Operator Files*. O alvo é sempre o
worker, qualquer que seja a imagem dos jobs do projeto.

Os passos, cada um com a regra do worker que cumpre:

1. ``uv export --locked --no-dev --no-emit-project --prune <nome> ...`` grava o fechamento travado,
   a lista de todas as dependências nas versões do ``uv.lock``, como arquivo de requisitos.
   ``--locked`` recusa um lock desatualizado, e ``--prune`` tira cada pacote do worker junto com
   as dependências que só ele usa: o ``boto3`` leva o ``s3transfer`` e o ``jmespath``, e o
   ``urllib3``, de que o ``requests`` também precisa, fica.
2. ``uv pip install --target --no-deps --only-binary :all:`` com ``--python-version`` e
   ``--python-platform`` instala os wheels do worker para esse fechamento, com os hashes do lock.
   ``--only-binary`` recusa uma distribuição de código-fonte, que seria compilada para esta
   máquina.
3. ``uv build --wheel`` constrói o projeto, recusado quando não é Python puro, e a mesma instalação
   põe o pacote dele na raiz.
4. O arquivo de trava do ``uv``, os scripts de ``bin/`` e o bytecode saem.
5. O módulo de entrada e os arquivos de ``include`` são copiados para a raiz com o modo de cada um;
   um nome que já está na raiz é recusado.
6. O ``.zip`` é gravado pelo Python, com o modo de cada arquivo, o bit de execução incluído; um
   conteúdo acima de 250 MB descompactado é recusado antes de gravar.

Medido em 2026-10-11 num projeto que dependia de ``petl``, ``requests``, ``boto3`` e ``pyyaml``:
cerca de 0,9 MB, com o projeto, ``tasks.py``, o ``petl`` e o ``requests`` com ``certifi``,
``charset_normalizer``, ``idna`` e ``urllib3``; sem ``boto3``, ``botocore``, ``s3transfer``,
``jmespath`` ou ``yaml``; os módulos compilados do ``charset_normalizer`` com a etiqueta
``cp312-cp312-manylinux2014_x86_64``, e ``cpython-313`` com ``python="3.13"``. No laboratório, um
``.zip`` com a mesma forma, montado à mão, rodou numa task Python em 2026-10-11, depois que a
política do endpoint de gateway do S3 passou a admitir o bucket em que o serviço guarda a cópia do
código: o ``petl`` foi importado de ``/usr/local/airflow/dags``. Nenhum ``.zip`` gravado por
``build_archive`` rodou num worker até essa data.

Exemplo:

.. code-block:: python

    from pathlib import Path

    from awsds_workflows import package_task

    project = Path("/home/usuario/src/meu-projeto")
    archive = package_task.build_archive(
        project,
        project / "tasks.py",
        Path("/tmp/meu-projeto.zip"),
    )
    print(archive.size_bytes, archive.top_level)
"""

from __future__ import annotations

import shutil
import tempfile
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from awsds_workflows import _uv
from awsds_workflows.errors import RefusalError

__all__ = [
    "ARCHIVE_LIMIT_BYTES",
    "TaskArchive",
    "WORKER_PLATFORM",
    "WORKER_PROVIDED",
    "WORKER_PYTHON",
    "build_archive",
]

WORKER_PYTHON = "3.12"
"""[public] A versão do CPython do worker, segundo o guia do MWAA Serverless lido em 2026-10-11.

O serviço pode trocar o interpretador sem aviso, e o log de uma task nomeia o que rodou nos
caminhos (``.../python3.12/site-packages/...``): quando o caminho mudar, passe a nova versão em
``python``.
"""

WORKER_PLATFORM = "x86_64-manylinux2014"
"""[public] A plataforma do worker, Linux x86_64, no formato do ``--python-platform`` do ``uv``."""

WORKER_PROVIDED = (
    "apache-airflow",
    "apache-airflow-providers-amazon",
    "boto3",
    "botocore",
    "dag-factory",
    "pyyaml",
    "lz4",
    "aws-encryption-sdk",
    "aws-cryptographic-material-providers",
    "aws-cryptography-internal-kms",
    "aws-cryptography-internal-dynamodb",
    "aws-cryptography-internal-primitives",
)
"""[public] Os pacotes que o worker já traz, da tabela do guia lida em 2026-10-11; eles ficam fora
do ``.zip``.

Numa task Python, a cópia do worker vence a do ``.zip``, como o guia diz e o laboratório mediu em
2026-10-11: o PyYAML 6.0.2 do worker foi importado no lugar do 6.0.1 de um ``.zip``. Numa task
Bash que roda ``python3 -m`` a partir de ``/usr/local/airflow/dags``, a pasta vem antes no
``sys.path``, e a cópia do ``.zip`` venceria (não medido). Sem esses pacotes no ``.zip``, as duas
tasks importam os do worker, então o código da task é escrito contra as versões dele: o Airflow
3.0.6, o provider da Amazon 9.32.0 e o ``boto3`` 1.43.1.
"""

ARCHIVE_LIMIT_BYTES = 250_000_000
"""[public] O limite do guia para o ``.zip``, que vale também para o conteúdo descompactado."""


@dataclass(frozen=True)
class TaskArchive:
    """[public] O ``.zip`` que ``build_archive`` gravou, com o que a linha de comando imprime.

    Exemplo:

    .. code-block:: python

        archive = build_archive(project, project / "tasks.py", Path("task.zip"))
        print(archive.path, archive.size_bytes, archive.unzipped_bytes)
        print(archive.top_level)  # ['certifi', ..., 'meu_pacote', 'tasks.py']
    """

    path: Path
    """[public] O caminho absoluto do ``.zip``."""

    size_bytes: int
    """[public] O tamanho do ``.zip``, em bytes."""

    unzipped_bytes: int
    """[public] A soma dos tamanhos dos arquivos dentro do ``.zip``, em bytes."""

    top_level: list[str]
    """[public] Os nomes na raiz do ``.zip``, em ordem alfabética."""

    python: str
    """[public] A versão do CPython para a qual os wheels foram escolhidos."""

    platform: str
    """[public] A plataforma para a qual os wheels foram escolhidos."""


def build_archive(
    project: Path,
    entry_module: Path | None,
    archive: Path,
    python: str = WORKER_PYTHON,
    platform: str = WORKER_PLATFORM,
    omit: Sequence[str] = (),
    include: Sequence[Path] = (),
) -> TaskArchive:
    """[public] Grava o ``.zip`` de uma task Python ou Bash a partir de um projeto uv.

    O projeto precisa de um ``pyproject.toml`` e de um ``uv.lock`` em dia, de um
    ``requires-python`` que admita ``python`` e de código próprio em Python puro. O módulo de
    entrada e os arquivos de ``include`` vão para a raiz com o modo de cada um, e o ``.zip`` guarda
    o bit de execução de um script ou de um binário. A pasta temporária da construção é apagada ao
    fim.

    Exemplo:

    .. code-block:: python

        # Uma task Python, com python_callable: tasks.run
        archive = build_archive(
            Path("meu-projeto"),
            Path("meu-projeto/tasks.py"),
            Path("meu-projeto.zip"),
            omit=["pandas"],
        )

        # Uma task Bash, que chama python3 -m meu_pacote ou bash run.sh
        archive = build_archive(
            Path("meu-projeto"),
            None,
            Path("meu-projeto.zip"),
            include=[Path("meu-projeto/run.sh")],
        )

    :param project: a pasta do projeto uv, com ``pyproject.toml`` e ``uv.lock``.
    :param entry_module: o arquivo ``.py`` que vai para a raiz do ``.zip`` e que o
        ``python_callable`` de uma task Python nomeia como ``<módulo>.<função>``; ``None`` quando
        só tasks Bash usam o ``.zip``.
    :param archive: o caminho do ``.zip``, numa pasta que já existe; um ``.zip`` que já está ali é
        substituído, e uma recusa o deixa como estava.
    :param python: a versão do CPython do worker, como ``3.12``.
    :param platform: a plataforma do worker no formato do ``--python-platform`` do ``uv``.
    :param omit: mais pacotes a deixar de fora, além de ``WORKER_PROVIDED``, pelo nome no PyPI.
    :param include: mais arquivos a pôr na raiz do ``.zip``, cada um com o próprio nome, como o
        script ``.sh`` ou o binário que uma task Bash chama; uma pasta não é aceita.
    :return: o ``.zip`` gravado, com o tamanho e os nomes da raiz.
    :raises awsds_workflows.errors.RefusalError: quando falta o ``uv.lock``, o módulo de entrada,
        um arquivo de ``include`` ou a pasta do ``.zip``, quando o ``uv`` não acha o Python que o
        projeto pede, quando ele recusa o lock ou uma dependência sem wheel para o alvo, quando o
        projeto não é Python puro, quando um arquivo tem o nome de outro que já está na raiz e
        quando o conteúdo passa do limite do worker.
    """
    # Os caminhos absolutos, porque o uv roda dentro da pasta do projeto.
    project = project.resolve()
    archive = archive.resolve()
    root_files = [path.resolve() for path in include]
    if entry_module is not None:
        root_files.insert(0, entry_module.resolve())
    _check_inputs(project, root_files, archive)

    with tempfile.TemporaryDirectory() as temporary:
        stage = Path(temporary)
        root = stage / "root"

        # O fechamento travado, sem o projeto e sem os pacotes do worker, em wheels do worker.
        closure = _uv.export_closure(project, [*WORKER_PROVIDED, *omit])
        requirements = stage / "requirements.txt"
        requirements.write_text(closure, encoding="utf-8")
        _uv.install_requirements(requirements, root, python, platform)

        # O pacote do projeto, de um wheel construído a partir do pyproject.toml.
        wheels = _uv.build_pure_wheel(project, stage / "dist")
        _uv.install_wheels(wheels, root, python, platform)
        _uv.remove_leftovers(root)

        # O módulo de entrada e os arquivos de include vão para a raiz depois da limpeza, que
        # apagaria um .pyc ou um .lock incluído.
        for path in root_files:
            _copy_to_root(path, root)

        unzipped_bytes = _write_archive(root, archive)
        top_level = sorted(path.name for path in root.iterdir())

    return TaskArchive(
        path=archive,
        size_bytes=archive.stat().st_size,
        unzipped_bytes=unzipped_bytes,
        top_level=top_level,
        python=python,
        platform=platform,
    )


def _check_inputs(
    project: Path,
    root_files: list[Path],
    archive: Path,
) -> None:
    """[private] Recusa, antes de qualquer download, o projeto sem ``uv.lock``, o arquivo da raiz
    que não existe ou é uma pasta e a pasta do ``.zip`` que não existe."""
    if not (project / "uv.lock").is_file():
        raise RefusalError(f"não há uv.lock em {project}: rode uv lock lá antes")
    for path in root_files:
        if not path.is_file():
            raise RefusalError(f"não há arquivo em {path}")
    if not archive.parent.is_dir():
        raise RefusalError(f"a pasta {archive.parent} não existe")


def _copy_to_root(
    path: Path,
    root: Path,
) -> None:
    """[private] Copia ``path`` para a raiz com o modo dele, e recusa um nome que já está lá, de um
    pacote ou de outro arquivo."""
    destination = root / path.name
    if destination.exists():
        raise RefusalError(f"{path.name} já está na raiz do .zip: renomeie {path}")
    shutil.copy2(path, destination)


def _write_archive(
    root: Path,
    archive: Path,
) -> int:
    """[private] Grava o conteúdo de ``root`` em ``archive``, sem uma pasta de topo, e devolve o
    tamanho descompactado; recusa sem gravar um conteúdo acima de ``ARCHIVE_LIMIT_BYTES``.

    O ``.zip`` é gravado pelo Python, e não pelo ``zip``, que nem todo ambiente traz; o
    ``ZipFile.write`` guarda o modo de cada arquivo, o bit de execução incluído.
    """
    files = sorted(path for path in root.rglob("*") if path.is_file())
    unzipped_bytes = sum(path.stat().st_size for path in files)
    if unzipped_bytes > ARCHIVE_LIMIT_BYTES:
        raise RefusalError(
            f"{archive} descompactaria em {unzipped_bytes} bytes, acima do limite de "
            f"{ARCHIVE_LIMIT_BYTES} bytes do worker; nada foi gravado"
        )

    # Cada arquivo entra pelo caminho relativo à raiz: o worker extrai o .zip em dags/.
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for path in files:
            zip_file.write(path, path.relative_to(root).as_posix())
    return unzipped_bytes
