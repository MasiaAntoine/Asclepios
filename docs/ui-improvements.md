# Améliorations UI/UX

## Dialog de confirmation de suppression

### Avant

- Confirmation native du navigateur : `confirm("Supprimer ... ?")`
- Pas de contexte visuel
- Pas d'information sur les conversations liées aux rapports
- Pas de cohérence avec le design d'Asclepios

### Après

**Composant personnalisé** : `DeleteConversationDialog.vue`

#### Fonctionnalités

1. **Design cohérent** avec l'identité visuelle d'Asclepios
   - Thème sombre/clair
   - Variables CSS personnalisées
   - Animations fluides (fade + zoom)
   - Backdrop blur

2. **Deux modes** :
   
   **Mode suppression (conversation non liée)**
   - Icône ambre d'avertissement
   - Titre de la conversation affiché
   - Message d'avertissement sur l'irréversibilité
   - Boutons : Annuler (gris) | Supprimer (rouge)
   - État de chargement pendant la suppression

   **Mode bloqué (conversation liée à un rapport)**
   - Icône rouge d'erreur
   - Explication claire : protection du dossier médical
   - Encadré informatif sur la raison du blocage
   - Bouton unique : Fermer

3. **UX améliorée**
   - Pas de popup native disgracieuse
   - Informations contextuelles claires
   - Confirmation en deux temps (clic + validation)
   - Protection contre les suppressions accidentelles
   - État visuel pendant l'opération

#### Technique

**Composant Dialog** : `app/src/components/ui/Dialog.vue`
- Basé sur **reka-ui** (headless UI primitives)
- Portal pour le rendu hors du DOM parent
- Overlay avec backdrop-blur
- Animations CSS natives (Tailwind)
- Accessibilité intégrée (ARIA, focus trap, ESC pour fermer)

**Intégration dans ChatView** :
```vue
<DeleteConversationDialog
  v-if="conversationToDelete"
  v-model:open="deleteDialogOpen"
  :conversation-title="conversationToDelete.title"
  :is-linked-to-report="conversationToDelete.isLinked"
  @confirm="confirmDelete"
  @cancel="cancelDelete"
/>
```

**Flow :**
1. Clic sur l'icône poubelle → `openDeleteDialog()`
2. State `conversationToDelete` + `deleteDialogOpen = true`
3. Dialog s'affiche avec animations
4. Utilisateur valide → `@confirm` → `confirmDelete()`
5. API call → suppression → fermeture dialog

#### Design tokens

```css
/* Couleurs dynamiques (thème) */
--foreground       /* Texte principal */
--muted-foreground /* Texte secondaire */
--border           /* Bordures */
--card             /* Fond carte */
--accent           /* Hover états */
--primary          /* Couleur marque */
```

**Ambre** : avertissement standard
**Rouge** : action destructive / erreur bloquante

## Prochaines améliorations possibles

- [ ] Dialog pour la génération de rapport (remplacer les status SSE)
- [ ] Dialog pour les erreurs critiques
- [ ] Toast notifications pour les actions réussies
- [ ] Modal de confirmation pour quitter une conversation en cours d'édition
- [ ] Drawer mobile pour la liste des conversations
