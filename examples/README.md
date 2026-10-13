# Os exemplos de workflow

Cinco workflows que rodaram no ambiente alvo em 2026-10-12 e 2026-10-13, um por pasta, cada uma
com a definição, o código e um `README.md` que diz o que o exemplo mostra, task por task, e o que
cada execução leu. Os passos para reproduzi-los, na ordem em que cada comando roda, estão na
página [Os exemplos, passo a passo](https://felipenoris.github.io/awsds-workflows/awsds_workflows/examples.html)
da documentação. Cada definição guarda só placeholders: os valores da conta entram pelo
`space_values.json` que `scripts/space_values.py` escreve num espaço do projeto, e os que um
exemplo pede além deles entram num segundo arquivo, que a página mostra.

| Exemplo | O que ele mostra | O `Code` do workflow | No ambiente alvo |
|---|---|---|---|
| [`probe-worker`](probe-worker/) | o que o worker tem: disco, CPU, memória, ferramentas e pacotes, numa task Bash inline | nenhum | rodou em 2026-10-13 |
| [`demo-python-operator`](demo-python-operator/) | uma task Python sobre o `.zip` do `package-task`: um CSV entra, um resumo sai no S3 | `demo-python-operator.zip` | rodou em 2026-10-12 |
| [`demo-bash-operator`](demo-bash-operator/) | uma task Bash sobre o mesmo projeto, com dois scripts, e a prova de que o worker não alcança a PyPI | `demo-bash-operator.zip` | rodou em 2026-10-12 |
| [`demo-devenv-job`](demo-devenv-job/) | um job de processamento na imagem padrão do SageMaker, sem rede, sobre o mesmo projeto | nenhum: o código é uma entrada do job | parou na permissão do projeto em 2026-10-12 |
| [`redshift-unload`](redshift-unload/) | uma task Python que descarrega uma consulta ao Redshift Serverless no S3, com `UNLOAD` | `redshift-unload.zip` | rodou em 2026-10-13 |

Os três `demo-*` dividem o projeto `uv` [`awsds-demo-job/`](awsds-demo-job/): um CSV entra, um
resumo em JSON sai, no worker ou dentro do job. Cada exemplo usa só o prefixo
`shared/exemplos/<exemplo>/` do projeto no bucket, a pasta `~/shared/exemplos/<exemplo>/` de um
espaço: a caixa de entrada `inbox/`, a caixa de saída `outbox/` e, no `demo-devenv-job`, a pasta de
código `awsds-demo-job/`.

## Os testes

`uv run pytest tests/test_examples.py` confere as cinco definições (cada uma renderiza com valores
fabricados, é YAML válido, pede só os valores do espaço e os do próprio exemplo e guarda os
arquivos sob o prefixo do exemplo), roda a task Python e o módulo de `UNLOAD` sobre dublês do
`boto3` e, com `-m network`, constrói os dois `.zip` e lê as raízes deles. O projeto
compartilhado tem os próprios testes, que o `uv run pytest` da raiz também roda.
