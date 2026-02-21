# -*- coding: utf-8 -*-
"""
CSV Import Service
==================
Parse, Mapping, Validierung und Import von CSV-Dateien.
Unterstuetzt: Kunden, Artikel, Buchungen, Bank-Auszuege (CSV + MT940)

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import os
import csv
import hashlib
import logging
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from io import StringIO
from typing import Dict, List, Optional, Tuple

from src.models import db
from src.models.csv_import import CSVImportJob

logger = logging.getLogger(__name__)

# Bekannte Spalten-Zuordnungen pro Import-Typ
FIELD_MAPPINGS = {
    'customer': {
        'fields': {
            'customer_number': 'Kundennummer',
            'company_name': 'Firma',
            'first_name': 'Vorname',
            'last_name': 'Nachname',
            'email': 'E-Mail',
            'phone': 'Telefon',
            'street': 'Strasse',
            'postal_code': 'PLZ',
            'city': 'Ort',
            'country': 'Land',
            'vat_id': 'USt-IdNr',
        },
        'required': ['last_name'],
        'unique_key': 'customer_number',
    },
    'article': {
        'fields': {
            'article_number': 'Artikelnummer',
            'name': 'Bezeichnung',
            'description': 'Beschreibung',
            'price': 'Preis',
            'category': 'Kategorie',
            'brand': 'Marke',
            'material': 'Material',
            'color': 'Farbe',
        },
        'required': ['name'],
        'unique_key': 'article_number',
    },
    'booking': {
        'fields': {
            'buchungsdatum': 'Buchungsdatum',
            'belegnummer': 'Belegnummer',
            'buchungstext': 'Buchungstext',
            'betrag_netto': 'Betrag Netto',
            'betrag_brutto': 'Betrag Brutto',
            'mwst_satz': 'MwSt-Satz',
            'soll_konto': 'Soll-Konto',
            'haben_konto': 'Haben-Konto',
            'buchungs_art': 'Buchungsart',
        },
        'required': ['buchungstext', 'betrag_netto'],
        'unique_key': 'belegnummer',
    },
    'bank_statement': {
        'fields': {
            'datum': 'Buchungsdatum',
            'betrag': 'Betrag',
            'verwendungszweck': 'Verwendungszweck',
            'auftraggeber': 'Auftraggeber/Empfaenger',
            'iban': 'IBAN',
            'bic': 'BIC',
            'waehrung': 'Waehrung',
        },
        'required': ['datum', 'betrag'],
        'unique_key': None,
    },
}

# Synonyme fuer automatisches Mapping
HEADER_SYNONYMS = {
    'kundennummer': 'customer_number', 'kd-nr': 'customer_number', 'kdnr': 'customer_number',
    'firma': 'company_name', 'company': 'company_name', 'firmenname': 'company_name',
    'vorname': 'first_name', 'first name': 'first_name',
    'nachname': 'last_name', 'name': 'last_name', 'last name': 'last_name',
    'e-mail': 'email', 'mail': 'email', 'emailadresse': 'email',
    'telefon': 'phone', 'tel': 'phone', 'phone': 'phone', 'fon': 'phone',
    'strasse': 'street', 'straße': 'street', 'street': 'street', 'adresse': 'street',
    'plz': 'postal_code', 'postleitzahl': 'postal_code', 'zip': 'postal_code',
    'ort': 'city', 'stadt': 'city', 'city': 'city',
    'land': 'country', 'country': 'country',
    'ust-idnr': 'vat_id', 'ust-id': 'vat_id', 'steuernummer': 'vat_id',
    'artikelnummer': 'article_number', 'art-nr': 'article_number', 'artnr': 'article_number',
    'bezeichnung': 'name', 'produktname': 'name', 'artikel': 'name',
    'beschreibung': 'description', 'description': 'description',
    'preis': 'price', 'vk-preis': 'price', 'einzelpreis': 'price',
    'kategorie': 'category', 'category': 'category',
    'marke': 'brand', 'brand': 'brand', 'hersteller': 'brand',
    'material': 'material', 'stoff': 'material',
    'farbe': 'color', 'colour': 'color',
    'buchungsdatum': 'buchungsdatum', 'datum': 'datum', 'date': 'datum',
    'belegnummer': 'belegnummer', 'beleg': 'belegnummer', 'beleg-nr': 'belegnummer',
    'buchungstext': 'buchungstext', 'text': 'buchungstext',
    'betrag': 'betrag', 'amount': 'betrag', 'summe': 'betrag',
    'betrag netto': 'betrag_netto', 'netto': 'betrag_netto',
    'betrag brutto': 'betrag_brutto', 'brutto': 'betrag_brutto',
    'mwst': 'mwst_satz', 'mwst-satz': 'mwst_satz', 'steuer': 'mwst_satz',
    'verwendungszweck': 'verwendungszweck', 'zweck': 'verwendungszweck',
    'auftraggeber': 'auftraggeber', 'empfaenger': 'auftraggeber',
    'iban': 'iban', 'bic': 'bic',
}


class CSVImportService:
    """Service fuer CSV-Import"""

    def detect_csv_format(self, file_content: bytes) -> Dict:
        """
        Erkennt CSV-Format: Encoding, Delimiter, Headers

        Returns:
            Dict mit encoding, delimiter, headers, preview_rows
        """
        # Encoding erkennen
        encoding = 'utf-8'
        for enc in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1']:
            try:
                text = file_content.decode(enc)
                encoding = enc
                break
            except (UnicodeDecodeError, ValueError):
                continue

        text = file_content.decode(encoding)

        # Delimiter erkennen
        sniffer = csv.Sniffer()
        try:
            sample = text[:4096]
            dialect = sniffer.sniff(sample, delimiters=';,\t|')
            delimiter = dialect.delimiter
        except csv.Error:
            delimiter = ';'

        # Headers und Preview
        reader = csv.reader(StringIO(text), delimiter=delimiter)
        rows = []
        for i, row in enumerate(reader):
            if i >= 6:
                break
            rows.append(row)

        headers = rows[0] if rows else []
        preview = rows[1:6] if len(rows) > 1 else []

        return {
            'encoding': encoding,
            'delimiter': delimiter,
            'headers': headers,
            'preview_rows': preview,
            'total_rows': text.count('\n') - 1,
        }

    def suggest_column_mapping(self, headers: List[str], import_type: str) -> Dict[str, str]:
        """
        Schlaegt automatisches Spalten-Mapping vor.

        Returns:
            Dict {csv_header: db_field}
        """
        mapping = {}
        available_fields = FIELD_MAPPINGS.get(import_type, {}).get('fields', {})

        for header in headers:
            normalized = header.strip().lower().replace('_', ' ').replace('-', ' ')

            # Direkter Match
            if normalized in HEADER_SYNONYMS:
                field = HEADER_SYNONYMS[normalized]
                if field in available_fields:
                    mapping[header] = field
                    continue

            # Teilmatch
            for synonym, field in HEADER_SYNONYMS.items():
                if synonym in normalized or normalized in synonym:
                    if field in available_fields:
                        mapping[header] = field
                        break

        return mapping

    def create_import_job(self, file_content: bytes, filename: str,
                          import_type: str, user: str) -> CSVImportJob:
        """Erstellt einen neuen Import-Job und speichert die Datei"""
        format_info = self.detect_csv_format(file_content)

        # Datei speichern
        upload_dir = os.path.join('instance', 'uploads', 'csv_imports')
        os.makedirs(upload_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_name = f'{timestamp}_{filename}'
        file_path = os.path.join(upload_dir, safe_name)

        with open(file_path, 'wb') as f:
            f.write(file_content)

        # Mapping vorschlagen
        suggested = self.suggest_column_mapping(format_info['headers'], import_type)

        job = CSVImportJob(
            import_type=import_type,
            filename=filename,
            file_path=file_path,
            encoding=format_info['encoding'],
            delimiter=format_info['delimiter'],
            status='uploaded',
            detected_headers=format_info['headers'],
            column_mapping=suggested,
            total_rows=format_info['total_rows'],
            created_by=user,
        )
        db.session.add(job)
        db.session.commit()

        return job

    def get_preview_data(self, job: CSVImportJob, max_rows: int = 20) -> List[Dict]:
        """Liest Vorschau-Daten mit aktuellem Mapping"""
        if not job.file_path or not os.path.exists(job.file_path):
            return []

        with open(job.file_path, 'r', encoding=job.encoding) as f:
            reader = csv.DictReader(f, delimiter=job.delimiter)
            rows = []
            for i, row in enumerate(reader):
                if i >= max_rows:
                    break
                rows.append(row)

        return rows

    def validate_import(self, job: CSVImportJob) -> Dict:
        """
        Validiert alle Zeilen gegen das Mapping.

        Returns:
            Dict mit valid_count, error_count, errors (list)
        """
        if not job.column_mapping:
            return {'valid_count': 0, 'error_count': 0, 'errors': ['Kein Spalten-Mapping definiert']}

        mapping = job.column_mapping
        required = FIELD_MAPPINGS.get(job.import_type, {}).get('required', [])

        # Inverse Mapping: db_field -> csv_header
        inv_map = {v: k for k, v in mapping.items()}

        rows = self.get_preview_data(job, max_rows=10000)
        errors = []
        valid = 0

        for i, row in enumerate(rows, start=2):
            row_errors = []

            # Pflichtfelder pruefen
            for req in required:
                csv_col = inv_map.get(req)
                if not csv_col or not row.get(csv_col, '').strip():
                    field_label = FIELD_MAPPINGS[job.import_type]['fields'].get(req, req)
                    row_errors.append(f'Pflichtfeld "{field_label}" fehlt')

            # Betrag-Felder validieren
            for field in ['price', 'betrag_netto', 'betrag_brutto', 'betrag', 'mwst_satz']:
                csv_col = inv_map.get(field)
                if csv_col and row.get(csv_col, '').strip():
                    val = row[csv_col].strip().replace('.', '').replace(',', '.')
                    try:
                        Decimal(val)
                    except InvalidOperation:
                        row_errors.append(f'Ungueltige Zahl in "{csv_col}": {row[csv_col]}')

            # Datum-Felder validieren
            for field in ['buchungsdatum', 'datum']:
                csv_col = inv_map.get(field)
                if csv_col and row.get(csv_col, '').strip():
                    if not self._parse_date(row[csv_col].strip()):
                        row_errors.append(f'Ungueltiges Datum in "{csv_col}": {row[csv_col]}')

            if row_errors:
                errors.append({'row': i, 'errors': row_errors})
            else:
                valid += 1

        job.status = 'validated'
        job.error_rows = len(errors)
        job.error_details = errors[:100]  # Max 100 Fehler speichern
        db.session.commit()

        return {
            'valid_count': valid,
            'error_count': len(errors),
            'errors': errors[:50],
        }

    def execute_import(self, job: CSVImportJob) -> Dict:
        """
        Fuehrt den Import aus.

        Returns:
            Dict mit imported, skipped, errors
        """
        if job.import_type == 'customer':
            return self._import_customers(job)
        elif job.import_type == 'article':
            return self._import_articles(job)
        elif job.import_type == 'booking':
            return self._import_bookings(job)
        elif job.import_type == 'bank_statement':
            return self._import_bank_statement(job)
        else:
            return {'imported': 0, 'skipped': 0, 'errors': ['Unbekannter Import-Typ']}

    def _import_customers(self, job: CSVImportJob) -> Dict:
        """Importiert Kunden"""
        from src.models.models import Customer

        mapping = job.column_mapping
        inv_map = {v: k for k, v in mapping.items()}
        rows = self.get_preview_data(job, max_rows=100000)

        imported = 0
        skipped = 0
        errors = []

        # Hoechste Kunden-ID ermitteln (Format: KD001, KD002, ...)
        last_customer = Customer.query.filter(
            Customer.id.like('KD%')
        ).order_by(Customer.id.desc()).first()

        if last_customer:
            try:
                next_num = int(last_customer.id[2:]) + 1
            except (ValueError, IndexError):
                next_num = 1
        else:
            next_num = 1

        for i, row in enumerate(rows, start=2):
            try:
                # Duplikat-Check ueber Kundennummer
                cust_nr = self._get_mapped_val(row, inv_map, 'customer_number')
                if cust_nr:
                    existing = Customer.query.filter_by(customer_number=cust_nr).first()
                    if existing:
                        skipped += 1
                        continue

                # Duplikat-Check ueber E-Mail
                email = self._get_mapped_val(row, inv_map, 'email')
                if email:
                    existing = Customer.query.filter_by(email=email).first()
                    if existing:
                        skipped += 1
                        continue

                company = self._get_mapped_val(row, inv_map, 'company_name')
                customer_type = 'business' if company else 'private'

                customer = Customer(
                    id=f'KD{next_num:03d}',
                    customer_type=customer_type,
                    customer_number=cust_nr or None,
                    company_name=company,
                    first_name=self._get_mapped_val(row, inv_map, 'first_name'),
                    last_name=self._get_mapped_val(row, inv_map, 'last_name') or 'Unbekannt',
                    email=email,
                    phone=self._get_mapped_val(row, inv_map, 'phone'),
                    street=self._get_mapped_val(row, inv_map, 'street'),
                    postal_code=self._get_mapped_val(row, inv_map, 'postal_code'),
                    city=self._get_mapped_val(row, inv_map, 'city'),
                    country=self._get_mapped_val(row, inv_map, 'country') or 'DE',
                    vat_id=self._get_mapped_val(row, inv_map, 'vat_id'),
                )
                db.session.add(customer)
                next_num += 1
                imported += 1

                if imported % 100 == 0:
                    db.session.flush()

            except Exception as e:
                errors.append({'row': i, 'error': str(e)})

        db.session.commit()
        self._finalize_job(job, imported, skipped, errors)
        return {'imported': imported, 'skipped': skipped, 'errors': errors}

    def _import_articles(self, job: CSVImportJob) -> Dict:
        """Importiert Artikel"""
        from src.models.models import Article

        mapping = job.column_mapping
        inv_map = {v: k for k, v in mapping.items()}
        rows = self.get_preview_data(job, max_rows=100000)

        imported = 0
        skipped = 0
        errors = []

        for i, row in enumerate(rows, start=2):
            try:
                art_nr = self._get_mapped_val(row, inv_map, 'article_number')
                if art_nr:
                    existing = Article.query.filter_by(article_number=art_nr).first()
                    if existing:
                        skipped += 1
                        continue

                price_str = self._get_mapped_val(row, inv_map, 'price')
                price = self._parse_decimal(price_str) if price_str else Decimal('0')

                article = Article(
                    article_number=art_nr or None,
                    name=self._get_mapped_val(row, inv_map, 'name') or 'Unbenannt',
                    description=self._get_mapped_val(row, inv_map, 'description'),
                    price=price,
                    brand=self._get_mapped_val(row, inv_map, 'brand'),
                    material=self._get_mapped_val(row, inv_map, 'material'),
                    color=self._get_mapped_val(row, inv_map, 'color'),
                )
                db.session.add(article)
                imported += 1

                if imported % 100 == 0:
                    db.session.flush()

            except Exception as e:
                errors.append({'row': i, 'error': str(e)})

        db.session.commit()
        self._finalize_job(job, imported, skipped, errors)
        return {'imported': imported, 'skipped': skipped, 'errors': errors}

    def _import_bookings(self, job: CSVImportJob) -> Dict:
        """Importiert Buchungen"""
        from src.models.buchhaltung import BuchhaltungBuchung as Buchung, Konto

        mapping = job.column_mapping
        inv_map = {v: k for k, v in mapping.items()}
        rows = self.get_preview_data(job, max_rows=100000)

        imported = 0
        skipped = 0
        errors = []

        # Konten-Cache
        konten = {k.kontonummer: k for k in Konto.query.all()}

        for i, row in enumerate(rows, start=2):
            try:
                beleg = self._get_mapped_val(row, inv_map, 'belegnummer')
                if beleg:
                    existing = Buchung.query.filter_by(belegnummer=beleg).first()
                    if existing:
                        skipped += 1
                        continue

                netto_str = self._get_mapped_val(row, inv_map, 'betrag_netto')
                brutto_str = self._get_mapped_val(row, inv_map, 'betrag_brutto')
                mwst_str = self._get_mapped_val(row, inv_map, 'mwst_satz')

                netto = self._parse_decimal(netto_str) if netto_str else Decimal('0')
                brutto = self._parse_decimal(brutto_str) if brutto_str else None
                mwst = self._parse_decimal(mwst_str) if mwst_str else Decimal('19')

                datum_str = self._get_mapped_val(row, inv_map, 'buchungsdatum')
                buchungsdatum = self._parse_date(datum_str) if datum_str else date.today()

                soll_nr = self._get_mapped_val(row, inv_map, 'soll_konto')
                haben_nr = self._get_mapped_val(row, inv_map, 'haben_konto')

                buchung = Buchung(
                    buchungsdatum=buchungsdatum,
                    belegnummer=beleg,
                    buchungstext=self._get_mapped_val(row, inv_map, 'buchungstext') or 'CSV-Import',
                    betrag_netto=netto,
                    betrag_brutto=brutto or netto * (1 + mwst / 100),
                    mwst_satz=mwst,
                    mwst_betrag=netto * mwst / 100,
                    buchungs_art=self._get_mapped_val(row, inv_map, 'buchungs_art') or 'einnahme',
                    soll_konto_id=konten[soll_nr].id if soll_nr and soll_nr in konten else None,
                    haben_konto_id=konten[haben_nr].id if haben_nr and haben_nr in konten else None,
                    erstellt_von='CSV-Import',
                )
                db.session.add(buchung)
                imported += 1

                if imported % 100 == 0:
                    db.session.flush()

            except Exception as e:
                errors.append({'row': i, 'error': str(e)})

        db.session.commit()
        self._finalize_job(job, imported, skipped, errors)
        return {'imported': imported, 'skipped': skipped, 'errors': errors}

    def _import_bank_statement(self, job: CSVImportJob) -> Dict:
        """Importiert Bank-Auszuege als Buchungen"""
        from src.models.buchhaltung import BuchhaltungBuchung as Buchung

        mapping = job.column_mapping
        inv_map = {v: k for k, v in mapping.items()}
        rows = self.get_preview_data(job, max_rows=100000)

        imported = 0
        skipped = 0
        errors = []

        for i, row in enumerate(rows, start=2):
            try:
                datum_str = self._get_mapped_val(row, inv_map, 'datum')
                betrag_str = self._get_mapped_val(row, inv_map, 'betrag')
                zweck = self._get_mapped_val(row, inv_map, 'verwendungszweck') or ''
                name = self._get_mapped_val(row, inv_map, 'auftraggeber') or ''

                if not betrag_str:
                    skipped += 1
                    continue

                betrag = self._parse_decimal(betrag_str)
                buchungsdatum = self._parse_date(datum_str) if datum_str else date.today()

                # Duplikat-Hash
                hash_input = f'{buchungsdatum}|{betrag}|{zweck}|{name}'
                import_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:32]

                existing = Buchung.query.filter_by(belegnummer=f'BANK-{import_hash}').first()
                if existing:
                    skipped += 1
                    continue

                text = f'{name}: {zweck}'.strip(': ')[:500]

                buchung = Buchung(
                    buchungsdatum=buchungsdatum,
                    belegnummer=f'BANK-{import_hash}',
                    buchungstext=text or 'Bank-Import',
                    beleg_art='Bank',
                    betrag_netto=abs(betrag),
                    betrag_brutto=abs(betrag),
                    mwst_satz=Decimal('0'),
                    mwst_betrag=Decimal('0'),
                    buchungs_art='einnahme' if betrag > 0 else 'ausgabe',
                    erstellt_von='CSV-Import (Bank)',
                )
                db.session.add(buchung)
                imported += 1

                if imported % 100 == 0:
                    db.session.flush()

            except Exception as e:
                errors.append({'row': i, 'error': str(e)})

        db.session.commit()
        self._finalize_job(job, imported, skipped, errors)
        return {'imported': imported, 'skipped': skipped, 'errors': errors}

    # === Hilfsfunktionen ===

    def _get_mapped_val(self, row: Dict, inv_map: Dict, field: str) -> Optional[str]:
        """Holt gemappten Wert aus einer CSV-Zeile"""
        csv_col = inv_map.get(field)
        if csv_col and csv_col in row:
            val = row[csv_col].strip()
            return val if val else None
        return None

    def _parse_decimal(self, val: str) -> Decimal:
        """Parst deutschen oder englischen Dezimalwert"""
        val = val.strip()
        # Tausendertrennzeichen entfernen
        if ',' in val and '.' in val:
            if val.index('.') < val.index(','):
                val = val.replace('.', '').replace(',', '.')
            else:
                val = val.replace(',', '')
        elif ',' in val:
            val = val.replace(',', '.')
        return Decimal(val)

    def _parse_date(self, val: str) -> Optional[date]:
        """Parst verschiedene Datumsformate"""
        val = val.strip()
        formats = ['%d.%m.%Y', '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d.%m.%y']
        for fmt in formats:
            try:
                return datetime.strptime(val, fmt).date()
            except ValueError:
                continue
        return None

    def _finalize_job(self, job: CSVImportJob, imported: int, skipped: int, errors: List):
        """Aktualisiert Job-Status nach Import"""
        job.imported_rows = imported
        job.skipped_rows = skipped
        job.error_rows = len(errors)
        job.error_details = errors[:100]
        job.status = 'imported' if not errors else 'imported'
        job.completed_at = datetime.utcnow()
        db.session.commit()
