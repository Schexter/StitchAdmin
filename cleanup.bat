@echo off
echo Loesche veraltete Dateien und Skripte...

del build.bat
del start.bat
del fix_sqlalchemy.bat
del setup_database.py
del build_config.py
del fix_dashboard_quick.py
del add_documents_blueprint.py
del setup_kachel_dashboard.bat

del create_crm_tables.sql
del create_document_tables.sql
del create_workflow_tables.sql
del create_nummernkreis_tables.sql
del create_finanzmanagement_tables.sql
del complete_database_setup.sql

del PYTHON313_FIX.md
del PROBLEM_BEHOBEN.md
del ZUGPFERD_README.md
del PROJEKT_STRUKTUR.md
del MIGRATION_KOMPLETT.md
del START_IN_INTELLIJ.txt
del MIGRATION_SUMMARY_HANS.md
del MIGRATION_ABGESCHLOSSEN.md
del IMPLEMENTATION_SUMMARY.md
del KACHEL_DASHBOARD_UMBAU.md
del IMPLEMENTATION_COMPLETE.md
del KACHEL_DASHBOARD_QUICKSTART.md
del app.py.backup_20251123_220108

del activity_log.json
del "Preisliste Import Lshop.xlsx"

echo Aufraeumen abgeschlossen. Diese Datei (cleanup.bat) kann jetzt auch geloescht werden.
pause
