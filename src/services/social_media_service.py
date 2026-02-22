# -*- coding: utf-8 -*-
"""
Social Media Service
====================
Meta Graph API Integration fuer Facebook + Instagram.
Posting, Scheduling, Insights.

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests

from src.models import db
from src.models.social_media import SocialMediaAccount, SocialMediaPost

logger = logging.getLogger(__name__)

GRAPH_BASE = 'https://graph.facebook.com/v18.0'


class MetaGraphService:
    """Meta (Facebook/Instagram) Graph API Service"""

    def __init__(self):
        self.app_id = None
        self.app_secret = None
        self._load_config()

    def _load_config(self):
        """Laedt Meta App-Konfiguration"""
        try:
            from src.models.company_settings import CompanySettings
            settings = CompanySettings.query.first()
            if settings:
                self.app_id = getattr(settings, 'meta_app_id', None)
                self.app_secret = getattr(settings, 'meta_app_secret', None)
        except Exception:
            pass

        # Fallback: Environment
        if not self.app_id:
            self.app_id = os.getenv('META_APP_ID')
            self.app_secret = os.getenv('META_APP_SECRET')

    def is_configured(self) -> bool:
        return bool(self.app_id and self.app_secret)

    def get_auth_url(self, redirect_uri: str) -> str:
        """Facebook OAuth URL generieren"""
        scopes = 'pages_show_list,pages_read_engagement,pages_manage_posts,instagram_basic,instagram_content_publish'
        return (
            f'https://www.facebook.com/v18.0/dialog/oauth'
            f'?client_id={self.app_id}'
            f'&redirect_uri={redirect_uri}'
            f'&scope={scopes}'
            f'&response_type=code'
        )

    def exchange_code(self, code: str, redirect_uri: str) -> Optional[Dict]:
        """Authorization Code -> Short-lived Token"""
        resp = requests.get(f'{GRAPH_BASE}/oauth/access_token', params={
            'client_id': self.app_id,
            'client_secret': self.app_secret,
            'redirect_uri': redirect_uri,
            'code': code,
        })

        if resp.status_code == 200:
            return resp.json()
        logger.error(f"Token-Exchange fehlgeschlagen: {resp.text}")
        return None

    def exchange_for_long_token(self, short_token: str) -> Optional[Dict]:
        """Short-lived Token -> Long-lived Token (~60 Tage)"""
        resp = requests.get(f'{GRAPH_BASE}/oauth/access_token', params={
            'grant_type': 'fb_exchange_token',
            'client_id': self.app_id,
            'client_secret': self.app_secret,
            'fb_exchange_token': short_token,
        })

        if resp.status_code == 200:
            return resp.json()
        return None

    def get_pages(self, user_token: str) -> List[Dict]:
        """Facebook-Seiten des Users auflisten"""
        resp = requests.get(f'{GRAPH_BASE}/me/accounts', params={
            'access_token': user_token,
            'fields': 'id,name,access_token,instagram_business_account',
        })

        if resp.status_code == 200:
            return resp.json().get('data', [])
        return []

    def publish_to_facebook(self, account: SocialMediaAccount, text: str,
                            image_path: str = None, link: str = None) -> Optional[str]:
        """
        Veroeffentlicht Post auf Facebook-Seite.
        Returns: post_id oder None
        """
        if not account.page_id or not account.access_token_encrypted:
            return None

        params = {
            'access_token': account.access_token_encrypted,
            'message': text,
        }

        if link:
            params['link'] = link

        if image_path and os.path.exists(image_path):
            # Foto-Post
            with open(image_path, 'rb') as f:
                resp = requests.post(
                    f'{GRAPH_BASE}/{account.page_id}/photos',
                    data=params,
                    files={'source': f}
                )
        else:
            # Text-Post
            resp = requests.post(f'{GRAPH_BASE}/{account.page_id}/feed', data=params)

        if resp.status_code in (200, 201):
            data = resp.json()
            return data.get('id') or data.get('post_id')

        logger.error(f"Facebook-Post fehlgeschlagen: {resp.status_code} {resp.text}")
        return None

    def publish_to_instagram(self, account: SocialMediaAccount, text: str,
                             image_url: str = None) -> Optional[str]:
        """
        Veroeffentlicht Post auf Instagram.
        Instagram erfordert eine oeffentlich erreichbare Bild-URL.
        Returns: post_id oder None
        """
        if not account.page_id or not account.access_token_encrypted or not image_url:
            return None

        # Step 1: Container erstellen
        resp = requests.post(f'{GRAPH_BASE}/{account.page_id}/media', data={
            'access_token': account.access_token_encrypted,
            'image_url': image_url,
            'caption': text,
        })

        if resp.status_code != 200:
            logger.error(f"Instagram-Container fehlgeschlagen: {resp.text}")
            return None

        container_id = resp.json().get('id')
        if not container_id:
            return None

        # Step 2: Veroeffentlichen
        resp = requests.post(f'{GRAPH_BASE}/{account.page_id}/media_publish', data={
            'access_token': account.access_token_encrypted,
            'creation_id': container_id,
        })

        if resp.status_code == 200:
            return resp.json().get('id')

        logger.error(f"Instagram-Publish fehlgeschlagen: {resp.text}")
        return None

    def publish_post(self, post: SocialMediaPost) -> bool:
        """Veroeffentlicht einen geplanten Post"""
        account = post.account
        if not account or not account.is_active:
            post.status = 'failed'
            post.error_message = 'Konto nicht aktiv'
            db.session.commit()
            return False

        full_text = post.text or ''
        if post.hashtags:
            full_text += '\n\n' + post.hashtags

        try:
            ext_id = None
            if account.platform == 'facebook':
                ext_id = self.publish_to_facebook(account, full_text, post.image_path, post.link_url)
            elif account.platform == 'instagram':
                ext_id = self.publish_to_instagram(account, full_text, post.link_url)

            if ext_id:
                post.external_post_id = ext_id
                post.status = 'published'
                post.published_at = datetime.utcnow()
            else:
                post.status = 'failed'
                post.error_message = 'API-Aufruf fehlgeschlagen'

        except Exception as e:
            post.status = 'failed'
            post.error_message = str(e)

        db.session.commit()
        return post.status == 'published'

    def schedule_post(self, post_id: int):
        """Plant einen Post mit APScheduler"""
        try:
            from src.services.scheduler_service import add_job

            post = SocialMediaPost.query.get(post_id)
            if not post or not post.scheduled_at:
                return

            def publish_task():
                p = SocialMediaPost.query.get(post_id)
                if p and p.status == 'scheduled':
                    self.publish_post(p)

            add_job(
                func=publish_task,
                trigger='date',
                job_id=f'social_post_{post_id}',
                run_date=post.scheduled_at,
            )
            logger.info(f"Social Media Post {post_id} geplant fuer {post.scheduled_at}")
        except Exception as e:
            logger.warning(f"Scheduling fehlgeschlagen: {e}")


class AutoPostService:
    """Erstellt automatische Posts aus Artikeln/Galerie"""

    def create_from_article(self, article_id: int, account_ids: List[int],
                            custom_text: str = None) -> List[SocialMediaPost]:
        """Erstellt Posts aus einem Artikel fuer mehrere Accounts"""
        from src.models.models import Article

        article = Article.query.get(article_id)
        if not article:
            return []

        text = custom_text or f'{article.name}\n\n{article.description or ""}'.strip()
        if article.price:
            text += f'\n\nPreis: {article.price:.2f} EUR'

        posts = []
        for acc_id in account_ids:
            account = SocialMediaAccount.query.get(acc_id)
            if not account:
                continue

            post = SocialMediaPost(
                account_id=acc_id,
                text=text,
                image_path=getattr(article, 'shop_image_path', None),
                source_type='article',
                source_id=article_id,
                status='draft',
            )
            db.session.add(post)
            posts.append(post)

        db.session.commit()
        return posts
