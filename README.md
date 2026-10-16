[![Testes do pacote](https://github.com/felipenoris/awsds-workflows/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/felipenoris/awsds-workflows/actions/workflows/tests.yml)
[![Documentação do pacote](https://github.com/felipenoris/awsds-workflows/actions/workflows/docs.yml/badge.svg?branch=main)](https://felipenoris.github.io/awsds-workflows/)

# awsds-workflows

Ferramentas para montar workflows num projeto do SageMaker Unified Studio, os workflows que o
Amazon MWAA Serverless executa: o pacote empacota o código de uma task Python ou Bash e o de um job
de processamento do SageMaker, preenche o arquivo de definição do workflow com os valores do
projeto e confere uma aplicação da CLI de CI/CD contra as regras do serviço e da esteira
(`awsds-workflows lint`). O procedimento completo, escrito para quem vai montar o primeiro
workflow, está na
documentação do pacote, <https://felipenoris.github.io/awsds-workflows/>, gerada de `docs/index.md`
e das docstrings.

## Requisitos

- Linux com internet, onde o `uv` alcança o PyPI. O que o pacote grava é copiado depois para o
  ambiente do SageMaker, que não precisa de internet.
- O [`uv`](https://docs.astral.sh/uv/) no `PATH` e o Python 3.12 ou mais novo, que o `uv` instala.
- O `aws` no `PATH`, só para a leitura dos valores da conta (`awsds-workflows values --profile`).

## Instalação

Pelo endereço do repositório, nunca pelo nome: o nome está livre no PyPI, e um pacote publicado lá
com ele por outra pessoa seria instalado no lugar deste.

```shell
uv tool install git+https://github.com/felipenoris/awsds-workflows
awsds-workflows --help
```

O `uv tool upgrade awsds-workflows` traz o commit mais novo da `main`.

## Exemplos

A pasta [`examples/`](examples/README.md) traz workflows de exemplo, cada um com a definição e o
código: os que rodaram no ambiente alvo e uma aplicação da CLI de CI/CD com um job do Visual ETL.
Os passos para reproduzi-los, a partir do `space_values.json` que `scripts/space_values.py` escreve
num espaço do projeto, estão na página
[Os exemplos, passo a passo](https://felipenoris.github.io/awsds-workflows/awsds_workflows/examples.html)
da documentação.

## Desenvolvimento e testes

```shell
uv sync --all-groups
uv run pytest
uv run pytest -m "not network"
uv run ruff check
uv run ruff format --check
uv run pdoc awsds_workflows --docformat restructuredtext -t docs/theme -o site
```

O `uv sync --all-groups` instala em `.venv/` o Python 3.13 do `.python-version`, o pacote e os
grupos `dev` (o `pytest`, o `ruff` e o `boto3` dos testes dos exemplos) e `docs` (o `pdoc`). O
`pytest` roda os testes do pacote e os de `examples/awsds-demo-job/`. Os testes marcados `network`
travam e constroem projetos de teste com o `uv` e precisam do PyPI; `-m "not network"` os pula.
O `pdoc`
grava o site em `site/`, a mesma geração que o workflow `docs.yml` publica a cada push na `main`;
o `-t docs/theme` traz as cores escuras do site.

O workflow [`tests.yml`](.github/workflows/tests.yml) roda o Ruff e os testes nos Pythons 3.12,
3.13 e 3.14. Para rodar os testes em outra versão sem trocar o `.venv/`, o `--isolated` usa um
ambiente temporário:

```shell
uv run --isolated --python 3.12 pytest
```
