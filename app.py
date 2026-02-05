import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dynamo_queries import DynamoDBQueries
import importlib
import sys

# Forcer le rechargement du module backbone_actions
if 'backbone_actions' in sys.modules:
    import backbone_actions
    importlib.reload(backbone_actions)
    from backbone_actions import BackboneActions
else:
    from backbone_actions import BackboneActions

# -----------------------
# Configuration
# -----------------------
st.set_page_config(page_title="AWS Batch Monitoring Dashboard", layout="wide")

# -----------------------
# Fonctions utilitaires
# -----------------------
@st.cache_data(ttl=60)  # Cache pendant 60 secondes
def load_jobs_from_dynamodb():
    """Charge les jobs depuis DynamoDB avec cache"""
    db = DynamoDBQueries()
    jobs = db.get_latest_state_per_job()
    return jobs

def extract_queue_name(queue_arn):
    """Extrait le nom de la queue depuis l'ARN"""
    if not queue_arn or not isinstance(queue_arn, str):
        return "Unknown"
    # ARN format: arn:aws:batch:region:account:job-queue/queue-name
    parts = queue_arn.split('/')
    if len(parts) > 1:
        return parts[-1]
    return queue_arn

def extract_job_definition_name(job_def_arn):
    """Extrait le nom de la job definition depuis l'ARN"""
    if not job_def_arn or not isinstance(job_def_arn, str):
        return "Unknown"
    # ARN format: arn:aws:batch:region:account:job-definition/name:version
    parts = job_def_arn.split('/')
    if len(parts) > 1:
        name_version = parts[-1]
        # Enlever la version
        return name_version.split(':')[0] if ':' in name_version else name_version
    return job_def_arn

def extract_task_id(job_name):
    """
    Extrait le Task ID depuis le jobName

    Format attendu: prefix-TASK_ID-suffix
    Exemple: pre-69490f5fc05fb78da7b7380f-1766395755577 → 69490f5fc05fb78da7b7380f
    Exemple: assembly-pre-no_output_4-694916fc74feae014064b737-zip_package-114sec → 694916fc74feae014064b737

    Args:
        job_name: Nom du job AWS Batch

    Returns:
        Task ID extrait ou "Unknown"
    """
    if not job_name or not isinstance(job_name, str):
        return "Unknown"

    # Séparer par tirets
    parts = job_name.split('-')

    # Chercher une partie qui ressemble à un ID MongoDB (24 caractères hexadécimaux)
    for part in parts:
        if len(part) == 24 and all(c in '0123456789abcdef' for c in part.lower()):
            return part

    # Si pas trouvé, retourner "Unknown"
    return "Unknown"

def format_task_type(queue_name, job_def_name):
    """
    Formate le type de tâche de manière lisible

    Mapping:
    - orchestrator-repair-ingest-standard-pre → Ingest
    - AssemblyStandard-pre → Assembly (Zip Package)
    - storage-pre-v2 → Storage
    - text-recognition-pre → Text Recognition
    """
    # Mapping basé sur la queue
    queue_lower = queue_name.lower() if queue_name else ""

    if "orchestrator" in queue_lower and "ingest" in queue_lower:
        return "Ingest"
    elif "assembly" in queue_lower:
        return "Assembly (Zip Package)"
    elif "text-recognition" in queue_lower or "text_recognition" in queue_lower:
        return "Text Recognition"

    # Mapping basé sur la job definition
    jobdef_lower = job_def_name.lower() if job_def_name else ""

    if "storage" in jobdef_lower:
        return "Storage"
    elif "assembly" in jobdef_lower:
        return "Assembly (Zip Package)"
    elif "text" in jobdef_lower and "recognition" in jobdef_lower:
        return "Text Recognition"
    elif "ingest" in jobdef_lower or "orchestrator" in jobdef_lower:
        return "Ingest"

    # Par défaut, retourner le nom de la queue formaté
    return queue_name if queue_name != "Unknown" else job_def_name

def format_jobs_dataframe(jobs):
    """Transforme les données DynamoDB en DataFrame pour le dashboard"""
    if not jobs:
        return pd.DataFrame()

    df = pd.DataFrame(jobs)

    # Convertir timestamp en datetime UTC puis en heure locale
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True).dt.tz_convert('Europe/Paris').dt.tz_localize(None)

    # Extraire les noms de queue et job definition
    df['Queue'] = df['jobQueue'].apply(extract_queue_name)
    df['JobDef'] = df['jobDefinition'].apply(extract_job_definition_name)

    # Créer le type de tâche formaté
    df['TaskType'] = df.apply(lambda row: format_task_type(row['Queue'], row['JobDef']), axis=1)

    # Récupérer le Task ID depuis DynamoDB (stocké par la Lambda)
    # Si non disponible, extraire depuis le Job Name (fallback)
    def get_task_id(row):
        # D'abord essayer depuis DynamoDB
        task_id = row.get('task_id')
        if task_id and task_id != '':
            return task_id

        # Sinon extraire depuis le Job Name (fallback pour anciens jobs)
        return extract_task_id(row.get('jobName', ''))

    df['TaskID'] = df.apply(get_task_id, axis=1)

    # Récupérer le Media ID depuis DynamoDB (stocké par la Lambda)
    # Si le champ n'existe pas, afficher "Unknown"
    df['MediaID'] = df.get('media_id', pd.Series(['Unknown'] * len(df)))
    # Remplacer les valeurs vides par "Unknown"
    df['MediaID'] = df['MediaID'].fillna('Unknown').replace('', 'Unknown')

    # Récupérer le Workspace UID depuis DynamoDB (stocké par la Lambda)
    # Si non disponible, extraire depuis le Job Name (format: "workspace-jobid-taskid")
    # ATTENTION: "recognise" et "assembly" ne sont PAS des workspace UIDs
    def get_workspace_uid(row):
        # D'abord essayer depuis DynamoDB
        workspace = row.get('workspace_uid')
        if workspace and workspace != '':
            return workspace

        # Sinon extraire depuis le Job Name (fallback pour anciens jobs)
        job_name = row.get('jobName')
        if pd.isna(job_name) or job_name == '':
            return 'Unknown'
        parts = str(job_name).split('-')
        if len(parts) > 0 and parts[0]:
            first_part = parts[0]
            # Exclure les task types qui ne sont pas des workspaces
            if first_part not in ['recognise', 'assembly']:
                return first_part
        return 'Unknown'

    df['WorkspaceUID'] = df.apply(get_workspace_uid, axis=1)

    # Stocker les valeurs originales pour les détails
    df['Queue_Original'] = df['Queue']
    df['JobDef_Original'] = df['JobDef']

    # Renommer et sélectionner les colonnes (Media ID, Task ID, Task Type, Status en premier)
    df_display = pd.DataFrame({
        'Media ID': df['MediaID'],
        'Task ID': df['TaskID'],
        'Task Type': df['TaskType'],
        'Workspace UID': df['WorkspaceUID'],
        'Status': df['status'],
        'Job ID': df['jobId'],
        'Job Name': df['jobName'],
        'Region': df['region'],
        'Timestamp': df['timestamp'],
        'Status Reason': df.get('statusReason', ''),
        'Queue_Original': df['Queue_Original'],
        'JobDef_Original': df['JobDef_Original'],
        'fullEvent': df.get('fullEvent', '')  # Garder le fullEvent pour l'affichage JSON
    })

    return df_display

# -----------------------
# Fonction pour récupérer l'historique d'un job
# -----------------------
def get_job_history(job_id):
    """Récupère l'historique complet d'un job"""
    db = DynamoDBQueries()
    history = db.get_job_history(job_id)
    return history

# -----------------------
# Header et bouton de rafraîchissement
# -----------------------
col_title, col_refresh = st.columns([4, 1])
with col_title:
    st.title("AWS Batch Monitoring Dashboard")
with col_refresh:
    if st.button("Rafraîchir", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.markdown("---")

# -----------------------
# Chargement des données
# -----------------------
with st.spinner("Chargement des données depuis DynamoDB..."):
    try:
        jobs = load_jobs_from_dynamodb()
        tasks_df = format_jobs_dataframe(jobs)

        if tasks_df.empty:
            st.warning("Aucun job trouvé dans DynamoDB")
            st.stop()

        st.success(f"{len(tasks_df)} jobs chargés depuis DynamoDB")
    except Exception as e:
        st.error(f"Erreur lors du chargement des données : {str(e)}")
        st.info("Vérifiez que vos credentials AWS sont configurés et que vous avez accès à DynamoDB")
        st.stop()

# -----------------------
# Filtrage des jobs
# -----------------------
st.markdown("### Filtres")
col1, col2, col3, col4, col5 = st.columns(5)

# Filtre par Status
status_filter = col1.multiselect(
    "Status",
    options=sorted(tasks_df["Status"].unique()),
    default=tasks_df["Status"].unique()
)

# Filtre par Task Type
# Exclure "my-batch-queue" des options
task_type_options = sorted([t for t in tasks_df["Task Type"].unique() if t != "my-batch-queue"])
tasktype_filter = col2.multiselect(
    "Task Type",
    options=task_type_options,
    default=task_type_options
)

# Filtre par Region
region_filter = col3.multiselect(
    "Region",
    options=sorted(tasks_df["Region"].unique()),
    default=tasks_df["Region"].unique()
)

# Filtre par Workspace UID
workspace_uids = tasks_df["Workspace UID"].dropna().unique()
workspace_filter = col4.multiselect(
    "Workspace UID",
    options=sorted([str(w) for w in workspace_uids]),
    default=list(workspace_uids)
)

# Filtre par Date
date_filter = col5.selectbox(
    "Période",
    options=["Tout", "Dernière heure", "Dernier jour", "3 derniers jours", "Dernière semaine", "Dernier mois"],
    index=0
)

# Appliquer le filtre de date
now = datetime.now()
if date_filter == "Dernière heure":
    date_threshold = now - timedelta(hours=1)
    tasks_df_filtered_by_date = tasks_df[tasks_df["Timestamp"] >= date_threshold]
elif date_filter == "Dernier jour":
    date_threshold = now - timedelta(days=1)
    tasks_df_filtered_by_date = tasks_df[tasks_df["Timestamp"] >= date_threshold]
elif date_filter == "3 derniers jours":
    date_threshold = now - timedelta(days=3)
    tasks_df_filtered_by_date = tasks_df[tasks_df["Timestamp"] >= date_threshold]
elif date_filter == "Dernière semaine":
    date_threshold = now - timedelta(days=7)
    tasks_df_filtered_by_date = tasks_df[tasks_df["Timestamp"] >= date_threshold]
elif date_filter == "Dernier mois":
    date_threshold = now - timedelta(days=30)
    tasks_df_filtered_by_date = tasks_df[tasks_df["Timestamp"] >= date_threshold]
else:  # "Tout"
    tasks_df_filtered_by_date = tasks_df

# Appliquer les autres filtres
# Si un filtre est vide, on considère que tous les éléments sont acceptés
filtered_df = tasks_df_filtered_by_date[
    (tasks_df_filtered_by_date["Status"].isin(status_filter) if status_filter else True) &
    (tasks_df_filtered_by_date["Task Type"].isin(tasktype_filter) if tasktype_filter else True) &
    (tasks_df_filtered_by_date["Region"].isin(region_filter) if region_filter else True) &
    (tasks_df_filtered_by_date["Workspace UID"].isin(workspace_filter) if workspace_filter else True)
].sort_values(by="Timestamp", ascending=False)

# -----------------------
# Métriques
# -----------------------
st.markdown("---")
st.markdown("### Statistiques")
col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)

total_jobs = len(filtered_df)
succeeded_jobs = (filtered_df["Status"] == "SUCCEEDED").sum()
failed_jobs = (filtered_df["Status"] == "FAILED").sum()
running_jobs = filtered_df["Status"].isin(["RUNNING", "STARTING", "RUNNABLE", "PENDING"]).sum()
success_rate = (succeeded_jobs / total_jobs * 100) if total_jobs > 0 else 0

col_m1.metric("Total Jobs", total_jobs)
col_m2.metric("Succeeded", succeeded_jobs)
col_m3.metric("Failed", failed_jobs)
col_m4.metric("Running", running_jobs)
col_m5.metric("Success Rate", f"{success_rate:.1f}%")

# -----------------------
# Tableau des jobs avec coloration
# -----------------------
st.markdown("---")
st.markdown("### Liste des Jobs")

def highlight_status(row):
    """Coloration conditionnelle selon le statut"""
    status = row["Status"]

    if status == "FAILED":
        return ['background-color: #ff6b6b; color: white' for _ in row]  # Rouge plus foncé
    elif status == "SUCCEEDED":
        return ['background-color: #51cf66; color: white' for _ in row]  # Vert plus foncé
    elif status in ["RUNNING", "STARTING", "RUNNABLE"]:
        return ['background-color: #ffd43b; color: black' for _ in row]  # Jaune plus foncé
    elif status == "PENDING":
        return ['background-color: #74c0fc; color: white' for _ in row]  # Bleu
    elif status == "SUBMITTED":
        return ['background-color: #a78bfa; color: white' for _ in row]  # Violet
    else:
        return ['background-color: #868e96; color: white' for _ in row]  # Gris

if not filtered_df.empty:
    # Colonnes à afficher (Media ID, Task ID, Task Type, Workspace UID, Status en premier)
    display_columns = ['Media ID', 'Task ID', 'Task Type', 'Workspace UID', 'Status', 'Job ID', 'Job Name', 'Region', 'Timestamp', 'Status Reason']

    # Afficher le tableau avec coloration
    st.dataframe(
        filtered_df[display_columns].style.apply(highlight_status, axis=1),
        use_container_width=True,
        height=400
    )
else:
    st.info("Aucun job ne correspond aux filtres sélectionnés")

# -----------------------
# Détails d'un job et historique
# -----------------------
if not filtered_df.empty:
    st.markdown("---")
    st.markdown("### Détails d'un Job")

    # Sélection d'un job
    selected_job_id = st.selectbox(
        "Sélectionner un Job ID",
        options=filtered_df["Job ID"].tolist(),
        format_func=lambda x: f"{x} - {filtered_df[filtered_df['Job ID']==x]['Job Name'].iloc[0]}"
    )

    if selected_job_id:
        # Afficher les détails du job sélectionné
        job_details = filtered_df[filtered_df["Job ID"] == selected_job_id].iloc[0]

        col_d1, col_d2 = st.columns(2)

        with col_d1:
            st.markdown("**Informations générales**")
            st.write(f"**Task Type:** {job_details['Task Type']}")
            st.write(f"**Workspace UID:** {job_details.get('Workspace UID', 'Unknown')}")
            st.write(f"**Media ID:** `{job_details['Media ID']}`")
            st.write(f"**Task ID:** `{job_details['Task ID']}`")
            st.write(f"**Job ID:** {job_details['Job ID']}")
            st.write(f"**Job Name:** {job_details['Job Name']}")
            st.write(f"**Status:** {job_details['Status']}")

        with col_d2:
            st.markdown("**Détails techniques**")
            st.write(f"**Queue:** {job_details['Queue_Original']}")
            st.write(f"**Job Definition:** {job_details['JobDef_Original']}")
            st.write(f"**Region:** {job_details['Region']}")
            st.write(f"**Timestamp:** {job_details['Timestamp']}")
            if job_details['Status Reason']:
                st.write(f"**Status Reason:** {job_details['Status Reason']}")

        # Événement brut (optionnel)
        with st.expander(f"Événement AWS complet (JSON)"):
            try:
                # Récupérer le fullEvent depuis le DataFrame original (tasks_df)
                full_job_data = tasks_df[tasks_df["Job ID"] == selected_job_id].iloc[0]
                if 'fullEvent' in full_job_data and full_job_data['fullEvent']:
                    import json
                    full_event = json.loads(full_job_data['fullEvent'])
                    st.json(full_event)
                else:
                    st.info("Événement complet non disponible")
            except Exception as e:
                st.error(f"Erreur lors de l'affichage de l'événement : {str(e)}")

        # Actions API
        st.markdown("---")
        st.markdown("### Actions")

        # Initialiser le client API
        if "backbone_client" not in st.session_state:
            st.session_state.backbone_client = BackboneActions()

        backbone = st.session_state.backbone_client

        # Récupérer les tâches Backbone pour ce media_id
        backbone_tasks = []
        selected_backbone_task_id = None
        media_id = job_details['Media ID']

        if backbone.is_available() and media_id != "Unknown":
            try:
                query_filter = f"eq(media_id,{media_id})"
                tasks_result = backbone.client.get_tasks(query_filter=query_filter)
                backbone_tasks = tasks_result.get('data', []) if isinstance(tasks_result, dict) else []

                if backbone_tasks:
                    # Créer une liste d'options pour le selectbox
                    task_options = []
                    for task in backbone_tasks:
                        task_id = task.get('task_id') or task.get('_id')
                        task_type = task.get('type', 'unknown')
                        task_status = task.get('status', 'unknown')
                        task_options.append({
                            'id': task_id,
                            'label': f"{task_type} ({task_status}) - {task_id}",
                            'type': task_type,
                            'status': task_status
                        })

                    # Selectbox pour choisir la tâche
                    selected_option = st.selectbox(
                        "Sélectionnez la tâche à utiliser:",
                        options=range(len(task_options)),
                        format_func=lambda i: task_options[i]['label'],
                        key=f"task_selector_{selected_job_id}"
                    )

                    selected_backbone_task_id = task_options[selected_option]['id']
                    st.info(f"Tâche sélectionnée: `{selected_backbone_task_id}`")
                else:
                    st.warning(f"Aucune tâche Backbone trouvée pour media_id: {media_id}")
            except Exception as e:
                st.error(f"Erreur lors de la récupération des tâches Backbone: {str(e)}")

        # Vérifier si l'API est disponible
        if not backbone.is_available():
            if backbone.init_error:
                if "AccessDenied" in backbone.init_error or "not authorized" in backbone.init_error:
                    st.warning("API BackboneClient : Problème de permissions AWS. Vérifiez vos credentials AWS.")
                    st.info("Les credentials AWS utilisés n'ont pas les permissions nécessaires pour accéder aux ressources BackboneClient.")
                else:
                    st.warning(f"API BackboneClient non disponible : {backbone.init_error}")
            else:
                st.warning("API BackboneClient non disponible. Configurez WORKSPACE_UID dans les secrets Streamlit ou variables d'environnement.")
                st.info("Pour configurer: créez un fichier `.streamlit/secrets.toml` avec `workspace_uid = \"VOTRE_UID\"`")

        col_a1, col_a2 = st.columns([3, 1])

        with col_a1:
            action = st.radio(
                "Action à exécuter",
                ["Restart", "Abort", "Broken", "Restart and set as broken"],
                horizontal=True
            )

        with col_a2:
            st.write("")  # Spacer
            st.write("")  # Spacer
            if st.button("Exécuter", use_container_width=True):
                # Utiliser le task_id sélectionné dans Backbone, ou celui extrait du job name
                task_id = selected_backbone_task_id if selected_backbone_task_id else job_details['Task ID']
                media_id = job_details['Media ID']
                region = job_details['Region']  # Récupérer la région du job

                # Vérifier que les IDs sont valides
                if not selected_backbone_task_id and (task_id == "Unknown" or media_id == "Unknown"):
                    st.error("Aucune tâche Backbone sélectionnée et Task ID/Media ID manquant. Impossible d'exécuter l'action.")
                elif not backbone.is_available():
                    st.error("API BackboneClient non disponible.")
                else:
                    # Exécuter l'action directement avec le task_id sélectionné
                    # La région est passée à chaque action pour mettre à jour AWS_DEFAULT_REGION
                    with st.spinner(f"Exécution de l'action {action}..."):
                        if action == "Abort":
                            # Appeler directement avec le task_id et la région
                            result = backbone.abort_task_direct(task_id, region=region)
                        elif action == "Broken":
                            # Appeler directement avec le task_id et la région
                            result = backbone.break_task_direct(task_id, region=region)
                        elif action == "Restart":
                            result = backbone.restart_task(task_id, media_id, region=region)
                        elif action == "Restart and set as broken":
                            result = backbone.restart_and_break_task_direct(task_id, media_id, region=region)
                        else:
                            result = {"success": False, "error": "Action inconnue"}

                    # Afficher le résultat
                    if result["success"]:
                        st.success(f"Action **{action}** exécutée avec succès sur la tâche **{task_id}**")

                        # Historique des actions
                        if "action_log" not in st.session_state:
                            st.session_state.action_log = []

                        st.session_state.action_log.append({
                            "Task ID": task_id,
                            "Media ID": media_id,
                            "Job ID": selected_job_id,
                            "Action": action,
                            "Status": "Success",
                            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                    else:
                        st.error(f"Erreur lors de l'exécution de l'action: {result.get('error', 'Erreur inconnue')}")

                        # Historique des actions (même en cas d'erreur)
                        if "action_log" not in st.session_state:
                            st.session_state.action_log = []

                        st.session_state.action_log.append({
                            "Task ID": task_id,
                            "Media ID": media_id,
                            "Job ID": selected_job_id,
                            "Action": action,
                            "Status": f"Error: {result.get('error', 'Unknown')}",
                            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })

        # Afficher l'historique des actions
        if "action_log" in st.session_state and st.session_state.action_log:
            with st.expander("Historique des actions"):
                actions_df = pd.DataFrame(st.session_state.action_log)
                st.dataframe(actions_df, use_container_width=True)
