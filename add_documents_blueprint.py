"""
Script zum Hinzufügen des Documents-Blueprints zur app.py
"""

def update_app_py():
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Finde die Zeile mit auth_controller
    old_line = "    register_blueprint_safe('src.controllers.auth_controller', 'auth_bp', 'Authentifizierung')"
    new_lines = """    register_blueprint_safe('src.controllers.auth_controller', 'auth_bp', 'Authentifizierung')
    
    # Dokumente & Post
    register_blueprint_safe('src.controllers.documents.documents_controller', 'documents_bp', 'Dokumente & Post')"""
    
    if old_line in content and "documents_controller" not in content:
        content = content.replace(old_line, new_lines)
        
        with open('app.py', 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("[OK] Documents-Blueprint erfolgreich hinzugefügt!")
        return True
    elif "documents_controller" in content:
        print("[INFO] Documents-Blueprint bereits vorhanden")
        return True
    else:
        print("[FEHLER] Konnte auth_controller Zeile nicht finden")
        return False

if __name__ == '__main__':
    update_app_py()
