"""``awsds_workflows.package_task``: o ``.zip`` de uma task, construído pelo ``uv`` sobre um
projeto de teste, e as recusas antes de qualquer download.

Os testes marcados ``network`` travam um projeto que depende do ``requests`` e do ``boto3`` e
constroem o ``.zip`` para o worker: o ``boto3`` e as dependências que só ele usa ficam de fora, o
``urllib3``, de que o ``requests`` também precisa, fica, e os módulos compilados do
``charset_normalizer`` têm a etiqueta do CPython pedido em Linux x86_64. Os outros testes não
chamam o ``uv``.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest
from conftest import write_project

from awsds_workflows import package_task
from awsds_workflows.errors import RefusalError


@pytest.fixture(scope="module")
def locked_project(
    tmp_path_factory: pytest.TempPathFactory,
) -> Path:
    """O projeto de teste travado, com o módulo de entrada ``tasks.py``, compartilhado pelos
    testes ``network`` do módulo."""
    project = write_project(tmp_path_factory.mktemp("projeto"), "demo-task", ["requests", "boto3"])
    (project / "tasks.py").write_text("from demo_task import run\n", encoding="utf-8")
    return project


@pytest.mark.network
def test_the_archive_leaves_out_the_worker_packages_and_keeps_shared_ones(
    locked_project: Path,
    tmp_path: Path,
) -> None:
    """O ``.zip`` traz o módulo de entrada, o projeto e o ``requests`` com o ``urllib3``, e não
    traz o ``boto3`` nem as dependências que só ele usa."""
    archive = package_task.build_archive(
        locked_project,
        locked_project / "tasks.py",
        tmp_path / "task.zip",
    )
    names = zipfile.ZipFile(archive.path).namelist()
    top_level = sorted({name.split("/")[0] for name in names})
    assert "tasks.py" in top_level
    assert "demo_task" in top_level
    assert "requests" in top_level
    assert "urllib3" in top_level
    assert "boto3" not in top_level
    assert "botocore" not in top_level
    assert "s3transfer" not in top_level
    assert "jmespath" not in top_level
    assert archive.top_level == top_level


@pytest.mark.network
def test_the_archive_holds_no_bytecode_lock_or_scripts(
    locked_project: Path,
    tmp_path: Path,
) -> None:
    """O ``.zip`` não traz bytecode, a trava do ``uv`` nem os scripts de ``bin/``, e o tamanho
    descompactado é a soma dos arquivos de dentro."""
    archive = package_task.build_archive(
        locked_project,
        locked_project / "tasks.py",
        tmp_path / "task.zip",
    )
    with zipfile.ZipFile(archive.path) as zip_file:
        infos = zip_file.infolist()
    names = [info.filename for info in infos]
    assert [name for name in names if "__pycache__" in name] == []
    assert [name for name in names if name.endswith(".pyc")] == []
    assert ".lock" not in names
    assert [name for name in names if name.startswith("bin/")] == []
    assert archive.unzipped_bytes == sum(info.file_size for info in infos)


@pytest.mark.network
@pytest.mark.parametrize("python", ["3.12", "3.13"])
def test_compiled_modules_carry_the_tag_of_the_requested_python(
    locked_project: Path,
    tmp_path: Path,
    python: str,
) -> None:
    """Cada módulo compilado do ``.zip`` é do CPython pedido em Linux x86_64, e não desta
    máquina."""
    archive = package_task.build_archive(
        locked_project,
        locked_project / "tasks.py",
        tmp_path / "task.zip",
        python=python,
    )
    names = zipfile.ZipFile(archive.path).namelist()
    compiled = [name for name in names if name.endswith(".so")]
    tag = f"cpython-{python.replace('.', '')}-x86_64-linux-gnu"
    assert compiled != []
    assert [name for name in compiled if tag not in name] == []


@pytest.mark.network
def test_omit_leaves_out_one_more_package(
    locked_project: Path,
    tmp_path: Path,
) -> None:
    """Um pacote de ``omit`` sai com as dependências que só ele usa."""
    archive = package_task.build_archive(
        locked_project,
        locked_project / "tasks.py",
        tmp_path / "task.zip",
        omit=["requests"],
    )
    assert "requests" not in archive.top_level
    assert "urllib3" not in archive.top_level
    assert "demo_task" in archive.top_level


@pytest.mark.network
def test_a_stale_lock_is_refused_and_nothing_is_written(
    tmp_path: Path,
) -> None:
    """Um ``pyproject.toml`` mudado depois do ``uv lock`` é recusado pelo ``--locked``."""
    project = write_project(tmp_path / "projeto", "demo-stale", [])
    (project / "tasks.py").write_text("", encoding="utf-8")
    pyproject = project / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    pyproject.write_text(text.replace("dependencies = []", 'dependencies = ["idna"]'), "utf-8")

    archive = tmp_path / "task.zip"
    with pytest.raises(RefusalError, match="uv export --locked falhou"):
        package_task.build_archive(project, project / "tasks.py", archive)
    assert not archive.exists()


def test_a_project_without_a_lock_is_refused(
    tmp_path: Path,
) -> None:
    """Um projeto sem ``uv.lock`` é recusado antes de qualquer chamada ao ``uv``."""
    (tmp_path / "tasks.py").write_text("", encoding="utf-8")
    with pytest.raises(RefusalError, match="não há uv.lock"):
        package_task.build_archive(tmp_path, tmp_path / "tasks.py", tmp_path / "task.zip")


def test_a_missing_entry_module_is_refused(
    tmp_path: Path,
) -> None:
    """Um módulo de entrada que não existe é recusado antes de qualquer chamada ao ``uv``."""
    (tmp_path / "uv.lock").write_text("", encoding="utf-8")
    with pytest.raises(RefusalError, match="não há módulo de entrada"):
        package_task.build_archive(tmp_path, tmp_path / "tasks.py", tmp_path / "task.zip")


def test_a_missing_archive_folder_is_refused(
    tmp_path: Path,
) -> None:
    """Uma pasta do ``.zip`` que não existe é recusada antes de qualquer chamada ao ``uv``."""
    (tmp_path / "uv.lock").write_text("", encoding="utf-8")
    (tmp_path / "tasks.py").write_text("", encoding="utf-8")
    with pytest.raises(RefusalError, match="não existe"):
        package_task.build_archive(tmp_path, tmp_path / "tasks.py", tmp_path / "nao" / "task.zip")


def test_content_over_the_limit_is_refused_and_nothing_is_written(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Um conteúdo acima do limite é recusado antes de gravar o ``.zip``."""
    root = tmp_path / "root"
    root.mkdir()
    (root / "grande.py").write_text("x" * 100, encoding="utf-8")
    monkeypatch.setattr(package_task, "ARCHIVE_LIMIT_BYTES", 10)

    archive = tmp_path / "task.zip"
    with pytest.raises(RefusalError, match="acima do limite"):
        package_task._write_archive(root, archive)
    assert not archive.exists()


def test_the_archive_has_no_top_level_folder(
    tmp_path: Path,
) -> None:
    """Cada arquivo entra pelo caminho relativo à raiz, sem uma pasta de topo."""
    root = tmp_path / "root"
    (root / "pacote").mkdir(parents=True)
    (root / "pacote" / "__init__.py").write_text("", encoding="utf-8")
    (root / "tasks.py").write_text("", encoding="utf-8")

    archive = tmp_path / "task.zip"
    unzipped_bytes = package_task._write_archive(root, archive)
    assert sorted(zipfile.ZipFile(archive).namelist()) == ["pacote/__init__.py", "tasks.py"]
    assert unzipped_bytes == 0
