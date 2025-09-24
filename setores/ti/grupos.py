from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from database import (db, GrupoUsuarios, GrupoMembro, GrupoUnidade, GrupoPermissao, 
                     User, Unidade, EmailMassa, EmailMassaDestinatario, get_brazil_time)
from auth.auth_helpers import setor_required
from setores.ti.painel import json_response, error_response
from setores.ti.email_service import email_service
import logging
from jinja2 import Template

grupos_bp = Blueprint('grupos', __name__)
logger = logging.getLogger(__name__)

@grupos_bp.route('/api/grupos', methods=['GET'])
@login_required
@setor_required('Administrador')
def listar_grupos():
    """Lista todos os grupos de usuários"""
    try:
        grupos = GrupoUsuarios.query.filter_by(ativo=True).order_by(GrupoUsuarios.data_criacao.desc()).all()
        
        grupos_data = []
        for grupo in grupos:
            grupos_data.append({
                'id': grupo.id,
                'nome': grupo.nome,
                'descricao': grupo.descricao,
                'ativo': grupo.ativo,
                'data_criacao': grupo.data_criacao.strftime('%d/%m/%Y %H:%M') if grupo.data_criacao else None,
                'membros_count': grupo.get_membros_count(),
                'unidades_count': grupo.get_unidades_count(),
                'criador': {
                    'id': grupo.criador.id,
                    'nome': f"{grupo.criador.nome} {grupo.criador.sobrenome}"
                }
            })
        
        return json_response(grupos_data)
        
    except Exception as e:
        logger.error(f"Erro ao listar grupos: {str(e)}")
        return error_response('Erro interno do servidor')

@grupos_bp.route('/api/grupos', methods=['POST'])
@login_required
@setor_required('Administrador')
def criar_grupo():
    """Cria um novo grupo de usuários"""
    try:
        data = request.get_json()
        
        if not data or not data.get('nome'):
            return error_response('Nome do grupo é obrigatório')
        
        # Verificar se já existe grupo com esse nome
        grupo_existente = GrupoUsuarios.query.filter_by(nome=data['nome']).first()
        if grupo_existente:
            return error_response('Já existe um grupo com este nome')
        
        # Criar grupo
        grupo = GrupoUsuarios(
            nome=data['nome'],
            descricao=data.get('descricao', ''),
            ativo=True,
            criado_por=current_user.id
        )
        
        db.session.add(grupo)
        db.session.flush()  # Para obter o ID
        
        # Adicionar membros se fornecidos
        membros_ids = data.get('membros', [])
        for usuario_id in membros_ids:
            membro = GrupoMembro(
                grupo_id=grupo.id,
                usuario_id=usuario_id,
                adicionado_por=current_user.id
            )
            db.session.add(membro)
        
        # Adicionar unidades se fornecidas
        unidades_ids = data.get('unidades', [])
        for unidade_id in unidades_ids:
            grupo_unidade = GrupoUnidade(
                grupo_id=grupo.id,
                unidade_id=unidade_id
            )
            db.session.add(grupo_unidade)
        
        db.session.commit()
        
        return json_response({
            'id': grupo.id,
            'nome': grupo.nome,
            'message': 'Grupo criado com sucesso'
        }, 201)
        
    except Exception as e:
        logger.error(f"Erro ao criar grupo: {str(e)}")
        db.session.rollback()
        return error_response('Erro interno do servidor')

@grupos_bp.route('/api/grupos/<int:grupo_id>', methods=['GET'])
@login_required
@setor_required('Administrador')
def obter_grupo(grupo_id):
    """Obtém detalhes de um grupo específico"""
    try:
        grupo = GrupoUsuarios.query.get(grupo_id)
        if not grupo:
            return error_response('Grupo não encontrado', 404)
        
        # Buscar membros
        membros = db.session.query(GrupoMembro, User).join(User).filter(
            GrupoMembro.grupo_id == grupo_id,
            GrupoMembro.ativo == True
        ).all()
        
        membros_data = []
        for membro, usuario in membros:
            membros_data.append({
                'id': membro.id,
                'usuario_id': usuario.id,
                'nome': f"{usuario.nome} {usuario.sobrenome}",
                'email': usuario.email,
                'nivel_acesso': usuario.nivel_acesso,
                'data_adicao': membro.data_adicao.strftime('%d/%m/%Y') if membro.data_adicao else None
            })
        
        # Buscar unidades
        unidades = db.session.query(GrupoUnidade, Unidade).join(Unidade).filter(
            GrupoUnidade.grupo_id == grupo_id
        ).all()
        
        unidades_data = []
        for grupo_unidade, unidade in unidades:
            unidades_data.append({
                'id': grupo_unidade.id,
                'unidade_id': unidade.id,
                'nome': unidade.nome
            })
        
        grupo_data = {
            'id': grupo.id,
            'nome': grupo.nome,
            'descricao': grupo.descricao,
            'ativo': grupo.ativo,
            'data_criacao': grupo.data_criacao.strftime('%d/%m/%Y %H:%M') if grupo.data_criacao else None,
            'criador': {
                'id': grupo.criador.id,
                'nome': f"{grupo.criador.nome} {grupo.criador.sobrenome}"
            },
            'membros': membros_data,
            'unidades': unidades_data
        }
        
        return json_response(grupo_data)
        
    except Exception as e:
        logger.error(f"Erro ao obter grupo {grupo_id}: {str(e)}")
        return error_response('Erro interno do servidor')

@grupos_bp.route('/api/grupos/<int:grupo_id>', methods=['PUT'])
@login_required
@setor_required('Administrador')
def atualizar_grupo(grupo_id):
    """Atualiza um grupo existente"""
    try:
        grupo = GrupoUsuarios.query.get(grupo_id)
        if not grupo:
            return error_response('Grupo não encontrado', 404)
        
        data = request.get_json()
        
        # Atualizar campos básicos
        if 'nome' in data:
            # Verificar se nome não conflita
            outro_grupo = GrupoUsuarios.query.filter(
                GrupoUsuarios.nome == data['nome'],
                GrupoUsuarios.id != grupo_id
            ).first()
            if outro_grupo:
                return error_response('Já existe outro grupo com este nome')
            grupo.nome = data['nome']
        
        if 'descricao' in data:
            grupo.descricao = data['descricao']
        
        if 'ativo' in data:
            grupo.ativo = data['ativo']
        
        grupo.data_atualizacao = get_brazil_time().replace(tzinfo=None)
        
        # Atualizar membros se fornecido
        if 'membros' in data:
            # Remover membros atuais
            GrupoMembro.query.filter_by(grupo_id=grupo_id).delete()
            
            # Adicionar novos membros
            for usuario_id in data['membros']:
                membro = GrupoMembro(
                    grupo_id=grupo_id,
                    usuario_id=usuario_id,
                    adicionado_por=current_user.id
                )
                db.session.add(membro)
        
        # Atualizar unidades se fornecido
        if 'unidades' in data:
            # Remover unidades atuais
            GrupoUnidade.query.filter_by(grupo_id=grupo_id).delete()
            
            # Adicionar novas unidades
            for unidade_id in data['unidades']:
                grupo_unidade = GrupoUnidade(
                    grupo_id=grupo_id,
                    unidade_id=unidade_id
                )
                db.session.add(grupo_unidade)
        
        db.session.commit()
        
        return json_response({'message': 'Grupo atualizado com sucesso'})
        
    except Exception as e:
        logger.error(f"Erro ao atualizar grupo {grupo_id}: {str(e)}")
        db.session.rollback()
        return error_response('Erro interno do servidor')

@grupos_bp.route('/api/grupos/<int:grupo_id>', methods=['DELETE'])
@login_required
@setor_required('Administrador')
def excluir_grupo(grupo_id):
    """Exclui um grupo"""
    try:
        grupo = GrupoUsuarios.query.get(grupo_id)
        if not grupo:
            return error_response('Grupo não encontrado', 404)
        
        # Marcar como inativo em vez de excluir
        grupo.ativo = False
        grupo.data_atualizacao = get_brazil_time().replace(tzinfo=None)
        
        db.session.commit()
        
        return json_response({'message': 'Grupo excluído com sucesso'})
        
    except Exception as e:
        logger.error(f"Erro ao excluir grupo {grupo_id}: {str(e)}")
        db.session.rollback()
        return error_response('Erro interno do servidor')

@grupos_bp.route('/api/grupos/<int:grupo_id>/enviar-email', methods=['POST'])
@login_required
@setor_required('Administrador')
def enviar_email_grupo(grupo_id):
    """Envia email em massa para todos os membros do grupo"""
    try:
        grupo = GrupoUsuarios.query.get(grupo_id)
        if not grupo:
            return error_response('Grupo não encontrado', 404)
        
        data = request.get_json()
        
        if not data or not data.get('assunto') or not data.get('mensagem'):
            return error_response('Assunto e mensagem são obrigatórios')
        
        # Buscar membros do grupo
        membros = db.session.query(User).join(GrupoMembro).filter(
            GrupoMembro.grupo_id == grupo_id,
            GrupoMembro.ativo == True
        ).all()
        
        if not membros:
            return error_response('Nenhum membro encontrado no grupo')
        
        # Criar registro de email em massa
        email_massa = EmailMassa(
            grupo_id=grupo_id,
            assunto=data['assunto'],
            conteudo=data['mensagem'],
            tipo=data.get('tipo', 'informativo'),
            destinatarios_count=len(membros),
            status='preparando',
            criado_por=current_user.id
        )
        
        db.session.add(email_massa)
        db.session.flush()
        
        # Criar template HTML
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
                .message { background-color: white; padding: 20px; margin: 15px 0; }
                .footer { text-align: center; margin-top: 20px; font-size: 12px; color: #666; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{{ assunto }}</h1>
                </div>
                
                <div class="content">
                    <p>Olá <strong>{{ nome_destinatario }}</strong>,</p>
                    
                    <div class="message">
                        {{ mensagem|safe }}
                    </div>
                    
                    <p><em>Esta mensagem foi enviada para o grupo: <strong>{{ nome_grupo }}</strong></em></p>
                </div>
                
                <div class="footer">
                    <p>Enviado por: {{ remetente }} em {{ data_envio }}</p>
                    <p>Sistema ERP Evoque Fitness</p>
                </div>
            </div>
        </body>
        </html>
        """)
        
        # Enviar emails
        sucessos = 0
        falhas = 0
        
        for membro in membros:
            # Criar registro de destinatário
            destinatario_record = EmailMassaDestinatario(
                email_massa_id=email_massa.id,
                usuario_id=membro.id,
                email_destinatario=membro.email,
                nome_destinatario=f"{membro.nome} {membro.sobrenome}",
                status_envio='pendente'
            )
            db.session.add(destinatario_record)
            
            # Gerar HTML personalizado
            corpo_html = template_html.render(
                assunto=data['assunto'],
                nome_destinatario=f"{membro.nome} {membro.sobrenome}",
                mensagem=data['mensagem'],
                nome_grupo=grupo.nome,
                remetente=f"{current_user.nome} {current_user.sobrenome}",
                data_envio=get_brazil_time().strftime('%d/%m/%Y às %H:%M')
            )
            
            # Tentar enviar email
            if email_service.enviar_email(membro.email, data['assunto'], corpo_html):
                destinatario_record.status_envio = 'enviado'
                destinatario_record.data_envio = get_brazil_time().replace(tzinfo=None)
                sucessos += 1
            else:
                destinatario_record.status_envio = 'falha'
                destinatario_record.erro_envio = 'Erro no envio'
                falhas += 1
        
        # Atualizar status do email em massa
        email_massa.enviados_count = sucessos
        email_massa.falhas_count = falhas
        email_massa.status = 'concluido' if falhas == 0 else 'erro'
        email_massa.data_envio = get_brazil_time().replace(tzinfo=None)
        email_massa.data_conclusao = get_brazil_time().replace(tzinfo=None)
        
        db.session.commit()
        
        return json_response({
            'message': f'Email enviado com sucesso! {sucessos} enviados, {falhas} falhas',
            'sucessos': sucessos,
            'falhas': falhas,
            'total': len(membros)
        })
        
    except Exception as e:
        logger.error(f"Erro ao enviar email para grupo {grupo_id}: {str(e)}")
        db.session.rollback()
        return error_response('Erro interno do servidor')

@grupos_bp.route('/api/grupos/emails-massa', methods=['GET'])
@login_required
@setor_required('Administrador')
def listar_emails_massa():
    """Lista histórico de emails em massa"""
    try:
        emails = EmailMassa.query.order_by(EmailMassa.data_criacao.desc()).limit(50).all()
        
        emails_data = []
        for email in emails:
            emails_data.append({
                'id': email.id,
                'assunto': email.assunto,
                'tipo': email.tipo,
                'grupo': {
                    'id': email.grupo.id,
                    'nome': email.grupo.nome
                } if email.grupo else None,
                'destinatarios_count': email.destinatarios_count,
                'enviados_count': email.enviados_count,
                'falhas_count': email.falhas_count,
                'status': email.status,
                'data_criacao': email.data_criacao.strftime('%d/%m/%Y %H:%M') if email.data_criacao else None,
                'data_envio': email.data_envio.strftime('%d/%m/%Y %H:%M') if email.data_envio else None,
                'criador': {
                    'id': email.criador.id,
                    'nome': f"{email.criador.nome} {email.criador.sobrenome}"
                }
            })
        
        return json_response(emails_data)
        
    except Exception as e:
        logger.error(f"Erro ao listar emails em massa: {str(e)}")
        return error_response('Erro interno do servidor')
