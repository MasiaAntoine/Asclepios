#!/usr/bin/env bash
# Déploie Asclepios sur le VPS (rsync + docker compose prod).
#
# Config dans .env (local, jamais .env.prod) :
#   DEPLOY_SSH_HOST=51.38.236.129
#   DEPLOY_SSH_USER=ubuntu
#   DEPLOY_SSH_PATH=~/asclepios
#   DEPLOY_SSH_PASSWORD=...   # optionnel — préférer une clé SSH
#
# Usage :
#   ./scripts/deploy_vps.sh
#   ./scripts/deploy_vps.sh --pull-vault
#   ./scripts/deploy_vps.sh --setup-firewall

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/.env"
COMPOSE_FILE="docker-compose.prod.yml"

PULL_VAULT=0
SETUP_FIREWALL=0

for arg in "$@"; do
  case "$arg" in
    --pull-vault) PULL_VAULT=1 ;;
    --setup-firewall) SETUP_FIREWALL=1 ;;
    -h|--help)
      sed -n '2,16p' "$0"
      exit 0
      ;;
    *)
      echo "Option inconnue : $arg" >&2
      exit 1
      ;;
  esac
done

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Fichier .env introuvable : $ENV_FILE" >&2
  exit 1
fi

if [[ ! -f "$ROOT/.env.prod" ]]; then
  echo "Fichier .env.prod introuvable (requis sur le VPS)." >&2
  exit 1
fi

# Lit une clé KEY=value depuis .env (dernière occurrence), sans sourcer tout le fichier.
env_get() {
  local key="$1"
  local line
  line="$(grep -E "^${key}=" "$ENV_FILE" | tail -n 1 || true)"
  if [[ -z "$line" ]]; then
    echo ""
    return 0
  fi
  local val="${line#*=}"
  # Enlever guillemets simples/doubles enveloppants
  if [[ "$val" =~ ^\".*\"$ ]]; then
    val="${val:1:${#val}-2}"
  elif [[ "$val" =~ ^\'.*\'$ ]]; then
    val="${val:1:${#val}-2}"
  fi
  printf '%s' "$val"
}

HOST="$(env_get DEPLOY_SSH_HOST)"
USER="$(env_get DEPLOY_SSH_USER)"
REMOTE_PATH="$(env_get DEPLOY_SSH_PATH)"
PASSWORD="$(env_get DEPLOY_SSH_PASSWORD)"

USER="${USER:-ubuntu}"
REMOTE_PATH="${REMOTE_PATH:-~/asclepios}"

if [[ -z "$HOST" ]]; then
  echo "DEPLOY_SSH_HOST manquant dans .env" >&2
  exit 1
fi

TARGET="${USER}@${HOST}"
export RSYNC_RSH="ssh -o StrictHostKeyChecking=accept-new"
SSH_CMD=(ssh -o StrictHostKeyChecking=accept-new "$TARGET")

if [[ -n "$PASSWORD" ]]; then
  if ! command -v sshpass >/dev/null 2>&1; then
    echo "DEPLOY_SSH_PASSWORD est défini mais sshpass est absent." >&2
    echo "  macOS : brew install hudochenkov/sshpass/sshpass" >&2
    echo "Ou mieux : ssh-copy-id ${TARGET}  puis laisse DEPLOY_SSH_PASSWORD vide." >&2
    exit 1
  fi
  export SSHPASS="$PASSWORD"
  export RSYNC_RSH="sshpass -e ssh -o StrictHostKeyChecking=accept-new"
  SSH_CMD=(sshpass -e ssh -o StrictHostKeyChecking=accept-new "$TARGET")
fi

echo "==> Sync → ${TARGET}:${REMOTE_PATH}"
rsync -avz --delete \
  --exclude node_modules \
  --exclude app/node_modules \
  --exclude .venv \
  --exclude .git \
  --exclude vault \
  --exclude '.auth-password-local' \
  --exclude '.env' \
  --exclude '.sync_state.json' \
  --exclude '**/__pycache__' \
  --exclude '*.pyc' \
  "$ROOT/" "${TARGET}:${REMOTE_PATH}/"

remote() {
  "${SSH_CMD[@]}" "$@"
}

if [[ "$SETUP_FIREWALL" -eq 1 ]]; then
  echo "==> Pare-feu (ufw)"
  remote "sudo ufw allow OpenSSH && sudo ufw allow 80/tcp && sudo ufw allow 443/tcp && sudo ufw --force enable && sudo ufw status"
fi

echo "==> Build & up (prod)"
remote "mkdir -p ${REMOTE_PATH}/vault && cd ${REMOTE_PATH} && docker compose -f ${COMPOSE_FILE} up -d --build"

if [[ "$PULL_VAULT" -eq 1 ]]; then
  echo "==> Pull vault OVH"
  remote "cd ${REMOTE_PATH} && docker compose -f ${COMPOSE_FILE} run --rm api python scripts/sync.py pull"
fi

echo "==> OK — https://asclepios.masia-antoine.fr"
