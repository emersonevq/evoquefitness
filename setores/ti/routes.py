import os
import os
import random
import string
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify, current_app, flash, redirect, url_for
from flask_login import LoginManager, login_required, current_user
from auth.auth_helpers import setor_required
from database import db, Chamado, User, Unidade, ProblemaReportado, ItemInternet, seed_unidades, get_brazil_time
import requests
from msal import ConfidentialClientApplication

ti_bp = Blueprint('ti', __name__, template_folder='templates')

# Configurações do Microsoft Graph API obtidas das variáveis de ambiente
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
TENANT_ID = os.getenv('TENANT_ID')
USER_ID = os.getenv('USER_ID')
EMAIL_TI = os.getenv('EMAIL_TI', 'ti@academiaevoque.com.br')

# Verificar se as variáveis de ambiente estão configuradas (não obrigatórias para desenvolvimento)
EMAIL_ENABLED = all([CLIENT_ID, CLIENT_SECRET, TENANT_ID, USER_ID])

if EMAIL_ENABLED:
    SCOPES = ["https://graph.microsoft.com/.default"]
    ENDPOINT = f"https://graph.microsoft.com/v1.0/users/{USER_ID}/sendMail"
    print("✅ Configurações de email Microsoft Graph carregadas")
else:
    SCOPES = []
    ENDPOINT = None
    print("⚠️  Email desabilitado: Variáveis de ambiente do Microsoft Graph não configuradas")

def get_access_token():
    if not EMAIL_ENABLED:
        current_app.logger.warning("⚠️  Tentativa de obter token com email desabilitado")
        return None

    try:
        current_app.logger.info(f"🔄 Configurando MSAL Client...")
        current_app.logger.info(f"🔑 CLIENT_ID: {CLIENT_ID[:8]}...")
        current_app.logger.info(f"🏢 TENANT_ID: {TENANT_ID}")
        current_app.logger.info(f"🌐 Authority: https://login.microsoftonline.com/{TENANT_ID}")

        app = ConfidentialClientApplication(
            client_id=CLIENT_ID,
            client_credential=CLIENT_SECRET,
            authority=f"https://login.microsoftonline.com/{TENANT_ID}"
        )

        current_app.logger.info(f"📋 Scopes: {SCOPES}")
        current_app.logger.info("🔄 Solicitando token...")

        result = app.acquire_token_for_client(scopes=SCOPES)

        current_app.logger.info(f"📥 Resultado recebido: {list(result.keys())}")

        if "access_token" in result:
            current_app.logger.info("✅ Token obtido com sucesso!")
            return result["access_token"]
        else:
            current_app.logger.error(f"❌ Erro ao obter token:")
            current_app.logger.error(f"   - Error: {result.get('error', 'N/A')}")
            current_app.logger.error(f"   - Error Description: {result.get('error_description', 'N/A')}")
            current_app.logger.error(f"   - Error Codes: {result.get('error_codes', 'N/A')}")
            current_app.logger.error(f"   - Correlation ID: {result.get('correlation_id', 'N/A')}")
            return None
    except Exception as e:
        current_app.logger.error(f"❌ Exceção ao obter token: {str(e)}")
        import traceback
        current_app.logger.error(f"🔍 Stack trace: {traceback.format_exc()}")
        return None

def testar_configuracao_email():
    """Função para testar se as configurações de e-mail estão funcionando"""
    try:
        current_app.logger.info("🔍 Testando configurações de e-mail...")
        current_app.logger.info(f"EMAIL_ENABLED: {EMAIL_ENABLED}")
        current_app.logger.info(f"CLIENT_ID presente: {'Sim' if CLIENT_ID else 'Não'}")
        current_app.logger.info(f"CLIENT_SECRET presente: {'Sim' if CLIENT_SECRET else 'Não'}")
        current_app.logger.info(f"TENANT_ID: {TENANT_ID}")
        current_app.logger.info(f"USER_ID: {USER_ID}")
        current_app.logger.info(f"EMAIL_TI: {EMAIL_TI}")

        # Verificar se todas as variáveis estão presentes
        if not all([CLIENT_ID, CLIENT_SECRET, TENANT_ID, USER_ID]):
            current_app.logger.error("❌ Variáveis de ambiente obrigatórias não configuradas")
            missing = []
            if not CLIENT_ID: missing.append("CLIENT_ID")
            if not CLIENT_SECRET: missing.append("CLIENT_SECRET")
            if not TENANT_ID: missing.append("TENANT_ID")
            if not USER_ID: missing.append("USER_ID")
            current_app.logger.error(f"❌ Variáveis faltando: {', '.join(missing)}")
            return False

        if EMAIL_ENABLED:
            current_app.logger.info("🔄 Tentando obter token...")
            token = get_access_token()
            if token:
                current_app.logger.info("✅ Token obtido com sucesso! Sistema de e-mail funcionando")
                current_app.logger.info(f"🔑 Token: {token[:20]}...")
                return True
            else:
                current_app.logger.error("❌ Falha ao obter token")
                return False
        else:
            current_app.logger.warning("⚠️ Sistema de e-mail desabilitado")
            return False
    except Exception as e:
        current_app.logger.error(f"❌ Erro ao testar configurações: {str(e)}")
        import traceback
        current_app.logger.error(f"🔍 Stack trace: {traceback.format_exc()}")
        return False

def enviar_email(assunto, corpo, destinatarios=None):
    if destinatarios is None:
        destinatarios = [EMAIL_TI]

    current_app.logger.info(f"📧 === INICIANDO ENVIO DE EMAIL ===")
    current_app.logger.info(f"📧 Destinatários: {destinatarios}")
    current_app.logger.info(f"📋 Assunto: {assunto}")
    current_app.logger.info(f"📄 Tamanho do corpo: {len(corpo)} caracteres")

    token = get_access_token()
    if not token:
        current_app.logger.error("❌ Token não obtido, não é possível enviar e-mail")
        return False

    current_app.logger.info(f"🔑 Token obtido: {token[:20]}...")
    current_app.logger.info(f"🌐 Endpoint: {ENDPOINT}")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    email_data = {
        "message": {
            "subject": assunto,
            "body": {
                "contentType": "Text",
                "content": corpo
            },
            "toRecipients": [
                {"emailAddress": {"address": addr}} for addr in destinatarios
            ]
        },
        "saveToSentItems": "false"
    }

    current_app.logger.info(f"�� Email data preparado para: {[r['emailAddress']['address'] for r in email_data['message']['toRecipients']]}")

    try:
        response = requests.post(ENDPOINT, headers=headers, json=email_data)
        if response.status_code == 202:
            current_app.logger.info("���� E-mail enviado com sucesso!")
            return True
        else:
            current_app.logger.error(f"❌ Falha ao enviar e-mail. Status: {response.status_code}")
            return False
    except Exception as e:
        current_app.logger.error(f"❌ Erro na requisição: {str(e)}")
        return False

def gerar_codigo_chamado():
    ultimo_chamado = Chamado.query.order_by(Chamado.id.desc()).first()
    if ultimo_chamado and ultimo_chamado.codigo.startswith("EVQ-"):
        try:
            ultimo_numero = int(ultimo_chamado.codigo.split("-")[1])
        except:
            ultimo_numero = 0
    else:
        ultimo_numero = 0
    
    novo_numero = ultimo_numero + 1
    numero_formatado = str(novo_numero).zfill(4)
    return f"EVQ-{numero_formatado}"

def gerar_protocolo():
    # Usar horário do Brasil para gerar protocolo
    data_brazil = get_brazil_time()
    data_str = data_brazil.strftime("%Y%m%d")
    count = Chamado.query.filter(Chamado.protocolo.like(f"{data_str}-%")).count()
    novo_num = count + 1
    return f"{data_str}-{novo_num}"

@ti_bp.route('/test-email')
@login_required
@setor_required('ti')
def test_email():
    """Rota para testar envio de e-mail"""
    try:
        # Testar configurações
        config_ok = testar_configuracao_email()

        if config_ok:
            # Tentar enviar e-mail de teste
            assunto = "Teste de E-mail - Sistema Evoque"
            corpo = f"""
Este é um e-mail de teste do sistema Evoque Fitness.

Dados do teste:
- Data/Hora: {get_brazil_time().strftime('%d/%m/%Y %H:%M:%S')}
- Usuário: {current_user.nome} {current_user.sobrenome}
- E-mail do usuário: {current_user.email}

Se você recebeu este e-mail, o sistema está funcionando corretamente!

---
Sistema de Suporte TI - Evoque Fitness
"""

            resultado = enviar_email(assunto, corpo, [current_user.email])

            if resultado:
                return jsonify({
                    'success': True,
                    'message': f'E-mail de teste enviado com sucesso para {current_user.email}'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Falha ao enviar e-mail de teste'
                })
        else:
            return jsonify({
                'success': False,
                'message': 'Configurações de e-mail não estão funcionando'
            })

    except Exception as e:
        current_app.logger.error(f"Erro no teste de e-mail: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro durante teste: {str(e)}'
        })

@ti_bp.route('/')
@login_required
@setor_required('ti')
def index():
    try:
        # Buscar chamados do usuário logado usando o relacionamento
        meus_chamados = Chamado.query.filter_by(usuario_id=current_user.id).order_by(Chamado.data_abertura.desc()).all()
        
        # Se não encontrar chamados pelo usuario_id, buscar pelo email (fallback para dados antigos)
        if not meus_chamados:
            meus_chamados = Chamado.query.filter_by(email=current_user.email).order_by(Chamado.data_abertura.desc()).all()
            
            # Vincular esses chamados ao usuário atual
            for chamado in meus_chamados:
                if not chamado.usuario_id:
                    chamado.usuario_id = current_user.id
            
            if meus_chamados:
                db.session.commit()
        
        return render_template('index.html', meus_chamados=meus_chamados)
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar chamados do usuário: {str(e)}")
        flash("Ocorreu um erro ao carregar seu histórico de chamados.", "danger")
        return render_template('index.html', meus_chamados=[])

@ti_bp.route('/painel')
@login_required
@setor_required('ti')
def painel():
    if not current_user.tem_permissao('Administrador'):
        flash('Você não tem permissão para acessar o painel administrativo.', 'danger')
        return redirect(url_for('ti.index'))
    return render_template('painel.html')

@ti_bp.route('/painel-agente')
@login_required
@setor_required('ti')
def painel_agente():
    """Painel específico para agentes de suporte"""
    # Verificar se o usuário é um agente de suporte
    from database import AgenteSuporte
    agente = AgenteSuporte.query.filter_by(usuario_id=current_user.id, ativo=True).first()

    if not agente:
        flash('Você não está registrado como agente de suporte.', 'warning')
        return redirect(url_for('ti.index'))

    return render_template('painel_agente.html', agente=agente)

@ti_bp.route('/abrir-chamado', methods=['GET', 'POST'])
@login_required
@setor_required('ti')
def abrir_chamado():
    try:
        unidades = Unidade.query.order_by(Unidade.nome).all()
        problemas = ProblemaReportado.query.filter_by(ativo=True).order_by(ProblemaReportado.nome).all()
        # Filtro ativo opcional para ItemInternet (pode não existir em dados antigos)
        try:
            itens_internet = ItemInternet.query.filter_by(ativo=True).order_by(ItemInternet.nome).all()
        except:
            itens_internet = ItemInternet.query.order_by(ItemInternet.nome).all()

        # Log de debug
        current_app.logger.info(f"📊 Dados carregados - Unidades: {len(unidades)}, Problemas: {len(problemas)}, Itens: {len(itens_internet)}")

        if not unidades:
            current_app.logger.info("🔄 Nenhuma unidade encontrada, executando seed_unidades()")
            seed_unidades()
            unidades = Unidade.query.order_by(Unidade.nome).all()
            problemas = ProblemaReportado.query.filter_by(ativo=True).order_by(ProblemaReportado.nome).all()
            # Filtro ativo opcional para ItemInternet (pode não existir em dados antigos)
            try:
                itens_internet = ItemInternet.query.filter_by(ativo=True).order_by(ItemInternet.nome).all()
            except:
                itens_internet = ItemInternet.query.order_by(ItemInternet.nome).all()
            current_app.logger.info(f"📊 Após seed - Unidades: {len(unidades)}, Problemas: {len(problemas)}, Itens: {len(itens_internet)}")
            
        if request.method == 'POST':
            try:
                codigo_gerado = gerar_codigo_chamado()
                protocolo_gerado = gerar_protocolo()

                dados_chamado = {
                    'nome_solicitante': request.form['nome_solicitante'],
                    'cargo': request.form['cargo'],
                    'email': request.form['email'],
                    'telefone': request.form['telefone'],
                    'unidade_id': request.form['unidade'],
                    'problema_id': request.form['problema'],
                    'internet_item_id': request.form.get('internet_item', ''),
                    'descricao': request.form.get('descricao', ''),
                    'data_visita_str': request.form.get('data_visita', '').strip(),
                    'prioridade': request.form.get('prioridade', 'Normal')
                }

                unidade_obj = Unidade.query.get(dados_chamado['unidade_id'])
                problema_obj = ProblemaReportado.query.get(dados_chamado['problema_id'])
                
                if not unidade_obj or not problema_obj:
                    return jsonify({
                        'status': 'error',
                        'message': 'Unidade ou problema inválido.'
                    }), 400

                unidade_nome_completo = unidade_obj.nome
                problema_nome = problema_obj.nome
                
                internet_item_nome = ""
                if dados_chamado['internet_item_id']:
                    item_obj = ItemInternet.query.get(dados_chamado['internet_item_id'])
                    internet_item_nome = item_obj.nome if item_obj else ""

                data_visita = None
                if dados_chamado['data_visita_str']:
                    try:
                        data_visita = datetime.strptime(dados_chamado['data_visita_str'], '%Y-%m-%d').date()
                    except ValueError:
                        return jsonify({
                            'status': 'error',
                            'message': 'Formato de data inválido. Use AAAA-MM-DD.'
                        }), 400

                descricao_completa = dados_chamado['descricao']
                if problema_nome == 'Internet' and internet_item_nome:
                    descricao_completa = f"Item: {internet_item_nome}\nDescrição: {descricao_completa}"

                # Usar horário do Brasil para data de abertura
                data_abertura_brazil = get_brazil_time()

                novo_chamado = Chamado(
                    codigo=codigo_gerado,
                    protocolo=protocolo_gerado,
                    solicitante=dados_chamado['nome_solicitante'],
                    cargo=dados_chamado['cargo'],
                    email=dados_chamado['email'],
                    telefone=dados_chamado['telefone'],
                    unidade=unidade_nome_completo,
                    problema=problema_nome,
                    internet_item=internet_item_nome,
                    descricao=descricao_completa,
                    data_visita=data_visita,
                    status='Aberto',
                    prioridade=dados_chamado['prioridade'],
                    data_abertura=data_abertura_brazil.replace(tzinfo=None),
                    usuario_id=current_user.id  # Vincular ao usuário logado
                )

                db.session.add(novo_chamado)
                db.session.commit()

                # Registrar evento de criação na linha do tempo
                try:
                    from database import ChamadoTimelineEvent
                    evento_criacao = ChamadoTimelineEvent(
                        chamado_id=novo_chamado.id,
                        usuario_id=current_user.id,
                        tipo='created',
                        descricao='Chamado criado',
                        status_anterior=None,
                        status_novo='Aberto'
                    )
                    db.session.add(evento_criacao)
                    db.session.commit()
                except Exception as e:
                    current_app.logger.warning(f"Falha ao registrar timeline de criação: {str(e)}")

                # Processar anexos enviados
                try:
                    from werkzeug.utils import secure_filename
                    from security.security_config import SecurityConfig
                    arquivos = request.files.getlist('anexos') or request.files.getlist('anexos[]')
                    if arquivos:
                        base_dir = os.path.join('static', 'uploads', 'chamados', codigo_gerado)
                        os.makedirs(base_dir, exist_ok=True)
                        for arquivo in arquivos:
                            if not arquivo or arquivo.filename == '':
                                continue
                            filename = secure_filename(arquivo.filename)
                            ext = os.path.splitext(filename)[1].lower()
                            if SecurityConfig.UPLOAD_EXTENSIONS and ext not in SecurityConfig.UPLOAD_EXTENSIONS:
                                continue
                            caminho = os.path.join(base_dir, filename)
                            arquivo.save(caminho)
                            tamanho = os.path.getsize(caminho) if os.path.exists(caminho) else None

                            from database import AnexoArquivo, ChamadoTimelineEvent
                            anexo = AnexoArquivo(
                                chamado_id=novo_chamado.id,
                                nome_original=arquivo.filename,
                                caminho_arquivo=caminho.replace('\\', '/'),
                                mime_type=arquivo.mimetype,
                                tamanho_bytes=tamanho,
                                usuario_id=current_user.id
                            )
                            db.session.add(anexo)
                            db.session.flush()

                            # Registrar timeline do anexo recebido na abertura
                            try:
                                evento_anexo = ChamadoTimelineEvent(
                                    chamado_id=novo_chamado.id,
                                    usuario_id=current_user.id,
                                    tipo='attachment_received',
                                    descricao=f'Anexo recebido na abertura: {arquivo.filename}',
                                    anexo_id=anexo.id,
                                    metadados=json.dumps({
                                        'arquivo_nome': arquivo.filename,
                                        'mime_type': arquivo.mimetype,
                                        'tamanho_bytes': tamanho,
                                        'origem': 'solicitante'
                                    })
                                )
                                db.session.add(evento_anexo)
                            except Exception as e:
                                current_app.logger.warning(f"Falha ao registrar timeline de anexo: {str(e)}")
                        db.session.commit()
                except Exception as e:
                    current_app.logger.error(f"Erro ao salvar anexos do chamado {codigo_gerado}: {str(e)}")
                    db.session.rollback()

                if hasattr(current_app, 'socketio'):
                    current_app.socketio.emit('novo_chamado', {
                        'id': novo_chamado.id,
                        'codigo': codigo_gerado,
                        'protocolo': protocolo_gerado,
                        'solicitante': dados_chamado['nome_solicitante'],
                        'problema': problema_nome,
                        'unidade': unidade_nome_completo,
                        'status': 'Aberto',
                        'data_abertura': data_abertura_brazil.isoformat(),
                        'prioridade': dados_chamado['prioridade']
                    })

                visita_tecnica_texto = (
                    f"Sim, agendada para {data_visita.strftime('%d/%m/%Y')}"
                    if data_visita else "Não requisitada"
                )

                internet_item_texto = (
                    f"\nItem de Internet: {internet_item_nome}"
                    if problema_nome == 'Internet' and internet_item_nome
                    else ""
                )

                corpo_email = f"""
Seu chamado foi registrado com sucesso! Aqui estão os detalhes:

Chamado: {codigo_gerado}
Protocolo: {protocolo_gerado}
Prioridade: {dados_chamado['prioridade']}
Nome do solicitante: {dados_chamado['nome_solicitante']}
Cargo: {dados_chamado['cargo']}
Unidade: {unidade_nome_completo}
E-mail: {dados_chamado['email']}
Telefone: {dados_chamado['telefone']}
Problema reportado: {problema_nome}{internet_item_texto}
Descrição: {dados_chamado['descricao']}
Visita técnica: {visita_tecnica_texto}

⚠️ Caso precise acompanhar o status do chamado, utilize o código acima.

Atenciosamente,
Suporte Evoque!

Por favor, não responda este e-mail, essa é uma mensagem automática!
"""
                destinatarios = [dados_chamado['email'], EMAIL_TI]
                assunto_email = f"ACADEMIA EVOQUE - CHAMADO #{codigo_gerado}"

                sucesso_email = enviar_email(assunto_email, corpo_email, destinatarios)
                if not sucesso_email:
                    current_app.logger.warning(f"Falha ao enviar e-mail para o chamado {codigo_gerado}")

                return jsonify({
                    'status': 'success',
                    'codigo_chamado': codigo_gerado,
                    'protocolo_chamado': protocolo_gerado,
                    'notificacao_data': {
                        'id': novo_chamado.id,
                        'codigo': codigo_gerado,
                        'solicitante': dados_chamado['nome_solicitante'],
                        'problema': problema_nome,
                        'data_abertura': data_abertura_brazil.strftime('%d/%m/%Y %H:%M:%S')
                    }
                })

            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Erro ao salvar chamado: {str(e)}")
                return jsonify({
                    'status': 'error',
                    'message': 'Erro ao abrir chamado. Tente novamente.'
                }), 500

        # Pré-preencher dados do usuário logado
        usuario_data = {
            'nome': f"{current_user.nome} {current_user.sobrenome}",
            'email': current_user.email
        }

        return render_template('abrir_chamado.html', 
                             unidades=unidades, 
                             problemas=problemas, 
                             itens_internet=itens_internet,
                             usuario_data=usuario_data)
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao processar página de chamados: {str(e)}")
        return render_template('abrir_chamado.html', unidades=[], problemas=[], itens_internet=[], 
                              error_message="Erro ao carregar unidades. Por favor, tente novamente mais tarde.")

@ti_bp.route('/api/meus-chamados')
@login_required
@setor_required('ti')
def api_meus_chamados():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 5  # 5 itens por página
        
        # Buscar chamados do usuário logado com paginação
        chamados_query = Chamado.query.filter_by(usuario_id=current_user.id).order_by(Chamado.data_abertura.desc())
        
        # Se não encontrar pelo usuario_id, buscar pelo email (fallback)
        if chamados_query.count() == 0:
            chamados_query = Chamado.query.filter_by(email=current_user.email).order_by(Chamado.data_abertura.desc())
        
        chamados_paginados = chamados_query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        chamados_list = []
        for chamado in chamados_paginados.items:
            data_abertura_brazil = chamado.get_data_abertura_brazil()
            anexos_payload = []
            try:
                for a in getattr(chamado, 'anexos', []) or []:
                    anexos_payload.append({
                        'id': a.id,
                        'nome': a.nome_original,
                        'url': a.url_publica() if hasattr(a, 'url_publica') else ('/' + a.caminho_arquivo if a.caminho_arquivo else None),
                        'tamanho_kb': round((a.tamanho_bytes or 0) / 1024)
                    })
            except Exception:
                anexos_payload = []

            chamados_list.append({
                'id': chamado.id,
                'codigo': chamado.codigo,
                'protocolo': chamado.protocolo,
                'solicitante': chamado.solicitante,
                'problema': chamado.problema,
                'unidade': chamado.unidade,
                'status': chamado.status,
                'prioridade': chamado.prioridade,
                'data_abertura': data_abertura_brazil.strftime('%d/%m/%Y %H:%M') if data_abertura_brazil else 'Não informado',
                'descricao': chamado.descricao or 'Sem descrição',
                'data_visita': chamado.data_visita.strftime('%d/%m/%Y') if chamado.data_visita else None,
                'anexos': anexos_payload
            })
        
        return jsonify({
            'chamados': chamados_list,
            'pagination': {
                'page': chamados_paginados.page,
                'pages': chamados_paginados.pages,
                'per_page': chamados_paginados.per_page,
                'total': chamados_paginados.total,
                'has_next': chamados_paginados.has_next,
                'has_prev': chamados_paginados.has_prev
            }
        })
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar chamados do usuário: {str(e)}")
        return jsonify({'error': 'Erro interno no servidor'}), 500

@ti_bp.route('/ver-meus-chamados', methods=['GET', 'POST'])
@login_required
@setor_required('ti')
def ver_meus_chamados():
    if request.method == 'POST':
        codigo = request.form.get('codigo', '').strip().upper()
        
        if not codigo:
            return jsonify({
                'status': 'error',
                'message': 'Código não informado.'
            }), 400

        if not codigo.startswith('EVQ-'):
            codigo = f"EVQ-{codigo.zfill(4)}"

        try:
            # Buscar chamado do usuário logado
            chamado = Chamado.query.filter_by(
                codigo=codigo, 
                usuario_id=current_user.id
            ).first()
            
            # Se não encontrar pelo usuario_id, buscar pelo email (fallback)
            if not chamado:
                chamado = Chamado.query.filter_by(
                    codigo=codigo,
                    email=current_user.email
                ).first()
            
            if not chamado:
                return jsonify({
                    'status': 'error',
                    'message': 'Chamado não encontrado ou você não tem permissão para visualizá-lo.'
                }), 404

            # Converter data de abertura para timezone do Brasil
            data_abertura_brazil = chamado.get_data_abertura_brazil()
            data_abertura_str = data_abertura_brazil.strftime('%d/%m/%Y %H:%M') if data_abertura_brazil else 'Não informado'

            resultado = {
                'tipo': 'chamado',
                'codigo_chamado': chamado.codigo,
                'protocolo': chamado.protocolo,
                'prioridade': chamado.prioridade,
                'status': chamado.status,
                'nome_solicitante': chamado.solicitante,
                'email': chamado.email or 'Não informado',
                'cargo': chamado.cargo,
                'telefone': chamado.telefone or 'Não informado',
                'unidade': chamado.unidade or 'Não informado',
                'problema_reportado': chamado.problema,
                'internet_item': chamado.internet_item or 'Não informado',
                'descricao': chamado.descricao or 'Sem descrição',
                'data_abertura': data_abertura_str,
                'visita_tecnica': 'Sim' if chamado.data_visita else 'Não requisitada',
                'data_visita_tecnica': chamado.data_visita.strftime('%d/%m/%Y') if chamado.data_visita else 'Não agendada',
            }
            
            return jsonify({
                'status': 'success',
                'resultado': resultado
            })

        except Exception as e:
            current_app.logger.error(f"Erro ao buscar chamado: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': 'Erro interno no servidor.'
            }), 500

    return render_template('ver_meus_chamados.html')

@ti_bp.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@ti_bp.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500

from .painel import painel_bp
ti_bp.register_blueprint(painel_bp, url_prefix='/painel')

# Registrar blueprints de agentes, grupos, auditoria e rotas avançadas
from .agentes import agentes_bp
from .grupos import grupos_bp
from .auditoria import auditoria_bp
from .rotas import rotas_bp
from .agente_api import agente_api_bp
ti_bp.register_blueprint(agentes_bp, url_prefix='/painel')
ti_bp.register_blueprint(grupos_bp, url_prefix='/painel')
ti_bp.register_blueprint(auditoria_bp, url_prefix='/painel')
ti_bp.register_blueprint(rotas_bp, url_prefix='/painel')
ti_bp.register_blueprint(agente_api_bp, url_prefix='/painel')

@ti_bp.route('/debug/dados')
@login_required
@setor_required('ti')
def debug_dados():
    """Rota de debug para verificar dados do banco"""
    try:
        unidades = Unidade.query.all()
        problemas = ProblemaReportado.query.all()
        itens_internet = ItemInternet.query.all()

        dados_debug = {
            'unidades': {
                'total': len(unidades),
                'lista': [{'id': u.id, 'nome': u.nome} for u in unidades[:5]]  # Primeiras 5
            },
            'problemas': {
                'total': len(problemas),
                'lista': [{'id': p.id, 'nome': p.nome, 'prioridade': p.prioridade_padrao, 'ativo': p.ativo} for p in problemas]
            },
            'itens_internet': {
                'total': len(itens_internet),
                'lista': [{'id': i.id, 'nome': i.nome, 'ativo': i.ativo} for i in itens_internet]
            }
        }

        return jsonify(dados_debug)

    except Exception as e:
        return jsonify({'error': str(e)})

@ti_bp.route('/api/chamados/recentes')
@login_required
@setor_required('ti')
def chamados_recentes():
    try:
        cinco_minutos_atras = get_brazil_time() - timedelta(minutes=5)
        chamados_recentes = Chamado.query.filter(
            Chamado.data_abertura >= cinco_minutos_atras.replace(tzinfo=None)
        ).order_by(Chamado.data_abertura.desc()).all()
        
        chamados_list = []
        for c in chamados_recentes:
            data_abertura_brazil = c.get_data_abertura_brazil()
            chamados_list.append({
                'id': c.id,
                'codigo': c.codigo,
                'solicitante': c.solicitante,
                'problema': c.problema,
                'data_abertura': data_abertura_brazil.strftime('%d/%m/%Y %H:%M:%S') if data_abertura_brazil else None,
                'status': c.status
            })
        
        return jsonify(chamados_list)
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar chamados recentes: {str(e)}")
        return jsonify({'error': 'Erro interno no servidor'}), 500
               
@ti_bp.route('/ajuda')
@login_required
@setor_required('ti')
def ajuda():
    faqs = [
        ("Como abrir um novo chamado?", 
         "<ol><li>Acesse o menu 'Abrir Chamado'</li><li>Preencha todos os campos obrigatórios</li><li>Clique em 'Enviar'</li><li>Anote o número do protocolo para acompanhamento</li></ol>"),
        ("Como acompanhar um chamado existente?", 
         "<ol><li>Acesse o menu 'Meus Chamados'</li><li>Digite o número do protocolo</li><li>Clique em 'Buscar'</li><li>Você verá o status atual e histórico</li></ol>"),
        ("O que fazer se esquecer o número do protocolo?", 
         "<ul><li>Verifique seu e-mail - enviamos uma confirmação</li><li>Contate o suporte TI com seus dados</li><li>Forneça data aproximada e detalhes do problema</li></ul>"),
        ("Quanto tempo leva para um chamado ser atendido?", 
         "<p>O tempo varia conforme a prioridade:</p><ul><li><strong>Crítico</strong>: 1 hora</li><li><strong>Alta</strong>: 4 horas</li><li><strong>Normal</strong>: 24 horas</li><li><strong>Baixa</strong>: 72 horas</li></ul>"),
        ("Como classificar a prioridade do meu chamado?", 
         "<p>Use estas diretrizes:</p><ul><li><strong>Crítico</strong>: Sistema totalmente inoperante</li><li><strong>Alta</strong>: Funcionalidade principal afetada</li><li><strong>Normal</strong>: Problema não impede operação</li><li><strong>Baixa</strong>: Dúvida ou melhoria</li></ul>"),
        ("Posso anexar arquivos ao chamado?", 
         "<p>Sim, na versão premium do sistema. Atualmente você pode:</p><ul><li>Descrever detalhadamente o problema</li><li>Incluir prints na descrição</li><li>Enviar arquivos posteriormente por e-mail</li></ul>")
    ]
    return render_template('ajuda.html', faqs=faqs)
