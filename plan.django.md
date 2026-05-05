# Plan — Application web Django (aioe)

## 1) Objectif

Construire une application web interne en Django, extensible, 100% testable automatiquement,
sans duplication de code, facile à refactorer.

Le package `transcriber` (ce repo) est utilisé comme première fonctionnalité,
mais l'architecture est conçue pour accueillir n'importe quelle nouvelle feature
sans modifier le reste.

---

## 2) Stack technique

| Composant | Choix | Raison |
|-----------|-------|--------|
| Backend | Django 5.x + DRF | Batteries incluses, structure claire par app |
| Tâches async | Celery + Redis | Transcription ~34 min → non bloquante |
| Base de données | PostgreSQL (prod) / SQLite (dev) | Standard Django |
| Frontend | HTMX + Alpine.js + Tailwind CSS | Simple, testable, pas de JS framework |
| Tests | pytest + pytest-django + factory_boy | Cohérent avec transcriber |
| Pipeline IA | `transcriber` installé comme dépendance | Pas de duplication de code |

---

## 3) Structure du projet

```
aioe/
  manage.py
  pyproject.toml
  .env
  .env.example

  config/                          ← configuration Django
    __init__.py
    settings/
      base.py                      ← commun à tous les environnements
      dev.py                       ← DEBUG=True, SQLite, pas de Redis
      prod.py                      ← PostgreSQL, Redis, S3
    urls.py                        ← routage racine
    celery.py                      ← configuration Celery

  apps/                            ← apps Django (couche web + DB uniquement)
    __init__.py
    users/
      models.py                    ← User (extend AbstractUser)
      views.py
      serializers.py
      urls.py
    projects/
      models.py                    ← Project (nom, client, date)
      views.py
      serializers.py
      urls.py
    transcriptions/
      models.py                    ← TranscriptionJob, TranscriptionResult
      views.py                     ← POST /transcriptions/, GET /transcriptions/{id}/
      serializers.py
      tasks.py                     ← @shared_task run_transcription_task()
      urls.py
      management/
        __init__.py
        commands/
          __init__.py
          transcribe.py            ← python manage.py transcribe --input audio.m4a
          retry_failed_jobs.py     ← python manage.py retry_failed_jobs
    # <nouvelle_feature>/          ← une app = une feature, ajout sans toucher au reste
    #   models.py
    #   views.py
    #   tasks.py
    #   urls.py
    #   management/__init__.py
    #   management/commands/__init__.py
    #   management/commands/       ← commandes propres à la feature

  services/                        ← couche métier (aucune dépendance Django)
    __init__.py
    transcription/
      __init__.py
      service.py                   ← appelle transcriber.pipeline.run_pipeline()
      schemas.py                   ← Pydantic: TranscriptionRequest, TranscriptionOutput
    # <nouvelle_feature>/          ← un service par feature, indépendant de Django
    #   service.py
    #   schemas.py

  infrastructure/                  ← clients externes isolés
    storage/
      s3_client.py                 ← upload/download fichiers audio
    llm/                           ← (si besoin LLM plus tard)
      openai_client.py
      ollama_client.py
    smtp/                          ← (si besoin envoi email plus tard)
      smtp_client.py

  templates/                       ← HTMX + Tailwind
    base.html
    transcriptions/
      list.html
      detail.html
    # <nouvelle_feature>/           ← un dossier de templates par feature

  static/
    css/                           ← Tailwind CSS
    js/                            ← Alpine.js

  tests/
    unit/                          ← <1s total, aucune dépendance externe
    integration/                   ← <30s, pas de vrai modèle IA
    functional/                    ← lent, lancé manuellement ou nightly
```

---

## 4) Architecture en couches

```
HTTP Request          manage.py (CLI)
    ↓                      ↓
apps/ (views.py)    apps/ (management/commands/)   ← deux points d'entrée
    ↓                      ↓
    └──────────┬───────────┘
               ↓
        services/ (service.py)   ← logique métier, Pydantic, PAS de Django
               ↓
        infrastructure/          ← S3, LLM, SMTP
               ↓
        transcriber (package)    ← pipeline IA autonome
```

Note : `views.py` et `management/commands/` peuvent aussi passer par `tasks.py` (Celery)
si l'opération doit être asynchrone (ex: transcription longue durée).

**Règle absolue :** `services/` et `infrastructure/` ne doivent jamais importer depuis `django`, `rest_framework` ou `apps/`.

---

## 5) Commandes CLI (management commands)

Les management commands Django permettent d'exécuter des actions en dehors du contexte HTTP,
tout en ayant accès à la DB, aux services et aux tâches Celery.

### Principe

```
python manage.py <commande> [options]
```

Chaque app peut avoir ses propres commandes dans `management/commands/`.
Elles appellent les mêmes `services/` que les views — **pas de duplication**.

### Structure

```python
# apps/transcriptions/management/commands/transcribe.py
from django.core.management.base import BaseCommand
from services.transcription.service import run
from services.transcription.schemas import TranscriptionRequest

class Command(BaseCommand):
    help = "Transcribe an audio file and save result to DB"

    def add_arguments(self, parser):
        parser.add_argument("--input", required=True)
        parser.add_argument("--lang", default="fr")
        parser.add_argument("--num-speakers", type=int)

    def handle(self, *args, **options):
        request = TranscriptionRequest(
            audio_path=options["input"],
            lang=options["lang"],
            num_speakers=options["num_speakers"],
        )
        result = run(request)
        self.stdout.write(f"Done: {result.speakers_found} speakers, {len(result.segments)} segments")
```

### Commandes utiles à prévoir

| Commande | Usage |
|----------|-------|
| `transcribe` | Lancer une transcription depuis le terminal |
| `retry_failed_jobs` | Relancer les jobs en erreur (Celery) |
| `cleanup_intermediates` | Supprimer les fichiers intermédiaires anciens |
| `export_results` | Exporter des résultats en batch (JSON/SRT/TXT) |

### Testabilité

Les commandes sont testables comme n'importe quel code Python :

```python
# tests/unit/apps/test_command_transcribe.py
from django.core.management import call_command

def test_transcribe_command(mock_service, tmp_audio):
    call_command("transcribe", input=str(tmp_audio), lang="fr")
    mock_service.assert_called_once()
```

---

## 6) Flux d'un job de transcription

```
POST /api/transcriptions/  (fichier audio + paramètres)
  → TranscriptionJobSerializer.validate()
  → TranscriptionJob.objects.create(status="pending")
  → run_transcription_task.delay(job_id)        ← Celery async
      → TranscriptionJob.status = "running"
      → services/transcription/service.run(request, pipeline_fn)
          → transcriber.pipeline.run_pipeline(...)
      → TranscriptionResult.objects.create(...)
      → TranscriptionJob.status = "done"

GET /api/transcriptions/{id}/
  → retourne job + résultat (segments, exports)
```

---

## 7) Stratégie de tests

### Principe
Tout le code contenant de la logique est testable automatiquement, sans navigateur, sans serveur, sans modèle IA.

### Arborescence des tests

```
tests/
  conftest.py                  ← fixtures partagées (UserFactory, ProjectFactory...)

  unit/                        ← <1s total
    services/
      test_transcription_service.py   ← mock run_pipeline(), teste la logique service
    apps/
      test_transcription_models.py    ← champs, contraintes, méthodes
      test_serializers.py             ← validation des inputs
      test_commands.py                ← management commands (call_command)

  integration/                 ← <30s
    test_transcription_api.py   ← APIClient HTTP + DB SQLite de test
    test_tasks.py               ← Celery ALWAYS_EAGER + service mocké

  functional/                  ← lent, nightly
    test_full_job_lifecycle.py  ← upload → job → résultat complet (vrai audio)
```

### Couche par couche

| Couche | Outil | Mock |
|--------|-------|------|
| `services/` | pytest + Pydantic | `transcriber.pipeline` mocké |
| `apps/` models | pytest-django, DB SQLite | — |
| `apps/` serializers | pytest, objets Python | — |
| API endpoints | DRF `APIClient` | service mocké |
| Celery tasks | `CELERY_TASK_ALWAYS_EAGER=True` | service mocké |
| Pipeline IA complet | pytest + vrai audio | rien (test fonctionnel) |

### Pattern injectable pour les services

```python
# services/transcription/service.py
def run(
    request: TranscriptionRequest,
    pipeline_fn=run_pipeline,          # ← injectable en test
) -> TranscriptionOutput:
    result = pipeline_fn(
        input_path=request.audio_path,
        lang=request.lang,
        ...
    )
    return TranscriptionOutput(
        segments=result["segments"],
        speakers_found=result["speakers_found"],
    )
```

```python
# tests/unit/services/test_transcription_service.py
def test_run_returns_output(tmp_path):
    mock_pipeline = Mock(return_value={
        "segments": [{"start": 0.0, "end": 2.0, "speaker": "SPEAKER_00", "text": "Bonjour"}],
        "speakers_found": 1,
        "audio_duration_s": 2.0,
        "speaker_map": {"SPEAKER_00": "Alice"},
    })
    request = TranscriptionRequest(audio_path=tmp_path / "audio.wav", lang="fr")
    result = run(request, pipeline_fn=mock_pipeline)
    assert result.speakers_found == 1
    assert len(result.segments) == 1
```

### CI recommandée

```yaml
# .github/workflows/ci.yml
test-fast:                        # à chaque commit — <2 min
  run: pytest tests/unit/ tests/integration/ -q

test-full:                        # nightly seulement
  run: pytest tests/functional/ --timeout=3600
```

---

## 8) Dépendances

```toml
[project]
dependencies = [
  "django>=5.2",
  "djangorestframework>=3.16",
  "celery[redis]>=5.4",
  "pydantic>=2.0",
  "django-environ>=0.11",          # gestion .env

  # package transcription (ce repo)
  "transcriber @ git+https://github.com/org/transcriber.git@main",
  # en dev local: "transcriber @ file:///path/to/transcriber"
]

[project.optional-dependencies]
dev = [
  "pytest>=8",
  "pytest-django>=4.9",
  "pytest-cov>=7",
  "pytest-timeout>=2.3",
  "factory-boy>=3.3",
  "ruff",
]
```

---

## 9) Modèles de données (Sprint 1)

### TranscriptionJob

| Champ | Type | Notes |
|-------|------|-------|
| `id` | UUID | clé primaire |
| `project` | FK Project | nullable |
| `created_by` | FK User | |
| `audio_file` | FileField | stocké S3 en prod |
| `lang` | CharField | ex: "fr" |
| `num_speakers` | IntegerField | nullable |
| `speaker_names` | JSONField | liste de noms |
| `model_size` | CharField | "medium" par défaut |
| `status` | CharField | pending/running/done/failed |
| `created_at` | DateTimeField | auto |
| `completed_at` | DateTimeField | nullable |

### TranscriptionResult

| Champ | Type | Notes |
|-------|------|-------|
| `job` | OneToOneField | FK TranscriptionJob |
| `segments` | JSONField | liste des segments |
| `speaker_map` | JSONField | SPEAKER_00 → nom |
| `speakers_found` | IntegerField | |
| `audio_duration_s` | FloatField | |
| `timings` | JSONField | timings par étape |
| `export_txt` | TextField | nullable |
| `export_srt` | TextField | nullable |

---

## 10) Sprints

### Sprint 1 — Transcription web (MVP)
- Initialiser le projet Django avec la structure ci-dessus
- App `transcriptions` : modèles, API CRUD, tâche Celery
- Service `services/transcription/service.py` injectable
- Templates HTMX : upload fichier, suivi statut job, affichage résultat
- Tests unit + integration complets

### Sprint 2 — Utilisateurs & projets
- Auth (login/logout, tokens API)
- App `projects` : associer des jobs à des projets
- App `users` : profils, permissions

### Sprint 3+ — Nouvelles features
- Chaque nouvelle feature = 1 app + 1 service + tests
- Aucune modification des features existantes requise
