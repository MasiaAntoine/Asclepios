#!/usr/bin/env python3
"""Sync chiffré incrémental <-> OVH Object Storage (S3)."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = ROOT / ".sync_state.json"
MARKER = b"MEDENC2\n"
# Marqueurs d'ancienne génération — ignorés / nettoyés, plus synchronisés.
LEGACY_DIR_MARKER = ".ovhdir"
SKIP_NAMES = {".DS_Store", ".vault_structure.json", "__pycache__", LEGACY_DIR_MARKER}
META_SHA = "sha256"

# Dossiers attendus même vides (créés localement, pas stockés sur OVH).
CANONICAL_DIRS = (
    "prise-de-sang",
    "medicaments",
    "rapports",
    "traumas",
    "chats",
    "scripts",
)


def load_config() -> dict:
    load_dotenv(ROOT / ".env")
    required = [
        "OVH_ACCESS_KEY",
        "OVH_SECRET_KEY",
        "OVH_BUCKET",
        "OVH_ENDPOINT",
        "OVH_REGION",
        "ENCRYPTION_KEY",
    ]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        sys.exit(f"Variables manquantes dans .env : {', '.join(missing)}")

    data_dir = ROOT / os.getenv("LOCAL_DATA_DIR", "data")
    return {
        "access_key": os.environ["OVH_ACCESS_KEY"],
        "secret_key": os.environ["OVH_SECRET_KEY"],
        "bucket": os.environ["OVH_BUCKET"],
        "endpoint": os.environ["OVH_ENDPOINT"].rstrip("/"),
        "region": os.environ["OVH_REGION"],
        "prefix": os.getenv("OVH_PREFIX", "vault").strip("/"),
        "data_dir": data_dir,
        "fernet": Fernet(os.environ["ENCRYPTION_KEY"].encode()),
    }


def s3_client(cfg: dict):
    return boto3.client(
        "s3",
        aws_access_key_id=cfg["access_key"],
        aws_secret_access_key=cfg["secret_key"],
        endpoint_url=cfg["endpoint"],
        region_name=cfg["region"],
        config=Config(
            signature_version="s3v4",
            connect_timeout=15,
            read_timeout=120,
            retries={"max_attempts": 3, "mode": "standard"},
        ),
    )


def remote_key(cfg: dict, relative: str) -> str:
    digest = hashlib.sha256(relative.encode()).hexdigest()
    return f"{cfg['prefix']}/{digest}.enc"


def file_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encode_blob(fernet: Fernet, relative: str, data: bytes) -> bytes:
    path_bytes = relative.encode()
    payload = len(path_bytes).to_bytes(4, "big") + path_bytes + data
    return MARKER + fernet.encrypt(payload)


def decode_blob(fernet: Fernet, data: bytes) -> tuple[str, bytes]:
    if data.startswith(MARKER):
        plain = fernet.decrypt(data[len(MARKER) :])
        n = int.from_bytes(plain[:4], "big")
        relative = plain[4 : 4 + n].decode()
        return relative, plain[4 + n :]

    if data.startswith(b"MEDENC1\n"):
        return "", fernet.decrypt(data[len(b"MEDENC1\n") :])

    raise ValueError("Objet distant non reconnu (pas chiffré par ce script)")


def load_state() -> dict:
    """État local : fichiers connus (chemin → clé S3 + hash contenu)."""
    empty = {"version": 2, "files": {}}
    if not STATE_FILE.exists():
        return empty
    try:
        raw = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return empty

    # Migration ancien format {path_to_key: {...}}
    if "files" not in raw and "path_to_key" in raw:
        files = {
            path: {"key": key, "sha256": ""}
            for path, key in raw.get("path_to_key", {}).items()
        }
        return {"version": 2, "files": files}

    if "files" not in raw or not isinstance(raw["files"], dict):
        return empty
    return {"version": 2, "files": raw["files"]}


def save_state(state: dict) -> None:
    payload = {"version": 2, "files": state.get("files", {})}
    STATE_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def _is_skipped(path: Path) -> bool:
    if path.name in SKIP_NAMES:
        return True
    return any(part in SKIP_NAMES or part == "__pycache__" for part in path.parts)


def ensure_canonical_dirs(data_dir: Path) -> None:
    """Crée les dossiers métier attendus (même vides)."""
    data_dir.mkdir(parents=True, exist_ok=True)
    for rel in CANONICAL_DIRS:
        (data_dir / rel).mkdir(parents=True, exist_ok=True)


def purge_legacy_markers(data_dir: Path) -> int:
    """Supprime les anciens .ovhdir / .vault_structure.json locaux."""
    if not data_dir.exists():
        return 0
    removed = 0
    legacy_manifest = data_dir / ".vault_structure.json"
    if legacy_manifest.exists():
        legacy_manifest.unlink()
        removed += 1
    for path in data_dir.rglob(LEGACY_DIR_MARKER):
        if path.is_file():
            path.unlink()
            removed += 1
    return removed


def dirs_from_paths(relative_paths: set[str] | list[str]) -> set[str]:
    """Déduit l'arborescence à partir des chemins de fichiers."""
    dirs: set[str] = set(CANONICAL_DIRS)
    for relative in relative_paths:
        parent = Path(relative).parent
        if parent == Path("."):
            continue
        for i in range(1, len(parent.parts) + 1):
            dirs.add(Path(*parent.parts[:i]).as_posix())
    return dirs


def materialize_dirs(data_dir: Path, relative_paths: set[str] | list[str]) -> None:
    """Recrée les dossiers à partir des chemins de fichiers (+ canoniques)."""
    data_dir.mkdir(parents=True, exist_ok=True)
    for rel in sorted(dirs_from_paths(relative_paths)):
        (data_dir / rel).mkdir(parents=True, exist_ok=True)


def iter_local_files(data_dir: Path):
    if not data_dir.exists():
        data_dir.mkdir(parents=True, exist_ok=True)
        return
    for path in sorted(data_dir.rglob("*")):
        if not path.is_file() or _is_skipped(path):
            continue
        yield path, path.relative_to(data_dir).as_posix()


def scan_local(data_dir: Path) -> dict[str, dict]:
    """relative → {path, sha256, data}."""
    out: dict[str, dict] = {}
    for path, relative in iter_local_files(data_dir):
        data = path.read_bytes()
        out[relative] = {
            "path": path,
            "sha256": file_sha256(data),
            "data": data,
        }
    return out


def list_remote_objects(client, cfg: dict) -> list[str]:
    prefix = f"{cfg['prefix']}/"
    keys: list[str] = []
    token = None
    while True:
        kwargs = {"Bucket": cfg["bucket"], "Prefix": prefix}
        if token:
            kwargs["ContinuationToken"] = token
        resp = client.list_objects_v2(**kwargs)
        for obj in resp.get("Contents", []):
            keys.append(obj["Key"])
        if not resp.get("IsTruncated"):
            break
        token = resp.get("NextContinuationToken")
    return keys


def delete_remote_keys(client, cfg: dict, keys: list[str]) -> int:
    if not keys:
        return 0
    deleted = 0
    for i in range(0, len(keys), 1000):
        batch = [{"Key": k} for k in keys[i : i + 1000]]
        client.delete_objects(
            Bucket=cfg["bucket"],
            Delete={"Objects": batch, "Quiet": True},
        )
        deleted += len(batch)
    return deleted


def upload_file(client, cfg: dict, relative: str, data: bytes, sha: str) -> str:
    key = remote_key(cfg, relative)
    blob = encode_blob(cfg["fernet"], relative, data)
    client.put_object(
        Bucket=cfg["bucket"],
        Key=key,
        Body=blob,
        ContentType="application/octet-stream",
        ServerSideEncryption="AES256",
        Metadata={META_SHA: sha},
    )
    return key


def head_remote_sha(client, cfg: dict, key: str) -> str | None:
    try:
        resp = client.head_object(Bucket=cfg["bucket"], Key=key)
    except ClientError:
        return None
    meta = resp.get("Metadata") or {}
    # boto3 lowercases metadata keys
    return meta.get(META_SHA) or meta.get("Sha256")


def remove_empty_dirs(data_dir: Path) -> None:
    """Supprime les dossiers vides (hors racine), du plus profond au plus haut."""
    if not data_dir.exists():
        return
    dirs = sorted(
        (p for p in data_dir.rglob("*") if p.is_dir()),
        key=lambda p: len(p.parts),
        reverse=True,
    )
    for d in dirs:
        try:
            next(d.iterdir())
        except StopIteration:
            d.rmdir()


def cmd_push(cfg: dict, *, full: bool = False) -> None:
    data_dir: Path = cfg["data_dir"]
    data_dir.mkdir(parents=True, exist_ok=True)
    purged = purge_legacy_markers(data_dir)
    if purged:
        print(f"Nettoyage marqueurs legacy : {purged} fichier(s)")
    ensure_canonical_dirs(data_dir)

    client = s3_client(cfg)
    local = scan_local(data_dir)
    tree = dirs_from_paths(local)
    print(f"Arborescence déduite des fichiers : {len(tree)} dossier(s)")

    state = load_state()
    old_files: dict = state.get("files", {})

    if full:
        remote_keys = list_remote_objects(client, cfg)
        n = delete_remote_keys(client, cfg, remote_keys)
        print(
            f"Mode --full : remote vidé ({n} objet(s)), "
            "tous les fichiers locaux seront renvoyés "
            "(ignore les hash — utiliser `push` sans --full pour l'incrémental)."
        )
        old_files = {}

    uploaded = 0
    skipped = 0
    new_state_files: dict[str, dict] = {}

    for relative, info in sorted(local.items()):
        sha = info["sha256"]
        prev = old_files.get(relative) or {}
        unchanged = (
            not full
            and prev.get("sha256") == sha
            and prev.get("key") == remote_key(cfg, relative)
        )
        if unchanged:
            # Vérifie que l'objet existe encore côté OVH
            try:
                client.head_object(Bucket=cfg["bucket"], Key=prev["key"])
                new_state_files[relative] = {"key": prev["key"], "sha256": sha}
                skipped += 1
                continue
            except ClientError:
                pass  # re-upload

        action = "nouveau" if relative not in old_files else "modifié"
        print(f"↑ {relative}  ({action})…", flush=True)
        key = upload_file(client, cfg, relative, info["data"], sha)
        new_state_files[relative] = {"key": key, "sha256": sha}
        uploaded += 1
        # Sauvegarde progressive : un Ctrl+C ne force pas à tout renvoyer
        save_state(
            {
                "files": {
                    **{p: old_files[p] for p in local if p in old_files},
                    **new_state_files,
                }
            }
        )

    # Suppressions distantes : plus présents en local (y compris anciens .ovhdir)
    expected_keys = {remote_key(cfg, rel) for rel in local}
    remote_keys = set(list_remote_objects(client, cfg))
    to_delete = sorted(remote_keys - expected_keys)
    key_to_old_path = {
        info["key"]: path
        for path, info in old_files.items()
        if info.get("key")
    }

    for key in to_delete:
        relative = key_to_old_path.get(key)
        if relative:
            print(f"× {relative}  (supprimé en local → retrait OVH)")
        else:
            print(f"× {key}  (orphelin distant)")

    deleted = delete_remote_keys(client, cfg, to_delete)

    save_state({"files": new_state_files})
    print(
        f"Push terminé : {uploaded} envoyé(s), {skipped} inchangé(s), "
        f"{deleted} supprimé(s) sur OVH."
    )


def cmd_pull(cfg: dict, *, full: bool = False) -> None:
    client = s3_client(cfg)
    data_dir: Path = cfg["data_dir"]
    data_dir.mkdir(parents=True, exist_ok=True)
    state = load_state()
    old_files: dict = state.get("files", {})
    key_to_path = {
        info["key"]: path
        for path, info in old_files.items()
        if info.get("key")
    }

    if full:
        # Comportement destructif local puis restauration complète
        for child in list(data_dir.iterdir()):
            if child.is_file() or child.is_symlink():
                child.unlink()
            elif child.is_dir():
                shutil.rmtree(child)
        print("Mode --full : data/ local vidé.")
        local = {}
    else:
        local = scan_local(data_dir)

    remote_keys = list_remote_objects(client, cfg)
    new_state_files: dict[str, dict] = {}
    remote_paths: set[str] = set()

    downloaded = 0
    skipped = 0
    failed = 0

    for key in remote_keys:
        remote_sha = None if full else head_remote_sha(client, cfg, key)
        relative = key_to_path.get(key)

        # Anciens marqueurs .ovhdir : ignorés (retirés au prochain push)
        if relative and Path(relative).name == LEGACY_DIR_MARKER:
            continue

        # Raccourci : chemin connu + hash local identique au remote
        if (
            not full
            and relative
            and remote_sha
            and relative in local
            and local[relative]["sha256"] == remote_sha
        ):
            new_state_files[relative] = {"key": key, "sha256": remote_sha}
            remote_paths.add(relative)
            skipped += 1
            continue

        # Téléchargement nécessaire
        resp = client.get_object(Bucket=cfg["bucket"], Key=key)
        blob = resp["Body"].read()
        meta = resp.get("Metadata") or {}
        remote_sha = meta.get(META_SHA) or remote_sha

        try:
            decoded_rel, plain = decode_blob(cfg["fernet"], blob)
        except (InvalidToken, ValueError) as exc:
            print(f"! Échec déchiffrement {key}: {exc}")
            failed += 1
            continue

        relative = decoded_rel or relative
        if not relative:
            print(f"! Ignoré (chemin inconnu) : {key}")
            failed += 1
            continue

        if Path(relative).name == LEGACY_DIR_MARKER:
            continue

        sha = remote_sha or file_sha256(plain)
        remote_paths.add(relative)

        dest = data_dir / relative
        if (
            not full
            and dest.exists()
            and dest.is_file()
            and file_sha256(dest.read_bytes()) == file_sha256(plain)
        ):
            new_state_files[relative] = {"key": key, "sha256": sha}
            skipped += 1
            continue

        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(plain)
        new_state_files[relative] = {"key": key, "sha256": file_sha256(plain)}
        action = "nouveau" if relative not in local else "modifié"
        print(f"↓ {relative}  ({action})")
        downloaded += 1

    # Suppressions locales : plus présents sur OVH
    removed = 0
    if not full:
        for relative in sorted(set(local) - remote_paths):
            path = data_dir / relative
            if path.exists():
                path.unlink()
                print(f"× {relative}  (absent d'OVH → retiré en local)")
                removed += 1

    # Arborescence = chemins des fichiers distants + dossiers canoniques
    materialize_dirs(data_dir, remote_paths)
    purge_legacy_markers(data_dir)
    if not full:
        remove_empty_dirs(data_dir)
        ensure_canonical_dirs(data_dir)

    save_state({"files": new_state_files})
    print(
        f"Pull terminé : {downloaded} reçu(s), {skipped} inchangé(s), "
        f"{removed} supprimé(s) en local, {failed} échec(s)."
    )


def auto_push_after_pdf(*, full: bool = False) -> bool:
    """
    Push incrémental de data/ vers OVH.
    À appeler après toute génération de PDF.
    Retourne True si le push a réussi.
    """
    print("— Push OVH automatique —")
    try:
        cfg = load_config()
        cmd_push(cfg, full=full)
        return True
    except SystemExit as exc:
        print(f"! Push OVH annulé : {exc}")
        return False
    except Exception as exc:
        print(f"! Push OVH échoué : {exc}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync chiffré incrémental vers OVH Object Storage",
    )
    parser.add_argument(
        "command",
        choices=["push", "pull"],
        help="push: data→OVH | pull: OVH→data",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Resynchronisation complète (wipe puis tout renvoyer / tout retélécharger)",
    )
    args = parser.parse_args()

    cfg = load_config()
    if args.command == "push":
        cmd_push(cfg, full=args.full)
    else:
        cmd_pull(cfg, full=args.full)


if __name__ == "__main__":
    main()
