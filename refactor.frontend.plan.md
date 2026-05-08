# Frontend Refactor Plan

## Objectif
Rendre le frontend plus modulaire, plus testable, et moins fragile face aux changements produit, sans regression fonctionnelle.

## Avancement
- Sprint A [done]: extraction partials templates, tests de rendu verts (53 tests).
- Sprint B [done]: scripts migres vers includes modules, lifecycle init/destroy via window.__htmxModules, tests rendu lifecycle verts.
- Sprint C [en cours]: edition inline (texte/speaker/topic/subtopic) — backend prêt, frontend a connecter.

## Constat (audit)

### 1. Duplication importante dans le viewer panel
- Meme logique UI recopiee dans plusieurs branches conditionnelles (timeline vs fallback, video vs audio).
- Risque: divergence de comportement, cout de maintenance eleve, corrections partielles.

### 2. Scripts inline dans des fragments HTMX
- Le JS est embarque dans les templates partiels remplaces via HTMX.
- Risque: listeners globaux potentiellement re-attaches, comportement difficile a raisonner sur la duree.

### 3. Couplage fort entre DOM et logique JS
- Selecteurs globaux et logique attachee aux classes/attributs actuels.
- Risque: un changement HTML casse des features sans signal precoce.

### 4. Performance perfectible sur la synchro timeline
- Boucle sur tous les segments a chaque timeupdate media.
- Risque: degradation progressive sur longues transcriptions.

### 5. Couverture frontend insuffisante
- Peu de tests de rendu template et pas de tests d interaction navigateur sur les flux critiques.
- Risque: regressions detectees tardivement.

## Priorites

### P0
- Eliminer la duplication majeure des templates du panel.
- Encapsuler le JS dans des modules init/destroy reutilisables.
- Introduire des tests de rendu serveur pour verrouiller la structure.

### P1
- Ajouter des tests navigateur pour sync, filter, bookmark, seek, edition.
- Stabiliser un contrat de data-attributes utilises par le JS.

### P2
- Optimiser la synchro active segment (indexation/scan incremental).
- Ameliorer DX (structure claire des composants et scripts).

## Architecture cible

### Templates
- Conserver un template conteneur principal.
- Extraire des partials reutilisables:
  - media player block (audio/video/no-media)
  - panel controls (sync/star/filter)
  - folder switcher
  - timeline topic/subtopic section
  - segment row item

### Scripts
- Migrer les scripts inline vers des modules sous static/transcriptions/js:
  - player-sync.js
  - bookmark-toggle.js
  - star-filter.js
  - index-scroll.js
  - edit-inline.js
  - bootstrap.js (orchestration)
- Chaque module expose:
  - init(root)
  - destroy(root)

### Contrat DOM stable
- Normaliser les data-attributes critiques:
  - data-component
  - data-action
  - data-segment-key
  - data-start / data-end
  - data-sync-linked
  - data-star-filtered
- Interdire la dependance sur des classes purement visuelles pour la logique JS.

## Strategie de tests

### 1. Tests de rendu serveur (Django)
But: verrouiller la structure HTML attendue selon les scenarios.

Cas minimaux:
- video + timeline
- audio + timeline
- no-media + timeline
- fallback table sans timeline
- presence des controles sync/star

### 2. Tests interaction navigateur (Playwright)
But: couvrir les parcours critiques utilisateur.

Cas minimaux:
- click segment => seek du player
- toggle sync => changement d etat
- toggle star filter => masquage/affichage correct
- bookmark toggle => persistance visuelle apres refresh
- inline edit texte/speaker/topic/subtopic => persistance apres refresh

### 3. Tests anti-regression HTMX
But: eviter les comportements fantomes apres swaps.

Cas minimaux:
- changement de dossier (hx-get) n empile pas les handlers
- interactions restent fonctionnelles apres 2-3 swaps consecutifs

## Plan d execution (iteratif)

### Sprint A - Refactor sans changement fonctionnel [DONE]
1. [x] Extraire partials templates depuis le viewer panel.
2. [x] Ajouter tests de rendu pour verrouiller avant/apres.
3. [x] Verifier qu aucune fonctionnalite n est modifiee.

Definition de done Sprint A:
- rendu identique fonctionnellement ✓
- duplication reduite significativement ✓
- tests rendu verts ✓

### Sprint B - Modularisation JS [DONE]
1. [x] Deplacer scripts inline vers modules includes (templates/scripts/).
2. [x] Introduire bootstrap init/destroy sur cycle de vie HTMX (window.__htmxModules).
3. [~] Tests navigateur Playwright (differé Sprint D, P1).

Definition de done Sprint B:
- plus de logique inline dans les templates partiels critiques ✓
- pas de double binding apres swaps ✓
- tests rendu lifecycle verts ✓

### Sprint C - Edition inline robuste [EN COURS]
1. [ ] UI inline edit segment texte dans _segments_table.html.
2. [ ] UI inline rename speaker dans _segments_table.html.
3. [ ] UI inline rename topic/subtopic dans les headers.
4. [ ] Module _edit_inline_scripts.html (fetch + CSRF + appUi.emitAjaxError).
5. [ ] Tests de rendu pour presence des data-attributes edition.

Definition de done Sprint C:
- edition inline stable
- persistance validee via edited.json
- tests rendu edition verts

### Sprint D - Performance et hardening
1. Optimiser detection segment actif (moins de scan global).
2. Ajouter checks de robustesse DOM (guards explicites).
3. Nettoyage final et documentation architecture frontend.

Definition de done Sprint D:
- fluidite correcte sur longues transcriptions
- zero warning connu de listeners dupliques
- architecture documentee

## Risques et mitigations

### Risque 1: regression visuelle pendant extraction des partials
- Mitigation: tests de rendu + refactor par petits pas.

### Risque 2: bug lifecycle HTMX (double init)
- Mitigation: contrat init/destroy strict + tests swaps repetes.

### Risque 3: dette de selecteurs fragiles
- Mitigation: data-attributes semantiques dedies a la logique.

## Checklist technique
- [x] Extraire partials templates
- [x] Ajouter tests unitaires de rendu templates (53 passants)
- [x] Migrer scripts inline vers modules includes
- [x] Implementer bootstrap init/destroy compatible HTMX
- [ ] Edition inline texte/speaker/topic/subtopic
- [ ] Ajouter tests Playwright parcours critiques (Sprint D)
- [~] Documenter contrat data-attributes

## KPIs de succes
- Diminution des lignes dupliquees dans le viewer panel.
- Augmentation de la couverture tests frontend (rendu + interaction).
- Aucun bug de comportement apres 3 changements de dossier consecutifs.
- Temps moyen de modification d un composant reduit (moins de points a toucher).
