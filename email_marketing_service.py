"""
Email Marketing Service
======================

Generate and send professional email campaigns using AI-generated content.

Supports multiple email providers:
1. SendGrid API (free tier: 100 emails/day) - RECOMMENDED
2. Gmail OAuth2 (uses existing YouTube/Google credentials)
3. SMTP (Gmail App Password, other providers)

Author: Autonomous Business Platform
Version: 2.0
"""

import os
import smtplib
import logging
import base64
import pickle
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmailMarketingService:
    """
    Generate and send professional marketing emails with AI-powered content.
    
    Supports multiple providers:
    - sendgrid: Uses SendGrid API (easiest, free 100/day)
    - gmail_oauth: Uses Google OAuth2 (same as YouTube)
    - smtp: Traditional SMTP (requires app password for Gmail)
    """
    
    # Email template types
    TEMPLATE_TYPES = {
        'product_launch': 'Product Launch Announcement',
        'newsletter': 'Weekly/Monthly Newsletter',
        'promotion': 'Special Offer/Discount',
        'cart_abandonment': 'Cart Abandonment Reminder',
        'welcome': 'Welcome Series',
        're_engagement': 'Win-Back Campaign'
    }
    
    def __init__(
        self,
        provider: Optional[str] = None,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_username: Optional[str] = None,
        smtp_password: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        sendgrid_api_key: Optional[str] = None
    ):
        """
        Initialize email marketing service.
        
        Args:
            provider: 'sendgrid', 'gmail_oauth', or 'smtp' (auto-detected if not specified)
            smtp_host: SMTP server hostname
            smtp_port: SMTP server port (587 for TLS, 465 for SSL)
            smtp_username: SMTP username
            smtp_password: SMTP password
            from_email: Sender email address
            from_name: Sender display name
            sendgrid_api_key: SendGrid API key
        """
        # Load from env
        self.sendgrid_api_key = sendgrid_api_key or os.getenv('SENDGRID_API_KEY')
        self.smtp_host = smtp_host or os.getenv('EMAIL_SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = smtp_port or int(os.getenv('EMAIL_SMTP_PORT', '587'))
        self.smtp_username = smtp_username or os.getenv('EMAIL_USERNAME')
        self.smtp_password = smtp_password or os.getenv('EMAIL_PASSWORD')
        self.from_email = from_email or os.getenv('EMAIL_FROM_ADDRESS', self.smtp_username)
        self.from_name = from_name or os.getenv('EMAIL_FROM_NAME', 'Husky Hub')
        
        # Auto-detect provider (prioritize SendGrid as it's easiest)
        if provider:
            self.provider = provider
        elif self.sendgrid_api_key:
            self.provider = 'sendgrid'
        elif self._check_gmail_oauth():
            self.provider = 'gmail_oauth'
        elif self.smtp_username and self.smtp_password:
            self.provider = 'smtp'
        else:
            self.provider = None
        
        # Gmail OAuth credentials (reuse YouTube token)
        self.gmail_service = None
        
        if self.provider:
            logger.info(f"✅ Email Marketing Service initialized (provider: {self.provider})")
        else:
            logger.warning("⚠️ No email provider configured. Options:")
            logger.warning("   1. Add SENDGRID_API_KEY to .env (easiest, free 100/day)")
            logger.warning("   2. Gmail OAuth will use your existing YouTube credentials")
            logger.warning("   3. Add EMAIL_USERNAME + EMAIL_PASSWORD for SMTP")
    
    def _check_gmail_oauth(self) -> bool:
        """Check if Gmail OAuth credentials exist (from YouTube setup)."""
        token_path = Path(__file__).parent / 'token.pickle'
        return token_path.exists()
    
    def _get_gmail_service(self):
        """Get Gmail API service using existing OAuth credentials."""
        if self.gmail_service:
            return self.gmail_service
        
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            
            token_path = Path(__file__).parent / 'token.pickle'
            
            if not token_path.exists():
                logger.error("❌ No OAuth token found. Run YouTube setup first.")
                return None
            
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
            
            # Check if we have Gmail scope
            if creds and creds.valid:
                # Build Gmail service
                self.gmail_service = build('gmail', 'v1', credentials=creds)
                logger.info("✅ Gmail OAuth service initialized")
                return self.gmail_service
            else:
                logger.warning("⚠️ OAuth credentials expired or invalid")
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize Gmail OAuth: {e}")
            return None
    
    def _send_via_gmail_oauth(self, to_email: str, subject: str, html_content: str) -> bool:
        """Send email using Gmail OAuth2 API."""
        try:
            service = self._get_gmail_service()
            if not service:
                logger.error("❌ Gmail OAuth not available")
                return False
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            msg.attach(MIMEText(html_content, 'html'))
            
            # Encode message
            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            
            # Send via Gmail API
            service.users().messages().send(
                userId='me',
                body={'raw': raw}
            ).execute()
            
            logger.info(f"✅ Email sent via Gmail OAuth to {to_email}")
            return True
            
        except Exception as e:
            error_str = str(e)
            if 'insufficient' in error_str.lower() or 'scope' in error_str.lower():
                logger.error("❌ Gmail OAuth missing email scope. Need to re-authorize with Gmail permissions.")
                logger.info("💡 Easiest fix: Use SendGrid instead (add SENDGRID_API_KEY to .env)")
            else:
                logger.error(f"❌ Gmail OAuth send failed: {e}")
            return False
    
    def _send_via_sendgrid(self, to_email: str, subject: str, html_content: str) -> bool:
        """Send email using SendGrid API."""
        if not self.sendgrid_api_key:
            logger.error("❌ SendGrid API key not configured")
            return False
        
        try:
            url = "https://api.sendgrid.com/v3/mail/send"
            headers = {
                "Authorization": f"Bearer {self.sendgrid_api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "personalizations": [{"to": [{"email": to_email}]}],
                "from": {"email": self.from_email, "name": self.from_name},
                "subject": subject,
                "content": [{"type": "text/html", "value": html_content}]
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code in [200, 202]:
                logger.info(f"✅ Email sent via SendGrid to {to_email}")
                return True
            else:
                logger.error(f"❌ SendGrid error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ SendGrid send failed: {e}")
            return False
    
    def _send_via_smtp(self, to_email: str, subject: str, html_content: str) -> bool:
        """Send email using traditional SMTP."""
        if not all([self.smtp_username, self.smtp_password]):
            logger.error("❌ SMTP credentials not configured")
            return False
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            msg.attach(MIMEText(html_content, 'html'))
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"✅ Email sent via SMTP to {to_email}")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"❌ SMTP Authentication failed: {e}")
            logger.error("💡 For Gmail without App Passwords, use SendGrid instead:")
            logger.error("   1. Sign up at https://sendgrid.com (free: 100 emails/day)")
            logger.error("   2. Create an API key")
            logger.error("   3. Add SENDGRID_API_KEY=your_key to .env")
            return False
        except Exception as e:
            logger.error(f"❌ SMTP send failed: {e}")
            return False
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """
        Send email using the configured provider.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML email body
            text_content: Plain text alternative (optional)
        
        Returns:
            True if sent successfully
        """
        if not self.provider:
            logger.error("❌ No email provider configured!")
            logger.error("💡 Easiest option: Add SENDGRID_API_KEY to .env")
            logger.error("   Sign up free at https://sendgrid.com")
            return False
        
        if self.provider == 'sendgrid':
            return self._send_via_sendgrid(to_email, subject, html_content)
        elif self.provider == 'gmail_oauth':
            return self._send_via_gmail_oauth(to_email, subject, html_content)
        elif self.provider == 'smtp':
            return self._send_via_smtp(to_email, subject, html_content)
        else:
            logger.error(f"❌ Unknown provider: {self.provider}")
            return False
    
    def generate_email_content(
        self,
        template_type: str,
        product_name: str,
        product_description: str,
        target_audience: str = "general consumers",
        special_offer: str = "",
        tone: str = "professional and friendly"
    ) -> Dict[str, str]:
        """
        Generate AI-powered email content.
        """
        logger.info(f"📝 Generating {template_type} email content...")
        
        try:
            import replicate
            
            prompt = f"""Generate a professional marketing email with these specifications:

Template Type: {self.TEMPLATE_TYPES.get(template_type, template_type)}
Product: {product_name}
Description: {product_description}
Target Audience: {target_audience}
Tone: {tone}
{f"Special Offer: {special_offer}" if special_offer else ""}

Generate the following components:
1. Subject Line (compelling, 50 chars max)
2. Preview Text (appears after subject, 100 chars max)
3. Email Headline (bold, attention-grabbing)
4. Body Copy (3-4 paragraphs, benefit-focused, conversational)
5. Call-to-Action (clear, action-oriented button text)

Format as JSON with keys: subject, preview_text, headline, body, cta"""

            output = replicate.run(
                "meta/meta-llama-3-70b-instruct",
                input={"prompt": prompt, "max_tokens": 1000, "temperature": 0.7}
            )
            
            response = "".join(output)
            
            try:
                import json
                content = json.loads(response)
            except:
                content = {
                    'subject': f"Introducing {product_name}!",
                    'preview_text': product_description[:100],
                    'headline': f"Discover {product_name}",
                    'body': f"We're excited to introduce {product_name}. {product_description}\n\n{special_offer if special_offer else 'Shop now!'}",
                    'cta': "Shop Now"
                }
            
            logger.info(f"✅ Generated email content: {content['subject']}")
            return content
            
        except Exception as e:
            logger.error(f"❌ Email content generation failed: {e}")
            return {
                'subject': f"Introducing {product_name}",
                'preview_text': product_description[:100],
                'headline': f"New: {product_name}",
                'body': product_description,
                'cta': "Learn More"
            }
    
    def create_html_email(
        self,
        subject: str,
        preview_text: str,
        headline: str,
        body: str,
        cta_text: str,
        cta_link: str,
        product_image_url: Optional[str] = None,
        brand_color: str = "#6366f1",
        product_name: str = "New Product",
        price: str = "",
        discount: str = ""
    ) -> str:
        """Create stunning, modern HTML email template with rich visuals."""
        
        # Generate gradient colors based on brand color
        from datetime import datetime
        current_year = datetime.now().year
        
        # Clean up body text - handle paragraphs properly
        body_paragraphs = body.split('\n') if body else ["Discover something amazing."]
        body_html = ''.join([f'<p style="margin: 0 0 16px 0; font-size: 16px; line-height: 1.7; color: #4b5563;">{p.strip()}</p>' for p in body_paragraphs if p.strip()])
        
        # Price display
        price_html = ""
        if price:
            if discount:
                price_html = f'''
                <div style="text-align: center; margin: 24px 0;">
                    <span style="font-size: 18px; color: #9ca3af; text-decoration: line-through; margin-right: 12px;">{price}</span>
                    <span style="font-size: 32px; font-weight: 800; color: #10b981;">{discount}</span>
                </div>
                '''
            else:
                price_html = f'''
                <div style="text-align: center; margin: 24px 0;">
                    <span style="font-size: 32px; font-weight: 800; color: #1f2937;">{price}</span>
                </div>
                '''
        
        # Build hero image section separately to avoid nested f-string issues
        hero_image_html = ""
        if product_image_url:
            hero_image_html = f"""
                    <tr>
                        <td style="position: relative;">
                            <div style="position: relative; overflow: hidden;">
                                <img src="{product_image_url}" alt="{product_name}" class="hero-image" style="width: 100%; height: 350px; object-fit: cover; display: block;">
                                <div style="position: absolute; bottom: 0; left: 0; right: 0; height: 100px; background: linear-gradient(to top, rgba(0,0,0,0.3), transparent);"></div>
                            </div>
                        </td>
                    </tr>
            """
        
        margin_top = "-60px" if product_image_url else "0"
        
        html = f'''
<!DOCTYPE html>
<html lang="en" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="x-apple-disable-message-reformatting">
    <meta name="color-scheme" content="light dark">
    <meta name="supported-color-schemes" content="light dark">
    <title>{subject}</title>
    <!--[if mso]>
    <style>
        * {{ font-family: Arial, sans-serif !important; }}
    </style>
    <![endif]-->
    <style>
        :root {{
            color-scheme: light dark;
            supported-color-schemes: light dark;
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            margin: 0;
            padding: 0;
            width: 100% !important;
            -webkit-text-size-adjust: 100%;
            -ms-text-size-adjust: 100%;
            background-color: #f3f4f6;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
        }}
        
        @media only screen and (max-width: 600px) {{
            .container {{
                width: 100% !important;
                padding: 0 16px !important;
            }}
            .hero-image {{
                height: 280px !important;
            }}
            .content-padding {{
                padding: 32px 24px !important;
            }}
            .headline {{
                font-size: 28px !important;
            }}
            .product-card {{
                margin: 0 16px !important;
            }}
        }}
        
        @media (prefers-color-scheme: dark) {{
            .dark-mode-bg {{
                background-color: #1f2937 !important;
            }}
            .dark-mode-text {{
                color: #f9fafb !important;
            }}
        }}
        
        .hover-grow:hover {{
            transform: scale(1.02);
        }}
    </style>
</head>
<body style="margin: 0; padding: 0; background-color: #f3f4f6;">
    <!-- Preview text -->
    <div style="display: none; max-height: 0; overflow: hidden; mso-hide: all;">
        {preview_text}
        &nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;
    </div>
    
    <!-- Email wrapper -->
    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #f3f4f6;">
        <tr>
            <td align="center" style="padding: 40px 16px;">
                
                <!-- Main container -->
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" class="container" style="max-width: 600px; width: 100%; background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);">
                    
                    <!-- Gradient Header -->
                    <tr>
                        <td style="background: linear-gradient(135deg, {brand_color} 0%, #8b5cf6 50%, #ec4899 100%); padding: 32px 24px; text-align: center;">
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td align="center">
                                        <!-- Logo/Brand -->
                                        <div style="display: inline-block; background: rgba(255,255,255,0.2); border-radius: 12px; padding: 12px 24px; margin-bottom: 16px;">
                                            <span style="font-size: 24px; font-weight: 800; color: #ffffff; letter-spacing: -0.5px;">✨ {self.from_name}</span>
                                        </div>
                                    </td>
                                </tr>
                                <tr>
                                    <td align="center" style="padding-top: 8px;">
                                        <span style="font-size: 13px; color: rgba(255,255,255,0.9); text-transform: uppercase; letter-spacing: 2px; font-weight: 600;">NEW ARRIVAL</span>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Hero Product Image -->
                    {hero_image_html}
                    
                    <!-- Product Card (overlapping image) -->
                    <tr>
                        <td style="padding: 0 24px;">
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" class="product-card" style="background: #ffffff; border-radius: 16px; margin-top: {margin_top}; position: relative; box-shadow: 0 10px 40px -10px rgba(0,0,0,0.15);">
                                <tr>
                                    <td class="content-padding" style="padding: 40px 32px;">
                                        
                                        <!-- Badge -->
                                        <div style="text-align: center; margin-bottom: 20px;">
                                            <span style="display: inline-block; background: linear-gradient(135deg, #fef3c7, #fde68a); color: #92400e; font-size: 12px; font-weight: 700; padding: 6px 16px; border-radius: 20px; text-transform: uppercase; letter-spacing: 1px;">🔥 Limited Edition</span>
                                        </div>
                                        
                                        <!-- Headline -->
                                        <h1 class="headline" style="font-size: 32px; font-weight: 800; color: #1f2937; text-align: center; margin: 0 0 8px 0; line-height: 1.2; letter-spacing: -0.5px;">
                                            {headline}
                                        </h1>
                                        
                                        <!-- Subheadline -->
                                        <p style="font-size: 18px; color: #6b7280; text-align: center; margin: 0 0 24px 0; font-weight: 500;">
                                            {product_name}
                                        </p>
                                        
                                        <!-- Divider -->
                                        <div style="width: 60px; height: 4px; background: linear-gradient(90deg, {brand_color}, #ec4899); margin: 0 auto 24px auto; border-radius: 2px;"></div>
                                        
                                        <!-- Body Content -->
                                        <div style="margin-bottom: 32px;">
                                            {body_html}
                                        </div>
                                        
                                        <!-- Features Grid -->
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin-bottom: 32px;">
                                            <tr>
                                                <td width="33%" style="text-align: center; padding: 16px 8px;">
                                                    <div style="font-size: 24px; margin-bottom: 8px;">🚀</div>
                                                    <div style="font-size: 12px; color: #6b7280; font-weight: 600; text-transform: uppercase;">Fast Shipping</div>
                                                </td>
                                                <td width="33%" style="text-align: center; padding: 16px 8px; border-left: 1px solid #e5e7eb; border-right: 1px solid #e5e7eb;">
                                                    <div style="font-size: 24px; margin-bottom: 8px;">✨</div>
                                                    <div style="font-size: 12px; color: #6b7280; font-weight: 600; text-transform: uppercase;">Premium Quality</div>
                                                </td>
                                                <td width="33%" style="text-align: center; padding: 16px 8px;">
                                                    <div style="font-size: 24px; margin-bottom: 8px;">💯</div>
                                                    <div style="font-size: 12px; color: #6b7280; font-weight: 600; text-transform: uppercase;">Satisfaction</div>
                                                </td>
                                            </tr>
                                        </table>
                                        
                                        {price_html}
                                        
                                        <!-- CTA Button -->
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                            <tr>
                                                <td align="center">
                                                    <a href="{cta_link}" style="display: inline-block; background: linear-gradient(135deg, {brand_color} 0%, #8b5cf6 100%); color: #ffffff; font-size: 16px; font-weight: 700; text-decoration: none; padding: 16px 48px; border-radius: 50px; text-transform: uppercase; letter-spacing: 1px; box-shadow: 0 4px 14px 0 rgba(99, 102, 241, 0.4); transition: all 0.3s ease;">
                                                        {cta_text} →
                                                    </a>
                                                </td>
                                            </tr>
                                        </table>
                                        
                                        <!-- Trust badges -->
                                        <div style="text-align: center; margin-top: 24px; padding-top: 24px; border-top: 1px solid #e5e7eb;">
                                            <span style="font-size: 13px; color: #9ca3af;">🔒 Secure Checkout</span>
                                            <span style="margin: 0 12px; color: #e5e7eb;">|</span>
                                            <span style="font-size: 13px; color: #9ca3af;">📦 Free Returns</span>
                                            <span style="margin: 0 12px; color: #e5e7eb;">|</span>
                                            <span style="font-size: 13px; color: #9ca3af;">💬 24/7 Support</span>
                                        </div>
                                        
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Social Links -->
                    <tr>
                        <td style="padding: 32px 24px; text-align: center;">
                            <p style="font-size: 14px; color: #6b7280; margin-bottom: 16px;">Follow us for exclusive deals</p>
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" align="center">
                                <tr>
                                    <td style="padding: 0 8px;">
                                        <a href="#" style="display: inline-block; width: 40px; height: 40px; background: #f3f4f6; border-radius: 50%; text-align: center; line-height: 40px; text-decoration: none; font-size: 18px;">📘</a>
                                    </td>
                                    <td style="padding: 0 8px;">
                                        <a href="#" style="display: inline-block; width: 40px; height: 40px; background: #f3f4f6; border-radius: 50%; text-align: center; line-height: 40px; text-decoration: none; font-size: 18px;">📸</a>
                                    </td>
                                    <td style="padding: 0 8px;">
                                        <a href="#" style="display: inline-block; width: 40px; height: 40px; background: #f3f4f6; border-radius: 50%; text-align: center; line-height: 40px; text-decoration: none; font-size: 18px;">🐦</a>
                                    </td>
                                    <td style="padding: 0 8px;">
                                        <a href="#" style="display: inline-block; width: 40px; height: 40px; background: #f3f4f6; border-radius: 50%; text-align: center; line-height: 40px; text-decoration: none; font-size: 18px;">▶️</a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="background: #1f2937; padding: 40px 32px; text-align: center;">
                            <p style="font-size: 20px; font-weight: 700; color: #ffffff; margin-bottom: 8px;">{self.from_name}</p>
                            <p style="font-size: 14px; color: #9ca3af; margin-bottom: 24px;">Premium products, exceptional quality</p>
                            
                            <div style="margin-bottom: 24px;">
                                <a href="{cta_link}" style="color: #a5b4fc; text-decoration: none; font-size: 13px; margin: 0 12px;">Shop</a>
                                <a href="{cta_link}" style="color: #a5b4fc; text-decoration: none; font-size: 13px; margin: 0 12px;">About</a>
                                <a href="{cta_link}" style="color: #a5b4fc; text-decoration: none; font-size: 13px; margin: 0 12px;">Contact</a>
                                <a href="{cta_link}" style="color: #a5b4fc; text-decoration: none; font-size: 13px; margin: 0 12px;">FAQ</a>
                            </div>
                            
                            <p style="font-size: 12px; color: #6b7280; margin-bottom: 16px;">
                                © {current_year} {self.from_name}. All rights reserved.
                            </p>
                            
                            <p style="font-size: 11px; color: #4b5563;">
                                You're receiving this because you subscribed to our newsletter.<br>
                                <a href="#" style="color: #9ca3af; text-decoration: underline;">Unsubscribe</a> · 
                                <a href="#" style="color: #9ca3af; text-decoration: underline;">Update preferences</a>
                            </p>
                        </td>
                    </tr>
                    
                </table>
                
            </td>
        </tr>
    </table>
    
</body>
</html>
'''
        return html
    
    def send_batch_emails(
        self,
        recipients: List[str],
        subject: str,
        html_content: str,
        delay_seconds: float = 1.0
    ) -> Dict[str, int]:
        """Send emails to multiple recipients."""
        import time
        
        results = {'sent': 0, 'failed': 0}
        
        if not self.provider:
            logger.error("❌ No email provider configured")
            return {'sent': 0, 'failed': len(recipients)}
        
        logger.info(f"📧 Sending batch email to {len(recipients)} recipients via {self.provider}...")
        
        for email in recipients:
            if self.send_email(email, subject, html_content):
                results['sent'] += 1
            else:
                results['failed'] += 1
            
            time.sleep(delay_seconds)
        
        logger.info(f"✅ Batch complete: {results['sent']} sent, {results['failed']} failed")
        return results
    
    def generate_and_send_campaign(
        self,
        template_type: str,
        product_name: str,
        product_description: str,
        recipients: List[str],
        cta_link: str,
        product_image_url: Optional[str] = None,
        special_offer: str = "",
        target_audience: str = "general consumers"
    ) -> Dict:
        """Complete workflow: Generate AI content and send email campaign."""
        
        # Sanitize inputs - handle None values
        product_name = str(product_name or "New Product")
        product_description = str(product_description or "Check out our latest product!")
        cta_link = str(cta_link or "https://example.com")
        special_offer = str(special_offer or "")
        target_audience = str(target_audience or "general consumers")
        
        logger.info(f"🚀 Launching email campaign: {template_type}")
        
        # Check if we can send
        if not self.provider:
            logger.error("❌ No email provider configured!")
            return {
                'subject': f"Introducing {product_name}!",
                'success_count': 0,
                'failed_count': len(recipients) if recipients else 0,
                'error': 'No email provider configured. Add SENDGRID_API_KEY to .env'
            }
        
        try:
            # Generate content
            content = self.generate_email_content(
                template_type, product_name, product_description,
                target_audience, special_offer
            )
            
            # Ensure content has all required keys
            if not content or not isinstance(content, dict):
                content = {
                    'subject': f"Introducing {product_name}!",
                    'preview_text': product_description[:100] if product_description else '',
                    'headline': f"New: {product_name}",
                    'body': product_description or "Check out our latest product!",
                    'cta': "Shop Now"
                }
            
            # Ensure all required keys exist with defaults
            content.setdefault('subject', f"Introducing {product_name}!")
            content.setdefault('preview_text', product_description[:100] if product_description else '')
            content.setdefault('headline', f"New: {product_name}")
            content.setdefault('body', product_description or "Check out our latest!")
            content.setdefault('cta', "Shop Now")
            
            # Create HTML email with new gorgeous template
            html = self.create_html_email(
                subject=content['subject'],
                preview_text=content['preview_text'],
                headline=content['headline'],
                body=content['body'],
                cta_text=content['cta'],
                cta_link=cta_link,
                product_image_url=product_image_url,
                brand_color="#6366f1",
                product_name=product_name,
                price=special_offer if special_offer else "",
                discount=""
            )
            
            # Send to recipients
            results = self.send_batch_emails(recipients, content['subject'], html)
            
            return {
                'subject': content['subject'],
                'content': content,
                'html': html,
                'success_count': results['sent'],
                'failed_count': results['failed'],
                'failed_emails': [],
                'delivery_results': results
            }
            
        except Exception as e:
            logger.error(f"❌ Email campaign error: {e}")
            return {
                'subject': f"Introducing {product_name}!",
                'success_count': 0,
                'failed_count': len(recipients),
                'error': str(e)
            }


# Example usage
if __name__ == "__main__":
    service = EmailMarketingService()
    print(f"Provider: {service.provider}")
    
    if service.provider:
        # Test send
        results = service.generate_and_send_campaign(
            template_type='product_launch',
            product_name='Test Product',
            product_description='This is a test email.',
            recipients=['test@example.com'],
            cta_link='https://example.com'
        )
        print(f"Results: {results['delivery_results']}")
