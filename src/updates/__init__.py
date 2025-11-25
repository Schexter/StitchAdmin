# -*- coding: utf-8 -*-
"""
StitchAdmin 2.0 - Updates Package
Backup und Update Management

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from .backup_manager import BackupManager, get_backup_manager
from .update_manager import UpdateManager, UpdateInfo, UpdateResult

__all__ = [
    'BackupManager',
    'get_backup_manager',
    'UpdateManager', 
    'UpdateInfo',
    'UpdateResult',
]
