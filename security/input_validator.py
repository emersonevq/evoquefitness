"""
Validador de entrada para prevenir ataques de injeção
"""
import re
import html
import json
from urllib.parse import unquote
from flask import current_app

class InputValidator:
    def __init__(self):
        # Padrões maliciosos conhecidos
        self.malicious_patterns = [
            # SQL Injection
            r"(\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b)",
            r"(\b(or|and)\s+\d+\s*=\s*\d+)",
            r"(\b(or|and)\s+['\"]?\w+['\"]?\s*=\s*['\"]?\w+['\"]?)",
            r"(--|#|/\*|\*/)",
            r"(\bxp_cmdshell\b)",
            
            # XSS
            r"(<script[^>]*>.*?</script>)",
            r"(javascript\s*:)",
            r"(vbscript\s*:)",
            r"(on\w+\s*=)",
            r"(<iframe[^>]*>)",
            r"(<object[^>]*>)",
            r"(<embed[^>]*>)",
            r"(<link[^>]*>)",
            r"(<meta[^>]*>)",
            
            # Command Injection
            r"(\b(cmd|powershell|bash|sh|exec|system|eval)\b)",
            r"(\||&|;|\$\(|\`)",
            r"(\.\.\/|\.\.\\)",
            
            # Path Traversal
            r"(\.\.[\\/])",
            r"(%2e%2e[\\/])",
            r"(etc[\\/]passwd)",
            r"(windows[\\/]system32)",
            
            # LDAP Injection
            r"(\*\)|\(\|)",
            r"(\)\(|\&\()",
        ]
        
        # Caracteres perigosos
        self.dangerous_chars = ['<', '>', '"', "'", '&', '\x00', '\r', '\n']
        
        # Extensões de arquivo perigosas
        self.dangerous_extensions = [
            '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js',
            '.jar', '.php', '.asp', '.aspx', '.jsp', '.py', '.rb', '.pl'
        ]
    
    def validate_request(self, request):
        """Valida uma requisição completa"""
        try:
            # Valida URL
            if not self.validate_url(request.url):
                return False
            
            # Valida headers
            if not self.validate_headers(request.headers):
                return False
            
            # Valida query parameters
            if not self.validate_query_params(request.args):
                return False
            
            # Valida dados do formulário
            if request.form and not self.validate_form_data(request.form):
                return False
            
            # Valida dados JSON
            if request.is_json:
                json_data = request.get_json(silent=True)
                if json_data and not self.validate_json_data(json_data):
                    return False
            
            # Valida arquivos enviados
            if request.files and not self.validate_uploaded_files(request.files):
                return False
            
            return True
            
        except Exception as e:
            current_app.logger.error(f"Erro na validação de entrada: {str(e)}")
            return False
    
    def validate_url(self, url):
        """Valida a URL da requisição"""
        # Decodifica URL
        decoded_url = unquote(url)
        
        # Verifica padrões maliciosos
        for pattern in self.malicious_patterns:
            if re.search(pattern, decoded_url, re.IGNORECASE):
                current_app.logger.warning(f"Padrão malicioso detectado na URL: {pattern}")
                return False
        
        # Verifica caracteres perigosos
        for char in self.dangerous_chars:
            if char in decoded_url:
                current_app.logger.warning(f"Caractere perigoso detectado na URL: {char}")
                return False
        
        return True
    
    def validate_headers(self, headers):
        """Valida headers HTTP"""
        dangerous_headers = ['X-Forwarded-Host', 'X-Original-URL', 'X-Rewrite-URL']
        
        for header_name, header_value in headers:
            # Verifica headers perigosos
            if header_name in dangerous_headers:
                if not self.is_safe_string(header_value):
                    return False
            
            # Verifica User-Agent suspeito
            if header_name.lower() == 'user-agent':
                if self.is_suspicious_user_agent(header_value):
                    return False
        
        return True
    
    def validate_query_params(self, args):
        """Valida parâmetros de query string"""
        for key, value in args.items():
            if not self.is_safe_string(key) or not self.is_safe_string(value):
                current_app.logger.warning(f"Parâmetro suspeito detectado: {key}={value}")
                return False
        return True
    
    def validate_form_data(self, form_data):
        """Valida dados de formulário"""
        for key, value in form_data.items():
            if not self.is_safe_string(key) or not self.is_safe_string(value):
                current_app.logger.warning(f"Dados de formulário suspeitos: {key}")
                return False
        return True
    
    def validate_json_data(self, json_data):
        """Valida dados JSON"""
        try:
            json_string = json.dumps(json_data)
            return self.is_safe_string(json_string)
        except Exception:
            return False
    
    def validate_uploaded_files(self, files):
        """Valida arquivos enviados"""
        for field_name, file_obj in files.items():
            if file_obj.filename:
                # Verifica extensão do arquivo
                if any(file_obj.filename.lower().endswith(ext) for ext in self.dangerous_extensions):
                    current_app.logger.warning(f"Extensão de arquivo perigosa: {file_obj.filename}")
                    return False
                
                # Verifica nome do arquivo
                if not self.is_safe_filename(file_obj.filename):
                    return False
        
        return True
    
    def is_safe_string(self, text):
        """Verifica se uma string é segura"""
        if not isinstance(text, str):
            text = str(text)
        
        # Verifica padrões maliciosos
        for pattern in self.malicious_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return False
        
        return True
    
    def is_safe_filename(self, filename):
        """Verifica se um nome de arquivo é seguro"""
        # Caracteres não permitidos em nomes de arquivo
        forbidden_chars = ['<', '>', ':', '"', '|', '?', '*', '\\', '/', '\x00']
        
        for char in forbidden_chars:
            if char in filename:
                return False
        
        # Verifica se não é um nome reservado do Windows
        reserved_names = [
            'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4',
            'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2',
            'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        ]
        
        name_without_ext = filename.split('.')[0].upper()
        if name_without_ext in reserved_names:
            return False
        
        return True
    
    def is_suspicious_user_agent(self, user_agent):
        """Verifica se o User-Agent é suspeito"""
        suspicious_patterns = [
            r'sqlmap',
            r'nikto',
            r'nmap',
            r'masscan',
            r'zap',
            r'burp',
            r'wget',
            r'curl.*bot',
            r'python-requests',
            r'scanner',
            r'exploit',
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, user_agent, re.IGNORECASE):
                return True
        
        return False
    
    def sanitize_input(self, text):
        """Sanitiza entrada de dados"""
        if not isinstance(text, str):
            text = str(text)
        
        # Escapa HTML
        text = html.escape(text)
        
        # Remove caracteres de controle
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        
        return text