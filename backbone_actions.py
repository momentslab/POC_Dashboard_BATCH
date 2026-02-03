"""
Module pour gérer les actions API via BackboneClient
"""
import os
from typing import Optional, Dict, Any
import streamlit as st


class BackboneActions:
    """Classe pour gérer les actions sur les tâches via BackboneClient"""
    
    def __init__(self):
        """Initialise le client BackboneClient"""
        # Récupérer workspace_uid depuis les secrets Streamlit ou variable d'environnement
        self.workspace_uid = self._get_workspace_uid()
        self.client = None
        
        if self.workspace_uid:
            try:
                from pyckbone import BackboneClient
                self.client = BackboneClient(workspace_uid=self.workspace_uid)
            except ImportError:
                st.warning("⚠️ Module pyckbone non installé. Les actions API ne sont pas disponibles.")
            except Exception as e:
                st.error(f"❌ Erreur lors de l'initialisation de BackboneClient: {str(e)}")
    
    def _get_workspace_uid(self) -> Optional[str]:
        """Récupère le workspace_uid depuis les secrets ou variables d'environnement"""
        # Essayer depuis les secrets Streamlit
        if hasattr(st, 'secrets') and 'workspace_uid' in st.secrets:
            return st.secrets['workspace_uid']
        
        # Essayer depuis les variables d'environnement
        return os.getenv('WORKSPACE_UID')
    
    def is_available(self) -> bool:
        """Vérifie si le client API est disponible"""
        return self.client is not None and self.workspace_uid is not None
    
    def abort_task(self, task_id: str) -> Dict[str, Any]:
        """
        Annule une tâche
        
        Args:
            task_id: ID de la tâche à annuler
            
        Returns:
            Résultat de l'opération
        """
        if not self.is_available():
            return {"success": False, "error": "BackboneClient non disponible"}
        
        try:
            result = self.client.abort_task_by_id(task_id=task_id)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def break_task(self, task_id: str) -> Dict[str, Any]:
        """
        Marque une tâche comme cassée
        
        Args:
            task_id: ID de la tâche à marquer comme cassée
            
        Returns:
            Résultat de l'opération
        """
        if not self.is_available():
            return {"success": False, "error": "BackboneClient non disponible"}
        
        try:
            result = self.client.break_task_by_id(task_id=task_id)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_task_info(self, task_id: str, media_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Récupère les informations d'une tâche
        
        Args:
            task_id: ID de la tâche
            media_id: ID du media (optionnel)
            
        Returns:
            Informations de la tâche
        """
        if not self.is_available():
            return {"success": False, "error": "BackboneClient non disponible"}
        
        try:
            query_filter = f"eq(task_id,{task_id})"
            result = self.client.get_tasks(query_filter=query_filter)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def restart_task(self, task_id: str, media_id: str) -> Dict[str, Any]:
        """
        Relance une tâche en récupérant ses paramètres originaux
        
        Args:
            task_id: ID de la tâche à relancer
            media_id: ID du media
            
        Returns:
            Résultat de l'opération
        """
        if not self.is_available():
            return {"success": False, "error": "BackboneClient non disponible"}
        
        try:
            # Récupérer les informations de la tâche
            task_info_result = self.get_task_info(task_id, media_id)
            
            if not task_info_result["success"]:
                return task_info_result
            
            task_info = task_info_result["result"]
            
            # Extraire les paramètres nécessaires
            # Note: La structure exacte dépend de la réponse de get_tasks()
            # On suppose que task_info contient les champs nécessaires
            task_name = task_info.get('task_name') or task_info.get('name')
            
            if not task_name:
                return {"success": False, "error": "task_name non trouvé dans les informations de la tâche"}
            
            # Paramètres optionnels
            language = task_info.get('language')
            profile_uid = task_info.get('profile_uid')
            dest_uid = task_info.get('dest_uid')
            prompt_uid = task_info.get('prompt_uid')
            
            # Relancer la tâche
            result = self.client.launch_task(
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
    
    def restart_and_break_task(self, task_id: str, media_id: str) -> Dict[str, Any]:
        """
        Marque une tâche comme cassée puis la relance
        
        Args:
            task_id: ID de la tâche
            media_id: ID du media
            
        Returns:
            Résultat de l'opération
        """
        # Marquer comme cassée
        break_result = self.break_task(task_id)
        
        if not break_result["success"]:
            return {"success": False, "error": f"Échec du break: {break_result['error']}"}
        
        # Relancer la tâche
        restart_result = self.restart_task(task_id, media_id)
        
        if not restart_result["success"]:
            return {"success": False, "error": f"Break réussi mais échec du restart: {restart_result['error']}"}
        
        return {"success": True, "result": {"break": break_result["result"], "restart": restart_result["result"]}}

