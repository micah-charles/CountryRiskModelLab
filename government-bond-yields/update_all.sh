#!/bin/zsh
set -euo pipefail
cd "$(dirname "$0")"
python3 refresh_project.py
node render_chart_png.mjs
node build_workbook.mjs
