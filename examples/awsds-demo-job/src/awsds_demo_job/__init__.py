"""awsds-demo-job: um CSV entra, um resumo em JSON sai.

Dois pontos de entrada dividem uma transformação:

    python -m awsds_demo_job      pastas locais: o modo de um job de processamento
    python -m awsds_demo_job.s3   prefixos do S3 pelo boto3: o modo de uma task no worker
"""

__version__ = "0.1.0"
