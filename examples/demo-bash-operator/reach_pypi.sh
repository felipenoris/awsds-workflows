#!/usr/bin/env bash
# A negativa da PyPI de demo-bash-operator: o worker não tem rota para a internet, então as duas
# tentativas devem falhar. Onde um firewall de DNS recusa o nome, em segundos; onde o nome resolve,
# depois dos timeouts de conexão (errno 101 depois de 43 s e de 64 s no ambiente alvo, 2026-10-12).
# O código de saída é a leitura: 1 quando nada respondeu, o esperado, e 0 quando algo respondeu.
# Cada falha imprime a causa numa linha, porque um erro do resolvedor e um timeout são leituras
# diferentes.
# Um BashOperator passa um arquivo .sh pelo Jinja antes de rodar: nada de chaves duplas nem de
# chave e cerquilha neste arquivo.
set -u

echo "proxy: $(env | grep -i -o -E '^(https?|no|all)_proxy=' | tr '\n' ' ')"
reached=0

start=$(date +%s)
if python3 - <<'PY'
import socket
import sys
import urllib.request

try:
    print("resolve: pypi.org ->", socket.getaddrinfo("pypi.org", 443)[0][4][0])
except OSError as e:
    print("resolve: pypi.org falhou:", repr(e))
try:
    urllib.request.urlopen("https://pypi.org/simple/", timeout=10)
except OSError as e:
    print("urllib:", repr(e))
    sys.exit(1)
PY
then
  echo "urllib: pypi.org respondeu"
  reached=1
else
  echo "urllib: pypi.org não respondeu"
fi
echo "urllib: $(( $(date +%s) - start )) s"

python3 -m pip --version
log=$(mktemp)
start=$(date +%s)
python3 -m pip download -vvv --no-deps --timeout 10 --retries 0 -d "$(mktemp -d)" six > "$log" 2>&1
rc=$?
grep -E 'Looking in indexes|Could not fetch URL|Successfully downloaded|^ERROR' "$log"
if [ "$rc" -eq 0 ]; then
  echo "pip: pypi.org respondeu"
  reached=1
else
  echo "pip: o download falhou, saída $rc"
fi
echo "pip: $(( $(date +%s) - start )) s"

if [ "$reached" -eq 1 ]; then
  exit 0
fi
exit 1
