# Test — Dialog de suppression de conversation

Guide de test pour vérifier le nouveau système de confirmation.

## Prérequis

1. Frontend lancé : `cd app && npm run dev`
2. Au moins 2 conversations existantes :
   - Une **sans rapport lié** (supprimable)
   - Une **avec rapport lié** (protégée)

## Tests fonctionnels

### Test 1 : Ouvrir la dialog (conversation supprimable)

1. Va sur `http://localhost:5173/assistant`
2. Survole une conversation **non liée à un rapport**
3. Clique sur l'icône **poubelle** (apparaît au hover)

**Résultat attendu :**
- ✅ Dialog s'ouvre avec animation (fade + zoom in)
- ✅ Overlay semi-transparent avec blur
- ✅ Icône **ambre** d'avertissement
- ✅ Titre : "Supprimer la conversation"
- ✅ Titre de la conversation affiché dans un encadré gris
- ✅ Message sur l'irréversibilité
- ✅ Boutons : "Annuler" (gris) | "Supprimer" (rouge)

### Test 2 : Annuler la suppression

1. Dans la dialog ouverte, clique sur **"Annuler"**

**Résultat attendu :**
- ✅ Dialog se ferme avec animation (fade + zoom out)
- ✅ Conversation toujours présente dans la liste
- ✅ Aucun appel API
- ✅ Pas d'erreur console

### Test 3 : Confirmer la suppression

1. Ouvre à nouveau la dialog
2. Clique sur **"Supprimer"**

**Résultat attendu :**
- ✅ Bouton passe en état "Suppression…" avec spinner
- ✅ Appel API : `POST /api/chats/{id}/delete`
- ✅ Conversation disparaît de la liste
- ✅ Dialog se ferme automatiquement
- ✅ Si c'était la conversation active, "Nouvelle conversation" s'ouvre
- ✅ Sync OVH déclenché en arrière-plan

### Test 4 : Conversation liée à un rapport (protégée)

1. Clique sur l'icône poubelle d'une conversation **avec icône cadenas**

**Résultat attendu :**
- ✅ Dialog s'ouvre avec animation
- ✅ Icône **rouge** d'erreur/alerte
- ✅ Titre : "Suppression impossible"
- ✅ Message : "Cette conversation est liée à un rapport médical"
- ✅ Encadré **ambre** avec explication détaillée
- ✅ Bouton unique : "Fermer" (bleu/primaire)
- ✅ Pas de bouton "Supprimer"

### Test 5 : Fermer une dialog protégée

1. Clique sur **"Fermer"** ou sur la croix en haut à droite

**Résultat attendu :**
- ✅ Dialog se ferme
- ✅ Aucun changement dans la liste
- ✅ Aucun appel API

### Test 6 : Fermer avec ESC

1. Ouvre n'importe quelle dialog
2. Appuie sur **Échap (ESC)**

**Résultat attendu :**
- ✅ Dialog se ferme
- ✅ Équivalent au bouton "Annuler" / "Fermer"

### Test 7 : Fermer en cliquant sur l'overlay

1. Ouvre une dialog
2. Clique **en dehors** de la dialog (sur l'overlay sombre)

**Résultat attendu :**
- ✅ Dialog se ferme (comportement natif reka-ui)
- ✅ Pas de changement dans la liste

## Tests visuels (thème)

### Thème clair

1. Active le thème clair de l'OS (si Asclepios le suit)
2. Ouvre une dialog

**Vérifications :**
- ✅ Overlay sombre mais pas trop opaque
- ✅ Textes lisibles (contraste suffisant)
- ✅ Couleurs cohérentes avec le reste de l'app
- ✅ Bordures visibles mais subtiles

### Thème sombre

1. Active le thème sombre
2. Ouvre une dialog

**Vérifications :**
- ✅ Fond de dialog sombre (`--card`)
- ✅ Textes clairs (`--foreground`)
- ✅ Icônes colorées bien visibles
- ✅ Encadré ambre lisible en dark mode

## Tests accessibilité

### Clavier

1. Ouvre une dialog
2. Navigue avec **Tab**

**Résultat attendu :**
- ✅ Focus piégé dans la dialog (ne sort pas)
- ✅ Ordre de focus logique : Croix → Annuler → Supprimer
- ✅ Indicateur de focus visible
- ✅ **Enter** sur "Supprimer" → confirme
- ✅ **ESC** → ferme

### ARIA

Inspecte avec DevTools :

**Résultat attendu :**
- ✅ `role="dialog"` sur le contenu
- ✅ `aria-label` ou `aria-labelledby` présent
- ✅ `aria-describedby` pour la description
- ✅ Boutons avec labels explicites

## Tests de régression

### Suppression pendant un chat en cours

1. Lance un message dans le chat (réponse en cours)
2. Essaie de supprimer une conversation

**Résultat attendu :**
- ✅ Dialog ne s'ouvre **pas** (`running.value` bloque)
- ✅ Pas de crash, pas d'erreur

### Suppression pendant génération de rapport

1. Lance la génération d'un rapport
2. Essaie de supprimer une conversation

**Résultat attendu :**
- ✅ Dialog ne s'ouvre **pas** (`generatingReport.value` bloque)

### Erreur réseau pendant la suppression

1. Coupe le backend (`api/dev.sh` arrêté)
2. Confirme une suppression

**Résultat attendu :**
- ✅ Erreur affichée : "Suppression impossible"
- ✅ Conversation restaurée dans la liste
- ✅ Dialog se ferme
- ✅ Pas de crash frontend

## Tests d'intégration

### Flow complet : Supprimer puis sync

1. Supprime une conversation
2. Vérifie `data/chats/` → fichier `.json` supprimé
3. Attends le sync OVH automatique
4. Vérifie les logs backend : "Push OVH"

**Résultat attendu :**
- ✅ Fichier local supprimé immédiatement
- ✅ Sync OVH déclenché en background (task)
- ✅ Aucune erreur dans les logs

### Suppression puis reload page

1. Supprime une conversation
2. Recharge la page (`F5`)

**Résultat attendu :**
- ✅ Conversation toujours absente de la liste
- ✅ Pas de flash de la conversation supprimée au chargement

## Checklist de validation

- [ ] Dialog s'ouvre avec animation fluide
- [ ] Thème clair/sombre cohérent
- [ ] Conversations protégées non supprimables
- [ ] Conversations standard supprimables
- [ ] Bouton "Annuler" fonctionne
- [ ] Bouton "Supprimer" déclenche l'API
- [ ] État de chargement visible pendant suppression
- [ ] ESC ferme la dialog
- [ ] Clic overlay ferme la dialog
- [ ] Navigation clavier fonctionnelle
- [ ] Pas de suppression pendant chat actif
- [ ] Erreurs réseau gérées proprement
- [ ] Sync OVH automatique après suppression

## Debug

### Dialog ne s'ouvre pas

**Console navigateur :**
```javascript
// Vérifier l'état
console.log(deleteDialogOpen.value)
console.log(conversationToDelete.value)
```

**Causes possibles :**
- `running.value` ou `generatingReport.value` = true
- Conversation introuvable dans la liste
- Erreur d'import du composant

### Dialog s'ouvre mais boutons ne répondent pas

**Console :**
```javascript
// Vérifier les handlers
console.log('confirmDelete', confirmDelete)
console.log('cancelDelete', cancelDelete)
```

**Causes possibles :**
- Erreur dans les émetteurs `@confirm` / `@cancel`
- `conversationToDelete.value` = null

### Suppression échoue silencieusement

**Terminal API :**
```bash
# Chercher les erreurs 403/404
[ERROR] 403 Forbidden
[ERROR] 404 Not Found
```

**Causes possibles :**
- Conversation liée à un rapport (devrait être bloquée avant)
- Fichier déjà supprimé manuellement

## Prochains tests

- [ ] Dialog responsive (mobile)
- [ ] Dialog avec lecteur d'écran (NVDA/JAWS)
- [ ] Multiple dialogs empilées (edge case)
- [ ] Dialog pendant transition de route
