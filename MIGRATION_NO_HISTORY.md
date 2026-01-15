# 🔄 Migration : Supprimer l'historique des jobs

## 📋 Objectif

Modifier le système pour que **chaque job n'ait qu'un seul état** (le dernier) dans DynamoDB, sans conserver l'historique des changements d'état.

---

## 🎯 Changements nécessaires

### ✅ Dashboard (FAIT)
- ✅ Méthode `get_latest_state_per_job()` simplifiée
- ✅ Méthode `get_job_history()` modifiée pour récupérer un seul état
- ✅ Section "Historique" supprimée du dashboard
- ✅ Ajout de la section "Événement AWS complet" pour voir le JSON brut

### ⏳ AWS (À FAIRE)

#### 1. Créer une nouvelle table DynamoDB

**Option A : Nouvelle table (Recommandé)**

1. Aller dans la console DynamoDB : https://eu-west-1.console.aws.amazon.com/dynamodbv2/home?region=eu-west-1

2. Cliquer sur **"Create table"**

3. Configuration :
   - **Table name** : `MonitoringToolTest_V2`
   - **Partition key** : `jobId` (Type: String)
   - **Sort key** : ❌ **NE PAS AJOUTER** (laisser vide)
   - **Table settings** : Default settings
   - Cliquer sur **"Create table"**

4. Attendre que la table soit créée (statut "Active")

**Option B : Modifier la table existante**

⚠️ **Impossible** : On ne peut pas modifier la clé primaire d'une table DynamoDB existante.

---

#### 2. Modifier la Lambda MonitoringTaskPOC

**Code complet de la Lambda :**

```python
import json
import boto3
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('MonitoringToolTest_V2')  # ← Nouvelle table

def lambda_handler(event, context):
    # Extraire les données de l'événement
    detail = event.get('detail', {})
    
    job_id = detail.get('jobId')
    job_name = detail.get('jobName')
    status = detail.get('status')
    job_queue = detail.get('jobQueue')
    job_definition = detail.get('jobDefinition')
    status_reason = detail.get('statusReason', '')
    
    # Extraire le Media ID (si configuré)
    media_id = detail.get('media_id')  # Ou extraction depuis jobName/tags/parameters
    
    # Timestamp
    timestamp = event.get('time', datetime.utcnow().isoformat())
    
    # Région et compte
    region = event.get('region')
    account = event.get('account')
    
    # Préparer l'item pour DynamoDB
    item = {
        'jobId': job_id,  # ← Clé primaire UNIQUEMENT (pas de Sort Key)
        'timestamp': timestamp,  # ← Devient un attribut normal
        'jobName': job_name,
        'status': status,
        'jobQueue': job_queue,
        'jobDefinition': job_definition,
        'region': region,
        'account': account,
        'statusReason': status_reason,
        'fullEvent': json.dumps(event)
    }
    
    # Ajouter media_id si disponible
    if media_id:
        item['media_id'] = media_id
    
    # PUT écrase automatiquement l'ancien item avec le même jobId
    table.put_item(Item=item)
    
    print(f"✅ Job {job_id} mis à jour avec le statut {status}")
    
    return {
        'statusCode': 200,
        'body': json.dumps(f'Job {job_id} updated to status {status}')
    }
```

**Étapes dans la console Lambda :**

1. Aller dans AWS Lambda : https://eu-west-1.console.aws.amazon.com/lambda/home?region=eu-west-1

2. Chercher la fonction **`MonitoringTaskPOC`**

3. Cliquer dessus

4. Dans l'onglet **"Code"**, remplacer le code par celui ci-dessus

5. Cliquer sur **"Deploy"** (bouton orange)

6. Attendre le message "Successfully updated"

---

#### 3. Modifier le dashboard pour pointer vers la nouvelle table

**Fichier : `dynamo_queries.py`**

Ligne 16, changer :
```python
def __init__(self, table_name: str = 'MonitoringToolTest_V2', region: str = 'eu-west-1'):
```

---

## 🧪 Test

### 1. Tester la Lambda

1. Dans la console Lambda, cliquer sur **"Test"**

2. Créer un événement de test :

```json
{
  "version": "0",
  "id": "test-123",
  "detail-type": "Batch Job State Change",
  "source": "aws.batch",
  "account": "388659957718",
  "time": "2024-12-24T10:00:00Z",
  "region": "eu-west-1",
  "detail": {
    "jobId": "test-job-001",
    "jobName": "pre-694a9d57b88940a9e5cd3bee-1766497635776",
    "status": "RUNNING",
    "jobQueue": "arn:aws:batch:eu-west-1:388659957718:job-queue/orchestrator-standard-pre",
    "jobDefinition": "arn:aws:batch:eu-west-1:388659957718:job-definition/storage-pre-v2:129",
    "statusReason": "Test"
  }
}
```

3. Cliquer sur **"Test"**

4. Vérifier dans DynamoDB que l'item a été créé

5. Modifier le statut dans l'événement de test (ex: "SUCCEEDED") et re-tester

6. Vérifier dans DynamoDB que l'item a été **mis à jour** (pas de doublon)

---

## ✅ Vérification finale

1. **DynamoDB** : Vérifier qu'il n'y a qu'un seul item par jobId
2. **Dashboard** : Lancer le dashboard et vérifier que tout s'affiche correctement
3. **Pas d'historique** : Vérifier que la section "Historique" a disparu

---

## 🗑️ Nettoyage (Optionnel)

Une fois que tout fonctionne avec la nouvelle table :

1. Supprimer l'ancienne table `MonitoringToolTest` (pour économiser les coûts)
2. Renommer `MonitoringToolTest_V2` en `MonitoringToolTest` (optionnel)

---

## 📝 Résumé des avantages

✅ **Plus simple** : Un seul état par job  
✅ **Plus rapide** : Pas besoin de déduplication  
✅ **Moins cher** : Moins de données stockées  
✅ **Plus clair** : Pas de confusion avec les anciens états  

## ⚠️ Inconvénient

❌ **Pas d'historique** : Impossible de voir les changements d'état passés  
   → Solution : Si besoin d'historique, activer CloudWatch Logs sur la Lambda

