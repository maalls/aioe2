# Plan — Contrôle qualité de transcript avec LLM

## 1) Objectif

Créer une fonction qui lit un transcript JSON diarizé et produit un compte rendu de qualité ciblé sur la cohérence locale des segments, pour détecter les segments potentiellement mal transcrits ou mal traduits.

Le système doit:
- Identifier les ruptures de cohérence dans le fil de conversation
- Prioriser les segments suspects avec une explication exploitable
- Donner un score global de confiance du transcript
- Rester traçable (raison, contexte, score par segment)

---

## 2) Périmètre fonctionnel (V1)

Entrée:
- Un fichier JSON de transcript (segments, timestamps, speaker, texte)
- Paramètres optionnels (langue attendue, taille de fenêtre contexte, seuil d’alerte)

Sortie:
- Un rapport JSON structuré
- Optionnel: un résumé texte pour l’UI

Détections V1:
- Segment hors contexte sémantique local
- Segment linguistiquement anormal (langue inattendue, bruit, tokenisation cassée)
- Segment contradictoire avec les tours voisins
- Segment possiblement attribué au mauvais speaker (signal faible)

Hors périmètre V1:
- Correction automatique du transcript
- Réécriture complète
- Validation factuelle externe (web, base métier)

---

## 3) Contrat de données

### 3.1 Schéma d’entrée minimal

Chaque segment doit exposer:
- id ou index
- start, end (secondes)
- speaker
- text

Exemple:

```json
{
  "segments": [
    {"id": 12, "start": 125.3, "end": 132.1, "speaker": "SPEAKER_01", "text": "..."}
  ],
  "language": "fr"
}
```

### 3.2 Schéma de sortie proposé

```json
{
  "global_score": 0.0,
  "summary": "...",
  "stats": {
    "total_segments": 0,
    "flagged_segments": 0,
    "high_risk_segments": 0
  },
  "flags": [
    {
      "segment_id": 12,
      "risk_score": 0.87,
      "severity": "high",
      "reason": "Rupture de cohérence contextuelle",
      "evidence": "Le segment introduit un sujet non relié aux 3 tours précédents",
      "context_window": [10, 11, 12, 13, 14],
      "suggested_action": "review-human"
    }
  ]
}
```

---

## 4) Architecture technique recommandée

Pipeline en 4 étapes:

1. Pré-validation
- Vérifier présence des champs requis
- Nettoyer espaces, caractères de contrôle, segments vides
- Normaliser les speakers (ex: SPEAKER_1 vers SPEAKER_01)

2. Feature engineering léger (non LLM)
- Longueur texte, ratio ponctuation, ratio caractères non alphabétiques
- Détection langue par segment (heuristique ou lib légère)
- Similarité segment vers voisins immédiats (embeddings optionnels)

3. Évaluation LLM par fenêtres glissantes
- Construire des fenêtres de contexte (k segments avant et après)
- Demander au LLM d’évaluer le segment central uniquement
- Obtenir un verdict structuré en JSON strict

4. Agrégation et scoring
- Fusionner signaux LLM + heuristiques
- Calculer score de risque par segment
- Générer score global et résumé final

---

## 5) Design du prompt LLM

Règles prompt:
- Instruction précise: évaluer la cohérence conversationnelle, pas réécrire
- Sortie JSON stricte avec schéma figé
- Interdire les textes hors JSON
- Faire noter la confiance du modèle

Template conceptuel:
- Contexte: segments n-2 à n+2
- Cible: segment n
- Critères: continuité thématique, cohérence pragmatique, alignement speaker, qualité linguistique
- Sortie: {is_suspicious, risk_score, reason, evidence, confidence}

Bonnes pratiques:
- Température basse (0 à 0.2)
- max_tokens limité
- Retry avec backoff si JSON invalide

---

## 6) Stratégie de scoring

Score final segment (exemple):
- 60% score LLM de cohérence
- 20% anomalies linguistiques
- 20% rupture statistique locale (similarité faible vs voisins)

Formule indicative:
- risk_score = 0.6 x llm_risk + 0.2 x lang_anomaly + 0.2 x local_break

Seuils:
- low: < 0.40
- medium: 0.40 à 0.69
- high: >= 0.70

Score global transcript:
- moyenne pondérée des risques
- pénalité additionnelle si pics high consécutifs

---

## 7) Intégration dans le projet

Organisation proposée:
- services/transcription_quality/service.py
- services/transcription_quality/schemas.py
- infrastructure/llm/lm_studio_client.py (ou client existant)
- apps/transcriptions/management/commands/check_transcript_quality.py

Entrées possibles:
- Appel CLI pour batch
- Appel depuis vue Django pour usage UI
- Tâche async si transcript long

Commande cible:
- python manage.py check_transcript_quality --input var/output/.../transcript.json --output var/output/.../quality_report.json

---

## 8) Qualité, tests et validation

### 8.1 Jeux de tests

Préparer un dataset de validation:
- 10 à 30 transcripts réels anonymisés
- Segments annotés manuellement: ok ou suspect
- Cas difficiles: interruptions, digressions, code-switching, bruit audio

### 8.2 Tests techniques

Unit tests:
- Parsing JSON entrée
- Construction des fenêtres
- Fusion des scores
- Validation schéma sortie

Integration tests:
- Exécution complète sur transcript fixture
- Stabilité format JSON final
- Gestion erreurs API LLM

### 8.3 Mesures de performance

- Precision@K sur segments signalés
- Recall sur segments réellement problématiques
- Taux de faux positifs par heure d’audio
- Temps de traitement par 1000 segments

Objectif V1 pragmatique:
- Prioriser un bon rappel, puis réduire le bruit

---

## 9) Gouvernance et sécurité

- Ne pas envoyer de données sensibles sans anonymisation
- Journaliser uniquement les métadonnées utiles
- Versionner prompts et schémas de sortie
- Conserver la traçabilité modèle: nom, version, paramètres

---

## 10) Plan d’implémentation par phases

Phase 1 (MVP, 1 à 2 jours):
- Schémas entrée/sortie
- Fenêtres glissantes
- Un appel LLM par segment cible
- Rapport JSON + seuil high/medium/low

Phase 2 (fiabilisation, 2 à 4 jours):
- Ajout heuristiques non LLM
- Fusion des scores
- Retry robuste + validation JSON stricte
- Tests unitaires et intégration de base

Phase 3 (industrialisation, 3 à 5 jours):
- Batch async
- Dashboard simple des segments suspects
- Calibration des seuils sur dataset annoté
- Mesures précision/rappel et tuning

---

## 11) Risques principaux et mitigations

Risque:
- Faux positifs sur conversations très digressives

Mitigation:
- Fenêtre de contexte plus large + calibration par type de réunion

Risque:
- Instabilité de format JSON LLM

Mitigation:
- Mode JSON strict, parser tolérant, retry borné

Risque:
- Coût/latence sur gros transcripts

Mitigation:
- Échantillonnage initial, batching, exécution async, cache par segment

---

## 12) Définition de done (V1)

La fonctionnalité est considérée terminée si:
- Une commande exécutable génère un rapport de qualité JSON valide
- Les segments suspects incluent raison et preuve contextuelle
- Le score global est calculé et documenté
- Les tests unitaires critiques passent
- Au moins un jeu de transcripts annotés est utilisé pour calibration initiale
