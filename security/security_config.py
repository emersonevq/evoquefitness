"""
Configurações centralizadas de segurança
"""
import os
from datetime import timedelta

class SecurityConfig:
    """Configurações de segurança centralizadas"""
    
    # Rate Limiting
    RATE_LIMIT_STORAGE_URL = "memory://"
    RATELIMIT_HEADERS_ENABLED = True
    
    # Configurações de sessão
    SESSION_COOKIE_SECURE = False  # True em produção com HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(days=3650)  # 10 anos para sessões permanentes
    
    # Configurações CSRF
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hora
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-change-in-production'
    
    # Configurações de upload
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    UPLOAD_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.pdf', '.doc', '.docx']
    
    # Configurações de logging
    SECURITY_LOG_LEVEL = 'INFO'
    SECURITY_LOG_FILE = 'logs/security.log'
    
    # Configurações de bloqueio
    MAX_LOGIN_ATTEMPTS = 5
    LOGIN_BLOCK_DURATION = 300  # 5 minutos
    IP_BLOCK_DURATION = 900  # 15 minutos
    
    # Headers de segurança - MAIS PERMISSIVOS PARA DESENVOLVIMENTO
    SECURITY_HEADERS = {
        'X-XSS-Protection': '1; mode=block',
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'SAMEORIGIN',  # Mudado de DENY para SAMEORIGIN
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Permissions-Policy': 'geolocation=(), microphone=(), camera=()',
    }
    
    # Content Security Policy - MUITO MAIS PERMISSIVO
    CSP_POLICY = {
        'default-src': "'self' 'unsafe-inline' 'unsafe-eval' data: blob:",
        'script-src': "'self' 'unsafe-inline' 'unsafe-eval' https: http: data: blob:",
        'style-src': "'self' 'unsafe-inline' https: http: data:",
        'font-src': "'self' https: http: data:",
        'img-src': "'self' data: blob: https: http:",
        'connect-src': "'self' wss: ws: https: http:",
        'media-src': "'self' data: blob: https: http:",
        'object-src': "'self' data:",
        'child-src': "'self' https: http:",
        'frame-src': "'self' https: http:",
        'worker-src': "'self' blob:",
        'form-action': "'self' https: http:",
        'base-uri': "'self'"
    }
    
    @classmethod
    def get_csp_string(cls):
        """Converte a política CSP para string"""
        return '; '.join([f"{key} {value}" for key, value in cls.CSP_POLICY.items()])
    
    @classmethod
    def update_for_production(cls):
        """Atualiza configurações para ambiente de produção"""
        cls.SESSION_COOKIE_SECURE = True
        cls.SECURITY_HEADERS['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        cls.SECURITY_HEADERS['X-Frame-Options'] = 'DENY'
        
        # CSP mais restritivo para produção
        cls.CSP_POLICY = {
            'default-src': "'self'",
            'script-src': "'self'",
            'style-src': "'self' 'unsafe-inline'",
            'font-src': "'self'",
            'img-src': "'self' data: https:",
            'connect-src': "'self' wss: ws:",
            'frame-ancestors': "'none'",
            'base-uri': "'self'",
            'form-action': "'self'"
        }
    
    @classmethod
    def enable_development_mode(cls):
        """Habilita modo de desenvolvimento com CSP muito permissivo"""
        cls.CSP_POLICY = {
            'default-src': "* 'unsafe-inline' 'unsafe-eval' data: blob:",
            'script-src': "* 'unsafe-inline' 'unsafe-eval'",
            'style-src': "* 'unsafe-inline'",
            'img-src': "* data: blob:",
            'font-src': "* data:",
            'connect-src': "* ws: wss:",
            'media-src': "* blob: data:",
            'object-src': "*",
            'child-src': "*",
            'frame-src': "*",
            'worker-src': "* blob:",
            'form-action': "*"
        }
