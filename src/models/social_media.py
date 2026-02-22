# -*- coding: utf-8 -*-
"""
Social Media Models
===================
SocialMediaAccount + SocialMediaPost fuer Facebook/Instagram Auto-Posting

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from datetime import datetime
from src.models import db


class SocialMediaAccount(db.Model):
    """Social Media Konto (Facebook/Instagram)"""
    __tablename__ = 'social_media_accounts'

    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(20), nullable=False)  # facebook, instagram
    account_name = db.Column(db.String(200))
    page_id = db.Column(db.String(100))  # Facebook Page ID / Instagram Business Account ID

    # OAuth (Long-lived Page Token)
    access_token_encrypted = db.Column(db.Text)
    token_expiry = db.Column(db.DateTime)

    # Status
    is_active = db.Column(db.Boolean, default=True)
    connected_at = db.Column(db.DateTime, default=datetime.utcnow)
    connected_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    # Beziehungen
    user = db.relationship('User', backref='social_media_accounts')
    posts = db.relationship('SocialMediaPost', backref='account', lazy='dynamic')

    def __repr__(self):
        return f"<SocialMediaAccount {self.platform} {self.account_name}>"


class SocialMediaPost(db.Model):
    """Social Media Post"""
    __tablename__ = 'social_media_posts'

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('social_media_accounts.id'), nullable=False, index=True)

    # Inhalt
    text = db.Column(db.Text)
    image_path = db.Column(db.String(500))
    link_url = db.Column(db.String(500))
    hashtags = db.Column(db.String(500))

    # Status: draft, scheduled, published, failed
    status = db.Column(db.String(20), default='draft', index=True)

    # Zeitplanung
    scheduled_at = db.Column(db.DateTime, index=True)
    published_at = db.Column(db.DateTime)

    # Externer Post
    external_post_id = db.Column(db.String(200))
    error_message = db.Column(db.Text)

    # Quelle
    source_type = db.Column(db.String(20))  # manual, article, gallery
    source_id = db.Column(db.Integer)

    # Meta
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    user = db.relationship('User', backref='social_media_posts')

    def __repr__(self):
        return f"<SocialMediaPost {self.id} [{self.status}]>"
