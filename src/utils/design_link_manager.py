"""
Link-Manager für Design-Workflow
Behandelt externe Design-Links und Grafikmanager-Integration
Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import os
import json
import requests
from datetime import datetime
from typing import Dict, List, Optional, Union
from urllib.parse import urlparse, urljoin
import mimetypes

class DesignLinkManager:
    """Manager für Design-Links und Grafikmanager-Integration"""
    
    def __init__(self):
        self.links_folder = 'data/design_links'
        self.graphics_manager_folder = 'data/graphics_manager'
        self.ensure_directories()
    
    def ensure_directories(self):
        """Erstellt alle benötigten Verzeichnisse"""
        os.makedirs(self.links_folder, exist_ok=True)
        os.makedirs(self.graphics_manager_folder, exist_ok=True)
    
    def process_design_link(self, url: str, order_id: str, user: str = None) -> Dict:
        """
        Verarbeitet einen Design-Link
        
        Args:
            url: URL des Designs
            order_id: Bestellungs-ID
            user: Benutzer der den Link eingibt
            
        Returns:
            Dict mit Verarbeitungsergebnis
        """
        try:
            # URL validieren
            if not self._validate_url(url):
                return {
                    'success': False,
                    'error': 'Ungültige URL',
                    'requires_graphics_manager': True
                }
            
            # Link-Informationen sammeln
            link_info = self._analyze_link(url)
            
            # Speichere Link-Informationen
            link_data = {
                'order_id': order_id,
                'url': url,
                'created_at': datetime.now().isoformat(),
                'created_by': user,
                'status': 'pending',
                'link_info': link_info,
                'graphics_manager_required': self._requires_graphics_manager(link_info),
                'workflow_status': 'link_provided'
            }
            
            # Speichere in Datei
            self._save_link_data(order_id, link_data)
            
            # Bestimme nächste Schritte
            next_steps = self._determine_next_steps(link_info)
            
            return {
                'success': True,
                'link_data': link_data,
                'requires_graphics_manager': link_data['graphics_manager_required'],
                'next_steps': next_steps,
                'workflow_status': link_data['workflow_status']
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Fehler bei Link-Verarbeitung: {str(e)}',
                'requires_graphics_manager': True
            }
    
    def _validate_url(self, url: str) -> bool:
        """Validiert URL"""
        try:
            parsed = urlparse(url)
            return bool(parsed.scheme and parsed.netloc)
        except:
            return False
    
    def _analyze_link(self, url: str) -> Dict:
        """Analysiert Link-Eigenschaften"""
        try:
            parsed = urlparse(url)
            
            # Basis-Informationen
            link_info = {
                'domain': parsed.netloc,
                'path': parsed.path,
                'scheme': parsed.scheme,
                'is_secure': parsed.scheme == 'https',
                'file_extension': None,
                'content_type': None,
                'file_size': None,
                'is_direct_file': False,
                'platform_type': self._detect_platform_type(parsed.netloc),
                'analysis_timestamp': datetime.now().isoformat()
            }
            
            # Dateierweiterung prüfen
            if parsed.path:
                path_parts = parsed.path.split('/')
                if path_parts and '.' in path_parts[-1]:
                    link_info['file_extension'] = path_parts[-1].split('.')[-1].lower()
                    link_info['is_direct_file'] = True
            
            # Versuche HEAD-Request für mehr Informationen
            try:
                response = requests.head(url, timeout=10, allow_redirects=True)
                
                link_info['status_code'] = response.status_code
                link_info['content_type'] = response.headers.get('content-type', '')
                link_info['file_size'] = response.headers.get('content-length')
                
                # Prüfe auf Redirect
                if response.history:
                    link_info['redirected'] = True
                    link_info['final_url'] = response.url
                
            except Exception as e:
                link_info['head_request_error'] = str(e)
            
            return link_info
            
        except Exception as e:
            return {
                'error': f'Fehler bei Link-Analyse: {str(e)}',
                'analysis_timestamp': datetime.now().isoformat()
            }
    
    def _detect_platform_type(self, domain: str) -> str:
        """Erkennt Plattform-Typ basierend auf Domain"""
        domain_lower = domain.lower()
        
        # Cloud-Speicher
        if 'dropbox.com' in domain_lower:
            return 'dropbox'
        elif 'drive.google.com' in domain_lower:
            return 'google_drive'
        elif 'onedrive.live.com' in domain_lower or 'onedrive.com' in domain_lower:
            return 'onedrive'
        elif 'wetransfer.com' in domain_lower:
            return 'wetransfer'
        elif 'mega.nz' in domain_lower or 'mega.co.nz' in domain_lower:
            return 'mega'
        
        # Design-Plattformen
        elif 'behance.net' in domain_lower:
            return 'behance'
        elif 'dribbble.com' in domain_lower:
            return 'dribbble'
        elif 'pinterest.com' in domain_lower or 'pinterest.de' in domain_lower:
            return 'pinterest'
        elif 'instagram.com' in domain_lower:
            return 'instagram'
        
        # Firmen-Domains
        elif any(keyword in domain_lower for keyword in ['company', 'corp', 'business', 'enterprise']):
            return 'corporate'
        
        # Standard-Webseite
        else:
            return 'website'
    
    def _requires_graphics_manager(self, link_info: Dict) -> bool:
        """Bestimmt ob Grafikmanager benötigt wird"""
        try:
            # Direkte Dateien mit bekannten Erweiterungen
            if link_info.get('is_direct_file'):
                extension = link_info.get('file_extension', '').lower()
                
                # Stickerei-Dateien brauchen meist keinen Grafikmanager
                if extension in ['dst', 'pes', 'jef', 'exp', 'vp3', 'vp4']:
                    return False
                
                # Druck-Dateien in hoher Qualität brauchen eventuell keinen
                if extension in ['svg', 'ai', 'eps', 'pdf']:
                    return False
                
                # Bilder brauchen meist Grafikmanager
                if extension in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff']:
                    return True
            
            # Plattform-basierte Entscheidung
            platform = link_info.get('platform_type', '')
            
            # Design-Plattformen brauchen meist Grafikmanager
            if platform in ['behance', 'dribbble', 'pinterest', 'instagram']:
                return True
            
            # Cloud-Speicher - abhängig vom Inhalt
            if platform in ['dropbox', 'google_drive', 'onedrive', 'wetransfer', 'mega']:
                return True  # Sicher ist sicher
            
            # Unbekannte Links brauchen Grafikmanager
            return True
            
        except Exception as e:
            # Im Zweifelsfall Grafikmanager anzeigen
            return True
    
    def _determine_next_steps(self, link_info: Dict) -> List[Dict]:
        """Bestimmt nächste Schritte im Workflow"""
        steps = []
        
        platform = link_info.get('platform_type', '')
        is_direct_file = link_info.get('is_direct_file', False)
        
        if is_direct_file:
            extension = link_info.get('file_extension', '').lower()
            
            if extension in ['dst', 'pes', 'jef', 'exp']:
                steps.append({
                    'action': 'download_embroidery_file',
                    'title': 'Stickerei-Datei herunterladen',
                    'description': 'Datei herunterladen und analysieren',
                    'priority': 'high'
                })
            elif extension in ['svg', 'ai', 'eps', 'pdf']:
                steps.append({
                    'action': 'download_vector_file',
                    'title': 'Vektor-Datei herunterladen',
                    'description': 'Datei für Druckvorbereitung herunterladen',
                    'priority': 'medium'
                })
            else:
                steps.append({
                    'action': 'download_and_optimize',
                    'title': 'Datei herunterladen und optimieren',
                    'description': 'Datei herunterladen und für Produktion optimieren',
                    'priority': 'medium'
                })
        
        # Plattform-spezifische Schritte
        if platform == 'google_drive':
            steps.append({
                'action': 'check_google_drive_permissions',
                'title': 'Google Drive Berechtigung prüfen',
                'description': 'Zugriff auf Google Drive Datei prüfen',
                'priority': 'high'
            })
        elif platform == 'dropbox':
            steps.append({
                'action': 'check_dropbox_link',
                'title': 'Dropbox Link prüfen',
                'description': 'Dropbox-Freigabe und Download prüfen',
                'priority': 'high'
            })
        elif platform in ['behance', 'dribbble', 'pinterest', 'instagram']:
            steps.append({
                'action': 'manual_download_required',
                'title': 'Manueller Download erforderlich',
                'description': f'Datei manuell von {platform.title()} herunterladen',
                'priority': 'high'
            })
        
        # Immer: Grafikmanager-Schritt wenn nötig
        if self._requires_graphics_manager(link_info):
            steps.append({
                'action': 'graphics_manager_processing',
                'title': 'Grafikmanager-Bearbeitung',
                'description': 'Design für Produktion anpassen',
                'priority': 'medium'
            })
        
        # Abschließende Schritte
        steps.append({
            'action': 'final_review',
            'title': 'Finale Überprüfung',
            'description': 'Design-Datei final prüfen und freigeben',
            'priority': 'low'
        })
        
        return steps
    
    def _save_link_data(self, order_id: str, link_data: Dict):
        """Speichert Link-Daten in Datei"""
        file_path = os.path.join(self.links_folder, f'{order_id}_link.json')
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(link_data, f, indent=2, ensure_ascii=False)
    
    def get_link_data(self, order_id: str) -> Optional[Dict]:
        """Holt Link-Daten für Bestellung"""
        file_path = os.path.join(self.links_folder, f'{order_id}_link.json')
        
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return None
        return None
    
    def update_link_status(self, order_id: str, status: str, user: str = None, notes: str = None) -> bool:
        """Aktualisiert Link-Status"""
        try:
            link_data = self.get_link_data(order_id)
            if not link_data:
                return False
            
            link_data['status'] = status
            link_data['updated_at'] = datetime.now().isoformat()
            link_data['updated_by'] = user
            
            if notes:
                if 'notes' not in link_data:
                    link_data['notes'] = []
                link_data['notes'].append({
                    'timestamp': datetime.now().isoformat(),
                    'user': user,
                    'note': notes
                })
            
            self._save_link_data(order_id, link_data)
            return True
            
        except Exception as e:
            print(f'Fehler beim Update des Link-Status: {e}')
            return False
    
    def create_graphics_manager_task(self, order_id: str, link_data: Dict, user: str = None) -> Dict:
        """Erstellt Grafikmanager-Aufgabe"""
        try:
            task_data = {
                'order_id': order_id,
                'type': 'link_processing',
                'status': 'pending',
                'created_at': datetime.now().isoformat(),
                'created_by': user,
                'priority': 'medium',
                'source_link': link_data['url'],
                'link_info': link_data.get('link_info', {}),
                'requirements': self._generate_processing_requirements(link_data),
                'workflow_steps': self._generate_workflow_steps(link_data)
            }
            
            # Speichere Aufgabe
            task_file = os.path.join(self.graphics_manager_folder, f'{order_id}_task.json')
            with open(task_file, 'w', encoding='utf-8') as f:
                json.dump(task_data, f, indent=2, ensure_ascii=False)
            
            return {
                'success': True,
                'task_id': order_id,
                'task_data': task_data
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Fehler beim Erstellen der Grafikmanager-Aufgabe: {str(e)}'
            }
    
    def _generate_processing_requirements(self, link_data: Dict) -> List[Dict]:
        """Generiert Bearbeitungs-Anforderungen"""
        requirements = []
        
        link_info = link_data.get('link_info', {})
        platform = link_info.get('platform_type', '')
        
        # Standard-Anforderungen
        requirements.append({
            'type': 'download',
            'title': 'Datei herunterladen',
            'description': 'Design-Datei vom angegebenen Link herunterladen',
            'mandatory': True
        })
        
        requirements.append({
            'type': 'format_check',
            'title': 'Format prüfen',
            'description': 'Dateiformat und Qualität prüfen',
            'mandatory': True
        })
        
        # Plattform-spezifische Anforderungen
        if platform in ['behance', 'dribbble', 'pinterest']:
            requirements.append({
                'type': 'manual_extraction',
                'title': 'Manueller Download',
                'description': f'Datei manuell von {platform.title()} herunterladen',
                'mandatory': True
            })
        
        # Format-spezifische Anforderungen
        if link_info.get('file_extension') in ['jpg', 'jpeg', 'png', 'gif']:
            requirements.append({
                'type': 'image_optimization',
                'title': 'Bild optimieren',
                'description': 'Auflösung, Farben und Format für Produktion optimieren',
                'mandatory': True
            })
        
        requirements.append({
            'type': 'production_ready',
            'title': 'Produktionsbereit machen',
            'description': 'Datei für Stickerei oder Druck vorbereiten',
            'mandatory': True
        })
        
        return requirements
    
    def _generate_workflow_steps(self, link_data: Dict) -> List[Dict]:
        """Generiert Workflow-Schritte"""
        steps = []
        
        steps.append({
            'step': 1,
            'title': 'Link analysieren',
            'description': 'Link-Eigenschaften und Plattform analysieren',
            'status': 'completed',
            'completed_at': datetime.now().isoformat()
        })
        
        steps.append({
            'step': 2,
            'title': 'Datei herunterladen',
            'description': 'Design-Datei vom Link herunterladen',
            'status': 'pending'
        })
        
        steps.append({
            'step': 3,
            'title': 'Format prüfen',
            'description': 'Dateiformat und Qualität analysieren',
            'status': 'pending'
        })
        
        steps.append({
            'step': 4,
            'title': 'Für Produktion anpassen',
            'description': 'Design für Stickerei oder Druck optimieren',
            'status': 'pending'
        })
        
        steps.append({
            'step': 5,
            'title': 'Finale Überprüfung',
            'description': 'Qualität prüfen und freigeben',
            'status': 'pending'
        })
        
        return steps
    
    def get_graphics_manager_task(self, order_id: str) -> Optional[Dict]:
        """Holt Grafikmanager-Aufgabe"""
        task_file = os.path.join(self.graphics_manager_folder, f'{order_id}_task.json')
        
        if os.path.exists(task_file):
            try:
                with open(task_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return None
        return None
    
    def update_graphics_manager_task(self, order_id: str, updates: Dict, user: str = None) -> bool:
        """Aktualisiert Grafikmanager-Aufgabe"""
        try:
            task_data = self.get_graphics_manager_task(order_id)
            if not task_data:
                return False
            
            task_data.update(updates)
            task_data['updated_at'] = datetime.now().isoformat()
            task_data['updated_by'] = user
            
            task_file = os.path.join(self.graphics_manager_folder, f'{order_id}_task.json')
            with open(task_file, 'w', encoding='utf-8') as f:
                json.dump(task_data, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            print(f'Fehler beim Update der Grafikmanager-Aufgabe: {e}')
            return False
    
    def check_link_requires_graphics_manager(self, order_id: str) -> bool:
        """Prüft ob Link Grafikmanager benötigt"""
        link_data = self.get_link_data(order_id)
        if not link_data:
            return False
        
        return link_data.get('graphics_manager_required', False)
    
    def get_all_pending_tasks(self) -> List[Dict]:
        """Holt alle wartenden Grafikmanager-Aufgaben"""
        tasks = []
        
        try:
            for filename in os.listdir(self.graphics_manager_folder):
                if filename.endswith('_task.json'):
                    task_file = os.path.join(self.graphics_manager_folder, filename)
                    try:
                        with open(task_file, 'r', encoding='utf-8') as f:
                            task_data = json.load(f)
                            if task_data.get('status') == 'pending':
                                tasks.append(task_data)
                    except:
                        continue
        except:
            pass
        
        return sorted(tasks, key=lambda x: x.get('created_at', ''), reverse=True)


# Singleton-Instanz
link_manager = DesignLinkManager()

# Hilfsfunktionen
def process_design_link(url: str, order_id: str, user: str = None) -> Dict:
    """Verarbeitet Design-Link"""
    return link_manager.process_design_link(url, order_id, user)

def check_link_exists(order_id: str) -> bool:
    """Prüft ob Link für Bestellung existiert"""
    return link_manager.get_link_data(order_id) is not None

def get_link_status(order_id: str) -> Optional[str]:
    """Holt Link-Status"""
    link_data = link_manager.get_link_data(order_id)
    return link_data.get('status') if link_data else None

def requires_graphics_manager(order_id: str) -> bool:
    """Prüft ob Grafikmanager benötigt wird"""
    return link_manager.check_link_requires_graphics_manager(order_id)

def create_graphics_manager_task(order_id: str, user: str = None) -> Dict:
    """Erstellt Grafikmanager-Aufgabe"""
    link_data = link_manager.get_link_data(order_id)
    if not link_data:
        return {'success': False, 'error': 'Keine Link-Daten gefunden'}
    
    return link_manager.create_graphics_manager_task(order_id, link_data, user)

def get_pending_graphics_tasks() -> List[Dict]:
    """Holt alle wartenden Grafikmanager-Aufgaben"""
    return link_manager.get_all_pending_tasks()
