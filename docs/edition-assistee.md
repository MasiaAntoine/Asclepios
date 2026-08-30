# Édition assistée par l'IA

## Principe

L'assistant Asclepios peut **proposer des modifications** aux fichiers dans `data/` (dossiers de relations, rapports, traumas) quand tu le lui demandes explicitement.

**Flow :**

1. Tu demandes : *"Mets à jour le dossier de Noémie, ajoute que..."*
2. L'assistant génère une **proposition de modification**
3. L'UI affiche un **diff** (avant/après) dans la conversation
4. Tu **valides** ou **refuses** la modification
5. Si validé : fichier modifié + sync OVH automatique

## Sécurité

- **Validation obligatoire** : aucune modification sans ton accord
- **Répertoires autorisés uniquement** : `relations/`, `personnes/`, `rapports/`, `traumas/`
- **Fichiers autorisés uniquement** : `.md` et `.json`
- **Protection path traversal** : impossible de sortir de `data/`
- **Unicité garantie** : `old_string` doit être unique dans le fichier

## Format pour l'IA

L'assistant utilise ce format JSON dans sa réponse :

```json:edit
{
  "path": "relations/noemie-lacour.md",
  "description": "Ajout détail sur la crise post-rupture",
  "old_string": "## Après / impact\n\n- **Énorme souffrance** après la rupture",
  "new_string": "## Après / impact\n\n- **Énorme souffrance** après la rupture\n- **Dépression d'environ 1 an**"
}
```

**Règles :**
- `path` : relatif à `data/` (ex: `relations/nom.md` ou `personnes/prenom-nom.md`)
- `description` : courte explication de la modification
- `old_string` : texte exact existant (minimum ~50 chars pour unicité)
- `new_string` : texte modifié

## Exemple d'utilisation

**Toi :**
> "Ajoute dans le dossier de Cécilia que la rupture a été difficile pour elle"

**Asclepios :**
> J'ai préparé une modification pour le dossier de Cécilia.
>
> [Affiche un diff avec le changement proposé]
>
> [Boutons : Appliquer | Refuser]

**Toi :** *[clique sur Appliquer]*

**Asclepios :**
> ✓ Modification appliquée et synchronisée

## API

### POST `/api/data/apply-edit`

Applique une modification validée par l'utilisateur.

**Request :**
```json
{
  "path": "relations/nom.md",
  "old_string": "texte exact",
  "new_string": "texte modifié"
}
```

**Response :** SSE stream avec logs + sync OVH

**Errors :**
- `403` : Répertoire non autorisé ou type de fichier interdit
- `404` : Fichier introuvable
- Validation : texte introuvable ou non unique dans le fichier

## Persistance

✅ **Les propositions sont sauvegardées dans l'historique** :
- Elles restent visibles après un refresh de la page
- Le statut (appliquée/refusée/en attente) est enregistré
- Chaque action est horodatée
- L'historique complet est dans `data/chats/{id}.json`

Voir [Persistance des propositions](persistance-edit-proposals.md) pour les détails.

## Limitations

- Pas d'édition de `profil.json` (utilise `/profil` UI ou `/api/profil/update`)
- Pas d'édition de fichiers système (`.env`, scripts, etc.)
- Pas de création de nouveaux fichiers (uniquement modification)
- Une seule modification à la fois par message
- Pas d'annulation (undo) d'une modification appliquée

## Cas d'usage typiques

- Enrichir un dossier de relation avec de nouveaux détails
- Compléter les dossiers famille/entourage/animaux
- Corriger/compléter un rapport médical
- Ajouter des notes dans un trauma
- Mettre à jour des contextes relationnels

## Technique

**Backend :**
- `api/main.py` : endpoint `/api/data/apply-edit`
- Pattern parsing : `_extract_edit_proposals()` cherche les blocs `json:edit`
- SSE marker : `EDIT_PROPOSAL:{json}` envoyé avant `[ANSWER_START]`

**Frontend :**
- `EditProposal.vue` : composant de validation avec diff
- `ChatView.vue` : parse les `EDIT_PROPOSAL:` et affiche le composant
- `diff` package : calcul des diffs ligne par ligne

**Instructions système :**
- Ajoutées dans `_CHAT_SYSTEM` (prompt système du chat)
- L'IA sait quand et comment proposer des edits
- Format strict pour garantir la parsing
