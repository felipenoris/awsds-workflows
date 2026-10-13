"""[private] As chamadas ao ``uv`` que os dois empacotadores fazem.

O ``uv`` é o programa que estiver no ``PATH``, e herda o ambiente do processo: as variáveis do
``uv``, como o ``UV_PYTHON`` que nomeia o interpretador, valem para cada chamada. Uma chamada que
termina com erro vira ``awsds_workflows.errors.RefusalError`` com a saída de erro do ``uv``, onde
ele diz que o lock está desatualizado, que uma dependência não publica wheel para a plataforma
pedida ou que não acha o Python que o projeto pede.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path

from awsds_workflows.errors import RefusalError


def run(
    arguments: list[str],
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> str:
    """[protected] Roda o ``uv`` com os argumentos e devolve a saída padrão, para os
    empacotadores.

    :param arguments: os argumentos depois de ``uv``.
    :param cwd: a pasta em que o ``uv`` roda; ``None`` é a pasta atual.
    :param env: as variáveis que completam e substituem as do processo nesta chamada; ``None``
        passa o ambiente do processo como está.
    :return: a saída padrão do ``uv``.
    :raises awsds_workflows.errors.RefusalError: quando o ``uv`` não está no ``PATH`` ou termina
        com erro.
    """
    executable = shutil.which("uv")
    if executable is None:
        raise RefusalError("o uv não está no PATH: instale-o (https://docs.astral.sh/uv/)")

    environment = None
    if env is not None:
        environment = {**os.environ, **env}

    # A saída do uv é UTF-8 e traz caracteres de desenho nas mensagens de erro.
    completed = subprocess.run(
        [executable, *arguments],
        cwd=cwd,
        env=environment,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        command = " ".join(arguments[:2])
        raise RefusalError(f"uv {command} falhou:\n{completed.stderr.strip()}")
    return completed.stdout


def export_closure(
    project: Path,
    pruned: Sequence[str] = (),
) -> str:
    """[protected] O fechamento travado do projeto como texto de requisitos, para os empacotadores:
    cada dependência na versão do ``uv.lock``, com os hashes, sem o próprio projeto e sem o grupo
    ``dev``.

    ``--locked`` recusa um lock desatualizado, e ``--prune`` tira cada pacote de ``pruned`` com as
    dependências que só ele usa.

    :param project: a pasta do projeto, com ``pyproject.toml`` e ``uv.lock``.
    :param pruned: os pacotes a tirar do fechamento, pelo nome no PyPI.
    :return: a saída do ``uv export``, um ``nome==versão`` por pacote, com o marcador PEP 508 de
        quem o tem e as linhas dos hashes.
    :raises awsds_workflows.errors.RefusalError: quando o ``uv`` recusa o lock ou não acha o Python
        que o projeto pede.
    """
    arguments = ["export", "--locked", "--no-dev", "--no-emit-project", "--no-header", "--quiet"]
    for name in pruned:
        arguments += ["--prune", name]
    return run(arguments, cwd=project)


def _install_arguments(
    target: Path,
    python: str,
    platform: str,
) -> list[str]:
    """[private] O começo de cada ``uv pip install`` dos empacotadores: em ``target``, sem
    dependências, com os wheels do alvo, e não os desta máquina."""
    arguments = ["pip", "install", "--quiet", "--target", str(target), "--no-deps"]
    arguments += ["--python-version", python, "--python-platform", platform]
    return arguments


def install_requirements(
    requirements: Path,
    target: Path,
    python: str,
    platform: str,
) -> None:
    """[protected] Instala em ``target`` os wheels do alvo para um arquivo de requisitos, para os
    empacotadores.

    ``--no-deps`` instala o arquivo como ele está, sem trazer de volta um pacote podado, e
    ``--only-binary :all:`` recusa uma distribuição de código-fonte, que seria compilada para esta
    máquina. Os hashes do arquivo, quando ele os traz, são conferidos.

    :param requirements: o arquivo de requisitos, um ``nome==versão`` por pacote.
    :param target: a pasta em que os pacotes são instalados lado a lado.
    :param python: a versão do CPython do alvo, como ``3.12``.
    :param platform: a plataforma do alvo no formato do ``--python-platform`` do ``uv``.
    :raises awsds_workflows.errors.RefusalError: quando uma dependência não publica wheel para o
        alvo ou um hash não confere.
    """
    arguments = _install_arguments(target, python, platform)
    arguments += ["--only-binary", ":all:", "--requirements", str(requirements)]
    run(arguments)


def build_pure_wheel(
    project: Path,
    out_dir: Path,
) -> list[Path]:
    """[protected] Constrói o wheel do projeto em ``out_dir`` e o recusa quando não é Python puro,
    para os empacotadores.

    Um wheel com módulos de extensão construído aqui seria desta máquina, e não do alvo. O
    ``requires-python`` do projeto precisa admitir a versão do alvo, porque a instalação seguinte
    o confere.

    :param project: a pasta do projeto, com o ``pyproject.toml``.
    :param out_dir: a pasta em que o wheel é gravado.
    :return: os wheels gravados, em ordem de nome.
    :raises awsds_workflows.errors.RefusalError: quando a construção falha ou o wheel não é Python
        puro.
    """
    run(["build", str(project), "--wheel", "--out-dir", str(out_dir), "--quiet"])
    wheels = sorted(out_dir.glob("*.whl"))
    impure = [wheel.name for wheel in wheels if not wheel.name.endswith("-none-any.whl")]
    if impure:
        names = ", ".join(impure)
        raise RefusalError(
            f"{names}: não é Python puro, e um wheel construído aqui não serve ao alvo; construa-o "
            "na plataforma do alvo"
        )
    return wheels


def install_wheels(
    wheels: list[Path],
    target: Path,
    python: str,
    platform: str,
) -> None:
    """[protected] Instala os wheels em ``target`` para o alvo, sem dependências, para os
    empacotadores.

    :param wheels: os arquivos ``.whl``.
    :param target: a pasta em que os pacotes são instalados lado a lado.
    :param python: a versão do CPython do alvo, como ``3.12``.
    :param platform: a plataforma do alvo no formato do ``--python-platform`` do ``uv``.
    :raises awsds_workflows.errors.RefusalError: quando o ``requires-python`` de um wheel não admite
        a versão do alvo.
    """
    arguments = _install_arguments(target, python, platform)
    arguments += [str(wheel) for wheel in wheels]
    run(arguments)


def remove_leftovers(
    folder: Path,
) -> None:
    """[protected] Apaga de ``folder`` o que o ``uv pip install --target`` deixa e o alvo não
    importa, para os empacotadores: o arquivo de trava ``.lock``, os scripts de ``bin/`` e o
    bytecode.

    Um bytecode de outra plataforma pode não carregar no alvo, e o alvo gera o seu.

    :param folder: a pasta em que os pacotes foram instalados.
    """
    lock_file = folder / ".lock"
    if lock_file.exists():
        lock_file.unlink()
    shutil.rmtree(folder / "bin", ignore_errors=True)

    # O bytecode: as pastas __pycache__ e um .pyc solto que um wheel traga.
    for cache in list(folder.rglob("__pycache__")):
        shutil.rmtree(cache)
    for bytecode in list(folder.rglob("*.pyc")):
        bytecode.unlink()
