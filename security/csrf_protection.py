"""
Proteção CSRF customizada para complementar o Flask-WTF
"""
import secrets
import hashlib
import time
from flask import session, request, current_app, abort

class CSRFProtection:
    def __init__(self):
        self.token_lifetime = 3600  # 1 hora
    
    def generate_csrf_token(self):
        """Gera um token CSRF único"""
        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_urlsafe(32)
            session['csrf_token_time'] = time.time()
        
        return session['csrf_token']
    
    def validate_csrf_token(self, token):
        """Valida um token CSRF"""
        if 'csrf_token' not in session:
            return False
        
        # Verifica se o token não expirou
        if 'csrf_token_time' in session:
            token_age = time.time() - session['csrf_token_time']
            if token_age > self.token_lifetime:
                self.clear_csrf_token()
                return False
        
        # Compara tokens de forma segura
        return secrets.compare_digest(session['csrf_token'], token)
    
    def clear_csrf_token(self):
        """Remove o token CSRF da sessão"""
        session.pop('csrf_token', None)
        session.pop('csrf_token_time', None)
    
    def protect_request(self):
        """Protege uma requisição contra CSRF"""
        if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            token = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token')
            
            if not token or not self.validate_csrf_token(token):
                try:
                    current_app.logger.warning(
                        f'Tentativa de CSRF detectada de {request.remote_addr} '
                        f'para {request.url}'
                    )
                except:
                    print(f'Tentativa de CSRF detectada de {request.remote_addr}')
                abort(403, description="CSRF token missing or invalid")
    
    def exempt_view(self, view_func):
        """Marca uma view como isenta de proteção CSRF"""
        view_func._csrf_exempt = True
        return view_func
    
    def is_exempt(self, view_func):
        """Verifica se uma view está isenta de proteção CSRF"""
        return getattr(view_func, '_csrf_exempt', False)