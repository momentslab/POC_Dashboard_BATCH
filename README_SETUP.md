# 🔧 Configuration du Dashboard - Guide de démarrage

Ce guide vous aide à configurer la connexion à DynamoDB pour le dashboard de monitoring AWS Batch.

---

## 📋 Prérequis

- Python 3.8+
- Compte AWS avec accès à DynamoDB
- Table DynamoDB `MonitoringToolTest` créée

---

## 🚀 Installation

### 1. Installer les dépendances Python

```bash
cd mon-dashboard-streamlit
pip install -r requirements.txt
```

### 2. Installer AWS CLI

**Sur macOS :**
```bash
brew install awscli
```

**Vérifier l'installation :**
```bash
aws --version
```

---

## 🔑 Configuration des credentials AWS

### 1. Créer une Access Key

1. Connectez-vous à la [Console AWS](https://console.aws.amazon.com/)
2. Allez dans **IAM** → **Users** → Votre utilisateur
3. Onglet **"Security credentials"**
4. Section **"Access keys"** → **"Create access key"**
5. Sélectionnez **"Command Line Interface (CLI)"**
6. **Téléchargez le fichier .csv** (important !)

### 2. Configurer AWS CLI

```bash
aws configure
```

Entrez vos credentials :
```
AWS Access Key ID [None]: AKIAXXXXXXXXXXXXXXXX
AWS Secret Access Key [None]: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
Default region name [None]: eu-west-1
Default output format [None]: json
```

### 3. Vérifier la configuration

```bash
# Test 1 : Vérifier l'identité
aws sts get-caller-identity

# Test 2 : Vérifier l'accès à DynamoDB
aws dynamodb describe-table --table-name MonitoringToolTest --region eu-west-1
```

---

## ✅ Tester la connexion

Exécutez le script de test :

```bash
python test_dynamo.py
```

**Résultat attendu :**
```
✅ Credentials AWS configurés correctement !
✅ Connexion à DynamoDB réussie !
✅ X jobs récupérés au total
🎉 Tous les tests sont passés !
```

---

## 🚀 Lancer le dashboard

Une fois les tests passés :

```bash
streamlit run app.py
```

Le dashboard s'ouvrira dans votre navigateur à l'adresse : `http://localhost:8501`

---

## 🔒 Sécurité

⚠️ **Ne commitez JAMAIS vos credentials AWS dans Git !**

Le fichier `.gitignore` est configuré pour protéger :
- `.aws/` (dossier de credentials)
- `*.csv` (fichiers de credentials téléchargés)

---

## 🐛 Dépannage

### Erreur : "Unable to locate credentials"

**Solution :**
```bash
aws configure
```

### Erreur : "AccessDeniedException"

**Solution :** Vérifiez que votre utilisateur IAM a les permissions DynamoDB :
- `dynamodb:Scan`
- `dynamodb:Query`
- `dynamodb:GetItem`

### Erreur : "ResourceNotFoundException"

**Solution :** Vérifiez que la table `MonitoringToolTest` existe dans la région `eu-west-1`.

---

## 📞 Support

En cas de problème, vérifiez :
1. Les credentials AWS sont configurés : `aws configure list`
2. La table DynamoDB existe : `aws dynamodb list-tables --region eu-west-1`
3. Les permissions IAM sont correctes

