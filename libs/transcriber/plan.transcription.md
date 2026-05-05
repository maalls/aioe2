# Plan de développement — Transcription audio avec identification des intervenants

## 1) Objectif produit
Créer un outil qui:
- prend un fichier audio (réunion, interview, podcast),
- produit une transcription horodatée,
- assigne chaque segment à un intervenant (`Personne A`, `Personne B`, etc. ou noms réels),
- permet de corriger facilement les erreurs de speaker labels.

Résultat attendu (exemple):
- `[00:01:12 - 00:01:18] Alice: Bonjour à tous...`
- `[00:01:18 - 00:01:24] Bob: Merci Alice...`

---

## 2) Approche recommandée (pipeline résumable par artefacts)
L’approche retenue est une pipeline en plusieurs étapes persistées sur disque:

1. **Pré-traitement audio** (WAV standard)
2. **Diarisation** (qui parle quand)
3. **Découpage en segments audio** (un fichier par segment diarizé)
4. **Transcription segment par segment** (un JSON par segment)
5. **Fusion finale** (agrégation, mapping noms, exports)

Pourquoi ce choix:
- Robuste aux longues durées: chaque étape produit des artefacts réutilisables.
- Reprise après erreur: pas besoin de relancer toute la chaîne.
- Débogage facilité: chaque sortie intermédiaire est inspectable.
- Prépare la parallélisation future de la transcription.

---

## 3) UX: informations à demander à l’utilisateur (simple et utile)
Pour simplifier l’algorithme sans alourdir l’UX, on part sur un seul mode: **assisté**.

### Mode assisté
Demander avant traitement:
- Nombre estimé de participants (optionnel mais très utile).
- Noms des participants (optionnel).
- Langue principale (fr, en, etc.).
- Type d’audio (réunion, interview, appel téléphonique).

Option avancée (si possible plus tard):
- Extraits de voix de référence (10-20s) pour certains participants.

Pourquoi ce mode:
- Réduit les erreurs de clustering diarisation.
- Permet de mapper directement `Personne A -> Alice` avec plus de confiance.
- Très simple côté utilisateur.

---

## 4) Pipeline technique détaillée

### 4.1 Pré-traitement
- Conversion en format standard (mono, 16 kHz WAV).
- Normalisation du volume.
- Réduction de bruit légère (optionnelle).
- Détection de silences.

Objectif: stabiliser la diarisation et la transcription.

### 4.2 Diarisation (passage 1)
- Détecter les segments de parole (VAD: Voice Activity Detection).
- Extraire des embeddings vocaux (x-vectors / ECAPA / pyannote embeddings).
- Clustering des segments par voix, contraint à `N` fourni par l'utilisateur.

Sortie intermédiaire:
- timeline avec segments: `[start, end, speaker_id]`.

### 4.3 Découpage audio par segment
- Pour chaque segment diarizé, extraire un fichier audio dédié:
  - `intermediates/segments/seg_000001.wav`, etc.
- Conserver un index de segment (`segment_id`) stable, trié chronologiquement.
- Conserver les métadonnées de segment (`start`, `end`, `speaker`) dans un index JSON.

Règle de reprise:
- Si un fichier segment existe déjà, ne pas le régénérer.

### 4.4 Transcription segmentée (passage 2)
- Transcrire chaque fichier segment avec un ASR local (ex: faster-whisper).
- Sauvegarder le résultat dans un fichier JSON individuel:
  - `intermediates/transcripts/seg_000001.json`, etc.
- Utiliser la langue fournie par l'utilisateur.

Règle de reprise:
- Si `seg_xxxxxx.json` existe déjà, skipper la transcription du segment.

Important:
- Les chevauchements de diarisation sont conservés en V1 (pas de résolution destructive).
- Le merge final applique un tri chronologique strict.

### 4.5 Réconciliation diarisation/transcription (passage 3)
- Corriger les chevauchements temporels.
- Lisser les changements de speaker trop fréquents (jitter).
- Re-segmenter si un segment est trop long (>30-45s) ou trop court (<0.7s).

### 4.6 Mapping identité (A/B/C -> noms)
- Si l’utilisateur a donné une liste de noms:
  - proposer un mapping semi-automatique (`Personne A = Alice ?`) avec validation.
- Si voix de référence dispo:
  - matching par similarité d’embeddings.

### 4.7 Post-traitement texte
- Ponctuation/capitalisation (si modèle ASR ne le fait pas bien).
- Option: résumé automatique, extraction d’actions.
- Export `.txt`, `.srt`, `.json` (json conseillé pour debug/édition).

---

## 5) Architecture logicielle proposée

## 5.1 Modules
- `ingest`: upload et conversion audio.
- `preprocess`: normalisation + VAD.
- `diarization`: segmentation + clustering + speaker labels.
- `segmenter`: découpage audio en fichiers segment.
- `asr`: transcription d'un segment audio.
- `fusion`: fusion des JSON segmentés + diarisation + identity.
- `identity`: mapping vers noms.
- `export`: txt/srt/json.
- `review-ui` (optionnel MVP+): interface correction labels.

## 5.2 Données intermédiaires (format JSON)
Exemple de schéma final agrégé:
```json
{
  "audio_id": "meeting_2026_05_05",
  "language": "fr",
  "speakers": ["SPEAKER_00", "SPEAKER_01"],
  "segments": [
    {
      "start": 12.40,
      "end": 16.82,
      "speaker": "SPEAKER_00",
      "text": "Bonjour a tous",
      "confidence": 0.93
    }
  ],
  "speaker_map": {
    "SPEAKER_00": "Alice",
    "SPEAKER_01": "Bob"
  }
}
```

Artefacts intermédiaires attendus:
- `intermediates/diarization.json`
- `intermediates/segments/index.json`
- `intermediates/segments/seg_XXXXXX.wav`
- `intermediates/transcripts/seg_XXXXXX.json`

La reprise est déduite à la volée depuis les artefacts présents:
- WAV présent => skip pré-traitement.
- `diarization.json` présent => skip diarisation.
- `seg_XXXXXX.wav` présent => skip découpage du segment.
- `seg_XXXXXX.json` présent => skip transcription du segment.

---

## 6) Décisions à valider avant de coder
1. ✅ Cible matérielle: MacBook Pro M4 (Apple Silicon) pour le dev initial. Le code doit abstraire le device (`cpu` / `mps` / `cuda`) pour être facilement reconfiguré selon la machine de l'utilisateur final. Utiliser une variable de config `DEVICE` injectée à l'initialisation des modèles.
2. ✅ Temps de traitement: le plus court possible. Cible: < 5 min pour 45 min d'audio sur M4. Modèle ASR par défaut: `small` (bon compromis vitesse/qualité). Option `large-v3` disponible en flag `--quality high` pour les cas où la précision prime sur la vitesse.
3. ✅ Langue: français par défaut au Sprint 1. Architecture multilingue dès le départ (paramètre `--lang` obligatoire, pas hardcodé). Ajout d'autres langues sans refactoring.
4. ✅ Volume: un fichier par meeting, durée max 2h. Pas de batch ni de file d'attente nécessaire au MVP. Le pipeline traite un seul fichier à la fois.
5. ✅ Interface de correction: V1. Au MVP, la correction se fait manuellement en éditant le `speaker_map` dans le `result.json` puis en relançant uniquement l'étape export (pas tout le pipeline).

---

## 7) Stack technique (local uniquement)

### Stack recommandée
| Rôle | Lib | Version cible |
|---|---|---|
| Langage | Python | 3.10+ |
| Diarisation | `pyannote.audio` | 3.x |
| ASR | `faster-whisper` | 1.x |
| Conversion audio | `ffmpeg` | 6.x (système) |
| CLI | `typer` | 0.12+ |
| Tests | `pytest` | 8.x |

### Modèle Whisper — choix critique
Le choix du modèle impacte directement la qualité et la vitesse:

| Modèle | WER fr (approx) | RAM | Vitesse CPU (1h audio) |
|--------|----------------|-----|------------------------|
| `tiny` | ~30% | 1 GB | ~5 min |
| `small` | ~18% | 2 GB | ~12 min |
| `medium` | ~12% | 5 GB | ~30 min |
| `large-v3` | ~8% | 10 GB | ~60 min |

**Recommandation Sprint 1**: `small` pour itérer vite, `large-v3` pour la qualité finale.

### Prérequis Day 1 — Bloqueur à anticiper
`pyannote.audio` exige un token HuggingFace (gratuit, mais obligatoire):
1. Créer un compte sur [huggingface.co](https://huggingface.co).
2. Accepter les conditions d'utilisation du modèle `pyannote/speaker-diarization-3.1`.
3. Générer un token d'accès (`read`) dans les paramètres du compte.
4. Exporter en variable d'environnement: `export HF_TOKEN=hf_...`

Sans ce token, la diarisation échoue dès le premier appel.

### Avantages
- Contrôle total, données sensibles restent localement.
- Aucun coût récurrent.

### Inconvénients
- Performance dépendante du matériel local.
- Temps de traitement plus long sans GPU.

---

## 8) Roadmap d'implémentation

### MVP (Sprint 1 — 1-2 semaines)
- CLI local fonctionnel (voir section 13).
- Mode assisté: langue + nombre participants + noms.
- Pipeline diarisation + transcription assistée.
- Sortie horodatée avec noms fournis par l'utilisateur.
- Export `.txt` + `.json`.

### V1 (Sprint 2-3 — 2-4 semaines)
- Mapping automatique speakers↔noms par score de confiance.
- Export `.srt`.
- Interface de correction manuelle des speakers.

### V2 (Sprint 4+ — 4+ semaines)
- Voix de référence par participant (embeddings).
- Traitement batch multi-fichiers.
- Résumé/chapitres/actions.
- Metrics dashboard qualité.

---

## 9) Métriques qualité à suivre
- `WER` (Word Error Rate) pour transcription.
- `DER` (Diarization Error Rate) pour speakers.
- Taux de segments avec speaker corrigé manuellement.
- Temps de traitement par minute d’audio.

Objectif pratique initial:
- DER < 20% sur réunions standards.
- WER acceptable en français conversationnel (<20-25% en bruit modéré).

---

## 10) Risques & mitigations
- Bruit élevé / voix qui se chevauchent:
  - Mitigation: VAD robuste, modèle diarisation adapté réunions.
- Beaucoup de participants (>6):
  - Mitigation: demander `N` à l’utilisateur, correction UI simple.
- Forte variabilité d’accents/langues:
  - Mitigation: sélection langue explicite, modèles adaptés.
- Saturation machine locale (CPU/GPU/RAM):
  - Mitigation: file d’attente des jobs, batch processing, cache des résultats intermédiaires.


---

## 11) Sprint 1 — Checklist technique actionnable

Objectif Sprint 1:
- Obtenir un POC local CLI qui prend un fichier audio et sort un JSON diarisation + transcription utilisable.

Durée cible:
- 5 à 8 jours de dev.

### 11.1 Tâches (ordre recommandé)
1. Initialiser le projet Python local.
2. Ajouter les dépendances de base (`ffmpeg`, `pyannote.audio`, `faster-whisper` ou `whisperx`, `typer`/`argparse`).
3. Créer une commande CLI: entrée audio + options `--lang`, `--num-speakers`, `--speaker-names`.
4. Implémenter la conversion audio standard (mono, 16kHz, WAV).
5. Implémenter la diarisation (segments `[start, end, speaker_id]`).
6. Implémenter le découpage audio en fichiers segment.
7. Implémenter la transcription segmentée avec JSON individuel par segment.
8. Implémenter la logique de reprise par détection d'artefacts existants.
9. Fusionner en un format JSON unique (`segments`, `speaker_map`, `metadata`).
10. Ajouter exports `.txt` et `.srt` basiques.
11. Ajouter logs + gestion d’erreurs (audio invalide, modèle manquant, OOM).
12. Ajouter tests d’intégration courts incluant la reprise après interruption.

### 11.2 Livrables de fin de sprint
- Un exécutable CLI local:
  - Exemple: `transcriber run --input ./var/audio/meeting.wav --lang fr --num-speakers 3 --speaker-names "Alice,Bob,Chloe"`
- Un fichier de sortie JSON stable (schéma documenté).
- Un export texte lisible avec timestamps et speakers.
- Un README d’exécution locale (pré-requis machine + commande de lancement).

### 11.3 Critères d'acceptation (Definition of Done)
- Le CLI traite un fichier de 15 minutes sans crash sur machine cible.
- Le JSON contient 100% des segments avec `start`, `end`, `speaker`, `text`.
- Les speakers sont cohérents (pas de sauts excessifs sur phrases continues).
- Les noms fournis par l’utilisateur sont correctement mappés quand disponibles.
- Le pipeline fonctionne sans aucun service cloud.
- Une relance du même job reprend là où le traitement s'est arrêté.

### 11.4 Stratégie de validation rapide
- Cas 1: audio calme, 2 speakers, langue française.
- Cas 2: audio réunion, 3-4 speakers, interruptions courtes.
- Cas 3: audio bruité (vérifier robustesse minimale).

Mesures à relever pour chaque cas:
- Temps total de traitement.
- Nombre de segments générés.
- Estimation qualitative de DER et lisibilité de la transcription.

### 11.5 Backlog immédiat Sprint 2 (pré-placé)
- UI minimale de revue/correction des speakers.
- Amélioration du mapping noms via embeddings de référence.
- Optimisation perf CPU/GPU (batching, cache intermédiaire).

---

## 12) Protocole de test cible (4 speakers, 45 minutes)

Objectif:
- Valider que le pipeline local tient un cas réaliste long avec 4 intervenants.

### 12.1 Préparation
1. Placer le fichier audio de test dans `var/audio/`.
2. Vérifier que le fichier est lisible et dans un format stable (WAV/MP3/M4A).
3. Préparer les métadonnées utilisateur:
   - `num_speakers = 4`
   - noms (ex: Alice, Bob, Chloe, David)
   - langue principale (ex: fr)

### 12.2 Paramètres de lancement recommandés
- Forcer `num_speakers=4` (ne pas laisser en auto pour ce test).
- Activer l'écriture des artefacts intermédiaires:
  - segments diarisation bruts,
  - index de segments audio,
  - transcriptions segmentées individuelles,
  - sortie fusionnée finale.
- Activer les logs détaillés (durée de chaque étape).

### 12.3 Mesures à collecter
1. Durée totale de traitement.
2. Temps par étape:
   - pré-traitement,
   - diarisation,
   - transcription,
   - fusion/mapping.
3. Nombre total de segments.
4. Répartition du temps de parole par speaker.
5. Nombre de corrections manuelles nécessaires sur mapping nom/voix.

### 12.4 Critères de succès pour ce test
1. Exécution complète sans crash ni blocage mémoire.
2. 4 clusters de speakers stables (pas de fragmentation excessive).
3. Sortie finale horodatée cohérente sur toute la réunion.
4. Mapping nom/voix validable en moins de 5 minutes de revue manuelle.
5. Reprise valide après interruption (kill/restart) sans recalcul inutile.

### 12.5 Risques spécifiques sur 45 minutes
- Dérive de cluster speaker au fil du temps:
  - mitigation: re-clustering léger par blocs puis réconciliation globale.
- Temps de calcul trop long en CPU-only:
  - mitigation: modèle ASR plus petit, découpage segmenté, reprise sur artefacts, cache intermédiaire.
- Overlap de voix fréquent:
  - mitigation: marquer les segments ambigus au lieu de forcer un mapping.

### 12.6 Sorties attendues du test
- Un `result.json` complet.
- Un export texte lisible pour revue métier.
- Un mini rapport test (1 page) avec:
  - temps de traitement,
  - qualité perçue,
  - points à corriger avant industrialisation.

---

## 13) Commande CLI type et format rapport de test

### 13.1 Commande de lancement (Sprint 1)
```bash
python -m transcriber run \
  --input var/audio/meeting.wav \
  --lang fr \
  --num-speakers 4 \
  --speaker-names "Alice,Bob,Chloe,David" \
  --output var/output/meeting \
  --save-intermediates \
  --verbose
```

Fichiers générés dans `var/output/meeting/`:
```
meeting.json          # résultat complet (source de vérité)
meeting.txt           # transcription lisible horodatée
meeting.srt           # sous-titres
intermediates/
  diarization.json    # segments bruts diarisation
  segments/
    index.json        # index des segments à transcrire
    seg_000001.wav    # audio segmenté
  transcripts/
    seg_000001.json   # transcription brute par segment
  mapping.json        # proposition de mapping speaker -> nom + scores
run_report.json       # métriques d'exécution
```

### 13.2 Format du rapport de test (run_report.json)
```json
{
  "audio_file": "meeting.wav",
  "audio_duration_s": 2700,
  "run_date": "2026-05-05T14:32:00",
  "timings": {
    "preprocess_s": 8,
    "diarization_s": 124,
    "segmentation_s": 20,
    "asr_s": 310,
    "fusion_s": 12,
    "total_s": 454
  },
  "speakers_found": 4,
  "segments_total": 312,
  "talk_time_ratio": {
    "SPEAKER_00": 0.34,
    "SPEAKER_01": 0.28,
    "SPEAKER_02": 0.22,
    "SPEAKER_03": 0.16
  },
  "mapping_confidence": {
    "SPEAKER_00": { "name": "Alice", "score": 0.91 },
    "SPEAKER_01": { "name": "Bob",   "score": 0.87 },
    "SPEAKER_02": { "name": "Chloe", "score": 0.73 },
    "SPEAKER_03": { "name": "David", "score": 0.68 }
  },
  "warnings": [],
  "resume": {
    "used_cached_wav": true,
    "used_cached_diarization": true,
    "segments_total": 312,
    "segments_transcribed_now": 27,
    "segments_reused": 285
  }
}
```

Lecture rapide:
- `timings.total_s`: temps machine total.
- `mapping_confidence.score`: en dessous de 0.70 → proposer correction manuelle.
- `warnings`: liste les segments ambigus ou erreurs non bloquantes.

### 13.3 Temps de traitement attendus (indicatifs)
| Config           | 45 min audio |
|------------------|-------------|
| CPU-only         | ~15-25 min  |
| GPU (RTX 3060+)  | ~3-6 min    |

Ratio cible acceptable: 1 minute d'audio traitée en < 35 secondes CPU.

---

## 14) Stratégie de tests

### 14.1 Philosophie générale
- Tests unitaires: valider chaque module isolément avec des entrées synthétiques.
- Tests fonctionnels: valider le comportement d'un module dans son contexte réel (vraie audio, vrais modèles).
- Tests d'intégration: valider le pipeline end-to-end sur un fichier réel.
- Tests de reprise: valider que chaque étape est skippée si son artefact existe déjà.
- Le fichier audio de référence pour les tests d'intégration est exclu du dépôt git (voir `.gitignore`).

### 14.2 Arborescence des tests
```
tests/
  unit/
    test_preprocess.py        # conversion audio, normalisation, VAD
    test_diarization.py       # clustering, segmentation
    test_segmenter.py         # découpage audio par segment
    test_asr.py               # transcription d'un segment court
    test_fusion.py            # fusion diarisation + ASR
    test_identity.py          # mapping speaker -> nom, scoring
    test_export.py            # formats de sortie txt/srt/json
  functional/
    test_preprocess_real.py   # sur un vrai fichier court (~30s)
    test_diarization_real.py  # sur un vrai audio 2 speakers
    test_asr_real.py          # transcription réelle d'un segment
    test_pipeline_short.py    # pipeline complet sur ~2 min audio
  integration/
    test_full_pipeline.py     # pipeline complet sur le fichier de référence 45 min
    test_resume_pipeline.py   # relance après interruption
  fixtures/
    short_2speakers.wav       # 30s, 2 speakers, généré synthétiquement
    short_silence.wav         # silence pur pour tester VAD
    short_noise.wav           # bruit de fond pour tester robustesse
var/
  audio/
    test/
      meeting_4speakers_45min.m4a                    # fichier réel (ignoré git)
```

### 14.3 Tests unitaires — détail par module

#### `test_preprocess.py`
- Conversion d'un WAV stéréo → mono 16kHz.
- Conversion d'un MP3 → WAV.
- Conversion d'un M4A → WAV.
- Normalisation du volume (vérifier que le RMS est dans la plage cible).
- VAD: détection correcte de silences sur fixture `short_silence.wav`.
- Rejet d'un fichier corrompu (exception attendue).

#### `test_diarization.py`
- Clustering retourne exactement `N` speakers quand `num_speakers` est forcé.
- Les segments sont non-chevauchants.
- Chaque segment a `start < end`.
- Tri chronologique des segments.
- Pas de segment de durée < 0.1s dans la sortie finale.

#### `test_asr.py`
- Transcription d'un segment de 5s retourne un texte non vide.
- La langue spécifiée est respectée (mock sur modèle).
- Gestion d'un segment silencieux (retourne `""` sans crash).
- Skip correct si le JSON de transcription segment existe déjà.

#### `test_fusion.py`
- Fusion de segments diarisation + ASR sans perte de segments.
- Timestamps cohérents après fusion.
- Regroupement de micro-segments adjacents du même speaker.
- Tri final strict par timestamp même en présence d'overlap.

#### `test_identity.py`
- Mapping correct quand autant de noms que de speakers.
- Score de confiance entre 0.0 et 1.0.
- Segments marqués "unknown" si score < seuil.
- Pas de doublon de nom dans le mapping final.

#### `test_export.py`
- Export JSON respecte le schéma (champs requis présents).
- Export TXT contient tous les timestamps.
- Export SRT: numérotation séquentielle, format timecode valide.

### 14.4 Tests fonctionnels — détail

Les tests fonctionnels utilisent de courts extraits audio synthétiques (fixtures) ou les 2 premières minutes du fichier de référence. Ils valident le comportement réel d'un module isolé, sans exécuter le pipeline complet.

#### `test_preprocess_real.py`
- Traiter `var/audio/test/meeting_4speakers_45min.m4a`.
- Vérifier que le WAV converti est lisible et dure le même temps (±1s).

#### `test_diarization_real.py`
- Diarisation sur les 2 premières minutes du fichier de référence.
- Vérifier que 3-4 clusters sont détectés.

#### `test_asr_real.py`
- Transcrire 30s du début du fichier.
- Vérifier que la sortie est du texte français lisible.

#### `test_pipeline_short.py`
- Pipeline complet sur les 2 premières minutes.
- Vérifier que le JSON de sortie est valide.
- Vérifier qu'au moins 2 speakers sont identifiés.

### 14.5 Tests d'intégration — détail

Les tests d'intégration exécutent le pipeline complet de bout en bout sur le fichier de référence 45 min. Ils ne remplacent pas les tests unitaires et sont lancés séparément (longs).

#### `test_full_pipeline.py`
```python
# Scénario: pipeline complet sur le fichier de référence
INPUT  = "var/audio/test/meeting_4speakers_45min.m4a"
PARAMS = {
    "lang": "fr",
    "num_speakers": 4,
    "speaker_names": ["Alison", "Gabrielle", "Malo", "Lamya"]
}
```
Assertions:
1. Exécution complète sans exception.
2. `result.json` généré et valide.
3. `speakers_found == 4`.
4. Durée couverte ≥ 95% de la durée totale audio.
5. Aucun segment avec `text == null`.
6. Tous les noms fournis sont présents dans `speaker_map`.
7. Temps de traitement logué dans `run_report.json`.

#### `test_resume_pipeline.py`
Scénario:
1. Lancer une première exécution et interrompre après diarisation ou au milieu de l'ASR.
2. Relancer avec les mêmes paramètres.

Assertions:
1. Le WAV n'est pas recalculé s'il existe déjà.
2. `diarization.json` n'est pas recalculé s'il existe déjà.
3. Les segments déjà transcrits ne sont pas retraités.
4. La sortie finale est identique à une exécution propre.

### 14.6 Fixtures synthétiques
Générer les fixtures courtes avec `ffmpeg` pour ne pas dépendre du fichier réel dans les tests unitaires:
```bash
# Silence 5s
ffmpeg -f lavfi -i anullsrc=r=16000:cl=mono -t 5 tests/fixtures/short_silence.wav

# Bruit blanc 10s
ffmpeg -f lavfi -i "anoisesrc=d=10:c=white:r=16000" tests/fixtures/short_noise.wav
```
Les fixtures `short_2speakers.wav` peuvent être générées via `pyttsx3` ou `gTTS` localement.

### 14.7 Outils et commandes
```bash
# Lancer tous les tests unitaires
pytest tests/unit/ -v

# Lancer les tests fonctionnels (nécessite modèles téléchargés)
pytest tests/functional/ -v --timeout=120

# Lancer l'intégration complète (long)
pytest tests/integration/ -v --timeout=1800 -s

# Rapport de couverture
pytest tests/unit/ --cov=transcriber --cov-report=term-missing
```

### 14.8 Seuils de qualité minimum (CI)
| Suite            | Couverture cible | Durée max  |
|------------------|-----------------|------------|
| Unitaires        | > 80%           | < 60s      |
| Fonctionnels     | —               | < 5 min    |
| Intégration      | —               | < 30 min   |
