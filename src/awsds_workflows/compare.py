"""[public] A comparação de duas definições de workflow pelo conteúdo do YAML.

A cópia versionada de uma definição e a que o portal salvou diferem no texto mesmo quando dizem o
mesmo: o portal reordena as chaves, dobra os textos longos em várias linhas e escreve as listas em
bloco (leituras do laboratório de 2026-10-10 e 2026-10-11). ``compare_definitions`` lê as duas como
YAML e lista só o que muda no conteúdo; os comentários, o layout do editor na primeira linha
inclusive, a ordem das chaves, as aspas e a forma dos textos e das listas não contam. Uma definição
salva traz os valores da conta, e ``awsds_workflows.render.restore_placeholders``
(``render --placeholders`` na linha de comando) devolve os placeholders antes da comparação.

Uma diferença sai como ``- caminho: valor`` para o que só a primeira definição tem e
``+ caminho: valor`` para o que só a segunda tem, e um valor que muda dá as duas linhas. O caminho
junta as chaves com ``.`` e as posições de uma lista com ``[i]``, e o valor é escrito em JSON, numa
linha. Os valores se comparam com o tipo: ``0`` e ``"0"`` diferem, assim como ``true`` e ``1``. As
listas se comparam posição a posição.

Exemplo:

.. code-block:: python

    from pathlib import Path

    from awsds_workflows import compare

    for line in compare.compare_definitions(Path("meu-workflow.yaml"), Path("salvo.yaml")):
        print(line)
    # + meu-workflow.is_paused_upon_creation: false
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from awsds_workflows.errors import RefusalError

__all__ = ["compare_definitions"]


def compare_definitions(
    first: Path,
    second: Path,
) -> list[str]:
    """[public] Lista as diferenças de conteúdo entre duas definições de workflow em YAML.

    Exemplo:

    .. code-block:: python

        compare_definitions(Path("meu-workflow.yaml"), Path("salvo.yaml"))
        # ['+ meu-workflow.is_paused_upon_creation: false']

    :param first: a primeira definição, como a cópia versionada; o que só ela tem sai com ``-``.
    :param second: a segunda definição, como a que o portal salvou, com os placeholders de volta;
        o que só ela tem sai com ``+``.
    :return: as linhas das diferenças, na ordem das chaves da primeira definição, com as chaves que
        só a segunda tem no fim de cada mapeamento; vazia quando as duas dizem o mesmo.
    :raises awsds_workflows.errors.RefusalError: quando um dos arquivos não existe, não é YAML ou
        não é um mapeamento, a forma de uma definição de workflow.
    """
    differences: list[str] = []
    _compare_mappings(_load_definition(first), _load_definition(second), "", differences)
    return differences


def _load_definition(
    path: Path,
) -> dict[Any, Any]:
    """[private] O conteúdo do arquivo YAML, recusado quando não é um mapeamento."""
    if not path.is_file():
        raise RefusalError(f"o arquivo {path} não existe")

    # Lido como arquivo, e não como texto, para que o erro do YAML nomeie o arquivo e a linha.
    try:
        with path.open(encoding="utf-8") as stream:
            content = yaml.safe_load(stream)
    except yaml.YAMLError as error:
        raise RefusalError(f"{path} não é YAML: {error}") from error

    if not isinstance(content, dict):
        raise RefusalError(f"{path} não é uma definição de workflow: o YAML não é um mapeamento")
    return content


def _compare_values(
    first: Any,
    second: Any,
    path: str,
    differences: list[str],
) -> None:
    """[private] Junta em ``differences`` o que muda entre os dois valores do caminho."""
    if isinstance(first, dict) and isinstance(second, dict):
        _compare_mappings(first, second, path, differences)
        return
    if isinstance(first, list) and isinstance(second, list):
        _compare_lists(first, second, path, differences)
        return

    # O tipo entra na comparação porque o Python iguala True a 1 e 1 a 1.0.
    if type(first) is type(second) and first == second:
        return
    differences.append(f"- {path}: {_as_json(first)}")
    differences.append(f"+ {path}: {_as_json(second)}")


def _compare_mappings(
    first: dict[Any, Any],
    second: dict[Any, Any],
    path: str,
    differences: list[str],
) -> None:
    """[private] Compara as chaves da primeira, na ordem dela, e depois lista as que só a segunda
    tem."""
    for key, value in first.items():
        key_path = _join(path, key)
        if key in second:
            _compare_values(value, second[key], key_path, differences)
        else:
            differences.append(f"- {key_path}: {_as_json(value)}")

    for key, value in second.items():
        if key not in first:
            differences.append(f"+ {_join(path, key)}: {_as_json(value)}")


def _compare_lists(
    first: list[Any],
    second: list[Any],
    path: str,
    differences: list[str],
) -> None:
    """[private] Compara as listas posição a posição; os itens além do fim da mais curta saem como
    só de um lado."""
    shared = min(len(first), len(second))
    for index in range(shared):
        _compare_values(first[index], second[index], f"{path}[{index}]", differences)

    for index in range(shared, len(first)):
        differences.append(f"- {path}[{index}]: {_as_json(first[index])}")
    for index in range(shared, len(second)):
        differences.append(f"+ {path}[{index}]: {_as_json(second[index])}")


def _join(
    path: str,
    key: Any,
) -> str:
    """[private] O caminho da chave dentro do caminho dado, com ``.`` entre os dois."""
    if not path:
        return str(key)
    return f"{path}.{key}"


def _as_json(
    value: Any,
) -> str:
    """[private] O valor em JSON, numa linha, com as chaves na ordem do arquivo."""
    # Uma data do YAML, que o JSON não representa, sai como texto.
    return json.dumps(value, ensure_ascii=False, default=str)
