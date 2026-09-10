#!/bin/bash
# ==============================================================================
# NOUNS TV - ATALHO DE MANUTENÇÃO FAST & M3U
# ==============================================================================
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
python3 "$DIR/manutencao_fast.py" "$@"
