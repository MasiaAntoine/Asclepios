# Persistance des propositions d'édition

## Principe

Les propositions d'édition générées par l'IA sont maintenant **sauvegardées dans l'historique de la conversation** et persistent après un refresh de la page.

## Fonctionnement

### 1. Création de la proposition

Quand l'IA génère une proposition d'édition :

```json
{
  "path": "relations/noemie-lacour.md",
  "description": "Ajout d'un texte de test",
  "old_string": "texte existant...",
  "new_string": "texte modifié...",
  "status": "pending",
  "created_at": "2026-08-30T18:07:23Z"
}
```

**Champs :**
- `path`, `description`, `old_string`, `new_string` : la proposition elle-même
- `status` : `"pending"` (en attente), `"applied"` (appliquée), `"rejected"` (refusée)
- `created_at` : timestamp de création
- `updated_at` : timestamp de dernière modification du statut (ajouté lors de l'action)

### 2. Sauvegarde dans le chat

La proposition est sauvegardée dans le message assistant :

```json
{
  "id": "a-abc123",
  "role": "assistant",
  "content": "Voici la proposition...",
  "created_at": "2026-08-30T18:07:23Z",
  "edit_proposals": [
    {
      "path": "relations/noemie-lacour.md",
      "description": "...",
      "old_string": "...",
      "new_string": "...",
      "status": "pending"
    }
  ]
}
```

**Fichier** : `data/chats/{conversation-id}.json`

### 3. Actions utilisateur

**Appliquer la modification :**
1. Clic sur "Appliquer"
2. API : `POST /api/data/apply-edit` → modifie le fichier + push OVH
3. API : `POST /api/data/update-edit-status` → met à jour `status: "applied"` dans le chat
4. UI : affiche ✓ "Modification appliquée et synchronisée"

**Refuser la modification :**
1. Clic sur "Refuser"
2. API : `POST /api/data/update-edit-status` → met à jour `status: "rejected"` dans le chat
3. UI : affiche ✗ "Modification refusée"

### 4. Chargement d'une conversation existante

Quand tu ouvres une conversation :
1. API : `GET /api/chats/{id}` → renvoie tous les messages avec leurs `edit_proposals`
2. Frontend : affiche chaque proposition avec son état sauvegardé
3. Les propositions **appliquées** ou **refusées** restent visibles mais en lecture seule

## Flux complet

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Utilisateur : "Ajoute coucou dans le dossier de Noémie" │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. IA génère une réponse avec un bloc ```json:edit```      │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Backend extrait la proposition                           │
│    - Ajoute status: "pending"                               │
│    - Ajoute created_at                                      │
│    - Sauvegarde dans data/chats/{id}.json                   │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Frontend affiche le composant EditProposal               │
│    - Diff coloré                                            │
│    - Boutons Appliquer / Refuser                            │
└─────────────────────────────────────────────────────────────┘
                           │
                    ┌──────┴──────┐
                    ▼             ▼
         ┌──────────────┐  ┌──────────────┐
         │  Appliquer   │  │   Refuser    │
         └──────────────┘  └──────────────┘
                │                  │
                ▼                  ▼
    ┌──────────────────┐  ┌──────────────────┐
    │ Modifie fichier  │  │ Marque "rejected"│
    │ Push OVH         │  │ dans le chat     │
    │ Marque "applied" │  └──────────────────┘
    └──────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Refresh page → proposition toujours visible avec statut  │
└─────────────────────────────────────────────────────────────┘
```

## API

### POST `/api/data/apply-edit`

Applique la modification au fichier et synchronise avec OVH.

**Request :**
```json
{
  "path": "relations/noemie-lacour.md",
  "old_string": "texte exact existant",
  "new_string": "texte modifié"
}
```

**Response :** SSE stream
```
data: ✓ Fichier modifié : relations/noemie-lacour.md
data: ▶  Sync
data: Push OVH (nouveaux / modifiés uniquement)…
data: [DONE]
```

### POST `/api/data/update-edit-status`

Met à jour le statut d'une proposition dans l'historique.

**Request :**
```json
{
  "conversation_id": "20260830-180723-abc123",
  "message_id": "a-abc123",
  "proposal_index": 0,
  "status": "applied"
}
```

**Response :**
```json
{
  "ok": true,
  "status": "applied"
}
```

**Statuts valides :** `"pending"`, `"applied"`, `"rejected"`

## Avantages

✅ **Historique complet** : toutes les modifications proposées sont tracées
✅ **Reproductibilité** : on peut voir ce qui a été appliqué ou refusé
✅ **Persistance** : survive au refresh de la page
✅ **Synchronisation** : push OVH automatique après application
✅ **Lecture seule** : les propositions appliquées/refusées ne peuvent plus être modifiées

## Cas d'usage

### Scénario 1 : Modification simple

```
Tu : "Ajoute une note dans le dossier de Noémie"
IA : [propose une modification]
Tu : [clique Appliquer]
→ Fichier modifié + sync OVH + status "applied" sauvegardé
```

### Scénario 2 : Refus puis retry

```
Tu : "Ajoute X dans le dossier"
IA : [propose modification A]
Tu : [clique Refuser]
→ Status "rejected" sauvegardé

Tu : "Non, plutôt Y"
IA : [propose modification B]
Tu : [clique Appliquer]
→ Modification B appliquée
```

### Scénario 3 : Historique après refresh

```
[Tu as appliqué 3 modifications hier]
[Tu refresh la page aujourd'hui]
→ Les 3 propositions sont visibles avec "✓ Modification appliquée"
→ Tu peux revoir le diff pour chacune
→ Boutons désactivés (déjà traitées)
```

## Limitations actuelles

- Pas d'annulation (undo) d'une modification appliquée
- Pas de réapplication d'une modification refusée (il faut redemander à l'IA)
- Les propositions ne sont pas versionnées (un seul état par proposition)

## Données stockées

**Taille** : ~500 bytes par proposition (dépend de la taille du diff)

**Exemple** :
- 1 conversation avec 10 messages
- 3 propositions d'édition
- Taille totale du chat : ~15 KB

**Nettoyage** : aucun (toutes les propositions sont conservées indéfiniment)

## Sécurité

- Les propositions sont stockées dans `data/chats/` (chiffré lors du push OVH)
- Seul l'endpoint `/api/data/update-edit-status` peut modifier le statut
- Pas de modification directe du contenu de la proposition après création
- Validation côté serveur : statut doit être `pending`, `applied` ou `rejected`

## Debug

### Voir les propositions sauvegardées

```bash
cd data/chats
cat {conversation-id}.json | jq '.messages[] | select(.edit_proposals != null) | .edit_proposals'
```

### Vérifier le statut

```bash
# Compter les propositions par statut
cat {id}.json | jq '[.messages[].edit_proposals[]?.status] | group_by(.) | map({status: .[0], count: length})'
```

### Supprimer une proposition (manuellement)

```bash
# Éditer le fichier JSON et retirer la proposition de l'array edit_proposals
# Puis relancer l'API pour recharger
```

## Prochaines améliorations possibles

- [ ] Badge "X modifications appliquées" dans la liste des conversations
- [ ] Filtre pour voir uniquement les conversations avec edits
- [ ] Export des modifications appliquées (changelog)
- [ ] Undo d'une modification récente
- [ ] Diff avant/après pour voir l'impact réel de la modification
