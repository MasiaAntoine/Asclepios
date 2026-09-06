# Vault Asclepios

Le dossier `vault/` (ex-`data/`) est la source de vérité locale. Chaque fichier est chiffré puis synchronisé vers OVH. Les conventions détaillées vivent aussi dans `vault/README.md` (syncé avec le vault).

## Arborescence

```text
vault/
├── identite/          profil.json, photo, signature
├── mutuelle/          cartes, contrat, notice
├── assistant/
│   ├── personality.md
│   ├── rapport-template.md
│   └── chats/         conversations IA
├── suivi/             poids.csv, labs.csv, traitements.json, configs
├── humains/
│   ├── personnes/     famille / entourage / animaux  prenom-nom.md
│   ├── relations/     dossiers relationnels  prenom-nom.md
│   ├── medecins/      doctors.json
│   └── photos/        toutes les photos (même stem que la fiche)
├── medicaments/       fiches Markdown
├── ordonnances/       PDF  YYYY-MM-DD_Prescripteur[_Type].pdf
├── prise-de-sang/     PDF  YYYY-MM-DD_Labo.pdf
├── rapports/          YYYY-MM-DD-slug.md
├── recits/            même convention que rapports
├── fonts/             polices PDF
├── scripts/           générateurs / parseurs
└── cache/             local only (agenda iCal) — jamais syncé
```

Chemins toujours relatifs au vault : `identite/profil.json`, `humains/photos/eva-masia.jpg`, `humains/personnes/eva-masia.md`.

## Non synchronisé

- `cache/`
- `.cache/` (parse PDF)
- `__pycache__/`, `.DS_Store`
