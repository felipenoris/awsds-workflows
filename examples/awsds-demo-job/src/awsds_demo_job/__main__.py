"""``python -m awsds_demo_job --input PASTA --output PASTA``: o modo de um job de processamento.

Cada CSV sob ``--input`` vira um resumo em JSON em ``--output``. O SageMaker baixa as entradas
para ``--input`` antes de o comando começar e envia ``--output`` ao S3 depois que ele termina,
então o comando não alcança rede nem tem credenciais da AWS: um job isolado roda assim.

O que ele imprime vai para ``/aws/sagemaker/ProcessingJobs``, que todo papel de projeto da conta
pode ler, por isso ele imprime o interpretador, as contagens e os caminhos, nunca uma célula dos
dados.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from awsds_demo_job import transform


def main(
    argv: list[str] | None = None,
) -> int:
    """Resume cada CSV da pasta de entrada na pasta de saída e devolve o código de saída.

    :param argv: os argumentos, sem o nome do programa; ``None`` lê ``sys.argv``.
    :return: 0 com cada CSV resumido, e 1 sem nenhum CSV na pasta de entrada.
    """
    parser = argparse.ArgumentParser(prog="awsds_demo_job")
    parser.add_argument("--input", required=True, type=Path, help="a pasta com os CSV")
    parser.add_argument("--output", required=True, type=Path, help="a pasta dos resumos")
    arguments = parser.parse_args(argv)

    print(f"python {sys.version.split()[0]} em {sys.executable}")

    # Os CSV da pasta de entrada e das subpastas dela, em ordem de caminho.
    files = []
    for path in sorted(arguments.input.rglob("*")):
        if path.is_file() and path.suffix.lower() == ".csv":
            files.append(path)
    if not files:
        print(f"nenhum CSV em {arguments.input}", file=sys.stderr)
        return 1

    arguments.output.mkdir(parents=True, exist_ok=True)
    for path in files:
        summary = transform.summarize(path.name, path.read_bytes())
        target = arguments.output / transform.result_name(path.name)
        target.write_bytes(transform.render(summary))
        print(f"{path.name}: {summary['rows']} linhas -> {target}")
    print(f"{len(files)} arquivo(s) processado(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
