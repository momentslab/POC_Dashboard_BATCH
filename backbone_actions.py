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
        self.init_error = None

        if self.workspace_uid:
            # Définir la variable d'environnement AVANT d'importer BackboneClient
            os.environ['WORKSPACE_UID'] = self.workspace_uid

            try:
                from pyckbone import BackboneClient
                self.client = BackboneClient(workspace_uid=self.workspace_uid)
            except ImportError:
                self.init_error = "Module pyckbone non installé"
                st.warning("Module pyckbone non installé. Les actions API ne sont pas disponibles.")
            except Exception as e:
                error_msg = str(e)
                self.init_error = error_msg
                # Ne pas afficher l'erreur ici, on la gérera plus tard
                # Pour éviter d'afficher l'erreur à chaque rechargement de page
    
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
        return self.client is not None and self.workspace_uid is not None
    
    def abort_task_direct(self, task_id: str) -> Dict[str, Any]:
        """
        Annule une tâche directement avec son task_id (sans recherche par media_id)

        Args:
            task_id: ID exact de la tâche à annuler

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

    def abort_task(self, task_id: str, media_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Annule une tâche

        Args:
            task_id: ID de la tâche à annuler (peut être inexact, on cherchera par media_id si fourni)
            media_id: ID du media (optionnel, utilisé pour retrouver la vraie tâche)

        Returns:
            Résultat de l'opération
        """
        if not self.is_available():
            return {"success": False, "error": "BackboneClient non disponible"}

        try:
            # Si media_id est fourni, chercher la vraie tâche d'abord
            actual_task_id = task_id
            if media_id and media_id != "Unknown":
                # Chercher la tâche par media_id
                query_filter = f"eq(media_id,{media_id})"
                tasks_result = self.client.get_tasks(query_filter=query_filter)

                # get_tasks retourne un dict avec 'data' contenant la liste des tâches
                tasks_list = tasks_result.get('data', []) if isinstance(tasks_result, dict) else tasks_result

                # Si on trouve des tâches, prendre la première (la plus récente normalement)
                if tasks_list and len(tasks_list) > 0:
                    actual_task_id = tasks_list[0].get('task_id') or tasks_list[0].get('_id')

            result = self.client.abort_task_by_id(task_id=actual_task_id)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def break_task_direct(self, task_id: str) -> Dict[str, Any]:
        """
        Marque une tâche comme cassée directement avec son task_id (sans recherche par media_id)

        Args:
            task_id: ID exact de la tâche à marquer comme cassée

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

    def break_task(self, task_id: str, media_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Marque une tâche comme cassée

        Args:
            task_id: ID de la tâche à marquer comme cassée (peut être inexact, on cherchera par media_id si fourni)
            media_id: ID du media (optionnel, utilisé pour retrouver la vraie tâche)

        Returns:
            Résultat de l'opération
        """
        if not self.is_available():
            return {"success": False, "error": "BackboneClient non disponible"}

        try:
            # Si media_id est fourni, chercher la vraie tâche d'abord
            actual_task_id = task_id
            if media_id and media_id != "Unknown":
                print(f"Recherche de la tâche avec media_id: {media_id}")
                # Chercher la tâche par media_id
                query_filter = f"eq(media_id,{media_id})"
                print(f"Query filter: {query_filter}")
                tasks_result = self.client.get_tasks(query_filter=query_filter)
                print(f"Résultat get_tasks: {tasks_result}")

                # get_tasks retourne un dict avec 'data' contenant la liste des tâches
                tasks_list = tasks_result.get('data', []) if isinstance(tasks_result, dict) else tasks_result
                print(f"Nombre de tâches trouvées: {len(tasks_list) if tasks_list else 0}")

                # Si on trouve des tâches, prendre la première (la plus récente normalement)
                if tasks_list and len(tasks_list) > 0:
                    print(f"Première tâche trouvée: {tasks_list[0]}")
                    actual_task_id = tasks_list[0].get('task_id') or tasks_list[0].get('_id')
                    print(f"Task ID trouvé: {actual_task_id}")
                else:
                    print(f"Aucune tâche trouvée avec media_id={media_id}, utilisation du task_id original: {task_id}")

            print(f"Appel break_task_by_id avec task_id: {actual_task_id}")
            result = self.client.break_task_by_id(task_id=actual_task_id)
            print(f"Résultat break_task_by_id: {result}")
            return {"success": True, "result": result}
        except Exception as e:
            print(f"Erreur dans break_task: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
    
    def get_task_info(self, task_id: str, media_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Récupère les informations d'une tâche

        Args:
            task_id: ID de la tâche
            media_id: ID du media (optionnel)

        Returns:
            Informations de la tâche (premier élément de data si trouvé)
        """
        if not self.is_available():
            return {"success": False, "error": "BackboneClient non disponible"}

        try:
            query_filter = f"eq(task_id,{task_id})"
            result = self.client.get_tasks(query_filter=query_filter)

            # Extraire la première tâche de 'data'
            tasks_list = result.get('data', []) if isinstance(result, dict) else []
            if tasks_list and len(tasks_list) > 0:
                return {"success": True, "result": tasks_list[0]}
            else:
                return {"success": False, "error": f"Tâche {task_id} non trouvée"}
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
            print(f"Récupération des infos de la tâche {task_id}")
            task_info_result = self.get_task_info(task_id, media_id)

            if not task_info_result["success"]:
                print(f"Échec de la récupération: {task_info_result.get('error')}")
                return task_info_result

            task_info = task_info_result["result"]
            print(f"Informations de la tâche: {task_info}")

            # Extraire les paramètres nécessaires
            # Les tâches Backbone utilisent 'type' comme nom de tâche
            task_name = task_info.get('type') or task_info.get('task_name') or task_info.get('name')

            if not task_name:
                print(f"task_name/type non trouvé. Clés disponibles: {list(task_info.keys())}")
                return {"success": False, "error": f"task_name/type non trouvé dans les informations de la tâche. Clés disponibles: {list(task_info.keys())}"}

            print(f"Task name trouvé: {task_name}")

            # Paramètres optionnels
            language = task_info.get('language')
            profile_uid = task_info.get('profile_uid')
            dest_uid = task_info.get('dest_uid')
            prompt_uid = task_info.get('prompt_uid')

            print(f"Lancement de la tâche: task_name={task_name}, media_id={media_id}")

            # Relancer la tâche
            result = self.client.launch_task(
                task_name=task_name,
                media_id=media_id,
                language=language,
                profile_uid=profile_uid,
                dest_uid=dest_uid,
                prompt_uid=prompt_uid
            )

            print(f"Résultat launch_task: {result}")
            return {"success": True, "result": result}
        except Exception as e:
            print(f"Erreur dans restart_task: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
    
    def restart_and_break_task_direct(self, task_id: str, media_id: str) -> Dict[str, Any]:
        """
        Marque une tâche comme cassée puis la relance (version directe sans recherche)

        Args:
            task_id: ID exact de la tâche
            media_id: ID du media

        Returns:
            Résultat de l'opération
        """
        # Marquer comme cassée directement
        break_result = self.break_task_direct(task_id)

        if not break_result["success"]:
            return {"success": False, "error": f"Échec du break: {break_result['error']}"}

        # Relancer la tâche
        restart_result = self.restart_task(task_id, media_id)

        if not restart_result["success"]:
            return {"success": False, "error": f"Break réussi mais échec du restart: {restart_result['error']}"}

        return {"success": True, "result": {"break": break_result["result"], "restart": restart_result["result"]}}

    def restart_and_break_task(self, task_id: str, media_id: str) -> Dict[str, Any]:
        """
        Marque une tâche comme cassée puis la relance

        Args:
            task_id: ID de la tâche
            media_id: ID du media

        Returns:
            Résultat de l'opération
        """
        # Marquer comme cassée (passer media_id pour retrouver la vraie tâche)
        break_result = self.break_task(task_id, media_id)

        if not break_result["success"]:
            return {"success": False, "error": f"Échec du break: {break_result['error']}"}

        # Relancer la tâche
        restart_result = self.restart_task(task_id, media_id)

        if not restart_result["success"]:
            return {"success": False, "error": f"Break réussi mais échec du restart: {restart_result['error']}"}

        return {"success": True, "result": {"break": break_result["result"], "restart": restart_result["result"]}}

