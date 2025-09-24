import os
import requests
import logging
from jinja2 import Template
from flask import current_app

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        # Configurações do Microsoft Graph API
        self.client_id = os.getenv('CLIENT_ID')
        self.client_secret = os.getenv('CLIENT_SECRET')
        self.tenant_id = os.getenv('TENANT_ID')
        self.user_id = os.getenv('USER_ID', 'no-reply@academiaevoque.com.br')
        self.from_email = self.user_id

        # URLs da API
        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        self.graph_url = "https://graph.microsoft.com/v1.0"

    def _obter_token_acesso(self):
        """Obtém token de acesso usando Client Credentials Flow"""
        try:
            url = f"{self.authority}/oauth2/v2.0/token"

            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'scope': 'https://graph.microsoft.com/.default',
                'grant_type': 'client_credentials'
            }

            logger.info(f"Solicitando token de acesso para tenant: {self.tenant_id}")
            response = requests.post(url, data=data)

            if response.status_code != 200:
                logger.error(f"Erro na autenticação: Status {response.status_code}, Resposta: {response.text}")
                return None

            token_data = response.json()
            logger.info("Token de acesso obtido com sucesso")
            return token_data.get('access_token')

        except Exception as e:
            logger.error(f"Erro ao obter token de acesso: {str(e)}")
            return None

    def enviar_email(self, destinatario, assunto, corpo_html, corpo_texto=None):
        """Envia um email usando Microsoft Graph API"""
        try:
            # Verificar configurações
            logger.info(f"Tentando enviar email para: {destinatario}")
            logger.info(f"Configurações: client_id={'***' if self.client_id else None}, tenant_id={self.tenant_id}, user_id={self.user_id}")

            if not all([self.client_id, self.client_secret, self.tenant_id]):
                missing = []
                if not self.client_id: missing.append('CLIENT_ID')
                if not self.client_secret: missing.append('CLIENT_SECRET')
                if not self.tenant_id: missing.append('TENANT_ID')
                logger.error(f"Credenciais do Microsoft Graph não configuradas: {', '.join(missing)}")
                return False

            # Obter token de acesso
            access_token = self._obter_token_acesso()
            if not access_token:
                logger.error("Não foi possível obter token de acesso")
                return False

            # Preparar cabeçalhos
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }

            # Estrutura simplificada baseada na documentação oficial
            # https://docs.microsoft.com/en-us/graph/api/user-sendmail
            email_data = {
                'message': {
                    'subject': assunto,
                    'body': {
                        'contentType': 'HTML',
                        'content': corpo_html
                    },
                    'toRecipients': [
                        {
                            'emailAddress': {
                                'address': destinatario
                            }
                        }
                    ]
                }
            }

            # Debug: log da estrutura sendo enviada
            logger.info(f"📤 Estrutura do email: {email_data}")

            # Enviar email
            url = f"{self.graph_url}/users/{self.user_id}/sendMail"
            logger.info(f"🌐 Enviando email via: {url}")

            response = requests.post(url, headers=headers, json=email_data)

            if response.status_code == 202:
                logger.info(f"✅ Email enviado com sucesso para {destinatario}")
                return True
            else:
                logger.error(f"❌ Erro ao enviar email. Status: {response.status_code}")
                logger.error(f"Headers da resposta: {dict(response.headers)}")
                logger.error(f"Corpo da resposta: {response.text}")
                return False

        except Exception as e:
            logger.error(f"❌ Exceção ao enviar email para {destinatario}: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    def notificar_agente_atribuido(self, chamado, agente):
        """Envia notificação quando um agente é atribuído a um chamado"""
        try:
            template_html = Template("""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                    .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                    .header { background-color: #007bff; color: white; padding: 20px; text-align: center; }
                    .content { background-color: #f8f9fa; padding: 20px; }
                    .info-box { background-color: white; padding: 15px; margin: 10px 0; border-left: 4px solid #007bff; }
                    .footer { text-align: center; margin-top: 20px; font-size: 12px; color: #666; }
                    .btn { background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🎯 Agente Atribuído ao Seu Chamado</h1>
                    </div>
                    
                    <div class="content">
                        <p>Olá <strong>{{ chamado.solicitante }}</strong>,</p>
                        
                        <p>Temos uma ótima notícia! Um agente de suporte foi atribuído ao seu chamado:</p>
                        
                        <div class="info-box">
                            <h3>📋 Detalhes do Chamado</h3>
                            <p><strong>Código:</strong> {{ chamado.codigo }}</p>
                            <p><strong>Protocolo:</strong> {{ chamado.protocolo }}</p>
                            <p><strong>Problema:</strong> {{ chamado.problema }}</p>
                            <p><strong>Prioridade:</strong> {{ chamado.prioridade }}</p>
                            <p><strong>Status:</strong> {{ chamado.status }}</p>
                        </div>
                        
                        <div class="info-box">
                            <h3>👨‍💻 Agente Responsável</h3>
                            <p><strong>Nome:</strong> {{ agente.nome }}</p>
                            <p><strong>Nível:</strong> {{ agente.nivel_experiencia|title }}</p>
                            <p><strong>Especialidades:</strong> {{ especialidades_texto }}</p>
                        </div>
                        
                        <div class="info-box">
                            <h3>📞 Próximos Passos</h3>
                            <p>{{ agente.nome }} irá analisar seu chamado e entrará em contato em breve. Você pode acompanhar o progresso do chamado através do sistema.</p>
                            <p>Se tiver alguma dúvida adicional ou informação que possa ajudar na resolução, responda este email.</p>
                        </div>
                        
                        <p style="text-align: center; margin: 30px 0;">
                            <a href="#" class="btn">Acompanhar Chamado</a>
                        </p>
                    </div>
                    
                    <div class="footer">
                        <p>Este é um email automático do sistema de suporte da Evoque Fitness.</p>
                        <p>Data: {{ data_atual }}</p>
                    </div>
                </div>
            </body>
            </html>
            """)
            
            # Preparar dados para o template
            especialidades_texto = ', '.join(agente.especialidades_list) if agente.especialidades_list else 'Suporte Geral'
            
            from database import get_brazil_time
            data_atual = get_brazil_time().strftime('%d/%m/%Y às %H:%M')
            
            corpo_html = template_html.render(
                chamado=chamado,
                agente=agente,
                especialidades_texto=especialidades_texto,
                data_atual=data_atual
            )
            
            # Versão texto
            corpo_texto = f"""
Olá {chamado.solicitante},

Um agente de suporte foi atribuído ao seu chamado!

DETALHES DO CHAMADO:
- Código: {chamado.codigo}
- Protocolo: {chamado.protocolo}
- Problema: {chamado.problema}
- Prioridade: {chamado.prioridade}

AGENTE RESPONSÁVEL:
- Nome: {agente.nome}
- Nível: {agente.nivel_experiencia.title()}
- Especialidades: {especialidades_texto}

{agente.nome} irá analisar seu chamado e entrará em contato em breve.

---
Sistema de Suporte Evoque Fitness
{data_atual}
            """
            
            assunto = f"🎯 Agente Atribuído - Chamado {chamado.codigo}"
            
            return self.enviar_email(chamado.email, assunto, corpo_html, corpo_texto)
            
        except Exception as e:
            logger.error(f"Erro ao gerar notificação de agente atribuído: {str(e)}")
            return False

    def enviar_email_massa(self, destinatarios, assunto, corpo_html, corpo_texto=None):
        """Envia email em massa para múltiplos destinatários"""
        sucessos = 0
        falhas = 0

        for destinatario in destinatarios:
            email = destinatario.get('email') if isinstance(destinatario, dict) else destinatario
            if self.enviar_email(email, assunto, corpo_html, corpo_texto):
                sucessos += 1
            else:
                falhas += 1

        return {'sucessos': sucessos, 'falhas': falhas}

    def enviar_codigo_reset_senha(self, usuario, codigo, token, url_base):
        """Envia email com código de reset de senha"""
        try:
            from database import get_brazil_time

            # Template HTML para reset de senha
            template_html = Template("""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; background-color: #f4f4f4; margin: 0; padding: 20px; }
                    .container { max-width: 600px; margin: 0 auto; background-color: white; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
                    .header { background: linear-gradient(135deg, #FF6200 0%, #1C2526 100%); color: white; padding: 30px 20px; text-align: center; }
                    .header h1 { margin: 0; font-size: 24px; }
                    .content { padding: 30px 20px; }
                    .codigo-box { background-color: #f8f9fa; border: 2px dashed #FF6200; border-radius: 8px; padding: 20px; text-align: center; margin: 20px 0; }
                    .codigo { font-size: 36px; font-weight: bold; color: #FF6200; letter-spacing: 8px; font-family: 'Courier New', monospace; }
                    .info-box { background-color: #e3f2fd; border-left: 4px solid #2196f3; padding: 15px; margin: 20px 0; }
                    .warning-box { background-color: #fff3e0; border-left: 4px solid #ff9800; padding: 15px; margin: 20px 0; }
                    .btn { display: inline-block; background-color: #FF6200; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold; }
                    .btn:hover { background-color: #e55a00; }
                    .footer { background-color: #f8f9fa; padding: 20px; text-align: center; color: #666; font-size: 12px; }
                    .security-note { background-color: #ffebee; border-left: 4px solid #f44336; padding: 15px; margin: 20px 0; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🔐 Recuperação de Senha</h1>
                        <p>Sistema Evoque Fitness</p>
                    </div>

                    <div class="content">
                        <p>Olá <strong>{{ usuario.nome }} {{ usuario.sobrenome }}</strong>,</p>

                        <p>Recebemos uma solicitação para redefinir a senha da sua conta. Use o código abaixo para prosseguir:</p>

                        <div class="codigo-box">
                            <p style="margin: 0; color: #666; font-size: 14px;">SEU CÓDIGO DE VERIFICAÇÃO</p>
                            <div class="codigo">{{ codigo }}</div>
                            <p style="margin: 0; color: #666; font-size: 12px;">Digite este código no sistema</p>
                        </div>

                        <div class="info-box">
                            <h3 style="margin-top: 0;">📋 Instruções:</h3>
                            <ol>
                                <li>Acesse a página de login</li>
                                <li>Clique em "Esqueci minha senha"</li>
                                <li>Digite o código acima quando solicitado</li>
                                <li>Defina sua nova senha</li>
                            </ol>
                        </div>

                        <div class="warning-box">
                            <h3 style="margin-top: 0;">⏰ Importante:</h3>
                            <ul>
                                <li>Este código é válido por <strong>30 minutos</strong></li>
                                <li>Pode ser usado apenas <strong>uma vez</strong></li>
                                <li>Se não foi você quem solicitou, ignore este email</li>
                            </ul>
                        </div>

                        <div style="text-align: center; margin: 30px 0;">
                            <a href="{{ url_base }}auth/reset-senha?token={{ token }}" class="btn">
                                🔗 Ou clique aqui para redefinir
                            </a>
                        </div>

                        <div class="security-note">
                            <h3 style="margin-top: 0;">🛡️ Segurança:</h3>
                            <p>Por questões de segurança, nunca compartilhe este código com outras pessoas. Nossa equipe nunca solicitará este código por telefone ou email.</p>
                        </div>
                    </div>

                    <div class="footer">
                        <p>Este é um email automático do Sistema Evoque Fitness</p>
                        <p>Data: {{ data_atual }}</p>
                        <p>Se você não solicitou esta alteração, pode ignorar este email com segurança.</p>
                    </div>
                </div>
            </body>
            </html>
            """)

            # Preparar dados para o template
            data_atual = get_brazil_time().strftime('%d/%m/%Y às %H:%M')

            corpo_html = template_html.render(
                usuario=usuario,
                codigo=codigo,
                token=token,
                url_base=url_base,
                data_atual=data_atual
            )

            # Versão texto simples
            corpo_texto = f"""
Recuperação de Senha - Sistema Evoque Fitness

Olá {usuario.nome} {usuario.sobrenome},

Recebemos uma solicitação para redefinir a senha da sua conta.

SEU CÓDIGO DE VERIFICAÇÃO: {codigo}

INSTRUÇÕES:
1. Acesse a página de login
2. Clique em "Esqueci minha senha"
3. Digite o código: {codigo}
4. Defina sua nova senha

IMPORTANTE:
- Este código é válido por 30 minutos
- Pode ser usado apenas uma vez
- Se não foi você quem solicitou, ignore este email

Link alternativo: {url_base}auth/reset-senha?token={token}

---
Sistema Evoque Fitness
{data_atual}
            """

            assunto = f"🔐 Código de Recuperação de Senha - {codigo}"

            return self.enviar_email(usuario.email, assunto, corpo_html, corpo_texto)

        except Exception as e:
            logger.error(f"Erro ao enviar email de reset de senha: {str(e)}")
            return False

# Instância global do serviço
email_service = EmailService()
