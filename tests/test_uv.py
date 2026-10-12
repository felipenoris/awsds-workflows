"""``awsds_workflows._uv``: a recusa de uma chamada que falha, do ``uv`` ausente, de um Python que o
``uv`` não acha e de um wheel que não é Python puro, o ``UV_PYTHON`` que chega ao ``uv``, e a
limpeza do que o ``uv pip install --target`` deixa.

Nenhum teste precisa do PyPI: a chamada que falha é uma opção que o ``uv`` não conhece, o Python
que o ``uv`` não acha é o 3.99 de um ``.python-version`` com os downloads de Python desligados, e o
wheel impuro é um nome de arquivo gravado por um dublê de ``run``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from awsds_workflows import _uv
from awsds_workflows.errors import RefusalError


def test_a_failed_call_is_refused_with_the_uv_message() -> None:
    """Uma chamada que o ``uv`` recusa vira ``RefusalError`` com os dois primeiros argumentos e
    a saída de erro do ``uv``."""
    with pytest.raises(RefusalError, match="uv export --opcao-que-nao-existe falhou") as refusal:
        _uv.run(["export", "--opcao-que-nao-existe"])
    assert "unexpected argument" in str(refusal.value)


def test_a_missing_uv_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sem ``uv`` no ``PATH``, a recusa diz o que instalar."""
    monkeypatch.setenv("PATH", "")
    with pytest.raises(RefusalError, match="o uv não está no PATH"):
        _uv.run(["--version"])


def test_a_missing_interpreter_is_refused_with_the_uv_message(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Com os downloads de Python desligados, uma pasta que pede um Python que o ``uv`` não acha é
    recusada com a mensagem que a documentação cita, como num space."""
    (tmp_path / ".python-version").write_text("3.99\n", encoding="utf-8")
    monkeypatch.setenv("UV_PYTHON_DOWNLOADS", "never")
    monkeypatch.delenv("UV_PYTHON", raising=False)
    with pytest.raises(RefusalError, match="No interpreter found for Python 3.99"):
        _uv.run(["venv", str(tmp_path / "venv")], cwd=tmp_path)


def test_uv_python_reaches_the_call(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """O ``UV_PYTHON`` do processo chega ao ``uv`` e nomeia o interpretador que ele não acharia."""
    (tmp_path / ".python-version").write_text("3.99\n", encoding="utf-8")
    monkeypatch.setenv("UV_PYTHON_DOWNLOADS", "never")
    monkeypatch.setenv("UV_PYTHON", sys.executable)
    _uv.run(["venv", str(tmp_path / "venv")], cwd=tmp_path)
    assert (tmp_path / "venv" / "pyvenv.cfg").is_file()


def test_an_impure_wheel_is_refused(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Um wheel com etiqueta de plataforma, construído para esta máquina, é recusado."""
    calls: list[list[str]] = []

    def fake_run(
        arguments: list[str],
        **options: object,
    ) -> str:
        """Grava um wheel impuro onde o ``uv build`` gravaria o do projeto."""
        calls.append(arguments)
        out_dir = Path(arguments[arguments.index("--out-dir") + 1])
        out_dir.mkdir()
        (out_dir / "demo-0.1.0-cp312-cp312-linux_x86_64.whl").write_bytes(b"")
        return ""

    monkeypatch.setattr(_uv, "run", fake_run)
    with pytest.raises(RefusalError, match="não é Python puro"):
        _uv.build_pure_wheel(tmp_path / "projeto", tmp_path / "dist")
    assert len(calls) == 1


def test_a_pure_wheel_is_returned(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Um wheel ``-none-any`` volta como o caminho do arquivo."""

    def fake_run(
        arguments: list[str],
        **options: object,
    ) -> str:
        """Grava um wheel puro onde o ``uv build`` gravaria o do projeto."""
        out_dir = Path(arguments[arguments.index("--out-dir") + 1])
        out_dir.mkdir()
        (out_dir / "demo-0.1.0-py3-none-any.whl").write_bytes(b"")
        return ""

    monkeypatch.setattr(_uv, "run", fake_run)
    wheels = _uv.build_pure_wheel(tmp_path / "projeto", tmp_path / "dist")
    assert wheels == [tmp_path / "dist" / "demo-0.1.0-py3-none-any.whl"]


def test_leftovers_are_removed_and_code_is_kept(
    tmp_path: Path,
) -> None:
    """A trava, os scripts de ``bin/`` e o bytecode saem; o código fica."""
    (tmp_path / ".lock").write_text("", encoding="utf-8")
    (tmp_path / "bin").mkdir()
    (tmp_path / "bin" / "script").write_text("", encoding="utf-8")
    (tmp_path / "demo" / "__pycache__").mkdir(parents=True)
    (tmp_path / "demo" / "__pycache__" / "x.cpython-313.pyc").write_bytes(b"")
    (tmp_path / "demo" / "solto.pyc").write_bytes(b"")
    (tmp_path / "demo" / "__init__.py").write_text("", encoding="utf-8")

    _uv.remove_leftovers(tmp_path)

    remaining = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*"))
    assert remaining == ["demo", "demo/__init__.py"]
