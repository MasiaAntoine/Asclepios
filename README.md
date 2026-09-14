# Asclepios

Dossier médical personnel : app Vue 3 + API FastAPI, vault chiffré syncé vers OVH Object Storage.

## Dev local

```bash
cp .env.example .env
# Remplir auth, OVH, ENCRYPTION_KEY (voir ci-dessous)
docker compose up
```

- App : http://localhost:5173  
- Auth : mot de passe + Google Authenticator (TOTP)

Générer le hash mot de passe et le secret TOTP :

```bash
docker compose exec -it api python scripts/hash_password.py
docker compose exec -it api python scripts/setup_totp.py --env development
```

Coller `AUTH_PASSWORD_HASH`, `SESSION_SECRET`, `AUTH_TOTP_SECRET` dans `.env`.

## Sync vault ↔ OVH

Le dossier `vault/` est la source de vérité locale. Les fichiers sont **chiffrés avant** l’upload (`ENCRYPTION_KEY`). OVH ne stocke que des blobs illisibles.

| Commande | Effet |
| --- | --- |
| `python scripts/sync.py push` | vault → OVH (incrémental) |
| `python scripts/sync.py pull` | OVH → vault (incrémental) |
| `… --full` | resync complète |

**Ne change pas** `ENCRYPTION_KEY` tant que des fichiers existent sur OVH (sinon tu ne pourras plus les déchiffrer). Même clé en local et en prod.

```bash
source .venv/bin/activate   # si hors Docker
python scripts/sync.py push
python scripts/sync.py pull
```

## Production (VPS)

Stack : Caddy (HTTPS) → frontend nginx + API. Seuls les ports **80/443** sont publics. `/api` et `/vault` exigent une session (mot de passe + TOTP).

Guide détaillé : [`deploy/DEPLOY.md`](deploy/DEPLOY.md)

### Config

- `.env.prod` — secrets **serveur** (auth prod, OVH, `ENCRYPTION_KEY`, `CORS_ORIGINS=https://asclepios.masia-antoine.fr`, `AUTH_COOKIE_SECURE=true`)
- `.env` — secrets **local** + infos SSH pour le script de déploiement :

```env
DEPLOY_SSH_HOST=51.38.236.129
DEPLOY_SSH_USER=ubuntu
DEPLOY_SSH_PATH=~/asclepios
DEPLOY_SSH_PASSWORD=...   # ou mieux : ssh-copy-id (clé SSH)
```

TOTP prod (entrée séparée « Asclepios Prod ») :

```bash
docker compose exec -it api python scripts/setup_totp.py --env production
```

### Déployer : `./scripts/deploy_vps.sh`

Depuis ton Mac, à la racine du projet :

```bash
# Première fois
./scripts/deploy_vps.sh --setup-firewall --pull-vault

# Mises à jour suivantes (code + rebuild)
./scripts/deploy_vps.sh

# Mise à jour + recharger le vault depuis OVH sur le VPS
./scripts/deploy_vps.sh --pull-vault
```

Que fait le script ?

1. **`rsync`** du projet vers le VPS (dont `.env.prod`) — sans `vault/` local, sans `node_modules`, sans ton `.env` local  
2. **`docker compose -f docker-compose.prod.yml up -d --build`** sur le serveur  
3. Avec **`--pull-vault`** : sur le VPS, lance `python scripts/sync.py pull` dans le conteneur API → télécharge / met à jour le `vault/` **du serveur** depuis OVH (chiffré → déchiffré avec `ENCRYPTION_KEY` de `.env.prod`)  
4. Avec **`--setup-firewall`** : ouvre SSH + 80 + 443 (ufw)

`--pull-vault` ne pousse **pas** ton vault Mac : il aligne le disque du VPS sur le bucket OVH. En pratique : tu fais `push` en local → OVH à jour → deploy avec `--pull-vault` → le VPS a les mêmes données.

Site : **https://asclepios.masia-antoine.fr**

## Structure

```text
asclepios/
├── .env / .env.prod     # secrets (non versionnés)
├── api/                 # FastAPI
├── app/                 # Vue 3
├── deploy/              # Caddy, nginx, guide VPS
├── scripts/
│   ├── sync.py          # push / pull chiffré
│   ├── deploy_vps.sh    # déploiement SSH
│   ├── hash_password.py
│   └── setup_totp.py
├── docker-compose.yml       # dev
├── docker-compose.prod.yml  # prod
└── vault/               # données médicales (gitignoré, sync OVH)
```

## Sécurité

- Ne commit jamais `.env`, `.env.prod`, ni `vault/`
- Auth obligatoire (mot de passe + TOTP) sur toute l’API et `/vault`
- En prod : API non exposée directement (seulement via Caddy HTTPS)
- Sauvegarde `ENCRYPTION_KEY` hors du projet
- Sans cette clé, les données sur OVH sont irrécupérables
