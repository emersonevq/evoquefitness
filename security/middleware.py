from flask import request, jsonify, session, g
from flask_login import current_user
from datetime import datetime, timedelta
from functools import wraps
import ipaddress
import logging
import json
import re

logger = logging.getLogger(__name__)

class SecurityMiddleware:
    def __init__(self, app=None):
        self.app = app
        self.blocked_ips = {}
        self.failed_attempts = {}
        self.rate_limits = {}

        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self.app = app
        app.before_request(self.before_request)
        app.after_request(self.after_request)

        # Configurações padrão
        app.config.setdefault('SECURITY_MAX_FAILED_ATTEMPTS', 5)
        app.config.setdefault('SECURITY_BLOCK_DURATION', 3600)
        app.config.setdefault('SECURITY_RATE_LIMIT_REQUESTS', 100)
        app.config.setdefault('SECURITY_RATE_LIMIT_WINDOW', 3600)

        logger.info("SecurityMiddleware inicializado")

    def get_client_ip(self):
        if request.headers.getlist("X-Forwarded-For"):
            ip = request.headers.getlist("X-Forwarded-For")[0].split(',')[0].strip()
        else:
            ip = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
        return ip

    def is_valid_ip(self, ip):
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False

    def is_whitelisted_ip(self, ip):
        whitelist = self.app.config.get('SECURITY_IP_WHITELIST', [
            '127.0.0.1', 'localhost', '::1',
            '192.168.1.109', '192.168.0.0/16', '10.0.0.0/8', '172.16.0.0/12'
        ])
        if ip in whitelist:
            return True
        for addr in whitelist:
            if '/' in addr:
                try:
                    if ipaddress.ip_address(ip) in ipaddress.ip_network(addr, strict=False):
                        return True
                except ValueError:
                    continue
        return False

    def record_failed_attempt(self, ip):
        now = datetime.now()
        if ip not in self.failed_attempts:
            self.failed_attempts[ip] = {'count': 0, 'first_attempt': now, 'last_attempt': now}

        self.failed_attempts[ip]['count'] += 1
        self.failed_attempts[ip]['last_attempt'] = now

        max_attempts = self.app.config.get('SECURITY_MAX_FAILED_ATTEMPTS')
        if self.failed_attempts[ip]['count'] >= max_attempts:
            self.block_ip(ip)
            logger.warning(f"IP {ip} bloqueado após {max_attempts} tentativas falhadas")

    def block_ip(self, ip, duration=None):
        duration = duration or self.app.config.get('SECURITY_BLOCK_DURATION')
        expires = datetime.now() + timedelta(seconds=duration)
        self.blocked_ips[ip] = {
            'blocked_at': datetime.now(),
            'expires': expires,
            'reason': 'Múltiplas tentativas falhadas'
        }
        logger.warning(f"IP {ip} bloqueado até {expires}")

    def is_ip_blocked(self, ip):
        block_info = self.blocked_ips.get(ip)
        if not block_info:
            return False

        expires = block_info.get('expires')
        if not expires or datetime.now() >= expires:
            self.blocked_ips.pop(ip, None)
            logger.info(f"Bloqueio expirado removido para IP {ip}")
            return False

        return True

    def unblock_ip(self, ip):
        if ip in self.blocked_ips:
            del self.blocked_ips[ip]
            logger.info(f"IP {ip} desbloqueado manualmente")

    def clear_failed_attempts(self, ip):
        self.failed_attempts.pop(ip, None)

    def check_rate_limit(self, ip):
        now = datetime.now()
        window = self.app.config['SECURITY_RATE_LIMIT_WINDOW']
        max_requests = self.app.config['SECURITY_RATE_LIMIT_REQUESTS']

        if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
            if getattr(current_user, 'nivel_acesso', '') in [
                'Administrador', 'Gerente', 'Gerente Regional', 'Gestor', 'Agente de suporte']:
                return True

        rate_info = self.rate_limits.setdefault(ip, {'requests': [], 'window_start': now})
        cutoff = now - timedelta(seconds=window)
        rate_info['requests'] = [t for t in rate_info['requests'] if t > cutoff]
        rate_info['requests'].append(now)

        if len(rate_info['requests']) > max_requests:
            logger.warning(f"Rate limit excedido para IP {ip}")
            return False

        return True

    def validate_input(self, data):
        if isinstance(data, str):
            patterns = [
                r'<script[^>]*>.*?</script>',
                r'union\s+select',
                r'drop\s+table',
                r'exec\s*\(',
                r'javascript:',
                r'on\w+\s*='
            ]
            for pattern in patterns:
                if re.search(pattern, data, re.IGNORECASE):
                    logger.warning(f"Entrada suspeita detectada: {pattern}")
                    return False
        return True

    def sanitize_input(self, data):
        if isinstance(data, str):
            data = re.sub(r'<script[^>]*>.*?</script>', '', data, flags=re.IGNORECASE)
            data = re.sub(r'javascript:', '', data, flags=re.IGNORECASE)
            data = re.sub(r'on\w+\s*=', '', data, flags=re.IGNORECASE)
        return data

    def before_request(self):
        client_ip = self.get_client_ip()

        if not self.is_valid_ip(client_ip):
            logger.error(f"IP inválido detectado: {client_ip}")
            return jsonify({'error': 'IP inválido'}), 400

        if self.is_whitelisted_ip(client_ip):
            return

        if self.is_ip_blocked(client_ip):
            expires = self.blocked_ips[client_ip]['expires']
            expires_str = expires.strftime('%Y-%m-%d %H:%M:%S') if expires else 'indefinido'
            return jsonify({
                'error': 'IP bloqueado',
                'message': f'Seu IP foi bloqueado até {expires_str}',
                'expires': expires_str
            }), 403

        if not self.check_rate_limit(client_ip):
            return jsonify({
                'error': 'Rate limit excedido',
                'message': 'Muitas requisições. Tente novamente mais tarde.'
            }), 429

        if request.is_json and request.content_length and request.content_length > 0:
            try:
                data = request.get_json(force=True, silent=True)
                if data and not self.validate_input(json.dumps(data)):
                    return jsonify({'error': 'Dados inválidos'}), 400
            except Exception as e:
                logger.warning(f"Erro ao validar JSON: {e}")

        for key, value in request.args.items():
            if not self.validate_input(value):
                return jsonify({'error': 'Parâmetros inválidos'}), 400

        for key, value in request.form.items():
            if not self.validate_input(value):
                return jsonify({'error': 'Dados do formulário inválidos'}), 400

        g.client_ip = client_ip
        g.security_validated = True

    def after_request(self, response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net "
            "https://cdnjs.cloudflare.com https://cdn.socket.io; style-src 'self' 'unsafe-inline' "
            "https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; img-src 'self' "
            "data: https://images.totalpass.com; connect-src 'self' wss: ws:;"
        )
        return response

    def get_security_status(self):
        return {
            'blocked_ips_count': len(self.blocked_ips),
            'failed_attempts_count': len(self.failed_attempts),
            'rate_limited_ips': len(self.rate_limits),
            'blocked_ips': list(self.blocked_ips.keys()),
            'security_active': True
        }

    def cleanup_expired_blocks(self):
        now = datetime.now()
        expired = [ip for ip, info in self.blocked_ips.items()
                   if info.get('expires') and now >= info['expires']]
        for ip in expired:
            del self.blocked_ips[ip]
            logger.info(f"Bloqueio expirado removido para IP {ip}")
        return len(expired)

# Decorador de segurança
def require_security_validation(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not getattr(g, 'security_validated', False):
            return jsonify({'error': 'Validação de segurança necessária'}), 403
        return f(*args, **kwargs)
    return decorated_function

# Decorador de rate limit (personalizado)
def rate_limit(max_requests=10, window=60):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)

            if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
                if getattr(current_user, 'nivel_acesso', '') in [
                    'Administrador', 'Gerente', 'Gerente Regional', 'Gestor', 'Agente de suporte']:
                    return f(*args, **kwargs)

            return f(*args, **kwargs)
        return decorated_function
    return decorator
