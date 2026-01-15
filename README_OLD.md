# 📊 Dashboard de Monitoring AWS Batch

Dashboard Streamlit pour visualiser et monitorer les jobs AWS Batch en temps réel.

## 🎯 Fonctionnalités

- ✅ **Vue d'ensemble** : Statistiques globales (taux de succès, jobs actifs)
- ✅ **Tableau interactif** : Tous les jobs avec filtres par statut, type, période
- ✅ **Détails des jobs** : Informations complètes + événement AWS brut
- ✅ **Coloration automatique** : Vert (SUCCEEDED), Rouge (FAILED), Bleu (RUNNING)
- ✅ **Extraction intelligente** : Task ID, Media ID, Task Type
- ✅ **Rafraîchissement** : Cache de 60s + bouton manuel

## 🏗️ Architecture

```
AWS Batch → EventBridge → Lambda → DynamoDB → Dashboard Streamlit
```

### Composants AWS

- **EventBridge** : Capture tous les événements AWS Batch
- **Lambda MonitoringTaskPOC** : Traite et stocke les événements
- **DynamoDB MonitoringToolTest_V2** : Stockage centralisé (dernier état uniquement)

### Composants Dashboard

- **app.py** : Interface Streamlit
- **dynamo_queries.py** : Module de requêtes DynamoDB
- **requirements.txt** : Dépendances Python

## 📋 Structure DynamoDB

**Table** : `MonitoringToolTest_V2`
- **Partition Key** : `jobId` (String)
- **Pas de Sort Key** → Un seul état par job (le dernier)

**Attributs stockés** :
- `jobId`, `timestamp`, `jobName`, `status`
- `jobQueue`, `jobDefinition`, `region`, `account`
- `statusReason`, `fullEvent` (JSON complet)
- `media_id` (optionnel)

## 🚀 Installation

Voir le fichier `README_SETUP.md` pour les instructions détaillées.

## 📝 Migration

Si vous avez l'ancienne version avec historique, voir `MIGRATION_NO_HISTORY.md`.

## 📁 Fichiers Importants

- **`app.py`** : Dashboard principal
- **`dynamo_queries.py`** : Requêtes DynamoDB
- **`lambda_code_no_history.py`** : Code de la Lambda AWS
- **`MIGRATION_NO_HISTORY.md`** : Guide de migration
- **`RESUME_MODIFICATIONS.md`** : Résumé des changements

## 🎨 Colonnes Affichées

1. **Media ID** : Identifiant du média
2. **Task ID** : Identifiant de la tâche (extrait du jobName)
3. **Task Type** : Type de tâche (storage, assembly, etc.)
4. **Status** : État actuel du job
5. **Job ID** : Identifiant AWS du job
6. **Job Name** : Nom complet du job
7. **Region** : Région AWS
8. **Timestamp** : Date/heure de l'événement
9. **Status Reason** : Raison du statut

## 🔧 Configuration

Par défaut, le dashboard se connecte à :
- **Table DynamoDB** : `MonitoringToolTest_V2`
- **Région AWS** : `eu-west-1`

Pour changer, modifier `dynamo_queries.py` ligne 16.

## 📊 Utilisation

```bash
cd mon-dashboard-streamlit
streamlit run app.py
```

Ouvrir : http://localhost:8501

## ⚠️ Note Importante

Cette version **ne conserve pas l'historique** des changements d'état. Seul le dernier état de chaque job est stocké.

Si vous avez besoin de l'historique, voir les solutions alternatives dans `RESUME_MODIFICATIONS.md`.
