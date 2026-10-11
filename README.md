[![Testes do pacote](https://github.com/felipenoris/awsds-workflows/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/felipenoris/awsds-workflows/actions/workflows/tests.yml)
[![Documentação do pacote](https://github.com/felipenoris/awsds-workflows/actions/workflows/docs.yml/badge.svg?branch=main)](https://felipenoris.github.io/awsds-workflows/)

# awsds-workflows

Empacota o código das tasks de um workflow do MWAA Serverless e renderiza as definições de workflow
de um projeto do SageMaker Unified Studio. O procedimento completo está na documentação do pacote,
<https://felipenoris.github.io/awsds-workflows/>, gerada de `docs/index.md` e das docstrings.

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

## Desenvolvimento e testes

```shell
uv sync --all-groups
uv run pytest
uv run pytest -m "not network"
uv run ruff check
uv run ruff format --check
uv run pdoc awsds_workflows --docformat restructuredtext -o site
```

O `uv sync --all-groups` instala em `.venv/` o Python 3.13 do `.python-version`, o pacote e os
grupos `dev` (o `pytest` e o `ruff`) e `docs` (o `pdoc`). Os testes marcados `network` travam e
constroem projetos de teste com o `uv` e precisam do PyPI; `-m "not network"` os pula. O `pdoc`
grava o site em `site/`, a mesma geração que o workflow `docs.yml` publica a cada push na `main`.

O workflow [`tests.yml`](.github/workflows/tests.yml) roda o Ruff e os testes nos Pythons 3.12,
3.13 e 3.14. Em outra versão, o `--isolated` roda os testes num ambiente temporário, sem trocar o
`.venv/`:

```shell
uv run --isolated --python 3.12 pytest
```
