#!/usr/bin/env bash
# Chamado pela task probe_bash: imprime como um script do .zip roda no worker.
echo "script: \$0 = $0"
echo "script: argumentos = $*"
echo "script: pasta de trabalho = $(pwd)"
