"""
Sistema de auditoria e logging de segurança
"""
import json
import logging
import os
from datetime import datetime
from flask import request, current_app, g
from flask_login import current_user

class AuditLogger:
    def __init__(self, log_dir='logs', log_file='security.log'):
        # Configura caminhos absolutos para os logs
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.log_dir = os.path.join(self.base_dir, log_dir)
        self.log_file = os.path.join(self.log_dir, log_file)
        
        # Cria o diretório se não existir
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Configura logger específico para segurança
        self.security_logger = logging.getLogger('security')
        self.security_logger.setLevel(logging.INFO)
        
        # Evita adicionar múltiplos handlers
        if not self.security_logger.handlers:
            handler = logging.FileHandler(self.log_file)
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.security_logger.addHandler(handler)
    
    def log_security_event(self, event_type, message, ip_address=None, url=None, extra_data=None):
        """Registra um evento de segurança"""
        try:
            log_entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'event_type': event_type,
                'message': message,
                'ip_address': ip_address or getattr(g, 'client_ip', 'unknown'),
                'url': url or (request.url if request else 'unknown'),
                'user_agent': request.headers.get('User-Agent', 'unknown') if request else 'unknown',
                'user_id': current_user.id if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated else None,
                'username': current_user.usuario if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated else None,
                'extra_data': extra_data or {}
            }
            
            self.security_logger.warning(json.dumps(log_entry, ensure_ascii=False))
            
        except Exception as e:
            # Fallback para logging básico se houver erro
            try:
                if hasattr(current_app, 'logger'):
                    current_app.logger.error(f"Erro ao registrar evento de segurança: {str(e)}", exc_info=True)
                else:
                    print(f"Erro ao registrar evento de segurança: {str(e)}")
            except:
                print(f"Erro crítico no sistema de auditoria: {str(e)}")
    
    def log_request(self, request, response):
        """Registra requisições importantes para auditoria"""
        try:
            # Só registra requisições importantes
            if not self.should_log_request(request):
                return
            
            log_entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'method': request.method,
                'url': request.url,
                'ip_address': getattr(g, 'client_ip', request.remote_addr),
                'user_agent': request.headers.get('User-Agent', ''),
                'user_id': current_user.id if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated else None,
                'username': current_user.usuario if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated else None,
                'status_code': response.status_code,
                'content_length': response.content_length,
                'referrer': request.headers.get('Referer', ''),
            }
            
            # Adiciona dados específicos para certas operações
            if request.endpoint:
                log_entry['endpoint'] = request.endpoint
                
                # Log específico para operações críticas
                if any(critical in request.endpoint for critical in ['login', 'logout', 'delete', 'create']):
                    log_entry['critical_operation'] = True
            
            self.security_logger.info(json.dumps(log_entry, ensure_ascii=False))
            
        except Exception as e:
            try:
                if hasattr(current_app, 'logger'):
                    current_app.logger.error(f"Erro ao registrar requisição: {str(e)}", exc_info=True)
                else:
                    print(f"Erro ao registrar requisição: {str(e)}")
            except:
                print(f"Erro crítico no log de requisições: {str(e)}")
    
    def should_log_request(self, request):
        """Determina se uma requisição deve ser registrada"""
        # Sempre registra operações críticas
        critical_methods = ['POST', 'PUT', 'DELETE', 'PATCH']
        if request.method in critical_methods:
            return True
        
        # Registra acessos a endpoints administrativos
        if request.endpoint and any(admin in request.endpoint for admin in ['admin', 'painel', 'manage']):
            return True
        
        # Registra tentativas de acesso a arquivos sensíveis
        sensitive_paths = ['/config', '/admin', '/.env', '/backup']
        if any(path in request.path for path in sensitive_paths):
            return True
        
        return False
    
    def log_login_attempt(self, username, success, ip_address, reason=None):
        """Registra tentativas de login"""
        event_type = 'LOGIN_SUCCESS' if success else 'LOGIN_FAILED'
        message = f"Tentativa de login para usuário '{username}'"
        
        if not success and reason:
            message += f" - Motivo: {reason}"
        
        extra_data = {
            'username': username,
            'success': success,
            'reason': reason
        }
        
        self.log_security_event(event_type, message, ip_address, extra_data=extra_data)
    
    def log_permission_denied(self, username, resource, ip_address):
        """Registra tentativas de acesso negado"""
        message = f"Acesso negado para usuário '{username}' ao recurso '{resource}'"
        
        extra_data = {
            'username': username,
            'resource': resource
        }
        
        self.log_security_event('ACCESS_DENIED', message, ip_address, extra_data=extra_data)
    
    def log_data_modification(self, table_name, operation, record_id, old_data=None, new_data=None):
        """Registra modificações de dados importantes"""
        message = f"Operação {operation} na tabela {table_name}"
        
        extra_data = {
            'table': table_name,
            'operation': operation,
            'record_id': record_id,
            'old_data': old_data,
            'new_data': new_data
        }
        
        self.log_security_event('DATA_MODIFICATION', message, extra_data=extra_data)