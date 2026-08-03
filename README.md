# Asclépios — sync chiffré OVH Object Storage

Synchronisation d’un dossier local `data/` vers un bucket OVH Object Storage (S3), avec chiffrement côté client avant l’envoi.

## Principe


| Commande | Effet |
| -------- | ----- |
| `push`   | Sync incrémental data→OVH (ajout / modif / suppression) |
| `pull`   | Sync incrémental OVH→data (ajout / modif / suppression) |
| `… --full` | Resync complète (wipe puis tout renvoyer / tout retélécharger) |


Le dossier unique de travail est `data/` : c’est à la fois la source du push et la destination du pull.

**Structure sur OVH** : chaque dossier de `data/` est stocké comme objet chiffré (`dossier/.ovhdir`) avec son chemin relatif dans le blob. Au `pull`, les dossiers sont recréés depuis OVH — pas de manifeste local indispensable.

Les fichiers sont chiffrés **avant** l’upload (`ENCRYPTION_KEY` dans `.env`). OVH ne stocke que des blobs illisibles. Un chiffrement serveur (SSE-OMK) peut s’ajouter côté OVH, mais la clé perso reste obligatoire pour relire les données.

## Prérequis

- Python 3.10+
- Un conteneur Object Storage OVH (API S3) + un utilisateur avec Access Key / Secret Key

## Installation

```bash
cd asclepios
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# deps des scripts métier (après pull) : pip install -r data/scripts/requirements.txt
cp .env.example .env
```

Remplir `.env` :

- `OVH_ACCESS_KEY` / `OVH_SECRET_KEY` — clés S3 de l’utilisateur Object Storage
- `OVH_BUCKET` — nom du conteneur (ex. `asclepios`)
- `OVH_REGION` / `OVH_ENDPOINT` — déjà préremplis pour Paris (`eu-west-par`)
- `ENCRYPTION_KEY` — clé Fernet déjà présente dans ton `.env` ; **ne pas la changer** tant que des fichiers chiffrés existent sur OVH, sinon tu ne pourras plus les déchiffrer

## Usage

Toujours activer le venv (ou utiliser `.venv/bin/python`) :

```bash
source .venv/bin/activate
```

### Push — sauvegarder sur OVH

1. Place tes fichiers dans `data/`
2. Lance :

```bash
python scripts/sync.py push
```

Comportement (incrémental) :

1. marqueurs `dossier/.ovhdir` pour l’arborescence
2. hash de chaque fichier local comparé à l’état (`.sync_state.json`)
3. upload seulement des fichiers **nouveaux ou modifiés**
4. suppression sur OVH des fichiers **effacés en local** (et orphelins)

Resync totale si besoin : `python scripts/sync.py push --full`

### Pull — restaurer en local

```bash
python scripts/sync.py pull
```

Comportement (incrémental) :

1. listing OVH + comparaison des hash (métadonnées / état local)
2. téléchargement seulement des fichiers **nouveaux ou modifiés**
3. suppression en local des fichiers **absents d’OVH**
4. dossiers recréés via les marqueurs `.ovhdir`

Resync totale : `python scripts/sync.py pull --full`

### Scripts métier

Les scripts qui traitent le contenu de `data/` vivent **dans** `data/scripts/` (chiffrés et synchronisés comme le reste). Ils ne sont pas versionnés dans git.

Après un `pull` (ou en local) :

```bash
python data/scripts/<script>.py
```

## Structure

```text
asclepios/
├── .env                 # secrets (non versionné)
├── .env.example
├── scripts/
│   └── sync.py          # seul script public : push / pull chiffré
├── requirements.txt
├── data/                # travail local + scripts métier (non versionné, sync OVH)
│   └── scripts/         # rapports / utilitaires liés aux données
└── README.md
```

## Sécurité

- Ne commit jamais `.env`
- Sauvegarde `ENCRYPTION_KEY` hors du projet (gestionnaire de mots de passe)
- Sans cette clé, les données sur OVH sont irrécupérables
- Le contenu de `data/` (y compris les scripts métier) n’est pas dans git : le dépôt public ne révèle pas la nature des données
- `push` et `pull` sont destructifs sur leur cible respective (remote ou `data/`) : une seule « vérité » à la fois
