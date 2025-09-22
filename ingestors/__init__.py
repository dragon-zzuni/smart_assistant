# -*- coding: utf-8 -*-
"""
Ingestors 패키지 - 다양한 소스에서 데이터를 수집하는 모듈들
"""

from .email_imap import EmailIMAPCollector
from .messenger_adapter import MessengerAdapter

__all__ = ['EmailIMAPCollector', 'MessengerAdapter']
