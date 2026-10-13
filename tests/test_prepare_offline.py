"""``awsds_workflows.prepare_offline``: as recusas antes de qualquer download e, com ``network``,
o ``.tar.gz`` de um projeto de teste: a raiz com o nome da pasta, nenhum link absoluto, nenhum
usuário desta máquina, o arquivo antigo substituído e a pasta do projeto intacta; extraído noutro
lugar, o projeto e a dependência rodam com o interpretador da pasta, sem ``uv`` no ambiente.
"""

from __future__ import annotations

import subprocess
import tarfile
from pathlib import Path

import pytest
from conftest import write_project

from awsds_workflows import prepare_offline
from awsds_workflows.errors import RefusalError


def another_platform() -> tuple[str, str]:
    """O dublê de ``_system``: um macOS em ARM."""
    return ("Darwin", "arm64")


def test_another_platform_is_refused(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fora de Linux x86_64 a recusa nomeia esta máquina, antes de ler o projeto."""
    monkeypatch.setattr(prepare_offline, "_system", another_platform)
    with pytest.raises(RefusalError, match="esta máquina é Darwin arm64"):
        prepare_offline.prepare_archive(tmp_path, tmp_path / "projeto.tar.gz")


def test_a_project_without_a_lock_is_refused(
    tmp_path: Path,
) -> None:
    """Sem ``uv.lock``, a recusa diz o que rodar."""
    with pytest.raises(RefusalError, match="não há uv.lock"):
        prepare_offline.prepare_archive(tmp_path, tmp_path / "projeto.tar.gz")


def test_a_name_without_tar_gz_is_refused(
    tmp_path: Path,
) -> None:
    """O nome do arquivo termina em ``.tar.gz``, o formato que o comando do job extrai."""
    (tmp_path / "uv.lock").write_text("", encoding="utf-8")
    with pytest.raises(RefusalError, match="nomeie o arquivo com .tar.gz"):
        prepare_offline.prepare_archive(tmp_path, tmp_path / "projeto.tgz")


def test_a_missing_archive_folder_is_refused(
    tmp_path: Path,
) -> None:
    """A pasta do ``.tar.gz`` tem de existir."""
    (tmp_path / "uv.lock").write_text("", encoding="utf-8")
    with pytest.raises(RefusalError, match="não existe"):
        prepare_offline.prepare_archive(tmp_path, tmp_path / "nao-existe" / "projeto.tar.gz")


@pytest.fixture(scope="module")
def locked_project(
    tmp_path_factory: pytest.TempPathFactory,
) -> Path:
    """O projeto de teste ``meu-projeto``, que depende do ``six``, travado, compartilhado pelos
    testes ``network`` do módulo."""
    project = tmp_path_factory.mktemp("projeto") / "meu-projeto"
    project.mkdir()
    return write_project(project, "meu-projeto", ["six"])


def test_a_refusal_leaves_the_old_archive(
    locked_project: Path,
    tmp_path: Path,
) -> None:
    """Um Python que o ``uv`` não baixa recusa depois de copiar o projeto, e o arquivo antigo fica
    como estava."""
    archive = tmp_path / "meu-projeto.tar.gz"
    archive.write_bytes(b"velho")
    with pytest.raises(RefusalError, match="uv sync --locked falhou"):
        prepare_offline.prepare_archive(locked_project, archive, python="3.99")
    assert archive.read_bytes() == b"velho"


@pytest.mark.network
def test_the_archive_has_the_project_root_relative_links_and_no_owner(
    locked_project: Path,
    tmp_path: Path,
) -> None:
    """O ``.tar.gz`` tem só a raiz ``meu-projeto/``, com a ``.venv/`` e o ``uv.lock``, nenhum link
    absoluto e nenhum usuário; ele substitui o arquivo que estava lá, e o projeto segue sem
    ``.venv/`` e sem ``.python/``."""
    archive_path = tmp_path / "meu-projeto.tar.gz"
    archive_path.write_bytes(b"velho")
    archive = prepare_offline.prepare_archive(locked_project, archive_path)
    assert archive.path == archive_path
    assert archive.root == "meu-projeto"
    assert archive.python.startswith("3.12.")
    assert archive.size_bytes == archive_path.stat().st_size
    assert archive.extracted_bytes > archive.size_bytes

    with tarfile.open(archive_path) as opened:
        members = opened.getmembers()
    names = {member.name for member in members}
    assert {name.split("/")[0] for name in names} == {"meu-projeto"}
    assert "meu-projeto/.venv/bin/python" in names
    assert "meu-projeto/uv.lock" in names
    assert [member.name for member in members if member.linkname.startswith("/")] == []
    assert [member.uname for member in members if member.uname] == []
    assert [member.uid for member in members if member.uid] == []
    assert not (locked_project / ".venv").exists()
    assert not (locked_project / ".python").exists()


@pytest.mark.network
def test_the_extracted_folder_runs_the_project_without_uv(
    locked_project: Path,
    tmp_path: Path,
) -> None:
    """Extraída noutra pasta, como o comando do job faz, a pasta roda o projeto e a dependência com
    o próprio interpretador, num ambiente sem ``uv``, e o prefixo é a ``.venv/`` extraída."""
    archive = prepare_offline.prepare_archive(locked_project, tmp_path / "meu-projeto.tar.gz")
    elsewhere = tmp_path / "noutra-pasta"
    elsewhere.mkdir()
    subprocess.run(["tar", "-xzf", archive.path, "-C", elsewhere], check=True)
    python = elsewhere / "meu-projeto" / ".venv" / "bin" / "python"
    code = "import sys, six, meu_projeto; print(meu_projeto.run(), sys.prefix)"
    run = subprocess.run(
        [python, "-c", code],
        env={"PATH": "/usr/bin:/bin"},
        check=True,
        capture_output=True,
        text=True,
    )
    assert run.stdout.split() == ["ok", str(elsewhere / "meu-projeto" / ".venv")]
