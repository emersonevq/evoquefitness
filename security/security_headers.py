"""
Adiciona headers de segurança às respostas HTTP
"""
from flask import current_app, request

class SecurityHeaders:
    def __init__(self):
        self.default_headers = {
            # Previne ataques XSS
            'X-XSS-Protection': '1; mode=block',
            
            # Previne MIME type sniffing
            'X-Content-Type-Options': 'nosniff',
            
            # Previne clickjacking - SAMEORIGIN permite iframes do mesmo domínio
            'X-Frame-Options': 'SAMEORIGIN',
            
            # Força HTTPS (comentado para desenvolvimento)
            # 'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            
            # Controla referrer
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            
            # Remove informações do servidor
            'Server': 'Evoque-Server',
            
            # Política de permissões
            'Permissions-Policy': 'geolocation=(), microphone=(), camera=()',
        }
        
        # CSP (Content Security Policy) - MUITO MAIS PERMISSIVO para desenvolvimento
        self.csp_policy = (
            "default-src 'self' 'unsafe-inline' 'unsafe-eval' data: blob:; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https: http: data: blob:; "
            "style-src 'self' 'unsafe-inline' https: http: data:; "
            "font-src 'self' 'unsafe-inline' https: http: data:; "
            "img-src 'self' 'unsafe-inline' https: http: data: blob:; "
            "connect-src 'self' https: http: ws: wss:; "
            "media-src 'self' https: http: data: blob:; "
            "object-src 'self' data:; "
            "child-src 'self' https: http:; "
            "frame-src 'self' https: http:; "
            "worker-src 'self' blob:; "
            "form-action 'self' https: http:; "
            "base-uri 'self'"
        )
    
    def add_security_headers(self, response):
        """Adiciona headers de segurança à resposta"""
        try:
            # Adiciona headers padrão
            for header, value in self.default_headers.items():
                response.headers[header] = value
            
            # Adiciona CSP apenas se não for arquivo estático
            try:
                if hasattr(request, 'path') and not request.path.startswith('/static/'):
                    response.headers['Content-Security-Policy'] = self.csp_policy
            except RuntimeError:
                # Se não há contexto de request, adiciona CSP mesmo assim
                response.headers['Content-Security-Policy'] = self.csp_policy
            
            # Remove headers que revelam informações
            response.headers.pop('Server', None)
            response.headers.pop('X-Powered-By', None)
            
            # Adiciona header customizado para identificar proteção
            response.headers['X-Security-Protected'] = 'Evoque-Security-v1.0'
            
            return response
            
        except Exception as e:
            try:
                if hasattr(current_app, 'logger'):
                    current_app.logger.error(f"Erro ao adicionar headers de segurança: {str(e)}")
                else:
                    print(f"Erro ao adicionar headers de segurança: {str(e)}")
            except:
                print(f"Erro crítico nos headers de segurança: {str(e)}")
            return response
    
    def set_csp_for_admin(self, response):
        """CSP mais restritivo para páginas administrativas"""
        admin_csp = (
            "default-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "connect-src 'self' ws: wss:; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        response.headers['Content-Security-Policy'] = admin_csp
        return response
    
    def add_cache_headers(self, response, cache_type='no-cache'):
        """Adiciona headers de cache apropriados"""
        if cache_type == 'no-cache':
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        elif cache_type == 'public':
            response.headers['Cache-Control'] = 'public, max-age=3600'
        
        return response
    
    def disable_csp_for_development(self):
        """Desabilita CSP completamente para desenvolvimento"""
        self.csp_policy = ""
        
    def enable_development_mode(self):
        """Configura headers para modo de desenvolvimento"""
        # CSP muito permissivo para desenvolvimento
        self.csp_policy = (
            "default-src * 'unsafe-inline' 'unsafe-eval' data: blob:; "
            "script-src * 'unsafe-inline' 'unsafe-eval'; "
            "style-src * 'unsafe-inline'; "
            "img-src * data: blob:; "
            "font-src * data:; "
            "connect-src * ws: wss:; "
            "media-src * blob: data:; "
            "object-src *; "
            "child-src *; "
            "frame-src *; "
            "worker-src * blob:; "
            "form-action *"
        )
        
        # Remove X-Frame-Options para permitir iframes
        if 'X-Frame-Options' in self.default_headers:
            del self.default_headers['X-Frame-Options']