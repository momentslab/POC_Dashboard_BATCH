# ✅ Checklist de Migration - Suppression de l'Historique

## 📋 Étapes à Suivre

### 1️⃣ Créer la Nouvelle Table DynamoDB

**Console** : https://eu-west-1.console.aws.amazon.com/dynamodbv2/home?region=eu-west-1

- [ ] Cliquer sur **"Create table"**
- [ ] **Table name** : `MonitoringToolTest_V2`
- [ ] **Partition key** : `jobId` (Type: String)
- [ ] **Sort key** : ❌ **Laisser vide** (ne pas ajouter)
- [ ] **Table settings** : Default settings
- [ ] Cliquer sur **"Create table"**
- [ ] Attendre que le statut soit **"Active"** (environ 1 minute)

**Vérification** :
- [ ] Table visible dans la liste
- [ ] Statut : Active
- [ ] Partition key : jobId
- [ ] Sort key : None

---

### 2️⃣ Modifier la Lambda MonitoringTaskPOC

**Console** : https://eu-west-1.console.aws.amazon.com/lambda/home?region=eu-west-1

- [ ] Chercher la fonction **`MonitoringTaskPOC`**
- [ ] Cliquer dessus
- [ ] Aller dans l'onglet **"Code"**
- [ ] Ouvrir le fichier `lambda_code_no_history.py` dans ce projet
- [ ] **Copier tout le code** du fichier
- [ ] **Coller** dans l'éditeur de la Lambda (remplacer tout)
- [ ] Vérifier que la ligne 14 contient : `table = dynamodb.Table('MonitoringToolTest_V2')`
- [ ] Cliquer sur **"Deploy"** (bouton orange en haut à droite)
- [ ] Attendre le message **"Successfully updated the function MonitoringTaskPOC"**

**Vérification** :
- [ ] Code déployé avec succès
- [ ] Pas d'erreur de syntaxe
- [ ] Table name = `MonitoringToolTest_V2`

---

### 3️⃣ Tester la Lambda

**Dans la console Lambda** :

- [ ] Cliquer sur **"Test"** (à côté de Deploy)
- [ ] Créer un nouvel événement de test :
  - **Event name** : `TestJobRunning`
  - **Template** : Copier le JSON ci-dessous
- [ ] Cliquer sur **"Save"**
- [ ] Cliquer sur **"Test"**

**JSON de test** :
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
    "statusReason": "Test en cours"
  }
}
```

**Vérification** :
- [ ] Exécution réussie (statut 200)
- [ ] Message : "Job test-job-001 updated to status RUNNING"
- [ ] Pas d'erreur dans les logs

---

### 4️⃣ Vérifier dans DynamoDB

**Console DynamoDB** :

- [ ] Aller dans la table `MonitoringToolTest_V2`
- [ ] Cliquer sur **"Explore table items"**
- [ ] Vérifier qu'un item existe avec :
  - **jobId** : `test-job-001`
  - **status** : `RUNNING`
  - **jobName** : `pre-694a9d57b88940a9e5cd3bee-1766497635776`

---

### 5️⃣ Tester la Mise à Jour (Écrasement)

**Dans la console Lambda** :

- [ ] Modifier l'événement de test :
  - Changer `"status": "RUNNING"` → `"status": "SUCCEEDED"`
  - Changer `"statusReason": "Test en cours"` → `"statusReason": "Test terminé"`
- [ ] Cliquer sur **"Test"** à nouveau

**Vérification dans DynamoDB** :
- [ ] Aller dans la table `MonitoringToolTest_V2`
- [ ] Rafraîchir la vue
- [ ] Vérifier qu'il y a **toujours 1 seul item** pour `test-job-001`
- [ ] Vérifier que le **status** est maintenant `SUCCEEDED`
- [ ] Vérifier que le **statusReason** est `Test terminé`

**✅ Si c'est bon** : L'écrasement fonctionne ! Pas de doublon.

---

### 6️⃣ Tester le Dashboard

**Dans le terminal** :

- [ ] Aller dans le dossier du projet : `cd mon-dashboard-streamlit`
- [ ] Lancer le dashboard : `streamlit run app.py`
- [ ] Ouvrir http://localhost:8501

**Vérification** :
- [ ] Dashboard se lance sans erreur
- [ ] Le job de test `test-job-001` apparaît dans le tableau
- [ ] Status : SUCCEEDED (en vert)
- [ ] Media ID : 694a9d57b88940a9e5cd3bee
- [ ] Task ID : 694a9d57b88940a9e5cd3bee
- [ ] Pas de doublon

**Cliquer sur le job** :
- [ ] Détails s'affichent correctement
- [ ] Section "Événement AWS complet" fonctionne
- [ ] Pas de section "Historique" (supprimée)

---

### 7️⃣ Test en Production (Optionnel)

**Attendre un vrai événement AWS Batch** :

- [ ] Lancer un job AWS Batch réel
- [ ] Attendre qu'il change d'état (RUNNING → SUCCEEDED)
- [ ] Vérifier dans DynamoDB qu'il n'y a qu'un seul item
- [ ] Vérifier dans le dashboard que tout s'affiche correctement

---

### 8️⃣ Nettoyage (Optionnel)

**Une fois que tout fonctionne** :

- [ ] Supprimer l'ancienne table `MonitoringToolTest` (pour économiser les coûts)
- [ ] Supprimer le job de test dans DynamoDB (jobId: `test-job-001`)

---

## 🎉 Félicitations !

Si toutes les cases sont cochées, la migration est terminée ! 

Votre système stocke maintenant uniquement le dernier état de chaque job, sans historique.

---

## 🆘 En Cas de Problème

### Erreur : "Table not found"
→ Vérifier que la table `MonitoringToolTest_V2` existe et est Active

### Erreur : "Access denied"
→ Vérifier les permissions IAM de la Lambda (doit avoir accès à DynamoDB)

### Dashboard vide
→ Vérifier que des jobs existent dans la table DynamoDB

### Doublons dans le tableau
→ Vérifier que la table n'a PAS de Sort Key (uniquement Partition Key)

---

## 📞 Support

Voir les fichiers :
- `MIGRATION_NO_HISTORY.md` : Guide détaillé
- `RESUME_MODIFICATIONS.md` : Résumé des changements
- `lambda_code_no_history.py` : Code de la Lambda

