# Plan d'implementation: edition de transcription

## Objectif
Permettre l'edition manuelle depuis l'interface sans ecraser les fichiers sources generes par pipeline, avec un mode brouillon, un historique minimal et une publication controlee.

## Principes
- Garder les fichiers source (`*.json`, `*.timeline.json`, `*.timeline.deep.json`) intacts (ne jamais les ecraser).
- Sauver l'etat edite complet dans un fichier `edited.json` par dossier.
- Le rendu UI lit `edited.json` si present, sinon le fichier source. Zero fusion complexe.
- Conserver un log d'operations `segment_edits_history.json` pour undo/audit.

## Perimetre fonctionnel cible
- Correction texte d'un segment.
- Renommage d'un speaker (global: tous les segments de ce speaker sont mis a jour).
- Reaffectation d'un segment par glisser-deposer vers un autre sous-topic.
- Renommage de topic.
- Renommage de sous-topic.
- Reordonnancement de segments dans un sous-topic.
- Filtre "modifies" pour visualiser les changements.

## Approche technique retenue

### 1) Etat edite complet par dossier
Fichier: `var/output/<folder>/edited.json`

- Meme structure que le fichier source (`*.timeline.deep.json`).
- Initialise par copie du fichier source a la premiere edition.
- Ecrase a chaque operation (ecriture atomique: tmp + rename).
- Jamais reecrit par le pipeline.

Avantages:
- Le rendu UI lit ce fichier sans fusion. Code identique au rendu source.
- Debuggable directement (lisible, pas de reconstruction mentale).
- Les exports corrigés (txt/srt/vtt/timeline) utilisent `edited.json` directement.

### 2) Historique des operations
Fichier: `var/output/<folder>/segment_edits_history.json`

Schema des operations:

```json
[
  {
    "id": "op_001",
    "type": "edit_segment_text",
    "created_at": "2026-05-08T12:00:00Z",
    "before": {"segment_key": "df78d5c2fa35802c", "text": "texte original"},
    "after":  {"segment_key": "df78d5c2fa35802c", "text": "texte corrige"}
  },
  {
    "id": "op_002",
    "type": "move_segment",
    "created_at": "2026-05-08T12:01:00Z",
    "before": {"segment_key": "df78d5c2fa35802c", "topic_id": "1", "subtopic_id": "1.1", "position": 2},
    "after":  {"segment_key": "df78d5c2fa35802c", "topic_id": "2", "subtopic_id": "2.3", "position": 4}
  },
  {
    "id": "op_003",
    "type": "rename_topic",
    "created_at": "2026-05-08T12:02:00Z",
    "before": {"topic_id": "2", "title": "Ancien titre"},
    "after":  {"topic_id": "2", "title": "Nouveau titre"}
  }
]
```

Types d'operations:
- `edit_segment_text`
- `edit_segment_speaker` (correction ponctuelle sur un segment)
- `rename_speaker` (renommage global: met a jour tous les segments du speaker dans `edited.json`)
- `move_segment`
- `rename_topic`
- `rename_subtopic`

Le undo rejoue simplement `before` sur `edited.json` et supprime la derniere operation du log.

### 3) Rendu simplifie
Dans `apps/transcriptions/views.py`:
- `_load_timeline_report()` retourne `edited.json` si present, sinon `.timeline.deep.json`, sinon `.timeline.json`.
- Aucune logique de fusion. Le code de rendu ne change pas.

### 4) Endpoints backend (atomiques)
Routes suggerees:
- `POST /transcription/edit/<folder>/segment/<segment_key>/text`
- `POST /transcription/edit/<folder>/segment/<segment_key>/move`
- `POST /transcription/edit/<folder>/speaker/<speaker_id>/rename`
- `POST /transcription/edit/<folder>/topic/<topic_id>/rename`
- `POST /transcription/edit/<folder>/subtopic/<subtopic_id>/rename`
- `POST /transcription/edit/<folder>/undo`
- `POST /transcription/edit/<folder>/reset`

Regles:
- CSRF obligatoire.
- Validation stricte des ids et payloads.
- Ecriture atomique du JSON (tmp + rename) pour eviter la corruption.

### 5) UX front
Dans `templates/transcriptions/_segments_table.html`:
- Bouton edit inline sur segment.
- Drag-and-drop HTML5 pour deplacer segment vers un sous-topic.
- Edition inline des titres topic/sous-topic (double clic ou icone crayon).
- Edition inline des labels speaker: double clic sur le nom du speaker dans un segment; renomme globalement tous les segments du meme speaker.
- Badges visuels:
  - "modifie"
  - "draft"
- Actions globales:
  - "Undo" (rejoue dernier `before` du history log)
  - "Reset" (supprime `edited.json` et le history, retour au source)

## Plan de livraison (iteratif)

### Sprint 1 (MVP solide)
- `edited.json` + history helpers lecture/ecriture.
- Endpoint edit texte segment.
- Endpoint rename speaker (global).
- Endpoint rename topic/sous-topic.
- UI inline edit texte + speaker + sauvegarde.
- Filtre "segments modifies".

### Sprint 2
- Drag-and-drop segment -> sous-topic.
- Reordonnancement intra sous-topic.
- Historique operations minimal (append).
- Bouton reset draft.

### Sprint 3
- Undo illimite (rejouer le history log en sens inverse).
- Export corrige (`*.corrected.timeline.deep.json`, `*.corrected.txt`, `*.corrected.srt`, `*.corrected.vtt`) depuis `edited.json`.
- Reset complet (supprimer `edited.json` + history).

## Validation / tests
- Unit tests:
  - merge overlay/source
  - validation payload move/rename/edit
  - ecriture atomique
- Integration tests:
  - parcours UI edit texte -> refresh -> persistance
  - drag-and-drop -> refresh -> position conservee
  - publish -> assets corriges generes

## Risques et mitigations
- Corruption `edited.json` (crash pendant ecriture):
  - Ecriture atomique: ecrire dans `edited.json.tmp` puis renommer.
  - Backup automatique `edited.bak.json` avant chaque operation.
- Divergence si pipeline retourne sur le meme folder:
  - Le pipeline ne touche jamais `edited.json`. Mais si l'utilisateur veut repartir du nouveau source, il fait "Reset".
- Incoherence timeline apres move (timestamps qui se croisent):
  - Garde-fous UI (ne pas permettre le drop si incoherence temporelle evidente).
  - Avertissement visuel plutot que blocage hard (souplesse editoriale).

## Definition of done
- Un utilisateur peut:
  - corriger un segment,
  - renommer topic/sous-topic,
  - deplacer un segment,
  - rafraichir la page sans perdre ses edits,
  - annuler sa derniere action (undo),
  - repartir du source via Reset.
- Les fichiers source pipeline (`*.json`, `*.timeline.deep.json`) restent inchanges.
- `edited.json` est la seule source de verite pour le rendu et les exports.
- Les tests critiques passent sur unit + integration.
