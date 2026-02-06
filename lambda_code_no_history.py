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
table = dynamodb.Table('MonitoringToolTest')  # ← Votre table actuelle


def extract_media_id_from_event(event):
    """
    Extrait le Media ID depuis l'événement AWS Batch
    Cherche dans detail.container.command l'argument --media_id
    """
    try:
        command = event.get('detail', {}).get('container', {}).get('command', [])

        # Trouver --media_id dans la commande
        for i, arg in enumerate(command):
            if arg == '--media_id' and i + 1 < len(command):
                return command[i + 1]

        return None  # Pas de media_id trouvé

    except Exception as e:
        print(f"Erreur lors de l'extraction du media_id: {e}")
        return None


def extract_workspace_uid_from_event(event):
    """
    Extrait le Workspace UID depuis l'événement AWS Batch
    Cherche dans detail.container.command l'argument --wuid
    """
    try:
        command = event.get('detail', {}).get('container', {}).get('command', [])

        # Trouver --wuid dans la commande
        for i, arg in enumerate(command):
            if arg == '--wuid' and i + 1 < len(command):
                return command[i + 1]

        return None

    except Exception as e:
        print(f"Erreur lors de l'extraction du workspace_uid: {e}")
        return None


def extract_task_id_from_event(event):
    """
    Extrait le Task ID depuis l'événement AWS Batch
    Cherche dans detail.container.command l'argument --task_id
    """
    try:
        command = event.get('detail', {}).get('container', {}).get('command', [])

        # Trouver --task_id dans la commande
        for i, arg in enumerate(command):
            if arg == '--task_id' and i + 1 < len(command):
                return command[i + 1]

        return None

    except Exception as e:
        print(f"Erreur lors de l'extraction du task_id: {e}")
        return None


def extract_assembly_id_from_event(event):
    """
    Extrait l'Assembly ID depuis l'événement AWS Batch
    Pour les jobs Assembly, l'ID est dans le job name
    Format: assembly-pre-LABEL-ASSEMBLY_ID-zip_package-DURATION
    Exemple: assembly-pre-06_02_26_10_14_cart-6985b698fa887fdaa7e55c0b-zip_package-400sec
    """
    try:
        detail = event.get('detail', {})
        job_name = detail.get('jobName', '')

        # Vérifier que c'est bien un job assembly
        if not job_name or not job_name.startswith('assembly-'):
            return None

        # Séparer par tirets
        parts = job_name.split('-')

        # Chercher une partie qui ressemble à un ID MongoDB (24 caractères hexadécimaux)
        for part in parts:
            if len(part) == 24 and all(c in '0123456789abcdef' for c in part.lower()):
                return part

        return None

    except Exception as e:
        print(f"Erreur lors de l'extraction de l'assembly_id: {e}")
        return None


def lambda_handler(event, context):
    """
    Handler principal de la Lambda
    Reçoit les événements AWS Batch depuis EventBridge et les stocke dans DynamoDB
    """

    # Logger l'événement reçu (utile pour le debug)
    print(f"Received event: {json.dumps(event)}")

    # Extraire les données de l'événement AWS Batch
    detail = event.get('detail', {})

    job_id = detail.get('jobId', 'unknown')
    job_name = detail.get('jobName', '')
    status = detail.get('status', '')
    job_queue = detail.get('jobQueue', '')
    job_definition = detail.get('jobDefinition', '')
    status_reason = detail.get('statusReason', '')

    # Détecter si c'est un job Assembly
    is_assembly_job = job_name.startswith('assembly-')

    # Initialiser les variables
    media_id = None
    task_id = None
    assembly_id = None
    workspace_uid = None

    if is_assembly_job:
        # Pour les jobs Assembly
        # Format: assembly-{WORKSPACE_UID}-{LABEL}-{ASSEMBLY_ID}-zip_package-{DURATION}
        # Exemple: assembly-pre-06_02_26_10_14_cart-6985b698fa887fdaa7e55c0b-zip_package-400sec

        # Extraire workspace_uid depuis le job name (2ème partie)
        parts = job_name.split('-')
        if len(parts) > 1:
            workspace_uid = parts[1]  # "pre"

        # Extraire assembly_id (ID de 24 caractères hexadécimaux)
        assembly_id = extract_assembly_id_from_event(event)

        # Les jobs Assembly n'ont PAS de media_id ni task_id
        # On les laisse à None

    else:
        # Pour les autres jobs (Ingest, Storage, Text Recognition, etc.)

        # Extraire le media_id depuis la commande (méthode principale)
        media_id = extract_media_id_from_event(event)

        # Fallback : Extraire depuis le jobName (si c'est un ID MongoDB de 24 caractères)
        if not media_id and job_name:
            parts = job_name.split('-')
            for part in parts:
                if len(part) == 24 and all(c in '0123456789abcdef' for c in part.lower()):
                    media_id = part
                    break

        # Extraire le workspace_uid depuis la commande (argument --wuid)
        workspace_uid = extract_workspace_uid_from_event(event)

        # Extraire le task_id depuis la commande (argument --task_id)
        task_id = extract_task_id_from_event(event)

        # Fallback : Extraire task_id depuis le jobName (si c'est un ID MongoDB de 24 caractères)
        if not task_id and job_name:
            parts = job_name.split('-')
            for part in parts:
                if len(part) == 24 and all(c in '0123456789abcdef' for c in part.lower()):
                    task_id = part
                    break

    # Timestamp de l'événement
    timestamp = event.get('time', datetime.utcnow().isoformat())
    
    # Région et compte AWS
    region = event.get('region')
    account = event.get('account')
    
    # Préparer l'item pour DynamoDB
    item = {
        'jobId': job_id,
        'timestamp': timestamp,
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

    # Ajouter workspace_uid seulement s'il existe
    if workspace_uid:
        item['workspace_uid'] = workspace_uid

    # Ajouter task_id seulement s'il existe
    if task_id:
        item['task_id'] = task_id

    # Ajouter assembly_id seulement s'il existe
    if assembly_id:
        item['assembly_id'] = assembly_id

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

