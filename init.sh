#!/usr/bin/env bash
set -e
uv pip install -e ".[dev]"
mkdir -p ~/.config/lake-of-vectors
[ -f ~/.config/lake-of-vectors/config.yaml ] || cp config.example.yaml ~/.config/lake-of-vectors/config.yaml
