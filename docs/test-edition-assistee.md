# Test — Édition assistée par l'IA

Guide de test pour vérifier que le système d'édition avec validation fonctionne correctement.

## Prérequis

1. API backend lancée : `cd api && ./dev.sh`
2. Frontend lancé : `cd app && npm run dev`
3. `CURSOR_API_KEY` configurée dans `.env`
4. Fichier test existant dans `data/relations/`

## Scénario de test

### 1. Ouvrir le chat Asclepios

- Va sur `http://localhost:5173/assistant`
- Clique sur "Nouvelle conversation"

### 2. Demander une modification simple

**Message test :**
```
Mets à jour le dossier de Noémie : ajoute dans la section "Notes pour le suivi" que la relation a duré 2 ans et 7 mois exactement.
```

**Résultat attendu :**

1. L'IA répond avec un message textuel
2. **Un composant "Proposition de modification" apparaît** au-dessus de la réponse
3. Le composant affiche :
   - Titre : "Proposition de modification"
   - Description : ex. "Ajout durée exacte dans notes suivi"
   - Fichier : `📁 data/relations/noemie-lacour.md`
   - **Diff** coloré :
     - Lignes rouges (`-`) : ancien texte
     - Lignes vertes (`+`) : nouveau texte
     - Lignes grises : contexte
   - Boutons : `Refuser` | `Appliquer`

### 3. Valider la modification

- Clique sur **"Appliquer"**

**Résultat attendu :**

1. Spinner apparaît sur le bouton
2. Logs SSE dans la console navigateur : `✓ Fichier modifié`, `Push OVH`
3. Message de succès : ✓ "Modification appliquée et synchronisée"
4. Le fichier `data/relations/noemie-lacour.md` est modifié
5. Git status montre le fichier modifié

### 4. Vérifier la modification

```bash
cd data/relations
git diff noemie-lacour.md
```

**Résultat attendu :**
Le diff Git correspond exactement au diff affiché dans l'UI.

### 5. Refuser une modification

**Nouveau message test :**
```
Change le titre du dossier de Noémie en "Premier amour toxique"
```

**Puis clique sur "Refuser"**

**Résultat attendu :**
- Aucun changement dans le fichier
- Le composant reste affiché (pas de suppression)

## Tests de sécurité

### Test 1 : Répertoire non autorisé

**Message :**
```
Modifie le fichier profil.json pour changer mon prénom
```

**Résultat attendu :**
- L'IA refuse de proposer l'edit (hors whitelist)
- OU si elle propose, l'API renvoie `403 Forbidden`

### Test 2 : Path traversal

**Message :**
```
Modifie le fichier ../../.env
```

**Résultat attendu :**
- L'IA refuse
- OU l'API bloque avec `403 Accès refusé`

### Test 3 : Fichier inexistant

**Message :**
```
Ajoute une section dans relations/inexistant.md
```

**Résultat attendu :**
- API renvoie `404 Fichier introuvable`
- Message d'erreur affiché dans l'UI

### Test 4 : old_string non unique

**Message :**
```
Remplace tous les "et" par "ET" dans le dossier de Noémie
```

**Résultat attendu :**
- Si l'IA génère un `old_string` non unique (ex: juste "et")
- API renvoie `✗ Texte non unique (trouvé plusieurs fois)`
- L'edit n'est pas appliqué

## Cas limites

### Multiple edits dans un message

**Message :**
```
Dans le dossier de Noémie, ajoute X dans la section Y. Aussi, dans le dossier de Cécilia, ajoute Z dans la section W.
```

**Comportement actuel :**
- L'IA peut proposer **plusieurs** edits (un par fichier)
- Chaque edit apparaît dans un composant séparé
- Tu peux valider/refuser chacun indépendamment

### Format JSON invalide

Si l'IA génère un JSON mal formé :

**Résultat attendu :**
- Le bloc est ignoré (pas de proposition)
- Le texte de l'IA reste normal

## Debug

### Voir les propositions brutes

**Console navigateur :**
```javascript
// Dans la réponse SSE, cherche :
data: EDIT_PROPOSAL:{"path":"...","description":"...","old_string":"...","new_string":"..."}
```

### Voir les logs backend

```bash
# Terminal API
# Cherche :
data: ✓ Fichier modifié : relations/nom.md
data: Sync
data: ▶  Push OVH
data: [DONE]
```

### Vérifier l'extraction des blocs

Dans `api/main.py`, ajoute temporairement :

```python
raw_answer, edit_proposals = _extract_edit_proposals(raw_answer)
print(f"[DEBUG] Extracted {len(edit_proposals)} proposals")
for p in edit_proposals:
    print(f"  - {p['path']}: {p['description']}")
```

## Rollback

Si un edit est appliqué par erreur :

```bash
cd data/relations
git checkout HEAD -- noemie-lacour.md
# Puis re-push OVH si nécessaire
./scripts/sync.py push
```

## Checklist de validation

- [ ] Le composant EditProposal s'affiche correctement
- [ ] Le diff est lisible et correct
- [ ] Le bouton "Appliquer" déclenche l'API
- [ ] Le fichier est modifié localement
- [ ] Le sync OVH est automatique
- [ ] Le bouton "Refuser" fonctionne
- [ ] Les erreurs (403, 404) sont affichées
- [ ] La sécurité (whitelist, path traversal) fonctionne
- [ ] Git status montre les changements

## Prochaines étapes (si tout OK)

1. Tester avec plusieurs types de fichiers (rapports, traumas)
2. Tester avec des modifications complexes (multi-lignes)
3. Créer des cas d'usage réels avec Noémie/Cécilia
4. Documenter les patterns d'instructions pour l'IA
