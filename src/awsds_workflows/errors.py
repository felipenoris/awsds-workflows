"""[public] A exceção que as ferramentas do pacote levantam quando recusam uma entrada.

A linha de comando imprime a mensagem na saída de erro e termina com 1; quem chama as funções do
pacote recebe a mesma mensagem em ``awsds_workflows.errors.RefusalError``.

Exemplo:

.. code-block:: python

    from pathlib import Path

    from awsds_workflows import errors, package_task

    project = Path("meu-projeto")
    try:
        package_task.build_archive(project, project / "tasks.py", Path("task.zip"))
    except errors.RefusalError as error:
        print(error)
"""

__all__ = ["RefusalError"]


class RefusalError(Exception):
    """[public] A ferramenta recusou a entrada, e a mensagem diz o motivo e o que fazer.

    Cobre o projeto sem ``uv.lock``, o arquivo ou a pasta que falta, a pasta de saída que já
    existe, o projeto com módulos de extensão, o conteúdo acima do limite do worker, o lock que
    discorda do ambiente do job, a linha do arquivo de ambiente que não é ``nome==versão``, o
    ``uv`` ou o ``aws`` que terminaram com erro, o placeholder sem valor e a definição de workflow
    que não é YAML ou não é um mapeamento.
    """
