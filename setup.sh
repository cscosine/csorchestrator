#!/usr/bin/env bash
# Owned by the project template (cs-project-template): change it there.
# Creates .venv, installs the project with its dev tools, installs the pre-commit hooks.
set -euo pipefail

if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
  echo "Do not source this script. Run: ./setup.sh"
  return 1
fi

usage() {
  cat <<USAGE
Usage: ./setup.sh [--python=<interpreter>]

  --python=<interpreter>        Python used to create .venv (default: python3, at least 3.11)
USAGE
}

PYTHON="python3"
for arg in "$@"; do
  case "${arg}" in
    --python=*) PYTHON="${arg#*=}" ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: ${arg}"; usage; exit 1 ;;
  esac
done

echo "Using Python: ${PYTHON}"

if ! "${PYTHON}" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'; then
  echo "Error: Python 3.11 or newer is required."
  echo "Found:"
  "${PYTHON}" --version
  exit 1
fi

"${PYTHON}" -m venv .venv

# shellcheck disable=SC1091
source .venv/bin/activate

python -m pip install --upgrade pip setuptools wheel
python -m pip install -e ".[dev]"

pre-commit install

echo "Setup complete."
echo ""
echo "Next: "
echo "  source .venv/bin/activate"
echo "  code ."
echo ""
echo "Or: "
echo "  ./open-code.sh"
