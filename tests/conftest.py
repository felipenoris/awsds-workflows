"""Os auxiliares dos testes: o projeto uv de teste.

Os testes marcados ``network`` travam e constroem projetos uv gravados em ``tmp_path`` e precisam
do PyPI; ``-m "not network"`` os pula. Fora de ``tmp_path``, só o cache do ``uv`` recebe arquivos.
"""

from __future__ import annotations

import subprocess
import textwrap
from pathlib import Path


def write_project(
    folder: Path,
    name: str,
    dependencies: list[str],
) -> Path:
    """Grava um projeto uv de Python puro em ``folder`` e o trava com ``uv lock``.

    O pacote do projeto tem o nome de ``name`` com ``_`` no lugar de ``-`` e uma função ``run``; o
    ``requires-python`` admite o worker (3.12) e o Python dos testes.
    """
    module = name.replace("-", "_")
    package = folder / "src" / module
    package.mkdir(parents=True)
    (package / "__init__.py").write_text('def run():\n    return "ok"\n', encoding="utf-8")

    listed = ", ".join(f'"{dependency}"' for dependency in dependencies)
    pyproject = textwrap.dedent(f"""\
        [project]
        name = "{name}"
        version = "0.1.0"
        requires-python = ">=3.12"
        dependencies = [{listed}]

        [build-system]
        requires = ["uv_build>=0.12,<0.13"]
        build-backend = "uv_build"
        """)
    (folder / "pyproject.toml").write_text(pyproject, encoding="utf-8")
    subprocess.run(["uv", "lock", "--quiet"], cwd=folder, check=True)
    return folder
