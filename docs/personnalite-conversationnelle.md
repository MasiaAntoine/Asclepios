# Personnalité conversationnelle de l'agent

## Objectif

Séparer proprement **comment** Asclepios parle de **ce qu'il sait**. La couche
médicale (données, sécurité, outils, édition) reste dans `api/main.py`. La
personnalité conversationnelle vit dans une couche dédiée, éditable sans
toucher au code.

## Architecture

Deux couches indépendantes, concaténées au moment de construire le prompt :

```
┌─────────────────────────────────────────────────┐
│ COUCHE 1 — Moteur médical                       │
│ api/main.py :: _MEDICAL_SYSTEM                  │
│  • sécurité médicale                            │
│  • outils (édition validée, vision)             │
│  • règles données (contexte, historique)        │
└─────────────────────────────────────────────────┘
                       +
┌─────────────────────────────────────────────────┐
│ COUCHE 2 — Personnalité conversationnelle       │
│ api/conversation_behavior.py                    │
│  • détection type d'échange (heuristique)       │
│  • injection profil éditable                    │
│  • hint de style ciblé                          │
│                                                 │
│ data/assistant-personality.md   ← éditable      │
│  • 17 sections de règles conversationnelles     │
└─────────────────────────────────────────────────┘
                       ↓
              Prompt système final
```

## Fichiers

- `api/conversation_behavior.py` — logique Python (détection + assembly).
- `data/assistant-personality.md` — règles éditables. Chargé à chaque tour, donc
  aucune reprise du serveur nécessaire après modification.

## Types d'échange détectés

`detect_exchange_type(message)` classe le message en :

| Type         | Déclencheurs                                                    | Hint injecté                                      |
| ------------ | --------------------------------------------------------------- | ------------------------------------------------- |
| `sensible`   | mots-clés de détresse ou d'urgence                              | prio sécurité, ton calme, 3114 si pertinent       |
| `rumination` | temps de réponse, « ça veut dire quoi », « elle a vu »          | ne pas construire de longue liste d'hypothèses    |
| `conseil`    | « que faire », « je devrais », adressé (`?` ou « tu penses »)   | recommander clairement, pas 5 options équivalentes |
| `analyse`    | « pourquoi », « explique », adressé à l'agent                   | séparer faits / interprétation / incertitude      |
| `simple`     | par défaut, message court ou partage non-interrogatif           | réponse courte, pas d'analyse forcée              |

Les heuristiques sont volontairement **légères** : elles orientent le style,
elles ne remplacent pas le jugement du modèle. C'est le fichier
`assistant-personality.md` qui porte la logique fine.

## Comment modifier la personnalité

Deux options :

1. **Édition directe** : ouvrir `data/assistant-personality.md` dans l'IDE et
   modifier ; les changements sont pris en compte au tour suivant.
2. **Via Asclepios lui-même** : demander par exemple « tu es trop formel, adapte
   ta personnalité pour être plus détendue » ; l'agent proposera un diff que tu
   valides ou refuses, comme n'importe quel autre dossier `data/` (voir
   [Édition assistée](edition-assistee.md)).

## Priorité en cas de conflit

Si une règle de personnalité entre en conflit avec la sécurité médicale, la
sécurité médicale prime **toujours**. C'est explicitement rappelé dans
`_MEDICAL_SYSTEM` et dans la règle 16 du fichier personnalité.

## Cas particulier : sujets sensibles

Quand un message contient des signaux de détresse (suicide, « j'en peux plus »,
etc.), la couche personnalité bascule automatiquement en mode `sensible` :

- humour désactivé
- disclaimer médical redevient pertinent
- rappel du 3114 (écoute suicide France, 24/7)

Ce basculement est **additif** — les règles du profil éditable restent
appliquées, seul le hint de style change.

## Extensions futures possibles

- Faire varier le hint en fonction de l'humeur détectée dans l'historique récent.
- Ajouter un paramètre `medical_risk_level` provenant du reste de l'app (ex :
  résultats de biologie récents anormaux) pour ajuster le ton.
- Externaliser aussi le `_MEDICAL_SYSTEM` en fichier éditable si tu veux tout
  piloter depuis `data/`.
