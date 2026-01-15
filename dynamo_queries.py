"""
Module pour gérer les requêtes DynamoDB
Utilisé par le dashboard Streamlit pour récupérer les données AWS Batch
"""

import boto3
from boto3.dynamodb.conditions import Attr, Key
from datetime import datetime, timedelta
import pandas as pd
from typing import List, Dict, Optional


class DynamoDBQueries:
    """Classe pour gérer toutes les requêtes DynamoDB"""
    
    def __init__(self, table_name: str = 'MonitoringToolTest', region: str = 'eu-west-1'):
        """
        Initialise la connexion à DynamoDB
        
        Args:
            table_name: Nom de la table DynamoDB
            region: Région AWS
        """
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.table = self.dynamodb.Table(table_name)
        self.table_name = table_name
        self.region = region
    
    def get_all_jobs(self) -> List[Dict]:
        """
        Récupère tous les jobs de la table DynamoDB
        Gère automatiquement la pagination
        
        Returns:
            Liste de tous les items (jobs)
        """
        print(f"📥 Récupération de tous les jobs depuis {self.table_name}...")
        
        response = self.table.scan()
        items = response['Items']
        
        # Gérer la pagination (si > 1MB de données)
        while 'LastEvaluatedKey' in response:
            print(f"   Pagination... {len(items)} items récupérés jusqu'à présent")
            response = self.table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response['Items'])
        
        print(f"✅ {len(items)} jobs récupérés au total")
        return items
    
    def get_failed_jobs(self) -> List[Dict]:
        """
        Récupère uniquement les jobs avec le statut FAILED
        
        Returns:
            Liste des jobs en échec
        """
        print(f"📥 Récupération des jobs FAILED...")
        
        response = self.table.scan(
            FilterExpression=Attr('status').eq('FAILED')
        )
        items = response['Items']
        
        while 'LastEvaluatedKey' in response:
            response = self.table.scan(
                ExclusiveStartKey=response['LastEvaluatedKey'],
                FilterExpression=Attr('status').eq('FAILED')
            )
            items.extend(response['Items'])
        
        print(f"✅ {len(items)} jobs FAILED récupérés")
        return items
    
    def get_jobs_by_status(self, status: str) -> List[Dict]:
        """
        Récupère les jobs par statut
        
        Args:
            status: Statut du job (RUNNING, SUCCEEDED, FAILED, etc.)
        
        Returns:
            Liste des jobs avec ce statut
        """
        print(f"📥 Récupération des jobs avec statut '{status}'...")
        
        response = self.table.scan(
            FilterExpression=Attr('status').eq(status)
        )
        items = response['Items']
        
        while 'LastEvaluatedKey' in response:
            response = self.table.scan(
                ExclusiveStartKey=response['LastEvaluatedKey'],
                FilterExpression=Attr('status').eq(status)
            )
            items.extend(response['Items'])
        
        print(f"✅ {len(items)} jobs avec statut '{status}' récupérés")
        return items
    
    def get_jobs_by_queue(self, queue_name: str) -> List[Dict]:
        """
        Récupère les jobs d'une queue spécifique
        
        Args:
            queue_name: Nom de la queue (ex: 'orchestrator')
        
        Returns:
            Liste des jobs de cette queue
        """
        print(f"📥 Récupération des jobs de la queue '{queue_name}'...")
        
        response = self.table.scan(
            FilterExpression=Attr('jobQueue').contains(queue_name)
        )
        items = response['Items']
        
        while 'LastEvaluatedKey' in response:
            response = self.table.scan(
                ExclusiveStartKey=response['LastEvaluatedKey'],
                FilterExpression=Attr('jobQueue').contains(queue_name)
            )
            items.extend(response['Items'])
        
        print(f"✅ {len(items)} jobs de la queue '{queue_name}' récupérés")
        return items
    
    def get_jobs_by_time_range(self, hours: int = 24) -> List[Dict]:
        """
        Récupère les jobs des dernières X heures
        
        Args:
            hours: Nombre d'heures (par défaut: 24)
        
        Returns:
            Liste des jobs récents
        """
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        print(f"📥 Récupération des jobs depuis {cutoff}...")
        
        response = self.table.scan(
            FilterExpression=Attr('timestamp').gt(cutoff)
        )
        items = response['Items']

        while 'LastEvaluatedKey' in response:
            response = self.table.scan(
                ExclusiveStartKey=response['LastEvaluatedKey'],
                FilterExpression=Attr('timestamp').gt(cutoff)
            )
            items.extend(response['Items'])

        print(f"✅ {len(items)} jobs récents récupérés")
        return items

    def get_latest_state_per_job(self) -> List[Dict]:
        """
        Récupère uniquement le dernier état de chaque job (sans historique)

        Groupe les jobs par jobId et garde seulement l'item avec le timestamp
        le plus récent pour chaque job.

        Returns:
            Liste des jobs (un seul item par jobId - le dernier état)
        """
        print(f"📥 Récupération de tous les jobs...")

        # Récupérer tous les items (avec historique)
        all_items = self.get_all_jobs()

        if not all_items:
            return []

        # Grouper par jobId et garder seulement le plus récent
        latest_jobs = {}

        for item in all_items:
            job_id = item.get('jobId')
            timestamp = item.get('timestamp')

            if not job_id or not timestamp:
                continue

            # Si ce job n'est pas encore dans le dict, ou si ce timestamp est plus récent
            if job_id not in latest_jobs or timestamp > latest_jobs[job_id].get('timestamp'):
                latest_jobs[job_id] = item

        # Convertir le dictionnaire en liste
        result = list(latest_jobs.values())

        print(f"✅ {len(result)} jobs uniques récupérés (dernier état seulement)")
        print(f"📊 {len(all_items)} items au total dans DynamoDB (avec historique)")

        return result

    def get_job_history(self, job_id: str) -> List[Dict]:
        """
        Récupère les informations d'un job spécifique

        Note: Avec la nouvelle structure (pas d'historique), cette méthode
        retourne uniquement l'état actuel du job dans une liste pour compatibilité.

        Args:
            job_id: ID du job

        Returns:
            Liste contenant l'état actuel du job
        """
        print(f"📥 Récupération du job '{job_id}'...")

        try:
            response = self.table.get_item(
                Key={'jobId': job_id}
            )

            if 'Item' in response:
                print(f"✅ Job trouvé")
                return [response['Item']]  # Retourner une liste pour compatibilité
            else:
                print(f"⚠️ Job non trouvé")
                return []
        except Exception as e:
            print(f"❌ Erreur lors de la récupération : {str(e)}")
            return []

    def get_statistics(self) -> Dict:
        """
        Calcule des statistiques globales sur les jobs

        Returns:
            Dictionnaire avec les statistiques
        """
        print(f"📊 Calcul des statistiques...")

        items = self.get_latest_state_per_job()

        if not items:
            return {
                'total': 0,
                'succeeded': 0,
                'failed': 0,
                'running': 0,
                'success_rate': 0
            }

        df = pd.DataFrame(items)

        stats = {
            'total': len(df),
            'succeeded': int((df['status'] == 'SUCCEEDED').sum()),
            'failed': int((df['status'] == 'FAILED').sum()),
            'running': int(df['status'].isin(['RUNNING', 'STARTING', 'RUNNABLE']).sum()),
        }

        stats['success_rate'] = (stats['succeeded'] / stats['total'] * 100) if stats['total'] > 0 else 0

        print(f"✅ Statistiques calculées : {stats['total']} jobs au total")
        return stats

    def test_connection(self) -> bool:
        """
        Test de connexion à DynamoDB

        Returns:
            True si la connexion fonctionne, False sinon
        """
        try:
            response = self.table.scan(Limit=1)
            print(f"✅ Connexion à DynamoDB réussie !")
            print(f"   Table : {self.table_name}")
            print(f"   Région : {self.region}")
            print(f"   Items dans la table : {self.table.item_count}")
            return True
        except Exception as e:
            print(f"❌ Erreur de connexion : {str(e)}")
            return False


# Exemple d'utilisation
if __name__ == "__main__":
    # Test du module
    db = DynamoDBQueries()

    # Test de connexion
    if db.test_connection():
        # Récupérer quelques statistiques
        stats = db.get_statistics()
        print(f"\n📊 Statistiques :")
        print(f"   Total jobs : {stats['total']}")
        print(f"   Succeeded : {stats['succeeded']}")
        print(f"   Failed : {stats['failed']}")
        print(f"   Running : {stats['running']}")
        print(f"   Taux de succès : {stats['success_rate']:.1f}%")

