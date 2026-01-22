"""
Input validation and API connection testing utilities
Provides real-time validation, pre-flight checks, and test connection functionality
"""

import re
import requests
import streamlit as st
from typing import Dict, Tuple, Optional, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a validation check"""
    is_valid: bool
    message: str
    details: Optional[Dict[str, Any]] = None


class APIValidator:
    """Validates API keys and tests connections"""
    
    @staticmethod
    def test_replicate_token(token: str) -> ValidationResult:
        """Test Replicate API token"""
        if not token or not token.strip():
            return ValidationResult(False, "Token is empty")
        
        token = token.strip()
        
        # Format check
        if not token.startswith('r8_'):
            return ValidationResult(False, "Invalid format - should start with 'r8_'")
        
        if len(token) < 40:
            return ValidationResult(False, "Token too short - check if complete")
        
        # Test actual connection
        try:
            headers = {'Authorization': f'Token {token}'}
            response = requests.get(
                'https://api.replicate.com/v1/account',
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                username = data.get('username', 'Unknown')
                return ValidationResult(
                    True, 
                    f"✅ Connected as @{username}",
                    {'username': username, 'data': data}
                )
            elif response.status_code == 401:
                return ValidationResult(False, "❌ Invalid token - authentication failed")
            else:
                return ValidationResult(
                    False, 
                    f"❌ Connection failed (HTTP {response.status_code})"
                )
                
        except requests.Timeout:
            return ValidationResult(False, "⏱️ Connection timeout - check internet")
        except requests.RequestException as e:
            return ValidationResult(False, f"❌ Connection error: {str(e)}")
    
    @staticmethod
    def test_printify_token(token: str, shop_id: str) -> ValidationResult:
        """Test Printify API token and shop ID"""
        if not token or not token.strip():
            return ValidationResult(False, "Token is empty")
        
        if not shop_id or not shop_id.strip():
            return ValidationResult(False, "Shop ID is empty")
        
        token = token.strip()
        shop_id = shop_id.strip()
        
        # Format check
        if not token.startswith('eyJ'):
            return ValidationResult(False, "Invalid format - should start with 'eyJ'")
        
        if not shop_id.isdigit():
            return ValidationResult(False, "Shop ID should be numeric")
        
        # Test connection
        try:
            headers = {'Authorization': f'Bearer {token}'}
            response = requests.get(
                f'https://api.printify.com/v1/shops/{shop_id}.json',
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                shop_title = data.get('title', 'Unknown')
                return ValidationResult(
                    True,
                    f"✅ Connected to shop: {shop_title}",
                    {'shop_title': shop_title, 'data': data}
                )
            elif response.status_code == 401:
                return ValidationResult(False, "❌ Invalid token - authentication failed")
            elif response.status_code == 404:
                return ValidationResult(False, "❌ Shop not found - check Shop ID")
            else:
                return ValidationResult(
                    False,
                    f"❌ Connection failed (HTTP {response.status_code})"
                )
                
        except requests.Timeout:
            return ValidationResult(False, "⏱️ Connection timeout - check internet")
        except requests.RequestException as e:
            return ValidationResult(False, f"❌ Connection error: {str(e)}")
    
    @staticmethod
    def test_anthropic_token(token: str) -> ValidationResult:
        """Test Anthropic API token"""
        if not token or not token.strip():
            return ValidationResult(False, "Token is empty")
        
        token = token.strip()
        
        # Format check
        if not token.startswith('sk-ant-'):
            return ValidationResult(False, "Invalid format - should start with 'sk-ant-'")
        
        # Test connection
        try:
            headers = {
                'x-api-key': token,
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json'
            }
            
            # Simple test: try to create a very small message
            data = {
                "model": "claude-3-haiku-20240307",
                "max_tokens": 10,
                "messages": [{"role": "user", "content": "Hi"}]
            }
            
            response = requests.post(
                'https://api.anthropic.com/v1/messages',
                headers=headers,
                json=data,
                timeout=15
            )
            
            if response.status_code == 200:
                return ValidationResult(True, "✅ Valid Anthropic API key")
            elif response.status_code == 401:
                return ValidationResult(False, "❌ Invalid API key")
            elif response.status_code == 429:
                return ValidationResult(True, "✅ Valid key (rate limited)")
            else:
                return ValidationResult(
                    False,
                    f"❌ Connection failed (HTTP {response.status_code})"
                )
                
        except requests.Timeout:
            return ValidationResult(False, "⏱️ Connection timeout - check internet")
        except requests.RequestException as e:
            return ValidationResult(False, f"❌ Connection error: {str(e)}")
    
    @staticmethod
    def test_shopify_credentials(shop_url: str, access_token: str) -> ValidationResult:
        """Test Shopify credentials"""
        if not shop_url or not shop_url.strip():
            return ValidationResult(False, "Shop URL is empty")
        
        if not access_token or not access_token.strip():
            return ValidationResult(False, "Access token is empty")
        
        shop_url = shop_url.strip().replace('https://', '').replace('http://', '')
        if not shop_url.endswith('.myshopify.com'):
            shop_url = f"{shop_url}.myshopify.com"
        
        access_token = access_token.strip()
        
        # Test connection
        try:
            headers = {'X-Shopify-Access-Token': access_token}
            response = requests.get(
                f'https://{shop_url}/admin/api/2024-01/shop.json',
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                shop_name = data.get('shop', {}).get('name', 'Unknown')
                return ValidationResult(
                    True,
                    f"✅ Connected to: {shop_name}",
                    {'shop_name': shop_name, 'data': data}
                )
            elif response.status_code == 401:
                return ValidationResult(False, "❌ Invalid access token")
            elif response.status_code == 404:
                return ValidationResult(False, "❌ Shop not found - check URL")
            else:
                return ValidationResult(
                    False,
                    f"❌ Connection failed (HTTP {response.status_code})"
                )
                
        except requests.Timeout:
            return ValidationResult(False, "⏱️ Connection timeout - check internet")
        except requests.RequestException as e:
            return ValidationResult(False, f"❌ Connection error: {str(e)}")


class InputValidator:
    """Validates user inputs"""
    
    @staticmethod
    def validate_email(email: str) -> ValidationResult:
        """Validate email format"""
        if not email or not email.strip():
            return ValidationResult(False, "Email is empty")
        
        email = email.strip()
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if re.match(pattern, email):
            return ValidationResult(True, "✅ Valid email format")
        else:
            return ValidationResult(False, "❌ Invalid email format")
    
    @staticmethod
    def validate_url(url: str) -> ValidationResult:
        """Validate URL format"""
        if not url or not url.strip():
            return ValidationResult(False, "URL is empty")
        
        url = url.strip()
        pattern = r'^https?://[^\s]+$'
        
        if re.match(pattern, url):
            return ValidationResult(True, "✅ Valid URL format")
        else:
            return ValidationResult(False, "❌ Invalid URL format (must start with http:// or https://)")
    
    @staticmethod
    def validate_text(text: str, min_length: int = 1, max_length: int = 10000, field_name: str = "Text") -> ValidationResult:
        """Validate text input"""
        if not text or not text.strip():
            return ValidationResult(False, f"{field_name} is empty")
        
        text = text.strip()
        length = len(text)
        
        if length < min_length:
            return ValidationResult(
                False,
                f"{field_name} too short (minimum {min_length} characters)"
            )
        
        if length > max_length:
            return ValidationResult(
                False,
                f"{field_name} too long (maximum {max_length} characters)"
            )
        
        return ValidationResult(True, f"✅ Valid {field_name.lower()}")
    
    @staticmethod
    def validate_number(value: str, min_val: float = None, max_val: float = None, field_name: str = "Number") -> ValidationResult:
        """Validate numeric input"""
        if not value or not str(value).strip():
            return ValidationResult(False, f"{field_name} is empty")
        
        try:
            num = float(str(value).strip())
            
            if min_val is not None and num < min_val:
                return ValidationResult(
                    False,
                    f"{field_name} must be at least {min_val}"
                )
            
            if max_val is not None and num > max_val:
                return ValidationResult(
                    False,
                    f"{field_name} must be at most {max_val}"
                )
            
            return ValidationResult(True, f"✅ Valid {field_name.lower()}")
            
        except (ValueError, TypeError):
            return ValidationResult(False, f"❌ {field_name} must be a number")


def display_validation_result(result: ValidationResult, show_success: bool = True):
    """Display validation result in Streamlit UI"""
    if result.is_valid:
        if show_success:
            st.success(result.message)
    else:
        st.error(result.message)
    
    if result.details:
        with st.expander("🔍 Details"):
            st.json(result.details)


def create_test_connection_button(
    label: str,
    validator_func,
    *args,
    key: str = None,
    **kwargs
) -> Optional[ValidationResult]:
    """Create a test connection button with automatic validation display"""
    if st.button(f"🔌 Test {label} Connection", key=key, type="secondary"):
        with st.spinner(f"Testing {label}..."):
            result = validator_func(*args, **kwargs)
            display_validation_result(result)
            return result
    return None


def validate_before_operation(
    validations: Dict[str, Tuple],
    operation_name: str = "operation"
) -> Tuple[bool, str]:
    """
    Run multiple validations before an operation
    
    Args:
        validations: Dict of {field_name: (validator_func, *args)}
        operation_name: Name of the operation for error messages
    
    Returns:
        (all_valid, error_message)
    """
    errors = []
    
    for field_name, (validator_func, *args) in validations.items():
        result = validator_func(*args)
        if not result.is_valid:
            errors.append(f"• {field_name}: {result.message}")
    
    if errors:
        error_msg = f"Cannot proceed with {operation_name}:\n" + "\n".join(errors)
        return False, error_msg
    
    return True, ""
