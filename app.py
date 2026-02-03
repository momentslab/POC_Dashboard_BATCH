import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dynamo_queries import DynamoDBQueries

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

    # Convertir timestamp en datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Extraire les noms de queue et job definition
    df['Queue'] = df['jobQueue'].apply(extract_queue_name)
    df['JobDef'] = df['jobDefinition'].apply(extract_job_definition_name)

    # Créer le type de tâche formaté
    df['TaskType'] = df.apply(lambda row: format_task_type(row['Queue'], row['JobDef']), axis=1)

    # Extraire le Task ID depuis le jobName
    df['TaskID'] = df['jobName'].apply(extract_task_id)

    # Récupérer le Media ID depuis DynamoDB (stocké par la Lambda)
    # Si le champ n'existe pas, afficher "Unknown"
    df['MediaID'] = df.get('media_id', pd.Series(['Unknown'] * len(df)))
    # Remplacer les valeurs vides par "Unknown"
    df['MediaID'] = df['MediaID'].fillna('Unknown').replace('', 'Unknown')

    # Stocker les valeurs originales pour les détails
    df['Queue_Original'] = df['Queue']
    df['JobDef_Original'] = df['JobDef']

    # Renommer et sélectionner les colonnes (Media ID, Task ID, Task Type, Status en premier)
    df_display = pd.DataFrame({
        'Media ID': df['MediaID'],
        'Task ID': df['TaskID'],
        'Task Type': df['TaskType'],
        'Status': df['status'],
        'Job ID': df['jobId'],
        'Job Name': df['jobName'],
        'Region': df['region'],
        'Timestamp': df['timestamp'],
        'Status Reason': df.get('statusReason', ''),
        'Queue_Original': df['Queue_Original'],
        'JobDef_Original': df['JobDef_Original']
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
col1, col2, col3, col4 = st.columns(4)

# Filtre par Status
status_filter = col1.multiselect(
    "Status",
    options=sorted(tasks_df["Status"].unique()),
    default=tasks_df["Status"].unique()
)

# Filtre par Task Type
tasktype_filter = col2.multiselect(
    "Task Type",
    options=sorted(tasks_df["Task Type"].unique()),
    default=tasks_df["Task Type"].unique()
)

# Filtre par Region
region_filter = col3.multiselect(
    "Region",
    options=sorted(tasks_df["Region"].unique()),
    default=tasks_df["Region"].unique()
)

# Filtre par Date
date_filter = col4.selectbox(
    "Période",
    options=["Tout", "Dernier jour", "3 derniers jours", "Dernière semaine"],
    index=0
)

# Appliquer le filtre de date
now = datetime.now()
if date_filter == "Dernier jour":
    date_threshold = now - timedelta(days=1)
    tasks_df_filtered_by_date = tasks_df[tasks_df["Timestamp"] >= date_threshold]
elif date_filter == "3 derniers jours":
    date_threshold = now - timedelta(days=3)
    tasks_df_filtered_by_date = tasks_df[tasks_df["Timestamp"] >= date_threshold]
elif date_filter == "Dernière semaine":
    date_threshold = now - timedelta(days=7)
    tasks_df_filtered_by_date = tasks_df[tasks_df["Timestamp"] >= date_threshold]
else:  # "Tout"
    tasks_df_filtered_by_date = tasks_df

# Appliquer les autres filtres
filtered_df = tasks_df_filtered_by_date[
    (tasks_df_filtered_by_date["Status"].isin(status_filter)) &
    (tasks_df_filtered_by_date["Task Type"].isin(tasktype_filter)) &
    (tasks_df_filtered_by_date["Region"].isin(region_filter))
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
    # Colonnes à afficher (Media ID, Task ID, Task Type, Status en premier)
    display_columns = ['Media ID', 'Task ID', 'Task Type', 'Status', 'Job ID', 'Job Name', 'Region', 'Timestamp', 'Status Reason']

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
                # Récupérer le fullEvent depuis les données
                if 'fullEvent' in job_details:
                    import json
                    full_event = json.loads(job_details['fullEvent'])
                    st.json(full_event)
                else:
                    st.info("Événement complet non disponible")
            except Exception as e:
                st.error(f"Erreur lors de l'affichage de l'événement : {str(e)}")

        # Actions (optionnel - pour Phase 3)
        st.markdown("---")
        st.markdown("### Actions (Simulation)")

        col_a1, col_a2 = st.columns([3, 1])

        with col_a1:
            action = st.radio(
                "Action à exécuter",
                ["Retry", "Abort", "Mark as Broken"],
                horizontal=True
            )

        with col_a2:
            st.write("")  # Spacer
            st.write("")  # Spacer
            if st.button("Exécuter", use_container_width=True):
                # Historique des actions
                if "action_log" not in st.session_state:
                    st.session_state.action_log = []

                st.session_state.action_log.append({
                    "Job ID": selected_job_id,
                    "Action": action,
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                st.success(f"Action **{action}** exécutée sur le job **{selected_job_id}** (simulation)")

        # Afficher l'historique des actions
        if "action_log" in st.session_state and st.session_state.action_log:
            with st.expander("Historique des actions"):
                actions_df = pd.DataFrame(st.session_state.action_log)
                st.dataframe(actions_df, use_container_width=True)
