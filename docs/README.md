# Documentation Asclepios

Documentation technique et guides d'utilisation pour le dossier médical personnel Asclepios.

## Table des matières

### Fonctionnalités

- **[Édition assistée par l'IA](edition-assistee.md)** — Permet à l'assistant Asclepios de proposer des modifications aux fichiers `data/` avec validation utilisateur
- **[Persistance des propositions d'édition](persistance-edit-proposals.md)** — Historique complet des modifications proposées, appliquées et refusées
- **[Personnalité conversationnelle](personnalite-conversationnelle.md)** — Couche indépendante qui définit *comment* Asclepios parle (empathie sans complaisance, capacité à challenger, gestion de l'incertitude…)

### UI/UX

- **[Améliorations d'interface](ui-improvements.md)** — Dialog de confirmation personnalisée, design system, composants réutilisables

### Architecture

*(À venir : architecture générale, flux de données, sécurité)*

### API

*(À venir : documentation complète des endpoints REST et SSE)*

### Développement

*(À venir : setup local, tests, contribution)*

## Liens rapides

- **Projet** : `/Users/antoine/Projects/projet_perso/asclepios`
- **API** : `api/main.py` (FastAPI)
- **Frontend** : `app/` (Vue 3 + TypeScript)
- **Données** : `data/` (vault local chiffré + sync OVH S3)
- **Scripts** : `data/scripts/` et `scripts/`

## Contact

Antoine — projet personnel médical 2024-2026
