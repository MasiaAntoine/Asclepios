# Test — Persistance des propositions d'édition

Guide de test pour vérifier que les propositions sont bien sauvegardées et persistent après refresh.

## Scénario 1 : Création et application

### Étapes

1. **Ouvre le chat Asclepios**
   - Va sur `http://localhost:5173/assistant`
   - Démarre une nouvelle conversation

2. **Demande une modification**
   ```
   Ajoute "coucou" à la fin du dossier de Noémie
   ```

3. **Vérifie la proposition**
   - ✅ Composant EditProposal s'affiche
   - ✅ Diff visible avec les changements
   - ✅ Boutons "Refuser" et "Appliquer" présents

4. **Applique la modification**
   - Clique sur "Appliquer"
   - ✅ Spinner s'affiche
   - ✅ Message "✓ Modification appliquée et synchronisée"
   - ✅ Boutons disparaissent (remplacés par le statut)

5. **Vérifie le fichier**
   ```bash
   tail data/relations/noemie-lacour.md
   # Doit contenir "coucou" à la fin
   ```

6. **Vérifie la sauvegarde dans le chat**
   ```bash
   # Trouve le dernier chat créé
   ls -lt data/chats/*.json | head -1
   
   # Lis son contenu
   cat data/chats/{id}.json | jq '.messages[-1].edit_proposals'
   ```
   
   **Résultat attendu :**
   ```json
   [
     {
       "path": "relations/noemie-lacour.md",
       "description": "...",
       "old_string": "...",
       "new_string": "...",
       "status": "applied",
       "created_at": "2026-08-30T...",
       "updated_at": "2026-08-30T..."
     }
   ]
   ```

7. **Refresh la page** (F5)
   - ✅ Conversation toujours ouverte
   - ✅ Proposition visible avec "✓ Modification appliquée et synchronisée"
   - ✅ Boutons désactivés (déjà traitée)
   - ✅ Diff toujours visible

## Scénario 2 : Refus d'une modification

### Étapes

1. **Nouvelle modification**
   ```
   Ajoute "test refus" dans le dossier de Cécilia
   ```

2. **Refuse la modification**
   - Clique sur "Refuser"
   - ✅ Message "✗ Modification refusée"
   - ✅ Boutons disparaissent

3. **Vérifie le fichier**
   ```bash
   cat data/relations/cecilia.md | grep "test refus"
   # Ne doit PAS trouver le texte
   ```

4. **Vérifie la sauvegarde**
   ```bash
   cat data/chats/{id}.json | jq '.messages[-1].edit_proposals[0].status'
   # Doit retourner "rejected"
   ```

5. **Refresh la page**
   - ✅ Proposition visible avec "✗ Modification refusée"
   - ✅ Pas de boutons

## Scénario 3 : Multiples propositions

### Étapes

1. **Demande plusieurs modifications**
   ```
   Mets à jour les dossiers de Noémie et Cécilia : ajoute une note dans chaque
   ```

2. **L'IA peut générer 2 propositions**
   - ✅ Deux composants EditProposal affichés
   - ✅ Un par fichier

3. **Actions différentes**
   - Applique la première
   - Refuse la seconde

4. **Vérifie les statuts**
   ```bash
   cat data/chats/{id}.json | jq '.messages[-1].edit_proposals[].status'
   # Doit retourner :
   # "applied"
   # "rejected"
   ```

5. **Refresh et vérifie**
   - ✅ Première proposition : appliquée
   - ✅ Seconde proposition : refusée

## Scénario 4 : Historique d'une conversation

### Étapes

1. **Ouvre une conversation existante**
   - Clique sur une conversation dans la liste

2. **Scroll vers le haut**
   - Cherche d'anciennes propositions d'édition

3. **Vérifie l'affichage**
   - ✅ Toutes les propositions sont visibles
   - ✅ Leur statut est correct (appliquée/refusée)
   - ✅ Les diffs sont affichés
   - ✅ Pas de boutons (lecture seule)

## Scénario 5 : Sync OVH

### Étapes

1. **Applique une modification**
   - Comme dans Scénario 1

2. **Vérifie les logs backend**
   ```bash
   # Terminal API
   # Cherche :
   data: ✓ Fichier modifié : relations/noemie-lacour.md
   data: ▶  Sync
   data: Push OVH (nouveaux / modifiés uniquement)…
   data: [DONE]
   ```

3. **Vérifie le fichier local**
   ```bash
   git status
   # Doit montrer : modified: data/relations/noemie-lacour.md
   ```

4. **Vérifie le sync state**
   ```bash
   cat .sync_state.json | jq '.["data/relations/noemie-lacour.md"]'
   # Doit avoir un nouveau hash
   ```

## Tests d'intégration

### Test API : update-edit-status

**Request :**
```bash
curl -X POST http://localhost:8000/api/data/update-edit-status \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "20260830-180723-abc123",
    "message_id": "a-def456",
    "proposal_index": 0,
    "status": "applied"
  }'
```

**Response attendue :**
```json
{
  "ok": true,
  "status": "applied"
}
```

### Test erreurs

**Statut invalide :**
```bash
curl -X POST http://localhost:8000/api/data/update-edit-status \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "...",
    "message_id": "...",
    "proposal_index": 0,
    "status": "invalid"
  }'
```

**Résultat attendu :** `400 Bad Request`

**Message introuvable :**
```bash
curl -X POST http://localhost:8000/api/data/update-edit-status \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "...",
    "message_id": "inexistant",
    "proposal_index": 0,
    "status": "applied"
  }'
```

**Résultat attendu :** `404 Not Found`

## Validation du format JSON

### Structure attendue dans le chat

```json
{
  "id": "20260830-180723-abc123",
  "title": "Discussion sur Noémie",
  "created_at": "2026-08-30T18:07:23Z",
  "updated_at": "2026-08-30T18:10:45Z",
  "messages": [
    {
      "id": "u-123",
      "role": "user",
      "content": "Ajoute coucou...",
      "created_at": "2026-08-30T18:07:23Z"
    },
    {
      "id": "a-456",
      "role": "assistant",
      "content": "Voici la proposition...",
      "created_at": "2026-08-30T18:07:25Z",
      "edit_proposals": [
        {
          "path": "relations/noemie-lacour.md",
          "description": "Ajout texte de test",
          "old_string": "...",
          "new_string": "...",
          "status": "applied",
          "created_at": "2026-08-30T18:07:25Z",
          "updated_at": "2026-08-30T18:08:12Z"
        }
      ]
    }
  ],
  "report_id": null
}
```

### Validation

```bash
# Valider que tous les chats sont du JSON valide
for f in data/chats/*.json; do
  jq empty "$f" 2>&1 || echo "❌ Invalid JSON: $f"
done

# Compter les propositions par statut (tous les chats)
cat data/chats/*.json | jq -s '[.[].messages[].edit_proposals[]?.status] | group_by(.) | map({status: .[0], count: length})'
```

## Checklist de validation

- [ ] Les propositions sont sauvegardées dans le JSON du chat
- [ ] Le statut initial est "pending"
- [ ] "Appliquer" → status "applied" + fichier modifié + push OVH
- [ ] "Refuser" → status "rejected" + fichier non modifié
- [ ] Refresh page → propositions toujours visibles avec bon statut
- [ ] Ouverture d'une vieille conversation → historique complet
- [ ] Plusieurs propositions dans un message → toutes sauvegardées
- [ ] Timestamps created_at et updated_at présents
- [ ] API /update-edit-status fonctionne
- [ ] Erreurs (404, 400) gérées proprement
- [ ] JSON valide après chaque modification

## Debug

### Propositions manquantes après refresh

**Symptôme :** Propositions visibles en live mais pas après refresh

**Vérifications :**
1. Check backend logs : "Réponse enregistrée dans le vault"
2. Check fichier JSON : `cat data/chats/{id}.json | jq '.messages[-1]'`
3. Check que `edit_proposals` est présent
4. Check que le frontend charge bien toutes les propriétés du message

**Solution probable :** Le backend ne sauvegarde pas les propositions → vérifier ligne 1710 de `api/main.py`

### Statut ne se met pas à jour

**Symptôme :** Clic sur Appliquer/Refuser mais statut reste "pending" après refresh

**Vérifications :**
1. Check console navigateur : erreurs d'appel API ?
2. Check logs backend : endpoint `/update-edit-status` appelé ?
3. Check fichier JSON : `status` a changé ?

**Solution probable :** Props `conversationId`, `messageId`, `proposalIndex` non passées au composant EditProposal

### Diff illisible

**Symptôme :** Diff trop long ou mal formaté

**Solution :** L'IA doit utiliser un `old_string` plus court et ciblé (50-200 caractères autour de la modification)

## Métriques

Pour mesurer l'utilisation de la fonctionnalité :

```bash
# Nombre total de propositions
cat data/chats/*.json | jq '[.[].messages[].edit_proposals[]?] | length'

# Nombre par statut
cat data/chats/*.json | jq -s '
  [.[].messages[].edit_proposals[]?] 
  | group_by(.status) 
  | map({status: .[0].status, count: length})
'

# Taux d'application
cat data/chats/*.json | jq -s '
  [.[].messages[].edit_proposals[]?] 
  | {
      total: length,
      applied: [.[] | select(.status == "applied")] | length,
      rejected: [.[] | select(.status == "rejected")] | length,
      pending: [.[] | select(.status == "pending")] | length
    }
'
```

## Prochaines étapes

- [ ] Ajouter un badge "X edits appliqués" sur les conversations dans la sidebar
- [ ] Filtrer les conversations par "contient des edits"
- [ ] Exporter l'historique des edits en changelog
- [ ] Permettre de réappliquer une modification refusée
