"""
Code de la Lambda MonitoringTaskPOC - Version sans historique
À copier-coller dans la console AWS Lambda

Cette version stocke uniquement le dernier état de chaque job (pas d'historique).
"""

import json
import boto3
from datetime import datetime

# Connexion à DynamoDB
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('MonitoringToolTest_V2')  # ← Nouvelle table sans Sort Key


def lambda_handler(event, context):
    """
    Handler principal de la Lambda
    Reçoit les événements AWS Batch depuis EventBridge et les stocke dans DynamoDB
    """
    
    # Extraire les données de l'événement AWS Batch
    detail = event.get('detail', {})
    
    job_id = detail.get('jobId')
    job_name = detail.get('jobName')
    status = detail.get('status')
    job_queue = detail.get('jobQueue')
    job_definition = detail.get('jobDefinition')
    status_reason = detail.get('statusReason', '')
    
    # Extraire le Media ID (si configuré)
    # Option 1 : Depuis l'événement directement
    media_id = detail.get('media_id')
    
    # Option 2 : Depuis les paramètres du job
    if not media_id:
        parameters = detail.get('parameters', {})
        media_id = parameters.get('media_id')
    
    # Option 3 : Depuis les tags
    if not media_id:
        tags = detail.get('tags', {})
        media_id = tags.get('media_id')
    
    # Option 4 : Extraire depuis le jobName (si c'est un ID MongoDB de 24 caractères)
    if not media_id and job_name:
        parts = job_name.split('-')
        for part in parts:
            if len(part) == 24 and all(c in '0123456789abcdef' for c in part.lower()):
                media_id = part
                break
    
    # Timestamp de l'événement
    timestamp = event.get('time', datetime.utcnow().isoformat())
    
    # Région et compte AWS
    region = event.get('region')
    account = event.get('account')
    
    # Préparer l'item pour DynamoDB
    item = {
        'jobId': job_id,  # ← Clé primaire UNIQUEMENT (pas de Sort Key)
        'timestamp': timestamp,  # ← Devient un attribut normal (pas une clé)
        'jobName': job_name,
        'status': status,
        'jobQueue': job_queue,
        'jobDefinition': job_definition,
        'region': region,
        'account': account,
        'statusReason': status_reason,
        'fullEvent': json.dumps(event)  # Événement complet en JSON
    }
    
    # Ajouter media_id seulement s'il existe
    if media_id:
        item['media_id'] = media_id
    
    # Stocker dans DynamoDB
    # put_item écrase automatiquement l'ancien item avec le même jobId
    # → Pas d'historique, uniquement le dernier état
    table.put_item(Item=item)
    
    print(f"✅ Job {job_id} mis à jour avec le statut {status}")
    
    return {
        'statusCode': 200,
        'body': json.dumps(f'Job {job_id} updated to status {status}')
    }


# Pour tester localement (optionnel)
if __name__ == "__main__":
    # Événement de test
    test_event = {
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
    
    # Tester
    result = lambda_handler(test_event, None)
    print(result)

