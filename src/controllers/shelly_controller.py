"""
Shelly Smart Device Controller
Verwaltung und Steuerung von Shelly-Geräten
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from src.models.models import db, ShellyDevice, ShellyEnergyReading, Machine, ShellyProductionEnergy
from src.utils.shelly_integration import ShellyDevice as ShellyAPI, ShellyScanner, ShellyEnergyTracker
from src.utils.activity_logger import log_activity
from datetime import datetime, timedelta
from sqlalchemy import func
import logging

logger = logging.getLogger(__name__)

shelly_bp = Blueprint('shelly', __name__, url_prefix='/shelly')


# ==========================================
# HAUPT-UI ROUTEN
# ==========================================

@shelly_bp.route('/')
@login_required
def index():
    """Shelly-Geräte Übersicht"""
    devices = ShellyDevice.query.all()

    # Hole Live-Status für alle Geräte
    for device in devices:
        try:
            shelly_api = ShellyAPI(device.ip_address)
            power_data = shelly_api.get_power_data(device.channel)

            if power_data:
                device.is_online = True
                device.is_on = power_data.get('is_on', False)
                device.last_power_w = power_data.get('power', 0)
                device.last_seen = datetime.now()
            else:
                device.is_online = False

        except Exception as e:
            logger.error(f"Fehler beim Abrufen des Status von {device.name}: {e}")
            device.is_online = False

    db.session.commit()

    # Statistiken
    total_devices = len(devices)
    online_devices = sum(1 for d in devices if d.is_online)
    assigned_devices = sum(1 for d in devices if d.machine_id)
    total_power = sum(d.last_power_w or 0 for d in devices if d.is_online)

    return render_template('shelly/index.html',
                         devices=devices,
                         stats={
                             'total': total_devices,
                             'online': online_devices,
                             'assigned': assigned_devices,
                             'total_power': total_power
                         })


@shelly_bp.route('/scan')
@login_required
def scan_page():
    """Netzwerk-Scan Seite"""
    return render_template('shelly/scan.html')


@shelly_bp.route('/device/<int:device_id>')
@login_required
def device_detail(device_id):
    """Geräte-Details und Energie-Historie"""
    device = ShellyDevice.query.get_or_404(device_id)

    # Hole aktuelle Live-Daten
    shelly_api = ShellyAPI(device.ip_address)
    live_data = shelly_api.get_power_data(device.channel)
    device_info = shelly_api.get_device_info()

    # Energie-Historie (letzte 24h)
    since = datetime.now() - timedelta(hours=24)
    energy_history = ShellyEnergyReading.query.filter(
        ShellyEnergyReading.device_id == device_id,
        ShellyEnergyReading.timestamp >= since
    ).order_by(ShellyEnergyReading.timestamp).all()

    # Produktions-Energie-Daten
    production_energy = ShellyProductionEnergy.query.filter_by(
        shelly_device_id=device_id
    ).order_by(ShellyProductionEnergy.start_time.desc()).limit(10).all()

    return render_template('shelly/device_detail.html',
                         device=device,
                         live_data=live_data,
                         device_info=device_info,
                         energy_history=energy_history,
                         production_energy=production_energy)


# ==========================================
# API ENDPOINTS
# ==========================================

@shelly_bp.route('/api/scan', methods=['POST'])
@login_required
def api_scan_network():
    """Scannt Netzwerk nach Shelly-Geräten"""
    data = request.get_json() or {}
    network_prefix = data.get('network_prefix', '192.168.1')

    try:
        logger.info(f"Starte Netzwerk-Scan für {network_prefix}.0/24")

        # Führe Scan durch
        scanner = ShellyScanner()
        found_devices = scanner.scan_network(network_prefix)

        # Bereite Ergebnis auf
        results = []
        for shelly_api in found_devices:
            device_info = shelly_api.get_device_info()
            power_data = shelly_api.get_power_data()

            # Prüfe ob schon in DB
            existing = ShellyDevice.query.filter_by(ip_address=shelly_api.ip).first()

            results.append({
                'ip': shelly_api.ip,
                'type': device_info.get('type', 'Unknown'),
                'mac': device_info.get('mac', ''),
                'fw': device_info.get('fw', ''),
                'name': device_info.get('name', ''),
                'power': power_data.get('power', 0),
                'is_on': power_data.get('is_on', False),
                'exists': existing is not None,
                'device_id': existing.id if existing else None
            })

        log_activity(current_user.username, 'shelly_scan', f'{len(results)} Shelly-Geräte gefunden')

        return jsonify({
            'success': True,
            'devices': results,
            'count': len(results)
        })

    except Exception as e:
        logger.error(f"Fehler beim Netzwerk-Scan: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@shelly_bp.route('/api/device/add', methods=['POST'])
@login_required
def api_add_device():
    """Fügt Shelly-Gerät zur Datenbank hinzu"""
    data = request.get_json()

    try:
        ip_address = data.get('ip_address')

        if not ip_address:
            return jsonify({'success': False, 'error': 'IP-Adresse erforderlich'}), 400

        # Hole Geräte-Info
        shelly_api = ShellyAPI(ip_address)
        device_info = shelly_api.get_device_info()

        if not device_info:
            return jsonify({'success': False, 'error': 'Gerät nicht erreichbar'}), 400

        # Prüfe Duplikate
        existing = ShellyDevice.query.filter_by(ip_address=ip_address).first()
        if existing:
            return jsonify({'success': False, 'error': 'Gerät bereits hinzugefügt'}), 400

        # Erstelle Gerät
        device = ShellyDevice(
            name=data.get('name', device_info.get('name', f"Shelly {device_info.get('type', 'Device')}")),
            ip_address=ip_address,
            device_type=device_info.get('type'),
            mac_address=device_info.get('mac'),
            firmware_version=device_info.get('fw'),
            created_by=current_user.username,
            is_online=True,
            last_seen=datetime.now()
        )

        db.session.add(device)
        db.session.commit()

        log_activity(current_user.username, 'shelly_added', f'Shelly-Gerät hinzugefügt: {device.name} ({ip_address})')

        return jsonify({
            'success': True,
            'device_id': device.id,
            'message': 'Gerät erfolgreich hinzugefügt'
        })

    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen des Geräts: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@shelly_bp.route('/api/device/<int:device_id>/control', methods=['POST'])
@login_required
def api_control_device(device_id):
    """Schaltet Shelly-Gerät ein/aus"""
    device = ShellyDevice.query.get_or_404(device_id)
    data = request.get_json()

    action = data.get('action')  # 'on', 'off', 'toggle'

    try:
        shelly_api = ShellyAPI(device.ip_address)

        if action == 'on':
            success = shelly_api.turn_on(device.channel)
        elif action == 'off':
            success = shelly_api.turn_off(device.channel)
        elif action == 'toggle':
            success = shelly_api.toggle(device.channel)
        else:
            return jsonify({'success': False, 'error': 'Ungültige Aktion'}), 400

        if success:
            # Aktualisiere Status
            power_data = shelly_api.get_power_data(device.channel)
            device.is_on = power_data.get('is_on', False)
            device.last_power_w = power_data.get('power', 0)
            device.last_seen = datetime.now()
            db.session.commit()

            log_activity(current_user.username, 'shelly_control', f'{device.name}: {action}')

            return jsonify({
                'success': True,
                'is_on': device.is_on,
                'power': device.last_power_w
            })
        else:
            return jsonify({'success': False, 'error': 'Steuerung fehlgeschlagen'}), 500

    except Exception as e:
        logger.error(f"Fehler bei der Steuerung von {device.name}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@shelly_bp.route('/api/device/<int:device_id>/assign', methods=['POST'])
@login_required
def api_assign_device(device_id):
    """Ordnet Shelly-Gerät einer Maschine zu"""
    device = ShellyDevice.query.get_or_404(device_id)
    data = request.get_json()

    machine_id = data.get('machine_id')
    assigned_to_type = data.get('assigned_to_type', 'machine')

    try:
        if machine_id:
            machine = Machine.query.get(machine_id)
            if not machine:
                return jsonify({'success': False, 'error': 'Maschine nicht gefunden'}), 404

        device.machine_id = machine_id
        device.assigned_to_type = assigned_to_type
        device.updated_by = current_user.username

        db.session.commit()

        log_activity(current_user.username, 'shelly_assigned',
                    f'{device.name} zugeordnet zu {machine.name if machine_id else "nichts"}')

        return jsonify({
            'success': True,
            'message': 'Zuordnung erfolgreich'
        })

    except Exception as e:
        logger.error(f"Fehler bei der Zuordnung: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@shelly_bp.route('/api/device/<int:device_id>/status')
@login_required
def api_device_status(device_id):
    """Holt aktuellen Status eines Geräts"""
    device = ShellyDevice.query.get_or_404(device_id)

    try:
        shelly_api = ShellyAPI(device.ip_address)
        power_data = shelly_api.get_power_data(device.channel)

        if power_data:
            # Aktualisiere DB
            device.is_online = True
            device.is_on = power_data.get('is_on', False)
            device.last_power_w = power_data.get('power', 0)
            device.last_seen = datetime.now()
            db.session.commit()

            return jsonify({
                'success': True,
                'is_online': True,
                'is_on': power_data.get('is_on', False),
                'power': power_data.get('power', 0),
                'voltage': power_data.get('voltage', 0),
                'current': power_data.get('current', 0),
                'energy': power_data.get('energy', 0),
                'temperature': power_data.get('temperature', 0)
            })
        else:
            device.is_online = False
            db.session.commit()

            return jsonify({
                'success': True,
                'is_online': False
            })

    except Exception as e:
        logger.error(f"Fehler beim Statusabruf: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@shelly_bp.route('/api/device/<int:device_id>/delete', methods=['POST'])
@login_required
def api_delete_device(device_id):
    """Löscht Shelly-Gerät"""
    device = ShellyDevice.query.get_or_404(device_id)

    try:
        device_name = device.name

        db.session.delete(device)
        db.session.commit()

        log_activity(current_user.username, 'shelly_deleted', f'Shelly-Gerät gelöscht: {device_name}')

        return jsonify({
            'success': True,
            'message': 'Gerät gelöscht'
        })

    except Exception as e:
        logger.error(f"Fehler beim Löschen: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@shelly_bp.route('/api/energy/record', methods=['POST'])
@login_required
def api_record_energy():
    """Zeichnet Energie-Messwerte auf (für Cronjob/Scheduler)"""
    try:
        devices = ShellyDevice.query.filter_by(active=True, track_energy=True).all()
        recorded = 0

        for device in devices:
            try:
                shelly_api = ShellyAPI(device.ip_address)
                power_data = shelly_api.get_power_data(device.channel)

                if power_data:
                    reading = ShellyEnergyReading(
                        device_id=device.id,
                        power_w=power_data.get('power'),
                        voltage_v=power_data.get('voltage'),
                        current_a=power_data.get('current'),
                        power_factor=power_data.get('pf'),
                        energy_wh=power_data.get('energy'),
                        is_on=power_data.get('is_on'),
                        temperature_c=power_data.get('temperature')
                    )

                    db.session.add(reading)
                    recorded += 1

            except Exception as e:
                logger.error(f"Fehler beim Aufzeichnen für {device.name}: {e}")

        db.session.commit()

        return jsonify({
            'success': True,
            'recorded': recorded
        })

    except Exception as e:
        logger.error(f"Fehler beim Aufzeichnen der Energie: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@shelly_bp.route('/api/dashboard')
@login_required
def api_dashboard_data():
    """Liefert Dashboard-Daten für Live-Monitoring"""
    try:
        devices = ShellyDevice.query.filter_by(active=True).all()

        dashboard_data = []
        for device in devices:
            # Hole Live-Daten
            shelly_api = ShellyAPI(device.ip_address)
            power_data = shelly_api.get_power_data(device.channel)

            # Heutige Energie
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_readings = ShellyEnergyReading.query.filter(
                ShellyEnergyReading.device_id == device.id,
                ShellyEnergyReading.timestamp >= today_start
            ).all()

            if today_readings and len(today_readings) > 1:
                today_energy_wh = max(r.energy_wh or 0 for r in today_readings) - min(r.energy_wh or 0 for r in today_readings)
            else:
                today_energy_wh = 0

            dashboard_data.append({
                'id': device.id,
                'name': device.name,
                'machine': device.machine.name if device.machine else None,
                'is_online': power_data is not None,
                'is_on': power_data.get('is_on', False) if power_data else False,
                'power': power_data.get('power', 0) if power_data else 0,
                'today_kwh': round(today_energy_wh / 1000, 2),
                'today_cost': round((today_energy_wh / 1000) * device.electricity_price_per_kwh, 2)
            })

        return jsonify({
            'success': True,
            'devices': dashboard_data,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Fehler beim Dashboard-Datenabruf: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


def register_shelly_blueprint(app):
    """Registriert Shelly Blueprint"""
    app.register_blueprint(shelly_bp)
    print("[OK] Shelly-Geräte Blueprint registriert")
