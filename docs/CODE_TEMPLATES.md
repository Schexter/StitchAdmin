# Code-Templates: StitchAdmin 2.0

**Erstellt von Hans Hahn - Alle Rechte vorbehalten**  
**Für:** Konsistente Code-Entwicklung

---

## 📋 Inhaltsverzeichnis

1. [Model-Template](#model-template)
2. [Controller-Template (Blueprint)](#controller-template-blueprint)
3. [Form-Template](#form-template)
4. [Template (Jinja2 HTML)](#template-jinja2-html)
5. [Service-Template](#service-template)
6. [Test-Template](#test-template)

---

## 🗄️ Model-Template

**Datei:** `src/models/neue_klasse.py`

```python
"""
Model: [Klassenname]
Beschreibung: [Was macht diese Klasse?]

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from src.models.models import db


class NeueKlasse(db.Model):
    """
    [Beschreibung der Klasse]
    
    Relationships:
        - [relationship_name]: [Ziel-Klasse]
    
    Example:
        >>> obj = NeueKlasse(name='Test', active=True)
        >>> db.session.add(obj)
        >>> db.session.commit()
    """
    
    __tablename__ = 'neue_klassen'
    
    # ===== PRIMARY KEY =====
    id = Column(String(50), primary_key=True)
    
    # ===== HAUPTFELDER =====
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    
    # ===== FOREIGN KEYS =====
    # parent_id = Column(String(50), ForeignKey('parents.id'), nullable=True)
    
    # ===== METADATEN =====
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    created_by = Column(String(80), nullable=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    updated_by = Column(String(80), nullable=True)
    
    # ===== RELATIONSHIPS =====
    # parent = relationship('Parent', backref='children')
    
    # ===== PROPERTIES =====
    @property
    def display_name(self) -> str:
        """Gibt benutzerfreundlichen Namen zurück"""
        return self.name or 'Unbekannt'
    
    # ===== METHODEN =====
    def to_dict(self) -> dict:
        """
        Konvertiert Model zu Dictionary
        
        Returns:
            dict: Model-Daten als Dictionary
        """
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'active': self.active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def get(self, key: str, default=None):
        """Dictionary-kompatible Getter-Methode"""
        return getattr(self, key, default)
    
    def __repr__(self) -> str:
        """String-Repräsentation"""
        return f'<NeueKlasse {self.name}>'
```

---

## 🎮 Controller-Template (Blueprint)

**Datei:** `src/controllers/neue_controller.py`

```python
"""
Controller: [Controller-Name]
Beschreibung: [Was verwaltet dieser Controller?]

Routes:
    GET    /neue/              - Liste
    GET    /neue/new           - Formular (Neu)
    POST   /neue/create        - Erstellen
    GET    /neue/<id>          - Details
    GET    /neue/<id>/edit     - Formular (Bearbeiten)
    POST   /neue/<id>/update   - Aktualisieren
    POST   /neue/<id>/delete   - Löschen

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from datetime import datetime

from src.models.models import db, NeueKlasse
from src.utils.id_generator import generate_id


# ===== BLUEPRINT =====
neue_bp = Blueprint('neue', __name__, url_prefix='/neue')


# ===== HELPER FUNCTIONS =====
def get_or_404(id: str) -> NeueKlasse:
    """
    Holt Objekt aus DB oder wirft 404
    
    Args:
        id: ID des Objekts
    
    Returns:
        NeueKlasse: Gefundenes Objekt
    
    Raises:
        404: Objekt nicht gefunden
    """
    obj = NeueKlasse.query.get(id)
    if not obj:
        flash('Objekt nicht gefunden', 'error')
        return redirect(url_for('neue.index'))
    return obj


# ===== ROUTES =====

@neue_bp.route('/')
@login_required
def index():
    """
    Liste aller Objekte
    
    Query Parameters:
        - search: Suchbegriff
        - active: Filter aktiv/inaktiv
        - page: Seitennummer (Pagination)
    
    Returns:
        Template: neue/index.html
    """
    # Basis-Query
    query = NeueKlasse.query
    
    # ===== FILTER: Suche =====
    search_term = request.args.get('search', '').strip()
    if search_term:
        query = query.filter(
            NeueKlasse.name.ilike(f'%{search_term}%')
        )
    
    # ===== FILTER: Aktiv/Inaktiv =====
    active_filter = request.args.get('active', 'all')
    if active_filter == 'active':
        query = query.filter(NeueKlasse.active == True)
    elif active_filter == 'inactive':
        query = query.filter(NeueKlasse.active == False)
    
    # ===== SORTIERUNG =====
    sort_by = request.args.get('sort_by', 'created_at')
    sort_order = request.args.get('sort_order', 'desc')
    
    if sort_order == 'asc':
        query = query.order_by(getattr(NeueKlasse, sort_by).asc())
    else:
        query = query.order_by(getattr(NeueKlasse, sort_by).desc())
    
    # ===== PAGINATION =====
    page = request.args.get('page', 1, type=int)
    per_page = 20
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    # ===== RENDER =====
    return render_template(
        'neue/index.html',
        objekte=pagination.items,
        pagination=pagination,
        search_term=search_term,
        active_filter=active_filter
    )


@neue_bp.route('/new')
@login_required
def new():
    """
    Formular für neues Objekt
    
    Returns:
        Template: neue/new.html
    """
    return render_template('neue/new.html')


@neue_bp.route('/create', methods=['POST'])
@login_required
def create():
    """
    Erstellt neues Objekt
    
    Form Data:
        - name: Name (required)
        - description: Beschreibung (optional)
        - active: Aktiv? (boolean)
    
    Returns:
        Redirect: neue.show oder neue.index
    """
    try:
        # ===== DATEN VALIDIEREN =====
        name = request.form.get('name', '').strip()
        if not name:
            flash('Name ist erforderlich', 'error')
            return redirect(url_for('neue.new'))
        
        # ===== ID GENERIEREN =====
        new_id = generate_id('NEU')
        
        # ===== OBJEKT ERSTELLEN =====
        obj = NeueKlasse(
            id=new_id,
            name=name,
            description=request.form.get('description', '').strip() or None,
            active=request.form.get('active') == 'on',
            created_by=current_user.username
        )
        
        # ===== SPEICHERN =====
        db.session.add(obj)
        db.session.commit()
        
        flash(f'{obj.name} erfolgreich erstellt', 'success')
        return redirect(url_for('neue.show', id=obj.id))
        
    except IntegrityError as e:
        db.session.rollback()
        flash(f'Datenbankfehler: {str(e)}', 'error')
        return redirect(url_for('neue.new'))
    
    except Exception as e:
        db.session.rollback()
        flash(f'Unerwarteter Fehler: {str(e)}', 'error')
        return redirect(url_for('neue.new'))


@neue_bp.route('/<string:id>')
@login_required
def show(id):
    """
    Zeigt Details eines Objekts
    
    Args:
        id: Objekt-ID
    
    Returns:
        Template: neue/show.html
    """
    obj = get_or_404(id)
    return render_template('neue/show.html', obj=obj)


@neue_bp.route('/<string:id>/edit')
@login_required
def edit(id):
    """
    Formular zum Bearbeiten
    
    Args:
        id: Objekt-ID
    
    Returns:
        Template: neue/edit.html
    """
    obj = get_or_404(id)
    return render_template('neue/edit.html', obj=obj)


@neue_bp.route('/<string:id>/update', methods=['POST'])
@login_required
def update(id):
    """
    Aktualisiert Objekt
    
    Args:
        id: Objekt-ID
    
    Form Data:
        - name: Name
        - description: Beschreibung
        - active: Aktiv?
    
    Returns:
        Redirect: neue.show
    """
    obj = get_or_404(id)
    
    try:
        # ===== DATEN VALIDIEREN =====
        name = request.form.get('name', '').strip()
        if not name:
            flash('Name ist erforderlich', 'error')
            return redirect(url_for('neue.edit', id=id))
        
        # ===== UPDATE =====
        obj.name = name
        obj.description = request.form.get('description', '').strip() or None
        obj.active = request.form.get('active') == 'on'
        obj.updated_by = current_user.username
        obj.updated_at = datetime.now()
        
        # ===== SPEICHERN =====
        db.session.commit()
        
        flash(f'{obj.name} erfolgreich aktualisiert', 'success')
        return redirect(url_for('neue.show', id=obj.id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Aktualisieren: {str(e)}', 'error')
        return redirect(url_for('neue.edit', id=id))


@neue_bp.route('/<string:id>/delete', methods=['POST'])
@login_required
def delete(id):
    """
    Löscht Objekt
    
    Args:
        id: Objekt-ID
    
    Returns:
        Redirect: neue.index
    """
    obj = get_or_404(id)
    
    try:
        name = obj.name
        db.session.delete(obj)
        db.session.commit()
        
        flash(f'{name} erfolgreich gelöscht', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Löschen: {str(e)}', 'error')
    
    return redirect(url_for('neue.index'))


# ===== API ROUTES (optional) =====

@neue_bp.route('/api/search')
@login_required
def api_search():
    """
    API: Suche nach Objekten
    
    Query Parameters:
        - q: Suchbegriff
        - limit: Max. Anzahl Ergebnisse (default: 10)
    
    Returns:
        JSON: Liste von Objekten
    """
    search_term = request.args.get('q', '').strip()
    limit = request.args.get('limit', 10, type=int)
    
    if not search_term:
        return jsonify([])
    
    results = NeueKlasse.query.filter(
        NeueKlasse.name.ilike(f'%{search_term}%')
    ).limit(limit).all()
    
    return jsonify([
        {
            'id': obj.id,
            'name': obj.name,
            'active': obj.active
        }
        for obj in results
    ])
```

---

## 📝 Form-Template

**Datei:** `src/forms/neue_forms.py`

```python
"""
Forms: [Form-Name]
Beschreibung: [Was macht dieses Formular?]

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, SelectField, IntegerField, FloatField
from wtforms.validators import DataRequired, Email, Optional, Length, NumberRange


class NeueForm(FlaskForm):
    """
    Formular für [Zweck]
    
    Fields:
        - name: Name (required, max 200 Zeichen)
        - description: Beschreibung (optional)
        - active: Aktiv? (boolean)
    
    Example:
        >>> form = NeueForm()
        >>> if form.validate_on_submit():
        ...     name = form.name.data
        ...     # Verarbeitung...
    """
    
    # ===== TEXT-FELDER =====
    name = StringField(
        'Name',
        validators=[
            DataRequired(message='Name ist erforderlich'),
            Length(max=200, message='Maximal 200 Zeichen')
        ],
        render_kw={'placeholder': 'Name eingeben...'}
    )
    
    description = TextAreaField(
        'Beschreibung',
        validators=[Optional()],
        render_kw={'rows': 4, 'placeholder': 'Optional: Beschreibung...'}
    )
    
    # ===== BOOLEAN-FELD =====
    active = BooleanField(
        'Aktiv',
        default=True
    )
    
    # ===== SELECT-FELD =====
    category = SelectField(
        'Kategorie',
        choices=[
            ('', '-- Bitte wählen --'),
            ('cat1', 'Kategorie 1'),
            ('cat2', 'Kategorie 2'),
            ('cat3', 'Kategorie 3')
        ],
        validators=[Optional()]
    )
    
    # ===== ZAHLEN-FELDER =====
    quantity = IntegerField(
        'Menge',
        validators=[
            Optional(),
            NumberRange(min=0, message='Muss positiv sein')
        ],
        default=0
    )
    
    price = FloatField(
        'Preis',
        validators=[
            Optional(),
            NumberRange(min=0.0, message='Muss positiv sein')
        ],
        render_kw={'step': '0.01', 'placeholder': '0.00'}
    )
```

---

## 🎨 Template (Jinja2 HTML)

### Index-Template

**Datei:** `templates/neue/index.html`

```html
{% extends "base.html" %}

{% block title %}[Plural-Name] - StitchAdmin{% endblock %}

{% block content %}
<div class="container-fluid py-4">
    
    <!-- ===== HEADER ===== -->
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h1 class="h3 mb-0">[Plural-Name]</h1>
        <a href="{{ url_for('neue.new') }}" class="btn btn-primary">
            <i class="fas fa-plus me-2"></i>Neu anlegen
        </a>
    </div>
    
    <!-- ===== SUCHE & FILTER ===== -->
    <div class="card mb-4">
        <div class="card-body">
            <form method="GET" action="{{ url_for('neue.index') }}" class="row g-3">
                
                <!-- Suchfeld -->
                <div class="col-md-4">
                    <input type="text" 
                           name="search" 
                           class="form-control" 
                           placeholder="Suchen..." 
                           value="{{ search_term }}">
                </div>
                
                <!-- Filter: Aktiv/Inaktiv -->
                <div class="col-md-3">
                    <select name="active" class="form-select">
                        <option value="all" {% if active_filter == 'all' %}selected{% endif %}>
                            Alle
                        </option>
                        <option value="active" {% if active_filter == 'active' %}selected{% endif %}>
                            Nur Aktive
                        </option>
                        <option value="inactive" {% if active_filter == 'inactive' %}selected{% endif %}>
                            Nur Inaktive
                        </option>
                    </select>
                </div>
                
                <!-- Buttons -->
                <div class="col-md-5">
                    <button type="submit" class="btn btn-primary">
                        <i class="fas fa-search me-2"></i>Suchen
                    </button>
                    <a href="{{ url_for('neue.index') }}" class="btn btn-secondary">
                        <i class="fas fa-times me-2"></i>Zurücksetzen
                    </a>
                </div>
                
            </form>
        </div>
    </div>
    
    <!-- ===== TABELLE ===== -->
    <div class="card">
        <div class="card-body">
            
            {% if objekte %}
            <div class="table-responsive">
                <table class="table table-hover">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Beschreibung</th>
                            <th>Status</th>
                            <th>Erstellt</th>
                            <th>Aktionen</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for obj in objekte %}
                        <tr>
                            <td>
                                <a href="{{ url_for('neue.show', id=obj.id) }}" class="text-decoration-none">
                                    <strong>{{ obj.name }}</strong>
                                </a>
                            </td>
                            <td>{{ obj.description|truncate(50) or '-' }}</td>
                            <td>
                                {% if obj.active %}
                                <span class="badge bg-success">Aktiv</span>
                                {% else %}
                                <span class="badge bg-secondary">Inaktiv</span>
                                {% endif %}
                            </td>
                            <td>
                                <small class="text-muted">
                                    {{ obj.created_at.strftime('%d.%m.%Y') }}
                                </small>
                            </td>
                            <td>
                                <!-- Buttons -->
                                <a href="{{ url_for('neue.show', id=obj.id) }}" 
                                   class="btn btn-sm btn-info" 
                                   title="Anzeigen">
                                    <i class="fas fa-eye"></i>
                                </a>
                                <a href="{{ url_for('neue.edit', id=obj.id) }}" 
                                   class="btn btn-sm btn-warning" 
                                   title="Bearbeiten">
                                    <i class="fas fa-edit"></i>
                                </a>
                                <button type="button" 
                                        class="btn btn-sm btn-danger" 
                                        onclick="confirmDelete('{{ obj.id }}', '{{ obj.name }}')"
                                        title="Löschen">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            
            <!-- ===== PAGINATION ===== -->
            {% if pagination.pages > 1 %}
            <nav aria-label="Seitennummerierung">
                <ul class="pagination justify-content-center">
                    
                    <!-- Vorherige Seite -->
                    <li class="page-item {% if not pagination.has_prev %}disabled{% endif %}">
                        <a class="page-link" 
                           href="{{ url_for('neue.index', page=pagination.prev_num, search=search_term, active=active_filter) }}">
                            Zurück
                        </a>
                    </li>
                    
                    <!-- Seitenzahlen -->
                    {% for page_num in pagination.iter_pages(left_edge=1, right_edge=1, left_current=1, right_current=2) %}
                        {% if page_num %}
                        <li class="page-item {% if page_num == pagination.page %}active{% endif %}">
                            <a class="page-link" 
                               href="{{ url_for('neue.index', page=page_num, search=search_term, active=active_filter) }}">
                                {{ page_num }}
                            </a>
                        </li>
                        {% else %}
                        <li class="page-item disabled">
                            <span class="page-link">...</span>
                        </li>
                        {% endif %}
                    {% endfor %}
                    
                    <!-- Nächste Seite -->
                    <li class="page-item {% if not pagination.has_next %}disabled{% endif %}">
                        <a class="page-link" 
                           href="{{ url_for('neue.index', page=pagination.next_num, search=search_term, active=active_filter) }}">
                            Weiter
                        </a>
                    </li>
                    
                </ul>
            </nav>
            {% endif %}
            
            {% else %}
            <!-- Keine Ergebnisse -->
            <div class="alert alert-info">
                <i class="fas fa-info-circle me-2"></i>
                {% if search_term %}
                Keine Ergebnisse für "{{ search_term }}" gefunden.
                {% else %}
                Noch keine Einträge vorhanden.
                {% endif %}
            </div>
            {% endif %}
            
        </div>
    </div>
    
</div>

<!-- ===== JAVASCRIPT ===== -->
<script>
function confirmDelete(id, name) {
    if (confirm(`Wirklich "${name}" löschen?`)) {
        // Erstelle verstecktes Formular
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = `/neue/${id}/delete`;
        document.body.appendChild(form);
        form.submit();
    }
}
</script>

{% endblock %}
```

---

### Show-Template

**Datei:** `templates/neue/show.html`

```html
{% extends "base.html" %}

{% block title %}{{ obj.name }} - StitchAdmin{% endblock %}

{% block content %}
<div class="container-fluid py-4">
    
    <!-- ===== HEADER ===== -->
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h1 class="h3 mb-0">{{ obj.name }}</h1>
        <div>
            <a href="{{ url_for('neue.edit', id=obj.id) }}" class="btn btn-warning">
                <i class="fas fa-edit me-2"></i>Bearbeiten
            </a>
            <a href="{{ url_for('neue.index') }}" class="btn btn-secondary">
                <i class="fas fa-arrow-left me-2"></i>Zurück
            </a>
        </div>
    </div>
    
    <!-- ===== DETAILS-CARD ===== -->
    <div class="card">
        <div class="card-body">
            
            <div class="row">
                
                <!-- Linke Spalte -->
                <div class="col-md-6">
                    <dl class="row">
                        <dt class="col-sm-4">Name:</dt>
                        <dd class="col-sm-8">{{ obj.name }}</dd>
                        
                        <dt class="col-sm-4">Status:</dt>
                        <dd class="col-sm-8">
                            {% if obj.active %}
                            <span class="badge bg-success">Aktiv</span>
                            {% else %}
                            <span class="badge bg-secondary">Inaktiv</span>
                            {% endif %}
                        </dd>
                        
                        <dt class="col-sm-4">Beschreibung:</dt>
                        <dd class="col-sm-8">{{ obj.description or '-' }}</dd>
                    </dl>
                </div>
                
                <!-- Rechte Spalte -->
                <div class="col-md-6">
                    <dl class="row">
                        <dt class="col-sm-4">Erstellt:</dt>
                        <dd class="col-sm-8">
                            {{ obj.created_at.strftime('%d.%m.%Y %H:%M') }} Uhr<br>
                            <small class="text-muted">von {{ obj.created_by or 'System' }}</small>
                        </dd>
                        
                        <dt class="col-sm-4">Aktualisiert:</dt>
                        <dd class="col-sm-8">
                            {{ obj.updated_at.strftime('%d.%m.%Y %H:%M') }} Uhr<br>
                            <small class="text-muted">von {{ obj.updated_by or 'System' }}</small>
                        </dd>
                    </dl>
                </div>
                
            </div>
            
        </div>
    </div>
    
</div>
{% endblock %}
```

---

## 🔧 Service-Template

**Datei:** `src/services/neue_service.py`

```python
"""
Service: [Service-Name]
Beschreibung: [Was macht dieser Service?]

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from src.models.models import db, NeueKlasse


class NeuerService:
    """
    Business-Logic für [Zweck]
    
    Methods:
        - get_all(): Holt alle Objekte
        - get_by_id(id): Holt Objekt nach ID
        - create(data): Erstellt neues Objekt
        - update(id, data): Aktualisiert Objekt
        - delete(id): Löscht Objekt
        - search(query): Sucht Objekte
    
    Example:
        >>> service = NeuerService()
        >>> objekt = service.get_by_id('NEU-20251110-0001')
        >>> if objekt:
        ...     print(objekt.name)
    """
    
    @staticmethod
    def get_all(active_only: bool = False) -> List[NeueKlasse]:
        """
        Holt alle Objekte aus der Datenbank
        
        Args:
            active_only: Nur aktive Objekte? (default: False)
        
        Returns:
            List[NeueKlasse]: Liste von Objekten
        """
        query = NeueKlasse.query
        
        if active_only:
            query = query.filter(NeueKlasse.active == True)
        
        return query.order_by(NeueKlasse.created_at.desc()).all()
    
    @staticmethod
    def get_by_id(id: str) -> Optional[NeueKlasse]:
        """
        Holt Objekt nach ID
        
        Args:
            id: Objekt-ID
        
        Returns:
            NeueKlasse oder None: Objekt wenn gefunden, sonst None
        """
        return NeueKlasse.query.get(id)
    
    @staticmethod
    def create(data: Dict[str, Any], user: str = 'system') -> NeueKlasse:
        """
        Erstellt neues Objekt
        
        Args:
            data: Dictionary mit Objekt-Daten
            user: Username des Erstellers
        
        Returns:
            NeueKlasse: Erstelltes Objekt
        
        Raises:
            ValueError: Wenn erforderliche Felder fehlen
        """
        # Validierung
        if not data.get('name'):
            raise ValueError('Name ist erforderlich')
        
        # ID generieren
        from src.utils.id_generator import generate_id
        new_id = generate_id('NEU')
        
        # Objekt erstellen
        obj = NeueKlasse(
            id=new_id,
            name=data['name'],
            description=data.get('description'),
            active=data.get('active', True),
            created_by=user
        )
        
        # Speichern
        db.session.add(obj)
        db.session.commit()
        
        return obj
    
    @staticmethod
    def update(id: str, data: Dict[str, Any], user: str = 'system') -> Optional[NeueKlasse]:
        """
        Aktualisiert Objekt
        
        Args:
            id: Objekt-ID
            data: Dictionary mit zu aktualisierenden Daten
            user: Username des Bearbeiters
        
        Returns:
            NeueKlasse oder None: Aktualisiertes Objekt wenn gefunden, sonst None
        
        Raises:
            ValueError: Wenn Validierung fehlschlägt
        """
        obj = NeueKlasse.query.get(id)
        if not obj:
            return None
        
        # Validierung
        if 'name' in data and not data['name']:
            raise ValueError('Name darf nicht leer sein')
        
        # Update
        if 'name' in data:
            obj.name = data['name']
        if 'description' in data:
            obj.description = data['description']
        if 'active' in data:
            obj.active = data['active']
        
        obj.updated_by = user
        obj.updated_at = datetime.now()
        
        # Speichern
        db.session.commit()
        
        return obj
    
    @staticmethod
    def delete(id: str) -> bool:
        """
        Löscht Objekt
        
        Args:
            id: Objekt-ID
        
        Returns:
            bool: True wenn gelöscht, False wenn nicht gefunden
        """
        obj = NeueKlasse.query.get(id)
        if not obj:
            return False
        
        db.session.delete(obj)
        db.session.commit()
        
        return True
    
    @staticmethod
    def search(query: str, limit: int = 20) -> List[NeueKlasse]:
        """
        Sucht Objekte nach Name
        
        Args:
            query: Suchbegriff
            limit: Maximale Anzahl Ergebnisse (default: 20)
        
        Returns:
            List[NeueKlasse]: Liste gefundener Objekte
        """
        return NeueKlasse.query.filter(
            NeueKlasse.name.ilike(f'%{query}%')
        ).limit(limit).all()
```

---

## 🧪 Test-Template

**Datei:** `tests/unit/test_neue_model.py`

```python
"""
Unit-Tests für NeueKlasse Model

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import pytest
from datetime import datetime

from src.models.models import db, NeueKlasse


class TestNeueKlasseModel:
    """Tests für NeueKlasse Model"""
    
    def test_create_objekt(self, session):
        """Test: Objekt erstellen"""
        obj = NeueKlasse(
            id='NEU-20251110-0001',
            name='Test-Objekt',
            description='Test-Beschreibung',
            active=True,
            created_by='testuser'
        )
        
        session.add(obj)
        session.commit()
        
        # Assertions
        assert obj.id == 'NEU-20251110-0001'
        assert obj.name == 'Test-Objekt'
        assert obj.description == 'Test-Beschreibung'
        assert obj.active is True
        assert obj.created_by == 'testuser'
        assert obj.created_at is not None
        assert obj.updated_at is not None
    
    def test_display_name(self, session):
        """Test: display_name Property"""
        obj = NeueKlasse(
            id='NEU-TEST-001',
            name='Test'
        )
        
        assert obj.display_name == 'Test'
        
        # Ohne Namen
        obj.name = None
        assert obj.display_name == 'Unbekannt'
    
    def test_to_dict(self, session):
        """Test: to_dict() Methode"""
        obj = NeueKlasse(
            id='NEU-TEST-002',
            name='Dict-Test',
            active=False
        )
        
        result = obj.to_dict()
        
        assert result['id'] == 'NEU-TEST-002'
        assert result['name'] == 'Dict-Test'
        assert result['active'] is False
        assert 'created_at' in result
        assert 'updated_at' in result
    
    def test_get_method(self, session):
        """Test: get() Methode (dict-kompatibel)"""
        obj = NeueKlasse(
            id='NEU-TEST-003',
            name='Get-Test'
        )
        
        assert obj.get('name') == 'Get-Test'
        assert obj.get('id') == 'NEU-TEST-003'
        assert obj.get('nonexistent', 'default') == 'default'
    
    def test_repr(self, session):
        """Test: __repr__() String-Repräsentation"""
        obj = NeueKlasse(
            id='NEU-TEST-004',
            name='Repr-Test'
        )
        
        assert repr(obj) == '<NeueKlasse Repr-Test>'


# Pytest ausführen
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
```

---

**Erstellt von Hans Hahn - Alle Rechte vorbehalten**  
**Nutze diese Templates für konsistenten, wartbaren Code!** 💪
