# Agenda médical (Google Agenda, lecture seule)

Affiche les rendez-vous du Google Agenda « Médical » dans l'app, et les rend
disponibles à l'assistant Asclepios. **Aucune écriture** : pas de création, pas
de modification, pas de stockage d'événements côté app.

## Quelle URL Google utiliser

Google propose plusieurs liens dans les paramètres du calendrier. Un seul est
adapté ici :

| Option | Verdict |
|---|---|
| **Adresse secrète au format iCal** | ✅ **À utiliser.** Fonctionne sur un calendrier **privé**, format `.ics` standard, aucun OAuth à configurer. |
| URL publique (HTML ou iCal public) | ❌ Exige de rendre l'agenda **public**. Inacceptable pour des rendez-vous médicaux. |
| API Google Calendar (OAuth) | Surdimensionné ici : nécessite un projet Google Cloud, un écran de consentement et un refresh token à maintenir, pour un besoin de lecture seule. |

### Où la trouver

Google Agenda → survoler le calendrier « Médical » → **Paramètres et partage**
→ section **Intégrer l'agenda** → **Adresse secrète au format iCal**.

Elle ressemble à :

```
https://calendar.google.com/calendar/ical/xxxxx%40group.calendar.google.com/private-yyyyyyyy/basic.ics
```

### Sécurité de ce secret

Cette URL est un **jeton d'accès en clair** : quiconque la possède peut lire
l'agenda. D'où les précautions en place :

- Elle vit **uniquement** dans `.env` (côté backend), jamais dans le frontend.
- Le navigateur n'appelle que `/api/agenda/*` ; l'URL n'est jamais renvoyée au client.
- `GET /api/agenda/status` expose seulement `configured: true/false`, pas l'URL.
- En cas de fuite : Google Agenda → **Réinitialiser les adresses privées**.

## Configuration

Dans `.env` :

```bash
MEDICAL_ICAL_URL=https://calendar.google.com/calendar/ical/.../private-.../basic.ics
```

Puis redémarrer l'API :

```bash
docker compose restart api
```

Sans cette variable, la page Agenda s'affiche avec un guide de mise en route
plutôt qu'une erreur.

## Architecture

```
Google Agenda (privé)
        │  adresse secrète iCal (.ics)
        ▼
api/agenda.py ─── fetch httpx + parse icalendar
        │            ├── cache mémoire (TTL 10 min)
        │            └── snapshot data/agenda-cache.json
        ├──────────► GET /api/agenda/events ──► useAgenda.ts ──► AgendaView.vue
        └──────────► format_for_ai() ─────────► medical_context.py ──► assistant
```

### Backend — `api/agenda.py`

| Fonction | Rôle |
|---|---|
| `get_events(data_dir, start, end, force)` | Événements normalisés de la fenêtre demandée |
| `format_for_ai(data_dir)` | Résumé texte des RDV pour le contexte de l'assistant |
| `status(data_dir)` | Diagnostic non sensible (configuré ? dernière synchro ?) |

Points d'implémentation :

- **Cache mémoire, TTL 10 min** — le flux Google n'est pas temps réel, inutile de le marteler.
- **Snapshot disque** (`data/agenda-cache.json`) — sert au contexte IA (jamais d'appel réseau bloquant pendant la construction du prompt) et de repli si Google est injoignable. Exclu du sync OVH (`SKIP_NAMES` dans `scripts/sync.py`) car il change à chaque fetch.
- **Récurrences expansées** via `recurring-ical-events` : une séance hebdomadaire apparaît à chaque occurrence.
- **Parser de secours intégré** : si `icalendar` n'est pas installé, un parser iCal minimal prend le relais (VEVENT simples, sans expansion des récurrences) plutôt que de planter.
- **`DTEND` des journées entières** est exclusif en iCal ; il est rendu inclusif pour ne pas afficher un jour de trop.

### Endpoints

| Méthode | Chemin | Description |
|---|---|---|
| GET | `/api/agenda/status` | Configuré ? dernière synchro ? (sans secret) |
| GET | `/api/agenda/events` | Événements. Query : `start`, `end` (ISO), `refresh=true` |

Codes d'erreur : `501` si `MEDICAL_ICAL_URL` est absent, `503` si le flux est
injoignable **et** qu'aucun snapshot n'existe.

Fenêtre par défaut : 60 jours en arrière → 365 jours en avant.

### Frontend

- `app/src/composables/useAgenda.ts` — état partagé (pattern singleton), index jour → événements, helpers de formatage.
- `app/src/views/AgendaView.vue` — grille mensuelle, panneau du jour sélectionné, liste « à venir », encart du prochain rendez-vous.
- Route `/agenda`, entrée « Agenda » dans la sidebar (section Suivi).

Les dates seules (`2026-09-10`) sont parsées explicitement en heure locale :
`new Date('2026-09-10')` les interpréterait en UTC et décalerait le jour affiché.

### Pourquoi pas le composant `Calendar` de shadcn

Le `Calendar` de shadcn est un **sélecteur de date** (date picker), pas une vue
agenda avec événements : pas de pastilles d'événements par jour, pas de détail,
pas de liste des prochains rendez-vous. La grille est donc construite sur mesure
avec les mêmes tokens de design (`--primary`, `--card`, `--border`…), ce qui
donne un rendu cohérent sans détourner un composant inadapté.

## Contexte pour l'assistant

`medical_context.py` ajoute une section « Agenda médical (rendez-vous) » lue
depuis le snapshot, sous la forme :

```
### Rendez-vous à venir

- 2026-09-03 à 14:30 — Consultation Dr Limodin · lieu : 12 rue des Lilas
- 2026-09-10 (journée) — Prise de sang à jeun
```

Le prompt système précise qu'Asclepios peut **lire** l'agenda mais pas le
modifier, et qu'il ne doit supposer aucun rendez-vous si la section est absente.

Tu peux donc lui demander : *« c'est quoi mon prochain rendez-vous ? »*,
*« prépare-moi la consultation de jeudi »*, *« est-ce que j'ai une prise de sang
avant mon RDV endocrino ? »*.

## Limites connues

- Lecture seule par conception : créer un RDV se fait dans Google Agenda.
- Propagation Google de quelques minutes, plus le TTL de 10 min du cache. Le bouton **Actualiser** force un refetch (`refresh=true`).
- Les invités, pièces jointes et visioconférences ne sont pas exploités (titre, horaire, lieu, description uniquement).
- Un seul calendrier à la fois.
