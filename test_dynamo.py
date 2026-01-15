"""
Script de test pour vérifier la connexion à DynamoDB
Exécutez ce script avant d'utiliser le dashboard Streamlit
"""

import boto3
from dynamo_queries import DynamoDBQueries


def test_aws_credentials():
    """Test 1 : Vérifier que les credentials AWS sont configurés"""
    print("\n" + "="*60)
    print("TEST 1 : Vérification des credentials AWS")
    print("="*60)
    
    try:
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        
        print("✅ Credentials AWS configurés correctement !")
        print(f"   Account ID : {identity['Account']}")
        print(f"   User ARN : {identity['Arn']}")
        return True
    except Exception as e:
        print(f"❌ Erreur : {str(e)}")
        print("\n💡 Solution :")
        print("   1. Installez AWS CLI : brew install awscli")
        print("   2. Configurez vos credentials : aws configure")
        return False


def test_dynamodb_connection():
    """Test 2 : Vérifier la connexion à DynamoDB"""
    print("\n" + "="*60)
    print("TEST 2 : Connexion à DynamoDB")
    print("="*60)
    
    try:
        db = DynamoDBQueries()
        
        if db.test_connection():
            return True
        else:
            return False
    except Exception as e:
        print(f"❌ Erreur : {str(e)}")
        print("\n💡 Vérifiez :")
        print("   - Que la table 'MonitoringToolTest' existe")
        print("   - Que vous êtes dans la région 'eu-west-1'")
        print("   - Que votre utilisateur IAM a les permissions DynamoDB")
        return False


def test_data_retrieval():
    """Test 3 : Récupérer des données de test"""
    print("\n" + "="*60)
    print("TEST 3 : Récupération de données")
    print("="*60)
    
    try:
        db = DynamoDBQueries()
        
        # Test 1 : Tous les jobs
        all_jobs = db.get_all_jobs()
        print(f"✅ {len(all_jobs)} jobs récupérés au total")
        
        # Test 2 : Dernier état de chaque job
        latest_jobs = db.get_latest_state_per_job()
        print(f"✅ {len(latest_jobs)} jobs uniques")
        
        # Test 3 : Statistiques
        stats = db.get_statistics()
        print(f"✅ Statistiques calculées :")
        print(f"   - Total : {stats['total']}")
        print(f"   - Succeeded : {stats['succeeded']}")
        print(f"   - Failed : {stats['failed']}")
        print(f"   - Running : {stats['running']}")
        print(f"   - Taux de succès : {stats['success_rate']:.1f}%")
        
        # Afficher un exemple de job
        if latest_jobs:
            print(f"\n📋 Exemple de job :")
            example = latest_jobs[0]
            print(f"   JobId : {example.get('jobId', 'N/A')}")
            print(f"   Status : {example.get('status', 'N/A')}")
            print(f"   JobName : {example.get('jobName', 'N/A')}")
            print(f"   Timestamp : {example.get('timestamp', 'N/A')}")
        
        return True
    except Exception as e:
        print(f"❌ Erreur : {str(e)}")
        return False


def main():
    """Exécute tous les tests"""
    print("\n" + "🔍 " + "="*58)
    print("🔍  TEST DE CONNEXION DYNAMODB - Dashboard Monitoring")
    print("🔍 " + "="*58)
    
    # Test 1
    test1 = test_aws_credentials()
    
    if not test1:
        print("\n❌ Les tests ont échoué. Configurez vos credentials AWS d'abord.")
        return
    
    # Test 2
    test2 = test_dynamodb_connection()
    
    if not test2:
        print("\n❌ Impossible de se connecter à DynamoDB.")
        return
    
    # Test 3
    test3 = test_data_retrieval()
    
    # Résumé
    print("\n" + "="*60)
    print("RÉSUMÉ DES TESTS")
    print("="*60)
    print(f"Test 1 (Credentials AWS) : {'✅ OK' if test1 else '❌ ÉCHEC'}")
    print(f"Test 2 (Connexion DynamoDB) : {'✅ OK' if test2 else '❌ ÉCHEC'}")
    print(f"Test 3 (Récupération données) : {'✅ OK' if test3 else '❌ ÉCHEC'}")
    
    if test1 and test2 and test3:
        print("\n🎉 Tous les tests sont passés ! Vous pouvez lancer le dashboard Streamlit.")
        print("\n💡 Commande pour lancer le dashboard :")
        print("   streamlit run app.py")
    else:
        print("\n❌ Certains tests ont échoué. Corrigez les erreurs avant de continuer.")


if __name__ == "__main__":
    main()

