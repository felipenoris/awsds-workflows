"""``awsds_workflows.cli``: cada subcomando chama a função do pacote com os argumentos da linha de
comando e imprime o resumo, e uma recusa termina com 1 e o motivo na saída de erro.

As funções do pacote são trocadas por dublês que gravam a chamada; as recusas são as reais, que
acontecem antes de qualquer chamada ao ``uv`` ou ao ``aws``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from awsds_workflows import cli, package_job, package_task, render


def test_help_exits_with_zero(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``--help`` lista os subcomandos e termina com 0."""
    with pytest.raises(SystemExit) as exit_info:
        cli.main(["--help"])
    assert exit_info.value.code == 0
    printed = capsys.readouterr().out
    for command in ("package-task", "package-job", "job-constraints", "render", "values"):
        assert command in printed


def test_a_missing_subcommand_is_a_usage_error() -> None:
    """Sem subcomando, o ``argparse`` termina com 2."""
    with pytest.raises(SystemExit) as exit_info:
        cli.main([])
    assert exit_info.value.code == 2


def test_package_task_passes_the_arguments_and_prints_the_summary(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``package-task`` chama ``build_archive`` com os padrões do worker e o ``--omit`` repetido,
    e imprime o tamanho, a raiz e o ``python_callable``."""
    calls: list[dict[str, object]] = []

    def fake_build_archive(
        project: Path,
        entry_module: Path,
        archive: Path,
        **options: object,
    ) -> package_task.TaskArchive:
        """Grava a chamada e devolve um ``.zip`` fabricado."""
        calls.append({"project": project, "entry": entry_module, "archive": archive, **options})
        return package_task.TaskArchive(
            path=archive,
            size_bytes=10,
            unzipped_bytes=20,
            top_level=["demo_task", "tasks.py"],
            python=str(options["python"]),
            platform=str(options["platform"]),
        )

    monkeypatch.setattr(package_task, "build_archive", fake_build_archive)
    code = cli.main(
        ["package-task", "projeto", "projeto/tasks.py", "task.zip", "--omit", "a", "--omit", "b"]
    )
    assert code == 0
    assert calls == [
        {
            "project": Path("projeto"),
            "entry": Path("projeto/tasks.py"),
            "archive": Path("task.zip"),
            "python": "3.12",
            "platform": "x86_64-manylinux2014",
            "omit": ["a", "b"],
        }
    ]
    printed = capsys.readouterr().out
    assert "task.zip: 10 bytes, 20 descompactados" in printed
    assert "raiz: demo_task, tasks.py" in printed
    assert "python_callable: tasks.<função>" in printed


def test_a_refusal_prints_the_reason_and_exits_with_one(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Uma recusa do pacote termina com 1 e o motivo na saída de erro."""
    (tmp_path / "tasks.py").write_text("", encoding="utf-8")
    code = cli.main(
        ["package-task", str(tmp_path), str(tmp_path / "tasks.py"), str(tmp_path / "t.zip")]
    )
    assert code == 1
    assert "não há uv.lock" in capsys.readouterr().err


def test_package_job_requires_the_environment_and_the_python() -> None:
    """``package-job`` sem ``--environment`` e ``--python`` é um erro de uso."""
    with pytest.raises(SystemExit) as exit_info:
        cli.main(["package-job", "projeto", "saida"])
    assert exit_info.value.code == 2


def test_package_job_passes_the_target_and_prints_the_summary(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``package-job`` chama ``build_folder`` com o ambiente, o Python e a plataforma padrão, e
    imprime o que veio da imagem e o que a pasta leva."""
    calls: list[dict[str, object]] = []

    def fake_build_folder(
        project: Path,
        output: Path,
        **options: object,
    ) -> package_job.JobFolder:
        """Grava a chamada e devolve uma pasta fabricada."""
        calls.append({"project": project, "output": output, **options})
        return package_job.JobFolder(
            path=output,
            size_bytes=30,
            from_environment={"idna": "3.10"},
            vendored={"six": "1.17.0"},
            top_level=["demo_job", "six.py"],
            python=str(options["python"]),
            platform=str(options["platform"]),
        )

    monkeypatch.setattr(package_job, "build_folder", fake_build_folder)
    code = cli.main(
        ["package-job", "projeto", "saida", "--environment", "ambiente.txt", "--python", "3.12"]
    )
    assert code == 0
    assert calls == [
        {
            "project": Path("projeto"),
            "output": Path("saida"),
            "environment": Path("ambiente.txt"),
            "python": "3.12",
            "platform": "x86_64-manylinux_2_28",
        }
    ]
    printed = capsys.readouterr().out
    assert "da imagem (1): idna" in printed
    assert "na pasta (1): six==1.17.0" in printed


def test_job_constraints_prints_one_pin_per_line(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``job-constraints`` imprime o ambiente da imagem como ``nome==versão``, em ordem."""
    environment = tmp_path / "ambiente.txt"
    environment.write_text("six==1.17.0\nIDNA==3.10\n", encoding="utf-8")
    code = cli.main(["job-constraints", "--environment", str(environment), "--python", "3.12"])
    assert code == 0
    assert capsys.readouterr().out == "idna==3.10\nsix==1.17.0\n"


def test_render_fills_the_file_from_the_values_file(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``render`` com ``--values-file`` imprime o arquivo preenchido, e com ``--placeholders``
    devolve os placeholders."""
    values = tmp_path / "valores.json"
    values.write_text(json.dumps({"PROJECTS_BUCKET": "meu-bucket"}), encoding="utf-8")
    definition = tmp_path / "workflow.yaml"
    definition.write_text("bucket: <PROJECTS_BUCKET>\n", encoding="utf-8")

    assert cli.main(["render", str(definition), "--values-file", str(values)]) == 0
    assert capsys.readouterr().out == "bucket: meu-bucket\n"

    saved = tmp_path / "salvo.yaml"
    saved.write_text("bucket: meu-bucket\n", encoding="utf-8")
    assert cli.main(["render", "--placeholders", str(saved), "--values-file", str(values)]) == 0
    assert capsys.readouterr().out == "bucket: <PROJECTS_BUCKET>\n"


def test_render_without_a_value_source_is_refused(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``render`` sem ``--values-file`` nem ``--profile`` termina com 1."""
    definition = tmp_path / "workflow.yaml"
    definition.write_text("", encoding="utf-8")
    assert cli.main(["render", str(definition)]) == 1
    assert "de onde vêm os valores" in capsys.readouterr().err


def test_profile_without_a_subnet_name_is_refused(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``--profile`` sem ``--subnet-name`` termina com 1, antes de qualquer chamada ao ``aws``."""
    assert cli.main(["values", "--profile", "perfil"]) == 1
    assert "--subnet-name" in capsys.readouterr().err


def test_values_merges_the_file_over_the_account(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``values`` com ``--profile`` e ``--values-file`` imprime os da conta completados e
    substituídos pelos do arquivo, em JSON."""
    calls: list[dict[str, object]] = []

    def fake_read_values(
        profile: str,
        **options: object,
    ) -> dict[str, str]:
        """Grava a chamada e devolve valores fabricados da conta."""
        calls.append({"profile": profile, **options})
        return {"PROJECT_ID": "abc123", "REGION": "us-west-2"}

    monkeypatch.setattr(render, "read_values", fake_read_values)
    values = tmp_path / "valores.json"
    values.write_text(json.dumps({"REGION": "sa-east-1", "JOB_PYTHON": "/opt/conda/bin/python"}))

    code = cli.main(
        [
            "values",
            "--profile",
            "perfil",
            "--subnet-name",
            "projeto-private-*",
            "--values-file",
            str(values),
        ]
    )
    assert code == 0
    assert calls == [
        {
            "profile": "perfil",
            "subnet_name": "projeto-private-*",
            "project": None,
            "image_name": None,
        }
    ]
    assert json.loads(capsys.readouterr().out) == {
        "JOB_PYTHON": "/opt/conda/bin/python",
        "PROJECT_ID": "abc123",
        "REGION": "sa-east-1",
    }
