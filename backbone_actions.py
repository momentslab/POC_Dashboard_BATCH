"""
Module pour gérer les actions API via BackboneClient avec support multi-région thread-safe
"""
import os
import threading
from typing import Optional, Dict, Any
import streamlit as st


class BackboneActions:
    """Classe pour gérer les actions sur les tâches via BackboneClient"""
    
    def __init__(self):
        """Initialise le client BackboneClient"""
        # Récupérer workspace_uid depuis les secrets Streamlit ou variable d'environnement
        self.workspace_uid = self._get_workspace_uid()
        self.init_error = None
        
        # Stockage local par thread pour les clients
        self._local = threading.local()
        
        # Lock pour la création de clients (éviter race conditions)
        self._creation_lock = threading.Lock()
        
        # Vérifier que workspace_uid est disponible
        if not self.workspace_uid:
            self.init_error = "WORKSPACE_UID non configuré"
    
    def _get_workspace_uid(self) -> Optional[str]:
        """Récupère le workspace_uid depuis les secrets ou variables d'environnement"""
        # Essayer depuis les secrets Streamlit
        try:
            if hasattr(st, 'secrets') and 'workspace_uid' in st.secrets:
                return st.secrets['workspace_uid']
        except Exception:
            pass

        # Essayer depuis les variables d'environnement (majuscules)
        workspace_uid = os.getenv('WORKSPACE_UID')
        if workspace_uid:
            return workspace_uid

        # Essayer aussi en minuscules
        return os.getenv('workspace_uid')
    
    def is_available(self) -> bool:
        """Vérifie si le client API est disponible"""
        return self.workspace_uid is not None
    
    def _get_client_for_region(self, region: str):
        """
        Obtient ou crée un client BackboneClient pour une région spécifique
        Utilise threading.local pour isoler les clients par thread
        
        Args:
            region: Région AWS (ex: 'eu-west-1', 'us-east-1')
            
        Returns:
            BackboneClient configuré pour cette région
        """
        # Initialiser le stockage local pour ce thread si nécessaire
        if not hasattr(self._local, 'clients'):
            self._local.clients = {}
        
        # Si on a déjà un client pour cette région dans ce thread, le retourner
        if region in self._local.clients:
            return self._local.clients[region]
        
        # Créer un nouveau client pour cette région
        # Utiliser un lock pour éviter les race conditions pendant la création
        with self._creation_lock:
            # Double-check après acquisition du lock
            if region in self._local.clients:
                return self._local.clients[region]
            
            try:
                # Sauvegarder les anciennes valeurs d'environnement
                old_default_region = os.environ.get('AWS_DEFAULT_REGION')
                old_region = os.environ.get('AWS_REGION')
                old_workspace_uid = os.environ.get('WORKSPACE_UID')
                
                # Définir temporairement les variables d'environnement
                os.environ['AWS_DEFAULT_REGION'] = region
                os.environ['AWS_REGION'] = region
                os.environ['WORKSPACE_UID'] = self.workspace_uid
                
                # Importer et créer le client
                from pyckbone import BackboneClient
                client = BackboneClient(workspace_uid=self.workspace_uid)
                
                # Restaurer immédiatement les anciennes valeurs
                if old_default_region:
                    os.environ['AWS_DEFAULT_REGION'] = old_default_region
                else:
                    os.environ.pop('AWS_DEFAULT_REGION', None)
                    
                if old_region:
                    os.environ['AWS_REGION'] = old_region
                else:
                    os.environ.pop('AWS_REGION', None)
                    
                if old_workspace_uid:
                    os.environ['WORKSPACE_UID'] = old_workspace_uid
                else:
                    os.environ.pop('WORKSPACE_UID', None)
                
                # Mettre en cache pour ce thread
                self._local.clients[region] = client
                
                print(f"✅ Client BackboneClient créé pour région {region} dans thread {threading.current_thread().name}")
                return client
                
            except ImportError:
                self.init_error = "Module pyckbone non installé"
                raise Exception("Module pyckbone non installé")
            except Exception as e:
                self.init_error = str(e)
                raise
    
    def abort_task_direct(self, task_id: str, region: str) -> Dict[str, Any]:
        """
        Annule une tâche directement avec son task_id

        Args:
            task_id: ID exact de la tâche à annuler
            region: Région AWS

        Returns:
            Résultat de l'opération
        """
        if not self.is_available():
            return {"success": False, "error": "BackboneClient non disponible"}

        try:
            # Obtenir le client pour cette région (thread-safe)
            client = self._get_client_for_region(region)

            # Exécuter l'action
            result = client.abort_task_by_id(task_id=task_id)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def break_task_direct(self, task_id: str, region: str) -> Dict[str, Any]:
        """
        Marque une tâche comme cassée (broken)

        Args:
            task_id: ID exact de la tâche
            region: Région AWS

        Returns:
            Résultat de l'opération
        """
        if not self.is_available():
            return {"success": False, "error": "BackboneClient non disponible"}

        try:
            # Obtenir le client pour cette région (thread-safe)
            client = self._get_client_for_region(region)

            # Exécuter l'action
            result = client.set_task_as_broken_by_id(task_id=task_id)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def restart_task(self, task_id: str, media_id: str, region: str) -> Dict[str, Any]:
        """
        Redémarre une tâche

        Args:
            task_id: ID de la tâche
            media_id: ID du media
            region: Région AWS

        Returns:
            Résultat de l'opération
        """
        if not self.is_available():
            return {"success": False, "error": "BackboneClient non disponible"}

        try:
            # Obtenir le client pour cette région (thread-safe)
            client = self._get_client_for_region(region)

            # Récupérer les informations de la tâche
            query_filter = f"eq(task_id,{task_id})"
            tasks_result = client.get_tasks(query_filter=query_filter)

            # Extraire la première tâche
            tasks_list = tasks_result.get('data', []) if isinstance(tasks_result, dict) else []
            if not tasks_list or len(tasks_list) == 0:
                return {"success": False, "error": f"Tâche {task_id} non trouvée"}

            task_info = tasks_list[0]

            # Extraire les paramètres nécessaires
            task_name = task_info.get('type') or task_info.get('task_name') or task_info.get('name')

            if not task_name:
                return {"success": False, "error": "task_name/type non trouvé dans les informations de la tâche"}

            # Paramètres optionnels
            language = task_info.get('language')
            profile_uid = task_info.get('profile_uid')
            dest_uid = task_info.get('dest_uid')
            prompt_uid = task_info.get('prompt_uid')

            # Relancer la tâche
            result = client.launch_task(
                task_name=task_name,
                media_id=media_id,
                language=language,
                profile_uid=profile_uid,
                dest_uid=dest_uid,
                prompt_uid=prompt_uid
            )

            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def restart_and_break_task_direct(self, task_id: str, media_id: str, region: str) -> Dict[str, Any]:
        """
        Redémarre une tâche et la marque comme broken

        Args:
            task_id: ID de la tâche
            media_id: ID du media
            region: Région AWS

        Returns:
            Résultat de l'opération
        """
        if not self.is_available():
            return {"success": False, "error": "BackboneClient non disponible"}

        try:
            # Marquer comme broken
            break_result = self.break_task_direct(task_id, region)

            if not break_result["success"]:
                return {"success": False, "error": f"Échec du break: {break_result['error']}"}

            # Redémarrer la tâche
            restart_result = self.restart_task(task_id, media_id, region)

            if not restart_result["success"]:
                return {"success": False, "error": f"Break réussi mais échec du restart: {restart_result['error']}"}

            return {
                "success": True,
                "result": {
                    "break": break_result["result"],
                    "restart": restart_result["result"]
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def repair_assembly(self, assembly_id: str, region: str) -> Dict[str, Any]:
        """
        Répare un assembly

        Args:
            assembly_id: ID de l'assembly à réparer
            region: Région AWS

        Returns:
            Résultat de l'opération
        """
        if not self.is_available():
            return {"success": False, "error": "BackboneClient non disponible"}

        try:
            # Obtenir le client pour cette région (thread-safe)
            client = self._get_client_for_region(region)

            # Exécuter l'action
            result = client.repair_assembly(assembly_id=assembly_id)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @property
    def client(self):
        """
        Propriété pour compatibilité avec l'ancien code qui utilise backbone.client
        Retourne un client pour la région par défaut (eu-west-1)
        """
        default_region = os.environ.get('AWS_DEFAULT_REGION', 'eu-west-1')
        return self._get_client_for_region(default_region)

