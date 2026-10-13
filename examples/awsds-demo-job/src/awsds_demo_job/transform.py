"""A transformação: um CSV entra, um resumo em JSON sai.

O resumo traz o número de linhas, os nomes das colunas, a soma, o mínimo e o máximo de cada coluna
cujas células são todas números, e o sha256 da entrada, para um resultado ser conferido contra o
arquivo de que veio sem ler nenhum dos dois num log. As chaves do resumo e o layout do JSON fixam
o resultado: o resumo de ``sample.csv`` tem o sha256
``1b2bc4d73bc49bca1a23a6d0971c1365362e785826a33adfcebec7925a248191``, o mesmo no laboratório
(2026-10-11) e no ambiente alvo (2026-10-12).
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
from typing import Any


def summarize(
    name: str,
    data: bytes,
) -> dict[str, Any]:
    """O resumo de um CSV, dado o nome e os bytes dele.

    :param name: o nome do arquivo, que o resumo guarda em ``input``.
    :param data: o conteúdo do arquivo, em UTF-8.
    :return: o resumo, com ``input``, ``sha256``, ``rows``, ``columns`` e ``numeric``.
    """
    reader = csv.DictReader(io.StringIO(data.decode("utf-8")))
    rows = list(reader)
    columns = list(reader.fieldnames or [])

    # Só uma coluna cujas células são todas números entra em numeric.
    numeric = {}
    for column in columns:
        values = numeric_values(rows, column)
        if values:
            numeric[column] = {"sum": sum(values), "min": min(values), "max": max(values)}
    return {
        "input": name,
        "sha256": hashlib.sha256(data).hexdigest(),
        "rows": len(rows),
        "columns": columns,
        "numeric": numeric,
    }


def numeric_values(
    rows: list[dict[str, str]],
    column: str,
) -> list[float]:
    """Os valores de uma coluna como números, ou uma lista vazia quando uma célula não é número.

    :param rows: as linhas do CSV, como o ``csv.DictReader`` as lê.
    :param column: o nome da coluna.
    :return: um número por linha, ou a lista vazia.
    """
    values = []
    for row in rows:
        cell = (row.get(column) or "").strip()
        try:
            values.append(float(cell))
        except ValueError:
            return []
    return values


def result_name(
    input_name: str,
) -> str:
    """O nome do resumo de um arquivo: ``inbox/sales.csv`` vira ``sales.result.json``.

    :param input_name: o nome ou a chave do arquivo de entrada.
    :return: o nome do resumo, sem pasta.
    """
    stem = input_name.rsplit("/", 1)[-1]
    if stem.lower().endswith(".csv"):
        stem = stem[: -len(".csv")]
    return f"{stem}.result.json"


def render(
    summary: dict[str, Any],
) -> bytes:
    """O resumo como JSON, com as chaves em ordem e uma linha nova no fim.

    :param summary: o resumo de ``summarize``.
    :return: o JSON em UTF-8.
    """
    return (json.dumps(summary, indent=2, sort_keys=True) + "\n").encode("utf-8")
