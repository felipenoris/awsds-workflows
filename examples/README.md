# Os exemplos de workflow

Cinco workflows que rodaram no ambiente alvo em 2026-10-12 e 2026-10-13, um por pasta, cada uma
com a definição, o código e um `README.md` com os passos para reproduzi-lo. Os valores da conta
entram pelo `space_values.json` que `scripts/space_values.py` escreve num espaço do projeto, e
cada definição guarda só placeholders. O procedimento inteiro, termo a termo, está na
[documentação do pacote](https://felipenoris.github.io/awsds-workflows/awsds_workflows.html); esta pasta é o caminho mais curto até uma execução.

| Exemplo | O que ele mostra | O `Code` do workflow | No ambiente alvo |
|---|---|---|---|
| [`probe-worker`](probe-worker/) | o que o worker tem: disco, CPU, memória, ferramentas e pacotes, numa task Bash inline | nenhum | rodou em 2026-10-13 |
| [`demo-python-operator`](demo-python-operator/) | uma task Python sobre o `.zip` do `package-task`: um CSV entra, um resumo sai no S3 | `demo-python-operator.zip` | rodou em 2026-10-12 |
| [`demo-bash-operator`](demo-bash-operator/) | uma task Bash sobre o mesmo projeto, com dois scripts, e a prova de que o worker não alcança a PyPI | `demo-bash-operator.zip` | rodou em 2026-10-12 |
| [`demo-devenv-job`](demo-devenv-job/) | um job de processamento na imagem padrão do SageMaker, sem rede, sobre o mesmo projeto | nenhum: o código é uma entrada do job | parou na permissão do projeto em 2026-10-12 |
| [`redshift-unload`](redshift-unload/) | uma task Python que descarrega uma consulta ao Redshift Serverless no S3, com `UNLOAD` | `redshift-unload.zip` | rodou em 2026-10-13 |

Os três `demo-*` dividem o projeto `uv` [`awsds-demo-job/`](awsds-demo-job/): um CSV entra, um
resumo em JSON sai, no worker ou dentro do job.

## Antes de começar

- **A máquina que empacota**: um Linux com internet, o `uv` e o pacote
  (`uv tool install git+https://github.com/felipenoris/awsds-workflows`), com este repositório
  clonado; os comandos dos exemplos rodam na raiz dele.
- **Um projeto no SageMaker Unified Studio** com um espaço (JupyterLab ou Code Editor): é lá que
  os valores são lidos, que os arquivos chegam ao S3 do projeto, pelo `~/shared/`, e que o
  resultado é lido. O ambiente alvo não tem internet, e nada é instalado nele.
- **O `aws` na máquina que empacota** é dispensável: tudo o que ele faria no S3 do projeto um
  espaço faz pelo `~/shared/`.

## Os valores

1. Copie `scripts/space_values.py` para um espaço do projeto e rode, num terminal de lá:

   ```shell
   python space_values.py > space_values.json
   ```

   O JSON traz a região, a conta, o papel do projeto, o projeto, o domínio, o bucket, o grupo de
   segurança e as duas sub-redes, e a chave KMS quando o projeto tem uma
   ([Os valores de dentro de um espaço](https://felipenoris.github.io/awsds-workflows/awsds_workflows.html#os-valores-de-dentro-de-um-espaco)).
2. Copie o `space_values.json` para a máquina que empacota. Ele leva os ids da conta, e o
   `.gitignore` deste repositório o deixa fora do git.
3. O `demo-devenv-job` e o `redshift-unload` pedem mais valores, cada um num arquivo que o
   `README.md` dele mostra: `valores-job.json`, com a imagem e o Python do job, e
   `valores-redshift.json`, com o workgroup, o banco e a tabela.

O `render` preenche uma definição com os arquivos, na ordem da linha de comando, cada um por cima
do anterior, e imprime o resultado:

```shell
awsds-workflows render examples/demo-python-operator/demo-python-operator.yaml \
    --values-file space_values.json > /tmp/demo-python-operator.yaml
awsds-workflows render examples/demo-devenv-job/demo-devenv-job.yaml \
    --values-file space_values.json --values-file valores-job.json > /tmp/demo-devenv-job.yaml
```

O arquivo preenchido leva os ids da conta: ele fica em `/tmp`, e nunca no repositório.

## Onde os arquivos ficam

Cada exemplo usa só o prefixo `shared/exemplos/<exemplo>/` do projeto no bucket, que num espaço é
a pasta `~/shared/exemplos/<exemplo>/`: a caixa de entrada `inbox/`, a caixa de saída `outbox/`
e, no `demo-devenv-job`, a pasta de código `awsds-demo-job/`. O `~/shared/` de um espaço é o
prefixo `s3://<bucket>/<domínio>/<projeto>/shared/` do bucket do projeto (lido no ambiente alvo
em 2026-10-12), então um `cp` para lá é um envio ao S3. Um `mkdir` deixa no prefixo um marcador
de pasta de zero bytes, que o sensor `inbox/?*` dos exemplos não casa.

## Os passos no portal

Os mesmos para os cinco, na página *Workflows* do projeto; o `README.md` de cada exemplo diz o
que é só dele.

1. **Crie um workflow vazio** com o nome do exemplo.
2. **Envie o `.zip`** em *Settings → Storage → Python/Bash Operator Files*, num exemplo que tem
   um. Num exemplo sem `Code`, esvazie o campo *Operator files zip S3 location* antes de salvar,
   ou o save falha com `Code not found in specified S3 location`.
3. **Importe a definição preenchida** com *Actions → Import definition file* e salve. Uma
   importação não substitui um workflow já salvo: apague o antigo antes.
4. **Ponha o arquivo na caixa de entrada**, num exemplo com sensor, e execute o workflow. O
   sensor espera 10 minutos; depois disso a execução termina sem erro e sem rodar o resto.
5. **Leia o log de cada task** no grupo de logs do workflow, e o resultado em `outbox/`.

Uma versão nova do `.zip` pede um envio e um save novos: o workflow roda a cópia que o serviço
tirou no último save ([O `.zip` no workflow](https://felipenoris.github.io/awsds-workflows/awsds_workflows.html#o-zip-no-workflow)).

## O que conferir

Os três `demo-*` gravam `sample.result.json`, o resumo de `sample.csv`, cujo sha256 é
`1b2bc4d73bc49bca1a23a6d0971c1365362e785826a33adfcebec7925a248191`, o mesmo no laboratório
(2026-10-11) e no ambiente alvo (2026-10-12). Num espaço:

```shell
sha256sum ~/shared/exemplos/demo-python-operator/outbox/*/sample.result.json
```

As leituras de cada execução, com as datas, estão no `README.md` de cada exemplo, e as perguntas
que uma execução deixa em [Como ler uma execução](https://felipenoris.github.io/awsds-workflows/awsds_workflows.html#como-ler-uma-execucao).

## Limpeza

Apague os workflows na página *Workflows* e a pasta `~/shared/exemplos/` do espaço. O grupo de
logs de cada workflow e os `.zip` em `dev/operatorFiles/` ficam ([Limpeza](https://felipenoris.github.io/awsds-workflows/awsds_workflows.html#limpeza)).

## Os testes

`uv run pytest tests/test_examples.py` confere as cinco definições (cada uma renderiza com valores
fabricados, é YAML válido, pede só os valores do espaço e os do próprio exemplo e guarda os
arquivos sob o prefixo do exemplo), roda a task Python e o módulo de `UNLOAD` sobre dublês do
`boto3` e, com `-m network`, constrói os dois `.zip` e lê as raízes deles. O projeto
compartilhado tem os próprios testes, que o `uv run pytest` da raiz também roda.
