"""
Segurança de sessão aprimorada
"""
import secrets
import hashlib
from datetime import datetime, timedelta
from flask import session, request, current_app, g
from flask_login import current_user

class SessionSecurity:
    def __init__(self):
        # Pega o timeout das configurações de environment (em minutos) e converte para segundos
        import os
        self.permanent_sessions = os.environ.get('SESSION_PERMANENT', 'true').lower() == 'true'
        if self.permanent_sessions:
            self.session_timeout = None
            self.max_session_lifetime = None
        else:
            timeout_minutes = int(os.environ.get('SESSION_TIMEOUT', 15))
            self.session_timeout = timeout_minutes * 60  # Converte minutos para segundos
            self.max_session_lifetime = 28800  # 8 horas
        self.regenerate_interval = 1800  # 30 minutos

    def init_session(self):
        """Inicializa uma nova sessão com dados de segurança"""
        session['_session_id'] = secrets.token_urlsafe(32)
        session['_created_at'] = datetime.utcnow().timestamp()
        session['_last_activity'] = datetime.utcnow().timestamp()
        session['_ip_address'] = self.get_client_ip()
        session['_user_agent_hash'] = self.hash_user_agent()
        session['_regenerated_at'] = datetime.utcnow().timestamp()
        # Tornar sessão permanente (cookie com expiração longa)
        try:
            from flask import session as _sess
            _sess.permanent = True
        except Exception:
            pass

    def validate_session(self):
        """Valida a sessão atual"""
        current_time = datetime.utcnow().timestamp()

        # Verifica se a sessão existe
        if '_session_id' not in session:
            return False

        # Verifica timeout de inatividade (desabilitado se permanente)
        if not self.permanent_sessions and '_last_activity' in session and self.session_timeout is not None:
            last_activity = session['_last_activity']
            if current_time - last_activity > self.session_timeout:
                self.destroy_session()
                return False

        # Verifica tempo máximo de vida da sessão (desabilitado se permanente)
        if not self.permanent_sessions and '_created_at' in session and self.max_session_lifetime is not None:
            created_at = session['_created_at']
            if current_time - created_at > self.max_session_lifetime:
                self.destroy_session()
                return False

        # Verifica se o IP mudou (possível session hijacking)
        if '_ip_address' in session:
            if session['_ip_address'] != self.get_client_ip():
                current_app.logger.warning(
                    f"IP address changed for session {session.get('_session_id', 'unknown')}: "
                    f"{session['_ip_address']} -> {self.get_client_ip()}"
                )
                self.destroy_session()
                return False

        # Verifica se o User-Agent mudou
        if '_user_agent_hash' in session:
            if session['_user_agent_hash'] != self.hash_user_agent():
                current_app.logger.warning(
                    f"User-Agent changed for session {session.get('_session_id', 'unknown')}"
                )
                self.destroy_session()
                return False

        # Regenera ID da sessão periodicamente
        if '_regenerated_at' in session:
            regenerated_at = session['_regenerated_at']
            if current_time - regenerated_at > self.regenerate_interval:
                self.regenerate_session_id()

        # Atualiza última atividade
        session['_last_activity'] = current_time

        return True
    
    def regenerate_session_id(self):
        """Regenera o ID da sessão mantendo os dados"""
        old_session_id = session.get('_session_id', 'unknown')
        session['_session_id'] = secrets.token_urlsafe(32)
        session['_regenerated_at'] = datetime.utcnow().timestamp()
        
        current_app.logger.info(
            f"Session ID regenerated: {old_session_id} -> {session['_session_id']}"
        )
    
    def destroy_session(self):
        """Destrói a sessão atual"""
        session_id = session.get('_session_id', 'unknown')
        session.clear()
        
        current_app.logger.info(f"Session destroyed: {session_id}")
    
    def get_client_ip(self):
        """Obtém o IP do cliente"""
        # Mesmo método do SecurityMiddleware
        headers_to_check = [
            'X-Forwarded-For',
            'X-Real-IP',
            'X-Client-IP',
            'CF-Connecting-IP',
        ]
        
        for header in headers_to_check:
            if header in request.headers:
                ip = request.headers[header].split(',')[0].strip()
                return ip
        
        return request.remote_addr or '127.0.0.1'
    
    def hash_user_agent(self):
        """Cria hash do User-Agent para detecção de mudanças"""
        user_agent = request.headers.get('User-Agent', '')
        return hashlib.sha256(user_agent.encode()).hexdigest()
    
    def is_session_valid(self):
        """Verifica se a sessão atual é válida"""
        return self.validate_session()
    
    def extend_session(self):
        """Estende o tempo de vida da sessão"""
        session['_last_activity'] = datetime.utcnow().timestamp()
    
    def get_session_info(self):
        """Retorna informações da sessão atual"""
        if '_session_id' not in session:
            return None
        
        current_time = datetime.utcnow().timestamp()
        created_at = session.get('_created_at', current_time)
        last_activity = session.get('_last_activity', current_time)
        
        return {
            'session_id': session['_session_id'],
            'created_at': datetime.fromtimestamp(created_at),
            'last_activity': datetime.fromtimestamp(last_activity),
            'ip_address': session.get('_ip_address'),
            'time_remaining': self.session_timeout - (current_time - last_activity),
            'total_lifetime': current_time - created_at
        }
