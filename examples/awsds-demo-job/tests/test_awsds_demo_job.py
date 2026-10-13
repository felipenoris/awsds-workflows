"""``awsds_demo_job``: a transformação e os dois modos, sem rede.

O modo S3 roda sobre um dublê do cliente ``s3`` do ``boto3``, um dicionário com as quatro
chamadas que ``run`` faz. Na raiz do repositório, ``uv run pytest`` acha estes testes pelo
``testpaths`` e o pacote pelo ``pythonpath``; na pasta do projeto, ``uv run pytest`` instala o
projeto antes.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from pathlib import Path

from awsds_demo_job import __main__ as local_mode
from awsds_demo_job import s3 as worker_mode
from awsds_demo_job import transform

SAMPLE = Path(__file__).resolve().parents[1] / "sample.csv"

# O sha256 do resumo de sample.csv, lido com sha256sum no laboratório (2026-10-11) e no ambiente
# alvo (2026-10-12).
RESULT_SHA256 = "1b2bc4d73bc49bca1a23a6d0971c1365362e785826a33adfcebec7925a248191"


def test_the_summary_of_the_sample() -> None:
    """A amostra tem dez linhas, quatro colunas, duas numéricas e o sha256 do próprio arquivo."""
    data = SAMPLE.read_bytes()
    summary = transform.summarize("sample.csv", data)
    assert summary["rows"] == 10
    assert summary["columns"] == ["date", "region", "units", "unit_price"]
    assert sorted(summary["numeric"]) == ["unit_price", "units"]
    assert summary["sha256"] == hashlib.sha256(data).hexdigest()


def test_a_column_with_text_is_not_numeric() -> None:
    """Uma célula que não é número tira a coluna de ``numeric``."""
    summary = transform.summarize("x.csv", b"a,b\n1,x\n2,3\n")
    assert list(summary["numeric"]) == ["a"]
    assert summary["numeric"]["a"] == {"sum": 3.0, "min": 1.0, "max": 2.0}


def test_the_result_name() -> None:
    """O nome do resumo troca a extensão ``.csv``, em qualquer caixa, e mantém outra."""
    assert transform.result_name("inbox/sales.CSV") == "sales.result.json"
    assert transform.result_name("notes.txt") == "notes.txt.result.json"


def test_the_result_of_the_sample_has_the_measured_sha256() -> None:
    """O resumo da amostra sai byte a byte como nas execuções medidas."""
    result = transform.render(transform.summarize("sample.csv", SAMPLE.read_bytes()))
    assert hashlib.sha256(result).hexdigest() == RESULT_SHA256


def test_local_mode_turns_every_csv_into_a_result(
    tmp_path: Path,
) -> None:
    """O modo do job grava um resumo por CSV da pasta de entrada."""
    inbox = tmp_path / "inbox"
    outbox = tmp_path / "outbox"
    inbox.mkdir()
    (inbox / "sample.csv").write_bytes(SAMPLE.read_bytes())

    assert local_mode.main(["--input", str(inbox), "--output", str(outbox)]) == 0
    result = json.loads((outbox / "sample.result.json").read_text(encoding="utf-8"))
    assert result["rows"] == 10


def test_local_mode_without_a_csv_fails(
    tmp_path: Path,
) -> None:
    """Uma pasta de entrada sem CSV termina com 1."""
    outbox = tmp_path / "outbox"
    assert local_mode.main(["--input", str(tmp_path), "--output", str(outbox)]) == 1


class FakeBody:
    """O corpo de um objeto do dublê, com o ``read`` que ``run`` chama."""

    def __init__(
        self,
        data: bytes,
    ) -> None:
        self.data = data

    def read(self) -> bytes:
        """Os bytes do objeto."""
        return self.data


class FakePaginator:
    """O paginador do dublê: uma página com as chaves sob o prefixo."""

    def __init__(
        self,
        objects: dict[str, bytes],
    ) -> None:
        self.objects = objects

    def paginate(
        self,
        Bucket: str,
        Prefix: str,
    ) -> Iterator[dict[str, list[dict[str, str]]]]:
        """A única página, com as chaves em ordem."""
        keys = sorted(key for key in self.objects if key.startswith(Prefix))
        yield {"Contents": [{"Key": key} for key in keys]}


class FakeS3:
    """As quatro chamadas que ``run`` faz, sobre um dicionário de chave para bytes."""

    def __init__(
        self,
        objects: dict[str, bytes],
    ) -> None:
        self.objects = dict(objects)
        self.order: list[tuple[str, str]] = []

    def get_paginator(
        self,
        name: str,
    ) -> FakePaginator:
        """O paginador de ``list_objects_v2``."""
        return FakePaginator(self.objects)

    def get_object(
        self,
        Bucket: str,
        Key: str,
    ) -> dict[str, FakeBody]:
        """O objeto, com o corpo."""
        return {"Body": FakeBody(self.objects[Key])}

    def put_object(
        self,
        Bucket: str,
        Key: str,
        Body: bytes,
    ) -> None:
        """Grava o objeto e anota a ordem."""
        self.order.append(("put", Key))
        self.objects[Key] = Body

    def delete_object(
        self,
        Bucket: str,
        Key: str,
    ) -> None:
        """Apaga o objeto e anota a ordem."""
        self.order.append(("delete", Key))
        del self.objects[Key]


def test_worker_mode_deletes_the_source_after_writing_the_result() -> None:
    """O modo do worker grava o resumo numa pasta da caixa de saída e só então apaga a origem."""
    fake = FakeS3({"p/inbox/sample.csv": SAMPLE.read_bytes()})
    assert worker_mode.run("b", "p/inbox", "p/outbox", client=fake) == 1
    assert [kind for kind, _key in fake.order] == ["put", "delete"]
    assert "p/inbox/sample.csv" not in fake.objects
    results = [key for key in fake.objects if key.endswith("/sample.result.json")]
    assert len(results) == 1
    assert results[0].startswith("p/outbox/")
