"""O job do Glue da aplicação houseprice-etl: lê um Parquet do S3 e grava os dados em CSV.

É o script que o Visual ETL gerou para um fluxo de três nós, uma origem Parquet no S3, um nó de
código que não muda os dados e um destino CSV no S3, com uma mudança: os caminhos de entrada e de
saída chegam como argumentos do job, ``--SOURCE_PATH`` e ``--TARGET_PATH``, em vez de escritos no
código, porque cada projeto tem os seus. A task do workflow passa os dois em ``script_args``.

Exemplo, os argumentos na task do workflow, sob o prefixo do exemplo no bucket do projeto:

.. code-block:: yaml

    script_args:
      "--SOURCE_PATH": s3://<prefixo do exemplo>/entrada/house-price.parquet
      "--TARGET_PATH": s3://<prefixo do exemplo>/saida/
"""

import sys

from awsglue.utils import getResolvedOptions
from pyspark.sql import DataFrame, SparkSession


def transform(
    input_df: DataFrame,
) -> DataFrame:
    """Devolve os dados sem mudança, como o nó de código (CustomCodeTransform) do fluxo."""
    return input_df


# Os dois caminhos chegam como argumentos do job.
arguments = getResolvedOptions(sys.argv, ["SOURCE_PATH", "TARGET_PATH"])
spark = SparkSession.builder.getOrCreate()

# Lê o Parquet de entrada, como o nó S3DataSource do fluxo.
houses = spark.read.format("parquet").load(arguments["SOURCE_PATH"])

# Aplica a transformação do nó de código.
result = houses.transform(transform)

# Grava em CSV sem cabeçalho e sem compressão, acrescentando à pasta, como o nó S3DataSink.
(
    result.write.format("csv")
    .option("header", False)
    .option("compression", "uncompressed")
    .mode("append")
    .save(arguments["TARGET_PATH"])
)
