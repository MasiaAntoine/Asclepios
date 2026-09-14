# Déploiement Asclepios sur VPS OVH

Domaine cible : **https://asclepios.masia-antoine.fr**  
VPS : `ubuntu@51.38.236.129`

## Prérequis

- [x] Docker + Compose sur le VPS
- [x] DNS A `asclepios` → IP du VPS (Hostinger)
- [ ] `.env.prod` rempli (auth, OVH, **même** `ENCRYPTION_KEY` que le local)
- [ ] Dans `.env.prod` :

```env
ASCLEPIOS_ENV=production
CORS_ORIGINS=https://asclepios.masia-antoine.fr
AUTH_COOKIE_SECURE=true
```

TOTP : entrée Google Authenticator **Asclepios Prod** (générée avec `setup_totp.py --env production`).

## Config SSH dans `.env` (local Mac — pas `.env.prod`)

```env
DEPLOY_SSH_HOST=51.38.236.129
DEPLOY_SSH_USER=ubuntu
DEPLOY_SSH_PATH=~/asclepios
# DEPLOY_SSH_PASSWORD=...   # éviter si possible
```

**Recommandé** : clé SSH (pas de mot de passe dans `.env`) :

```bash
ssh-copy-id ubuntu@51.38.236.129
```

Sinon, avec mot de passe : `brew install hudochenkov/sshpass/sshpass` + `DEPLOY_SSH_PASSWORD=...` dans `.env`.

## Déploiement automatique

Depuis le Mac, à la racine du projet :

```bash
chmod +x scripts/deploy_vps.sh

# Première fois (pare-feu + deploy + pull vault)
./scripts/deploy_vps.sh --setup-firewall --pull-vault

# Ensuite, à chaque mise à jour
./scripts/deploy_vps.sh

# Avec re-sync vault OVH → VPS
./scripts/deploy_vps.sh --pull-vault
```

Le script :
1. `rsync` le projet (dont `.env.prod`) vers le VPS — **sans** `vault/` local ni `node_modules`
2. `docker compose -f docker-compose.prod.yml up -d --build`

## Pare-feu (manuel ou via le script)

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status
```

Ou : `./scripts/deploy_vps.sh --setup-firewall`

## Vérifier

1. Ouvre https://asclepios.masia-antoine.fr
2. Login mot de passe **prod** → code Authenticator **Prod**
3. Sans cookie : `curl -I https://asclepios.masia-antoine.fr/api/settings/status` → 401

## Sync vault

```bash
./scripts/deploy_vps.sh --pull-vault
```

Ou sur le VPS :

```bash
cd ~/asclepios
docker compose -f docker-compose.prod.yml run --rm api python scripts/sync.py pull
```

## Suite sécurité (recommandé)

- Clé SSH + retirer `DEPLOY_SSH_PASSWORD` du `.env`
- `fail2ban`, snapshots OVH
- Ne jamais exposer 8001 / 5173
- Ne jamais committer `.env` / `.env.prod`
