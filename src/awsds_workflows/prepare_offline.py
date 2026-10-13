"""[public] A pasta de um projeto uv preparada para rodar sem rede, com o próprio interpretador,
num ``.tar.gz``: a entrada de código de um job de processamento, que o comando do job extrai no
volume antes de rodar.

A pasta do ``package-job`` (``awsds_workflows.package_job``) vai ao S3 expandida, um objeto por
arquivo, e leva só o que o ambiente da imagem do job não tem. Um projeto com a ``.venv/`` pronta,
de muitos arquivos pequenos, pode ir como um objeto só: o ``.tar.gz`` da pasta inteira, com o
CPython e as dependências dentro dela, nas versões do projeto. A imagem entra só com o sistema, o
``bash``, o ``tar``, o ``gzip``, o ``sudo`` e a glibc; o interpretador da imagem não é chamado, e o
lock do projeto não precisa concordar com ela.

``prepare_archive`` grava o ``.tar.gz`` a partir de uma cópia do projeto, sem alterar a pasta dele:

1. A cópia leva o projeto sem a ``.venv/``, o ``.python/``, o ``.git`` e os caches, e com o
   ``uv.lock``.
2. ``uv sync --locked --python <versão> --no-dev --no-editable`` recria a ``.venv/`` da cópia com o
   CPython gerenciado pelo ``uv`` instalado em ``.python/``, dentro dela (``UV_PYTHON_INSTALL_DIR``
   e ``UV_MANAGED_PYTHON``), e os pacotes copiados do cache (``UV_LINK_MODE=copy``). O projeto
   entra como pacote, porque a instalação editável grava um ``.pth`` com o caminho absoluto da
   pasta; ``--locked`` recusa um lock desatualizado.
3. Cada link absoluto de ``.venv/`` e ``.python/`` fica relativo, apontando para o arquivo real
   dentro da cópia: o ``uv`` cria absolutos o ``.venv/bin/python`` e o link da versão em
   ``.python/``. O ``home`` de ``pyvenv.cfg`` guarda o caminho de origem, que o Python não consulta
   quando o link resolve.
4. O ``.tar.gz`` é gravado pelo Python, com os links e os modos, com a raiz do nome da pasta do
   projeto e sem o usuário desta máquina.
5. A prova: o arquivo é extraído numa pasta temporária, e o ``.venv/bin/python`` de lá, num
   ambiente sem o ``uv``, lê a versão do pacote do projeto e o próprio prefixo, que tem de ser a
   ``.venv/`` extraída.

A pasta só serve ao job preparada na plataforma dele, Linux x86_64, porque o ``uv`` baixa o
interpretador e os wheels da máquina em que roda; outra plataforma é recusada antes de qualquer
download. O ``VolumeSizeInGB`` do job tem de caber o arquivo e a pasta extraída.

Medido em 2026-10-13 sobre ``examples/awsds-demo-job``, com o uv 0.11.32: o CPython 3.12.13 em
100.119.806 bytes extraídos, 98.862.413 deles o interpretador, num ``.tar.gz`` de 34.111.121 bytes,
gravado em 14 s com o download. A pasta extraída noutro caminho, por um usuário sem privilégio e
sem ``uv`` nem rede, rodou o projeto sobre a amostra e escreveu o resumo com o sha256 das execuções
medidas. Nenhum ``.tar.gz`` rodou num job até essa data.

Exemplo:

.. code-block:: python

    from pathlib import Path

    from awsds_workflows import prepare_offline

    archive = prepare_offline.prepare_archive(
        Path("/home/usuario/src/meu-projeto"),
        Path("/tmp/meu-projeto.tar.gz"),
    )
    print(archive.root, archive.python, archive.size_bytes)
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import tarfile
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path

from awsds_workflows import _uv
from awsds_workflows.errors import RefusalError

__all__ = [
    "DEFAULT_PYTHON",
    "OfflineArchive",
    "prepare_archive",
]

DEFAULT_PYTHON = "3.12"
"""[public] A versão do CPython que vai na pasta por padrão, a do worker e a da imagem padrão do
job."""

# A plataforma do job, o sistema e a máquina como o platform os nomeia.
_JOB_SYSTEM = ("Linux", "x86_64")

# O que a cópia do projeto deixa para trás: o que o uv, o git e o pytest gravam.
_LEFT_BEHIND = shutil.ignore_patterns(".venv", ".python", ".git", "__pycache__", ".pytest_cache")


@dataclass(frozen=True)
class OfflineArchive:
    """[public] O ``.tar.gz`` que ``prepare_archive`` gravou, com o que a linha de comando imprime.

    Exemplo:

    .. code-block:: python

        archive = prepare_archive(Path("meu-projeto"), Path("/tmp/meu-projeto.tar.gz"))
        print(archive.root)  # 'meu-projeto'
        print(archive.python)  # '3.12.13'
    """

    path: Path
    """[public] O caminho absoluto do ``.tar.gz``."""

    size_bytes: int
    """[public] O tamanho do ``.tar.gz``, em bytes."""

    extracted_bytes: int
    """[public] A soma dos tamanhos dos arquivos da pasta, em bytes, o que a extração ocupa no
    volume do job."""

    root: str
    """[public] O nome da pasta na raiz do ``.tar.gz``, o da pasta do projeto."""

    python: str
    """[public] A versão completa do CPython que foi na pasta, como ``3.12.13``."""


def prepare_archive(
    project: Path,
    archive: Path,
    python: str = DEFAULT_PYTHON,
) -> OfflineArchive:
    """[public] Grava o ``.tar.gz`` da pasta de um projeto uv preparada com o próprio interpretador.

    Exemplo:

    .. code-block:: python

        archive = prepare_archive(Path("meu-projeto"), Path("/tmp/meu-projeto.tar.gz"))

    :param project: a pasta do projeto uv, com ``pyproject.toml`` e ``uv.lock``; ela não é
        alterada.
    :param archive: o caminho do ``.tar.gz``, numa pasta que já existe; um arquivo que já está ali
        é substituído, e uma recusa o deixa como estava.
    :param python: a versão do CPython que vai na pasta, como ``3.12``; o ``requires-python`` do
        projeto tem de admiti-la.
    :return: o ``.tar.gz`` gravado, com os tamanhos, a raiz e a versão do interpretador.
    :raises awsds_workflows.errors.RefusalError: quando esta máquina não é Linux x86_64, quando
        falta o ``uv.lock`` ou a pasta do arquivo, quando o nome não termina em ``.tar.gz``, quando
        o ``uv`` recusa o lock ou não acha nem baixa o Python pedido, quando um link da pasta
        aponta para fora dela e quando a pasta extraída não roda.
    """
    # Os caminhos absolutos, porque o uv roda dentro da cópia.
    project = project.resolve()
    archive = archive.resolve()
    _check_inputs(project, archive)
    root = project.name

    with tempfile.TemporaryDirectory() as temporary:
        workspace = Path(temporary).resolve()
        stage = workspace / root
        shutil.copytree(project, stage, symlinks=True, ignore=_LEFT_BEHIND)
        _sync(stage, python)
        _relink(stage)

        # O arquivo é gravado e provado na pasta temporária, e só então toma o lugar do antigo.
        staged = workspace / archive.name
        _write_archive(stage, staged, root)
        version = _check_extracted(staged, workspace / "check", root, _project_name(stage))
        extracted_bytes = _size(stage)
        shutil.move(staged, archive)

    return OfflineArchive(
        path=archive,
        size_bytes=archive.stat().st_size,
        extracted_bytes=extracted_bytes,
        root=root,
        python=version,
    )


def _system() -> tuple[str, str]:
    """[private] O sistema e a máquina desta plataforma, como o ``platform`` os nomeia; o dublê dos
    testes troca esta função."""
    return (platform.system(), platform.machine())


def _check_inputs(
    project: Path,
    archive: Path,
) -> None:
    """[private] Recusa, antes de qualquer download, outra plataforma, o projeto sem ``uv.lock``,
    um nome que não termina em ``.tar.gz`` e a pasta do arquivo que não existe."""
    system = _system()
    if system != _JOB_SYSTEM:
        machine = " ".join(system)
        raise RefusalError(
            f"esta máquina é {machine}, e a pasta só serve ao job preparada em Linux x86_64"
        )
    if not (project / "uv.lock").is_file():
        raise RefusalError(f"não há uv.lock em {project}: rode uv lock lá antes")
    if not archive.name.endswith(".tar.gz"):
        raise RefusalError(
            f"{archive.name}: nomeie o arquivo com .tar.gz, o formato que o tar -xzf do job extrai"
        )
    if not archive.parent.is_dir():
        raise RefusalError(f"a pasta {archive.parent} não existe")


def _sync(
    stage: Path,
    python: str,
) -> None:
    """[private] Recria a ``.venv/`` da cópia com o CPython gerenciado pelo ``uv`` em ``.python/``,
    o projeto como pacote e as dependências de execução, nas versões do lock."""
    environment = {
        # O interpretador fica dentro da cópia, baixado pelo uv, nunca um Python desta máquina.
        "UV_PYTHON_INSTALL_DIR": str(stage / ".python"),
        "UV_PYTHON_DOWNLOADS": "automatic",
        "UV_MANAGED_PYTHON": "1",
        # A .venv/ fica dentro da cópia, mesmo com UV_PROJECT_ENVIRONMENT no ambiente.
        "UV_PROJECT_ENVIRONMENT": str(stage / ".venv"),
        # Os pacotes são copiados do cache, e não ligados a ele por hardlink.
        "UV_LINK_MODE": "copy",
    }
    arguments = ["sync", "--locked", "--python", python, "--no-dev", "--no-editable", "--quiet"]
    _uv.run(arguments, cwd=stage, env=environment)


def _symlinks(
    folder: Path,
) -> list[Path]:
    """[private] Cada link simbólico de ``folder``, em ordem de caminho, sem entrar num link para
    uma pasta."""
    found: list[Path] = []
    for directory, folders, files in os.walk(folder):
        for name in folders + files:
            path = Path(directory) / name
            if path.is_symlink():
                found.append(path)
    return sorted(found)


def _relink(
    stage: Path,
) -> None:
    """[private] Troca cada link absoluto de ``.venv/`` e ``.python/`` por um relativo ao arquivo
    real, e recusa um que aponte para fora da cópia."""
    for folder in (stage / ".venv", stage / ".python"):
        for link in _symlinks(folder):
            if not Path(os.readlink(link)).is_absolute():
                continue
            real = link.resolve()
            if not real.is_relative_to(stage):
                raise RefusalError(f"{link.relative_to(stage)} aponta para fora da pasta: {real}")
            link.unlink()
            link.symlink_to(os.path.relpath(real, link.parent))


def _without_owner(
    member: tarfile.TarInfo,
) -> tarfile.TarInfo:
    """[private] O membro sem o usuário e o grupo desta máquina, que o job não tem."""
    member.uid = 0
    member.gid = 0
    member.uname = ""
    member.gname = ""
    return member


def _write_archive(
    stage: Path,
    archive: Path,
    root: str,
) -> None:
    """[private] Grava a cópia em ``archive`` sob a pasta ``root``, com os links e os modos."""
    with tarfile.open(archive, "w:gz", compresslevel=6) as opened:
        opened.add(stage, arcname=root, filter=_without_owner)


def _project_name(
    stage: Path,
) -> str:
    """[private] O nome do projeto no ``pyproject.toml``, o da distribuição que a ``.venv/``
    instalou."""
    pyproject = tomllib.loads((stage / "pyproject.toml").read_text(encoding="utf-8"))
    return pyproject["project"]["name"]


def _check_extracted(
    archive: Path,
    folder: Path,
    root: str,
    name: str,
) -> str:
    """[private] Extrai o ``.tar.gz`` em ``folder`` e roda o ``.venv/bin/python`` de lá num
    ambiente sem o ``uv``: devolve a versão do interpretador, e recusa uma pasta que não roda ou
    cujo interpretador não usa a ``.venv/`` extraída."""
    folder.mkdir()
    with tarfile.open(archive) as opened:
        opened.extractall(folder, filter="data")
    interpreter = folder / root / ".venv" / "bin" / "python"
    code = (
        "import importlib.metadata, sys\n"
        f"importlib.metadata.version({name!r})\n"
        "print(sys.version.split()[0])\n"
        "print(sys.prefix)\n"
    )
    completed = subprocess.run(
        [interpreter, "-c", code],
        env={"PATH": "/usr/bin:/bin"},
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        raise RefusalError(f"a pasta extraída não roda:\n{completed.stderr.strip()}")
    version, prefix = completed.stdout.split()
    if Path(prefix) != folder / root / ".venv":
        raise RefusalError(f"o interpretador da pasta extraída usa {prefix}, e não a .venv/ dela")
    return version


def _size(
    folder: Path,
) -> int:
    """[private] A soma dos tamanhos dos arquivos de ``folder``, sem contar os links."""
    total = 0
    for path in folder.rglob("*"):
        if path.is_file() and not path.is_symlink():
            total += path.stat().st_size
    return total
