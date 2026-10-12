"""``awsds_workflows.package_job``: o arquivo de ambiente da imagem, a pasta de código de um job
construída pelo ``uv`` sobre um projeto de teste, e as recusas.

O ambiente da imagem é um arquivo ``nome==versão`` gravado pelo teste, como o que
``uv pip list --format freeze`` escreve num espaço. Os testes marcados ``network`` travam um projeto
que depende do ``idna`` na versão do ambiente e do ``six``, que o ambiente não tem: a pasta leva o
``six`` e o projeto, e não o ``idna``. Os outros testes não chamam o ``uv``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from conftest import write_project

from awsds_workflows import package_job
from awsds_workflows.errors import RefusalError

IDNA_IN_THE_IMAGE = "3.10"


def write_environment(
    folder: Path,
    text: str,
) -> Path:
    """Grava o arquivo de ambiente da imagem em ``folder``."""
    environment = folder / "ambiente.txt"
    environment.write_text(text, encoding="utf-8")
    return environment


def test_markers_are_evaluated_for_the_job_python_and_platform(
    tmp_path: Path,
) -> None:
    """Um marcador que não vale para o interpretador do job tira a linha; os nomes saem
    normalizados."""
    environment = write_environment(
        tmp_path,
        "Charset_Normalizer==3.4.0\n"
        "tomli==2.0.1 ; python_full_version < '3.11'\n"
        "numpy==2.3.0 ; python_full_version >= '3.12'\n"
        "pywin32==311 ; sys_platform == 'win32'\n"
        "nvidia-nccl==2.0 ; platform_machine == 'aarch64'\n",
    )
    versions = package_job.environment_versions(environment, python="3.12")
    assert versions == {"charset-normalizer": "3.4.0", "numpy": "2.3.0"}


def test_hash_and_annotation_lines_belong_to_the_requirement_above(
    tmp_path: Path,
) -> None:
    """As linhas recuadas de um ``uv export`` com hashes e anotações não viram requisitos."""
    environment = write_environment(
        tmp_path,
        "idna==3.10 \\\n"
        "    --hash=sha256:aaaa \\\n"
        "    --hash=sha256:bbbb\n"
        "    # via requests\n"
        "six==1.17.0\n",
    )
    versions = package_job.environment_versions(environment, python="3.13")
    assert versions == {"idna": "3.10", "six": "1.17.0"}


def test_a_line_that_is_not_a_pin_is_refused(
    tmp_path: Path,
) -> None:
    """O ``nome @ file:///...`` que o ``pip freeze`` escreve para um pacote do conda é recusado:
    ignorado, ele faria o pacote parecer ausente da imagem."""
    environment = write_environment(
        tmp_path,
        "idna==3.10\nnumpy @ file:///home/conda/feedstock_root/numpy-2.3.0.tar.bz2\n",
    )
    with pytest.raises(RefusalError, match="linha 2"):
        package_job.environment_versions(environment, python="3.12")


def test_a_missing_environment_file_is_refused(
    tmp_path: Path,
) -> None:
    """Um arquivo de ambiente que não existe é recusado."""
    with pytest.raises(RefusalError, match="não existe"):
        package_job.environment_versions(tmp_path / "ambiente.txt", python="3.12")


def test_a_project_without_a_lock_is_refused(
    tmp_path: Path,
) -> None:
    """Um projeto sem ``uv.lock`` é recusado antes de qualquer chamada ao ``uv``."""
    environment = write_environment(tmp_path, "idna==3.10\n")
    with pytest.raises(RefusalError, match="não há uv.lock"):
        package_job.build_folder(tmp_path, tmp_path / "saida", environment, python="3.12")


def test_an_existing_output_folder_is_refused(
    tmp_path: Path,
) -> None:
    """Uma pasta de saída que já existe é recusada, e nada é sobrescrito."""
    (tmp_path / "uv.lock").write_text("", encoding="utf-8")
    environment = write_environment(tmp_path, "idna==3.10\n")
    (tmp_path / "saida").mkdir()
    with pytest.raises(RefusalError, match="já existe"):
        package_job.build_folder(tmp_path, tmp_path / "saida", environment, python="3.12")


@pytest.mark.network
def test_the_folder_holds_only_what_the_image_lacks(
    tmp_path: Path,
) -> None:
    """A pasta leva o projeto e o ``six``; o ``idna``, na versão da imagem, vem da imagem."""
    project = write_project(
        tmp_path / "projeto",
        "demo-job",
        [f"idna=={IDNA_IN_THE_IMAGE}", "six"],
    )
    environment = write_environment(tmp_path, f"idna=={IDNA_IN_THE_IMAGE}\npip==25.0\n")

    folder = package_job.build_folder(project, tmp_path / "saida", environment, python="3.12")
    assert folder.from_environment == {"idna": IDNA_IN_THE_IMAGE}
    assert list(folder.vendored) == ["six"]
    assert "demo_job" in folder.top_level
    assert "six.py" in folder.top_level
    assert "idna" not in folder.top_level
    assert [path for path in folder.path.rglob("__pycache__")] == []
    assert not (folder.path / ".lock").exists()


@pytest.mark.network
def test_a_version_the_image_holds_differently_is_refused_with_the_constraints(
    tmp_path: Path,
) -> None:
    """Um pacote fixado no lock numa versão diferente da imagem recusa a construção, com o bloco
    que alinha o projeto à imagem."""
    project = write_project(tmp_path / "projeto", "demo-conflict", ["idna==3.9"])
    environment = write_environment(tmp_path, f"idna=={IDNA_IN_THE_IMAGE}\n")
    output = tmp_path / "saida"

    with pytest.raises(RefusalError, match="discordam") as refusal:
        package_job.build_folder(project, output, environment, python="3.12")
    assert f"idna: 3.9 no lock, {IDNA_IN_THE_IMAGE} na imagem" in str(refusal.value)
    assert f'"idna=={IDNA_IN_THE_IMAGE}",' in str(refusal.value)
    assert not output.exists()
