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

## 2) Approche recommandée (multi-passes)
L’approche la plus robuste est une pipeline en plusieurs passes:

1. **Pré-traitement audio**
2. **Diarisation (qui parle quand)**
3. **Transcription segmentée (quoi est dit)**
4. **Attribution d’identité (A/B/C -> noms)**
5. **Post-traitement + fusion + export**

Pourquoi ce choix:
- Séparer `qui parle` de `ce qui est dit` donne de meilleurs résultats qu’une transcription brute monolithique.
- Permet d’améliorer chaque étape indépendamment.
- Facilite les corrections utilisateur (surtout sur les speakers).

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

## 4.1 Pré-traitement
- Conversion en format standard (mono, 16 kHz WAV).
- Normalisation du volume.
- Réduction de bruit légère (optionnelle).
- Détection de silences.

Objectif: stabiliser la diarisation et la transcription.

## 4.2 Diarisation (passage 1)
- Détecter les segments de parole (VAD: Voice Activity Detection).
- Extraire des embeddings vocaux (x-vectors / ECAPA / pyannote embeddings).
- Clustering des segments par voix.

Stratégie du nombre de speakers:
- Si utilisateur fournit `N`: contraindre le clustering à `N`.
- Sinon: estimer `N` automatiquement (BIC, silhouette score, méthodes pyannote).

Sortie intermédiaire:
- timeline avec segments: `[start, end, speaker_id]`.

## 4.3 Transcription segmentée (passage 2)
- Transcrire chaque segment diarizé avec un ASR local (ex: faster-whisper / WhisperX).
- Utiliser la langue fournie ou auto-détection.
- Aligner les timestamps au mot si possible.

Important:
- Regrouper intelligemment les micro-segments adjacents du même speaker pour éviter un texte haché.

## 4.4 Réconciliation diarisation/transcription (passage 3)
- Corriger les chevauchements temporels.
- Lisser les changements de speaker trop fréquents (jitter).
- Re-segmenter si un segment est trop long (>30-45s) ou trop court (<0.7s).

## 4.5 Mapping identité (A/B/C -> noms)
- Si l’utilisateur a donné une liste de noms:
  - proposer un mapping semi-automatique (`Personne A = Alice ?`) avec validation.
- Si voix de référence dispo:
  - matching par similarité d’embeddings.

## 4.6 Post-traitement texte
- Ponctuation/capitalisation (si modèle ASR ne le fait pas bien).
- Option: résumé automatique, extraction d’actions.
- Export `.txt`, `.srt`, `.json` (json conseillé pour debug/édition).

---

## 5) Architecture logicielle proposée

## 5.1 Modules
- `ingest`: upload et conversion audio.
- `preprocess`: normalisation + VAD.
- `diarization`: segmentation + clustering + speaker labels.
- `asr`: transcription des segments.
- `fusion`: fusion diarisation + ASR.
- `identity`: mapping vers noms.
- `export`: txt/srt/json.
- `review-ui` (optionnel MVP+): interface correction labels.

## 5.2 Données intermédiaires (format JSON)
Exemple de schéma:
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

---

## 6) Stack technique (local uniquement)

## Stack recommandée
- Python
- `pyannote.audio` (diarisation)
- `faster-whisper` ou `whisperx` (ASR)
- `ffmpeg` (conversion)

Avantages:
- Contrôle total, coût variable faible.
- Données sensibles restent localement.

Inconvénients:
- Complexité d’intégration/perf.
- Besoin CPU/GPU selon volume.

Contraintes à anticiper:
- Performance dépendante du matériel local.
- Temps de traitement potentiellement plus long sans GPU.

---

## 7) Roadmap d’implémentation

## MVP (2-4 semaines)
- Upload fichier audio.
- Formulaire assisté: langue + nombre participants + noms (optionnels).
- Diarisation auto + transcription.
- Sortie `Personne A/B/C` horodatée.
- Export `.txt` + `.json`.

## V1 (4-8 semaines)
- Meilleur mapping speakers->noms.
- Export `.srt`.
- Interface de correction manuelle des speakers.

## V2 (8+ semaines)
- Voix de référence par participant.
- Traitement batch multi-fichiers.
- Résumé/chapitres/actions.
- Metrics dashboard qualité.

---

## 8) Métriques qualité à suivre
- `WER` (Word Error Rate) pour transcription.
- `DER` (Diarization Error Rate) pour speakers.
- Taux de segments avec speaker corrigé manuellement.
- Temps de traitement par minute d’audio.

Objectif pratique initial:
- DER < 20% sur réunions standards.
- WER acceptable en français conversationnel (<20-25% en bruit modéré).

---

## 9) Risques & mitigations
- Bruit élevé / voix qui se chevauchent:
  - Mitigation: VAD robuste, modèle diarisation adapté réunions.
- Beaucoup de participants (>6):
  - Mitigation: demander `N` à l’utilisateur, correction UI simple.
- Forte variabilité d’accents/langues:
  - Mitigation: sélection langue explicite, modèles adaptés.
- Saturation machine locale (CPU/GPU/RAM):
  - Mitigation: file d’attente des jobs, batch processing, cache des résultats intermédiaires.

---

## 10) Décisions à valider avant de coder
1. Cible matérielle minimale (CPU-only ou GPU recommandé)?
2. Temps maximal acceptable de traitement par heure d’audio?
3. Langues cibles initiales (fr uniquement ou multilingue)?
4. Volume attendu (heures/jour) pour dimensionner l’infrastructure locale.
5. Besoin d’interface de correction dès MVP ou en V1.

---

## 11) Proposition d’approche “meilleur rapport qualité/effort”
- Commencer par **Mode assisté léger**:
  - demander langue + nombre de participants + noms (optionnels).
- Pipeline **3 passes**:
  1. Diarisation,
  2. Transcription segmentée,
  3. Réconciliation + mapping noms.
- Ajouter une mini étape de validation humaine finale (2-3 minutes) pour corriger les speakers.

Cette approche donne généralement un gros gain qualité sans complexifier excessivement le produit.

---

## 12) Prochaine étape technique suggérée
Implémenter un POC CLI qui prend un fichier audio et produit un `result.json` diarizé+transcrit.
Ensuite brancher une UI simple pour revue et export.

---

## 13) Sprint 1 — Checklist technique actionnable

Objectif Sprint 1:
- Obtenir un POC local CLI qui prend un fichier audio et sort un JSON diarisation + transcription utilisable.

Durée cible:
- 5 à 8 jours de dev.

### 13.1 Tâches (ordre recommandé)
1. Initialiser le projet Python local.
2. Ajouter les dépendances de base (`ffmpeg`, `pyannote.audio`, `faster-whisper` ou `whisperx`, `typer`/`argparse`).
3. Créer une commande CLI: entrée audio + options `--lang`, `--num-speakers`, `--speaker-names`.
4. Implémenter la conversion audio standard (mono, 16kHz, WAV).
5. Implémenter la diarisation (segments `[start, end, speaker_id]`).
6. Implémenter la transcription segmentée par speaker.
7. Fusionner en un format JSON unique (`segments`, `speaker_map`, `metadata`).
8. Ajouter exports `.txt` et `.srt` basiques.
9. Ajouter logs + gestion d’erreurs (audio invalide, modèle manquant, OOM).
10. Ajouter 3 tests d’intégration sur fichiers audio courts (1, 2, 3 speakers).

### 13.2 Livrables de fin de sprint
- Un exécutable CLI local:
  - Exemple: `transcriber run --input ./var/audio/meeting.wav --lang fr --num-speakers 3 --speaker-names "Alice,Bob,Chloe"`
- Un fichier de sortie JSON stable (schéma documenté).
- Un export texte lisible avec timestamps et speakers.
- Un README d’exécution locale (pré-requis machine + commande de lancement).

### 13.3 Critères d’acceptation (Definition of Done)
- Le CLI traite un fichier de 15 minutes sans crash sur machine cible.
- Le JSON contient 100% des segments avec `start`, `end`, `speaker`, `text`.
- Les speakers sont cohérents (pas de sauts excessifs sur phrases continues).
- Les noms fournis par l’utilisateur sont correctement mappés quand disponibles.
- Le pipeline fonctionne sans aucun service cloud.

### 13.4 Stratégie de validation rapide
- Cas 1: audio calme, 2 speakers, langue française.
- Cas 2: audio réunion, 3-4 speakers, interruptions courtes.
- Cas 3: audio bruité (vérifier robustesse minimale).

Mesures à relever pour chaque cas:
- Temps total de traitement.
- Nombre de segments générés.
- Estimation qualitative de DER et lisibilité de la transcription.

### 13.5 Backlog immédiat Sprint 2 (pré-placé)
- UI minimale de revue/correction des speakers.
- Amélioration du mapping noms via embeddings de référence.
- Optimisation perf CPU/GPU (batching, cache intermédiaire).

---

## 14) Protocole de test cible (4 speakers, 45 minutes)

Objectif:
- Valider que le pipeline local tient un cas réaliste long avec 4 intervenants.

### 14.1 Préparation
1. Placer le fichier audio de test dans `var/audio/`.
2. Vérifier que le fichier est lisible et dans un format stable (WAV/MP3/M4A).
3. Préparer les métadonnées utilisateur:
   - `num_speakers = 4`
   - noms (ex: Alice, Bob, Chloe, David)
   - langue principale (ex: fr)

### 14.2 Paramètres de lancement recommandés
- Forcer `num_speakers=4` (ne pas laisser en auto pour ce test).
- Activer l'écriture des artefacts intermédiaires:
  - segments diarisation bruts,
  - transcription segmentée,
  - sortie fusionnée finale.
- Activer les logs détaillés (durée de chaque étape).

### 14.3 Mesures à collecter
1. Durée totale de traitement.
2. Temps par étape:
   - pré-traitement,
   - diarisation,
   - transcription,
   - fusion/mapping.
3. Nombre total de segments.
4. Répartition du temps de parole par speaker.
5. Nombre de corrections manuelles nécessaires sur mapping nom/voix.

### 14.4 Critères de succès pour ce test
1. Exécution complète sans crash ni blocage mémoire.
2. 4 clusters de speakers stables (pas de fragmentation excessive).
3. Sortie finale horodatée cohérente sur toute la réunion.
4. Mapping nom/voix validable en moins de 5 minutes de revue manuelle.

### 14.5 Risques spécifiques sur 45 minutes
- Dérive de cluster speaker au fil du temps:
  - mitigation: re-clustering léger par blocs puis réconciliation globale.
- Temps de calcul trop long en CPU-only:
  - mitigation: modèle ASR plus petit, traitement par chunks, cache intermédiaire.
- Overlap de voix fréquent:
  - mitigation: marquer les segments ambigus au lieu de forcer un mapping.

### 14.6 Sorties attendues du test
- Un `result.json` complet.
- Un export texte lisible pour revue métier.
- Un mini rapport test (1 page) avec:
  - temps de traitement,
  - qualité perçue,
  - points à corriger avant industrialisation.

---

## 15) Commande CLI type et format rapport de test

### 15.1 Commande de lancement (Sprint 1)
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
  asr_segments.json   # transcription brute par segment
  mapping.json        # proposition de mapping speaker -> nom + scores
run_report.json       # métriques d'exécution
```

### 15.2 Format du rapport de test (run_report.json)
```json
{
  "audio_file": "meeting.wav",
  "audio_duration_s": 2700,
  "run_date": "2026-05-05T14:32:00",
  "timings": {
    "preprocess_s": 8,
    "diarization_s": 124,
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
  "warnings": []
}
```

Lecture rapide:
- `timings.total_s`: temps machine total.
- `mapping_confidence.score`: en dessous de 0.70 → proposer correction manuelle.
- `warnings`: liste les segments ambigus ou erreurs non bloquantes.

### 15.3 Temps de traitement attendus (indicatifs)
| Config           | 45 min audio |
|------------------|-------------|
| CPU-only         | ~15-25 min  |
| GPU (RTX 3060+)  | ~3-6 min    |

Ratio cible acceptable: 1 minute d'audio traitée en < 35 secondes CPU.

---

## 16) Stratégie de tests

### 16.1 Philosophie générale
- Tests unitaires: valider chaque module isolément avec des entrées synthétiques.
- Tests fonctionnels: valider le comportement d'un module dans son contexte réel (vraie audio, vrais modèles).
- Tests d'intégration: valider le pipeline end-to-end sur un fichier réel.
- Le fichier audio de référence pour les tests d'intégration est exclu du dépôt git (voir `.gitignore`).

### 16.2 Arborescence des tests
```
tests/
  unit/
    test_preprocess.py        # conversion audio, normalisation, VAD
    test_diarization.py       # clustering, segmentation
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
  fixtures/
    short_2speakers.wav       # 30s, 2 speakers, généré synthétiquement
    short_silence.wav         # silence pur pour tester VAD
    short_noise.wav           # bruit de fond pour tester robustesse
var/
  audio/
    test/
      meeting_4speakers_45min.m4a                    # fichier réel (ignoré git)
```

### 16.3 Tests unitaires — détail par module

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

#### `test_fusion.py`
- Fusion de segments diarisation + ASR sans perte de segments.
- Timestamps cohérents après fusion.
- Regroupement de micro-segments adjacents du même speaker.

#### `test_identity.py`
- Mapping correct quand autant de noms que de speakers.
- Score de confiance entre 0.0 et 1.0.
- Segments marqués "unknown" si score < seuil.
- Pas de doublon de nom dans le mapping final.

#### `test_export.py`
- Export JSON respecte le schéma (champs requis présents).
- Export TXT contient tous les timestamps.
- Export SRT: numérotation séquentielle, format timecode valide.

### 16.4 Tests fonctionnels — détail

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

### 16.5 Tests d'intégration — détail

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

### 16.6 Fixtures synthétiques
Générer les fixtures courtes avec `ffmpeg` pour ne pas dépendre du fichier réel dans les tests unitaires:
```bash
# Silence 5s
ffmpeg -f lavfi -i anullsrc=r=16000:cl=mono -t 5 tests/fixtures/short_silence.wav

# Bruit blanc 10s
ffmpeg -f lavfi -i "anoisesrc=d=10:c=white:r=16000" tests/fixtures/short_noise.wav
```
Les fixtures `short_2speakers.wav` peuvent être générées via `pyttsx3` ou `gTTS` localement.

### 16.7 Outils et commandes
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

### 16.8 Seuils de qualité minimum (CI)
| Suite            | Couverture cible | Durée max  |
|------------------|-----------------|------------|
| Unitaires        | > 80%           | < 60s      |
| Fonctionnels     | —               | < 5 min    |
| Intégration      | —               | < 30 min   |
