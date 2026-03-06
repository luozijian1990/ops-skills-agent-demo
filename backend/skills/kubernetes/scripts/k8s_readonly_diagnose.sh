#!/usr/bin/env bash
set -euo pipefail

KUBECTL_BIN="/usr/local/bin/kubectl"
KUBECONFIG_PATH_INPUT="${1:-}"
KUBECONFIG_PATH=""
NAMESPACE="${2:-}"
RESOURCE="${3:-}"

if [[ -n "${KUBECONFIG_PATH_INPUT}" ]]; then
  KUBECONFIG_PATH="${KUBECONFIG_PATH_INPUT}"
else
  for candidate in \
    "./skills/kubernetes/kubeconfig" \
    "./skills/kubernetes/kubeconfig.yaml" \
    "./skills/kubernetes/.kubeconfig" \
    "./skills/kubeconfig" \
    "./skills/kubeconfig.yaml" \
    "./skills/.kubeconfig"
  do
    if [[ -f "${candidate}" ]]; then
      KUBECONFIG_PATH="${candidate}"
      break
    fi
  done

  if [[ -z "${KUBECONFIG_PATH}" ]]; then
    KUBECONFIG_PATH="./skills/kubernetes/kubeconfig"
  fi
fi

if [[ ! -x "${KUBECTL_BIN}" ]]; then
  if command -v kubectl >/dev/null 2>&1; then
    KUBECTL_BIN="$(command -v kubectl)"
  else
    echo "ERROR: kubectl not found at /usr/local/bin/kubectl and not in PATH." >&2
    exit 1
  fi
fi

if [[ ! -f "${KUBECONFIG_PATH}" ]]; then
  echo "ERROR: kubeconfig not found: ${KUBECONFIG_PATH}" >&2
  echo "Place kubeconfig under ./skills/kubernetes/ or pass it as first argument." >&2
  exit 1
fi

run() {
  echo
  printf ">>>"
  printf " %q" "$@"
  echo
  "$@"
}

echo "Using kubectl: ${KUBECTL_BIN}"
echo "Using kubeconfig: ${KUBECONFIG_PATH}"

run "${KUBECTL_BIN}" --kubeconfig "${KUBECONFIG_PATH}" version --client
run "${KUBECTL_BIN}" --kubeconfig "${KUBECONFIG_PATH}" config get-contexts
run "${KUBECTL_BIN}" --kubeconfig "${KUBECONFIG_PATH}" config current-context
run "${KUBECTL_BIN}" --kubeconfig "${KUBECONFIG_PATH}" get nodes -o wide
run "${KUBECTL_BIN}" --kubeconfig "${KUBECONFIG_PATH}" get ns

if [[ -n "${NAMESPACE}" ]]; then
  run "${KUBECTL_BIN}" --kubeconfig "${KUBECONFIG_PATH}" get pods -n "${NAMESPACE}" -o wide
  run "${KUBECTL_BIN}" --kubeconfig "${KUBECONFIG_PATH}" get events -n "${NAMESPACE}" --sort-by=.lastTimestamp
else
  run "${KUBECTL_BIN}" --kubeconfig "${KUBECONFIG_PATH}" get pods -A -o wide
  run "${KUBECTL_BIN}" --kubeconfig "${KUBECONFIG_PATH}" get events -A --sort-by=.lastTimestamp
fi

if [[ -n "${RESOURCE}" ]]; then
  if [[ -n "${NAMESPACE}" ]]; then
    run "${KUBECTL_BIN}" --kubeconfig "${KUBECONFIG_PATH}" get "${RESOURCE}" -n "${NAMESPACE}" -o wide || true
    run "${KUBECTL_BIN}" --kubeconfig "${KUBECONFIG_PATH}" describe "${RESOURCE}" -n "${NAMESPACE}" || true
  else
    run "${KUBECTL_BIN}" --kubeconfig "${KUBECONFIG_PATH}" get "${RESOURCE}" -A -o wide || true
    run "${KUBECTL_BIN}" --kubeconfig "${KUBECONFIG_PATH}" describe "${RESOURCE}" || true
  fi
fi

echo
echo "Readonly diagnosis completed."
