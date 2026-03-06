#!/usr/bin/env bash
set -u -o pipefail

DOCKER_BIN="/usr/local/bin/docker"
REMOTE_INPUT="${1:-}"
TARGET_CONTAINER="${2:-}"
LOG_LINES="${3:-200}"
REMOTE_ENDPOINT=""

resolve_remote_endpoint() {
  if [[ -n "${REMOTE_INPUT}" ]]; then
    REMOTE_ENDPOINT="${REMOTE_INPUT}"
  elif [[ -n "${DOCKER_HOST:-}" ]]; then
    REMOTE_ENDPOINT="${DOCKER_HOST}"
  elif [[ -f "./skills/docker/endpoint" ]]; then
    REMOTE_ENDPOINT="$(head -n 1 ./skills/docker/endpoint | tr -d '[:space:]')"
  else
    REMOTE_ENDPOINT=""
  fi

  if [[ -n "${REMOTE_ENDPOINT}" && "${REMOTE_ENDPOINT}" != *"://"* ]]; then
    REMOTE_ENDPOINT="tcp://${REMOTE_ENDPOINT}"
  fi
}

run_cmd() {
  echo
  printf ">>>"
  printf " %q" "$@"
  echo
  if ! "$@"; then
    echo "WARN: 命令执行失败，继续后续诊断。" >&2
  fi
}

run_docker() {
  run_cmd "${DOCKER_BIN}" -H "${REMOTE_ENDPOINT}" "$@"
}

if [[ ! -x "${DOCKER_BIN}" ]]; then
  echo "ERROR: 未找到可执行 Docker CLI: ${DOCKER_BIN}" >&2
  exit 1
fi

resolve_remote_endpoint

if [[ -z "${REMOTE_ENDPOINT}" ]]; then
  echo "ERROR: 未提供远程 Docker 端点。" >&2
  echo "请传入第一个参数（如 10.0.0.8:2375 或 tcp://10.0.0.8:2375），或设置 DOCKER_HOST，或写入 ./skills/docker/endpoint。" >&2
  exit 1
fi

if ! [[ "${LOG_LINES}" =~ ^[0-9]+$ ]]; then
  echo "ERROR: log_lines 必须是整数，当前值: ${LOG_LINES}" >&2
  exit 1
fi

echo "使用 Docker CLI: ${DOCKER_BIN}"
echo "远程端点: ${REMOTE_ENDPOINT}"
if [[ -n "${DOCKER_TLS_VERIFY:-}" ]]; then
  echo "DOCKER_TLS_VERIFY=${DOCKER_TLS_VERIFY}"
fi
if [[ -n "${DOCKER_CERT_PATH:-}" ]]; then
  echo "DOCKER_CERT_PATH=${DOCKER_CERT_PATH}"
fi

echo
echo "===== 基线只读诊断 ====="
run_docker version
run_docker info
run_docker ps -a --no-trunc
run_docker images --digests
run_docker network ls
run_docker volume ls
run_docker stats --no-stream

if [[ -n "${TARGET_CONTAINER}" ]]; then
  echo
  echo "===== 目标容器深入诊断: ${TARGET_CONTAINER} ====="
  run_docker inspect "${TARGET_CONTAINER}"
  run_docker logs --tail "${LOG_LINES}" "${TARGET_CONTAINER}"
  run_docker top "${TARGET_CONTAINER}"
fi

echo
echo "只读诊断完成。"
