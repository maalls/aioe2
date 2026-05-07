# Plan: service de rapport a partir d'une transcription JSON diarisee

## 1. Objectif
Creer un service applicatif qui prend en entree un fichier JSON de transcription (avec diarization), puis produit un rapport exploitable pour l'equipe produit/metier.

Le service doit rester independant du pipeline ASR (v1/v2): il consomme uniquement le JSON final.

## 2. Portee
- In scope:
  - Lecture/validation du JSON de transcription.
  - Calcul d'indicateurs conversationnels (temps de parole, tours, rythme).
  - Extraction d'elements actionnables (questions, decisions, actions) via heuristiques robustes.
  - Export du rapport en JSON et Markdown.
  - Commande Django pour execution locale/prod.
- Out of scope (phase 1):
  - Scoring LLM de qualite.
  - Attribution semantique avancee (sentiment fin, intentions complexes).
  - UI dediee de visualisation (on peut l'ajouter en phase 2).

## 3. Entree attendue
Format minimal attendu (deja present dans vos sorties):
- `audio_file`
- `audio_duration_s`
- `speaker_map` (ex: SPEAKER_00 -> Malo)
- `talk_time_s`
- `segments[]` avec:
  - `start` (float)
  - `end` (float)
  - `speaker` (SPEAKER_XX)
  - `text` (str)

Regles de robustesse:
- Si `speaker_map` absent: fallback sur l'identifiant brut `speaker`.
- Si `talk_time_s` absent: recalcul depuis `segments`.
- Segments invalides (`end <= start`) ignores et comptes dans les warnings.

## 4. Sortie rapport proposee
Un objet `TranscriptionReport` avec:

- `meta`
  - `source_json`
  - `generated_at`
  - `audio_duration_s`
  - `speakers_found`
- `overview`
  - `total_segments`
  - `total_talk_time_s`
  - `silence_ratio`
  - `avg_segment_duration_s`
- `speakers[]`
  - `speaker_id`
  - `speaker_label`
  - `talk_time_s`
  - `talk_share_pct`
  - `turn_count`
  - `avg_turn_duration_s`
  - `words_count`
  - `words_per_min`
  - `longest_monologue_s`
- `interaction`
  - `handover_count`
  - `interruptions_estimated`
  - `question_count`
  - `response_latency_median_s`
- `highlights`
  - `key_moments[]` (timestamp + resume court)
  - `decisions[]`
  - `action_items[]`
  - `risks[]`
- `warnings[]`
  - Incoherences de donnees detectees.

Exports:
- `report.json` (machine-readable)
- `report.md` (lecture humaine)

## 5. Architecture technique
Nouveau module propose:
- `services/transcription_report/schemas.py`
- `services/transcription_report/analyzers.py`
- `services/transcription_report/service.py`
- `services/transcription_report/markdown.py`

Commande management:
- `apps/transcriptions/management/commands/generate_transcription_report.py`

Signature cible:
- `TranscriptionReportService.run(input_json_path: Path, output_dir: Path | None = None) -> TranscriptionReport`

Pipeline interne du service:
1. `load_and_validate()`
2. `normalize_segments()`
3. `compute_speaker_metrics()`
4. `compute_interaction_metrics()`
5. `extract_highlights_heuristic()`
6. `build_report()`
7. `export_json_md()`

## 6. Heuristiques phase 1 (sans LLM)
- Questions: segment termine par `?` ou commence par marqueurs (`est-ce que`, `pourquoi`, `comment`, etc.).
- Decisions: presence de motifs (`on decide`, `on valide`, `ok pour`, `go`).
- Actions: motifs (`je vais`, `on va`, `a faire`, `todo`, `prochaine etape`).
- Risques: motifs (`bloquant`, `risque`, `probleme`, `retard`, `incertitude`).

Ces heuristiques sont simples, tracables, et evitent la dependance modele.

## 7. Integration avec l'existant
- Aucun impact sur `transcription2` (service de transcription garde tel quel).
- Le reporting est un service separe, appele apres generation du JSON.
- Reutilise la structure `var/output/<job_id>/`:
  - entree: transcript JSON existant
  - sortie: `report.json` + `report.md`

## 8. Plan d'implementation
1. Creer schemas Pydantic du rapport.
2. Implementer analyseurs metriques (overview/speakers/interaction).
3. Implementer extraction highlights heuristique.
4. Implementer rendu Markdown.
5. Ajouter commande Django `generate_transcription_report`.
6. Ajouter tests unitaires:
   - JSON nominal
   - JSON partiel (fallback)
   - segments invalides
   - calculs de pourcentages/latences
7. Ajouter 1 test integration sur un dossier `var/output/...`.

## 9. Definition of Done
- Commande executable:
  - `python manage.py generate_transcription_report --input-json <path/to/transcript.json>`
- Genere `report.json` et `report.md` sans erreur.
- Tests unitaires verts pour le module reporting.
- Aucune regression sur `transcription2`.

## 10. Evolution phase 2 (optionnelle)
- Ajouter un mode `--with-llm` pour enrichir `highlights`.
- Ajouter scoring de qualite conversationnelle (ecoute, equilibre, clarte).
- Exposer le rapport via endpoint API et page UI dediee.
