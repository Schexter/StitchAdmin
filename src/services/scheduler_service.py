# -*- coding: utf-8 -*-
"""
Scheduler Service - APScheduler Integration fuer StitchAdmin
Hintergrund-Jobs: Social Media Posts, E-Mail-Polling, Bank-Sync

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import os
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

logger = logging.getLogger(__name__)

_scheduler = None
_app = None


def init_scheduler(app):
    """APScheduler mit Flask-App initialisieren"""
    global _scheduler, _app

    # Nicht im Reloader-Child-Prozess starten
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
        _app = app
        db_url = app.config.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///instance/stitchadmin.db')

        jobstores = {
            'default': SQLAlchemyJobStore(url=db_url, tablename='apscheduler_jobs')
        }
        executors = {
            'default': ThreadPoolExecutor(max_workers=4)
        }
        job_defaults = {
            'coalesce': True,
            'max_instances': 1,
            'misfire_grace_time': 300,
        }

        _scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
        )
        _scheduler.start()
        logger.info("APScheduler gestartet")
    else:
        logger.info("APScheduler uebersprungen (Reloader-Prozess)")


def get_scheduler():
    """Scheduler-Instanz abrufen"""
    return _scheduler


def add_job(func, trigger, job_id=None, **kwargs):
    """Job zum Scheduler hinzufuegen (mit Flask app_context)"""
    if not _scheduler:
        logger.warning("Scheduler nicht initialisiert - Job wird nicht geplant")
        return None

    def wrapped_func(*args, **kw):
        with _app.app_context():
            return func(*args, **kw)

    return _scheduler.add_job(
        wrapped_func,
        trigger=trigger,
        id=job_id,
        replace_existing=True,
        **kwargs
    )


def remove_job(job_id):
    """Job entfernen"""
    if _scheduler:
        try:
            _scheduler.remove_job(job_id)
            return True
        except Exception:
            return False
    return False


def list_jobs():
    """Alle geplanten Jobs auflisten"""
    if _scheduler:
        return _scheduler.get_jobs()
    return []


def shutdown_scheduler():
    """Scheduler sauber beenden"""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("APScheduler beendet")
