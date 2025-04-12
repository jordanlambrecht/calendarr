#!/usr/bin/env python3
# src/services/webhook_service.py

import logging
import requests
from typing import Dict, List, Any

logger = logging.getLogger("service_webhook")


class WebhookService:
    """Service for sending data to webhooks"""
    
    def __init__(self, http_timeout: int = 30):
        """
        Initialize WebhookService
        
        Args:
            http_timeout: HTTP request timeout in seconds
        """
        self.http_timeout = http_timeout
    
    def send_request(self, webhook_url: str, payload: Dict[str, Any], 
                   success_codes: List[int]) -> bool:
        """
        Send data to a webhook and check for success
        
        Args:
            webhook_url: URL to send data to
            payload: Data to send
            success_codes: HTTP status codes that indicate success
            
        Returns:
            Boolean indicating success
        """
        headers = {'Content-Type': 'application/json'}
        
        try:
            response = requests.post(
                webhook_url, 
                json=payload, 
                headers=headers, 
                timeout=self.http_timeout
            )
            logger.debug(f"Webhook URL: {webhook_url}")
            is_success = response.status_code in success_codes
            emoji = "✅" if is_success else "❌"

            logger.info(f"{emoji}  Webhook response status code: {response.status_code}")
            
            if is_success:
                return True
            else:
                logger.error(f"❌  Failed to send webhook: {response.text}")
                return False
                
        except requests.RequestException as e:
            logger.error(f"Error sending to webhook: {str(e)}")
            return False