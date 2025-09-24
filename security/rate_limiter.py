"""
Sistema de Rate Limiting para prevenir ataques de força bruta e DDoS
"""
from datetime import datetime, timedelta
from collections import defaultdict
import time

from flask_login import current_user

class RateLimiter:
    def __init__(self):
        # Armazena tentativas por IP
        self.attempts = defaultdict(list)

        # Configurações de rate limiting por endpoint
        self.limits = {
            'auth.login': {'requests': 5, 'window': 300},           # 5 tentativas em 5 minutos
            'auth.first_login': {'requests': 3, 'window': 300},     # 3 tentativas em 5 minutos
            'ti.abrir_chamado': {'requests': 10, 'window': 60},     # 10 chamados por minuto
            'api_endpoints': {'requests': 50, 'window': 60},        # APIs mais restritivas
            'default': {'requests': 100, 'window': 60}              # 100 requests por minuto (padrão)
        }

    def is_allowed(self, ip, endpoint):
        """Verifica se uma requisição é permitida baseada no rate limiting"""
        current_time = time.time()

        # Ignora limite para usuários com nível alto
        if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
            if hasattr(current_user, 'nivel_acesso') and current_user.nivel_acesso in [
                'Administrador', 'Gerente', 'Gerente Regional', 'Gestor', 'Agente de suporte'
            ]:
                return True

        # Define limite para o endpoint
        limit_config = self.get_limit_config(endpoint)
        max_requests = limit_config['requests']
        window_seconds = limit_config['window']

        key = f"{ip}:{endpoint or 'unknown'}"

        # Limpa tentativas antigas
        self.cleanup_old_attempts(key, current_time, window_seconds)

        # Verifica se excedeu o limite
        if len(self.attempts[key]) >= max_requests:
            return False

        # Registra tentativa atual
        self.attempts[key].append(current_time)
        return True

    def get_limit_config(self, endpoint):
        """Obtém configuração de limite para um endpoint específico"""
        if not endpoint:
            return self.limits['default']

        if endpoint.startswith('api') or '/api/' in str(endpoint):
            return self.limits['api_endpoints']

        return self.limits.get(endpoint, self.limits['default'])

    def cleanup_old_attempts(self, key, current_time, window_seconds):
        """Remove tentativas antigas fora da janela de tempo"""
        cutoff_time = current_time - window_seconds
        self.attempts[key] = [
            attempt_time for attempt_time in self.attempts[key]
            if attempt_time > cutoff_time
        ]

    def get_remaining_attempts(self, ip, endpoint):
        """Retorna o número de tentativas restantes"""
        current_time = time.time()
        limit_config = self.get_limit_config(endpoint)
        max_requests = limit_config['requests']
        window_seconds = limit_config['window']

        key = f"{ip}:{endpoint or 'unknown'}"
        self.cleanup_old_attempts(key, current_time, window_seconds)

        return max(0, max_requests - len(self.attempts[key]))

    def get_reset_time(self, ip, endpoint):
        """Retorna quando o rate limit será resetado"""
        current_time = time.time()
        limit_config = self.get_limit_config(endpoint)
        window_seconds = limit_config['window']

        key = f"{ip}:{endpoint or 'unknown'}"

        if not self.attempts[key]:
            return current_time

        oldest_attempt = min(self.attempts[key])
        return oldest_attempt + window_seconds

    def block_ip_temporarily(self, ip, duration_minutes=15):
        """Bloqueia um IP temporariamente"""
        current_time = time.time()
        block_until = current_time + (duration_minutes * 60)

        # Usa chave especial para bloquear
        key = f"{ip}:blocked"
        self.attempts[key] = [block_until] * 1000  # Garante bloqueio

    def is_ip_blocked(self, ip):
        """Verifica se um IP está bloqueado"""
        current_time = time.time()
        key = f"{ip}:blocked"

        if key in self.attempts:
            future_attempts = [t for t in self.attempts[key] if t > current_time]
            if future_attempts:
                return True
            else:
                del self.attempts[key]

        return False
