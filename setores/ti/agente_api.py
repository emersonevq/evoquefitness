from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from database import db, Chamado, AgenteSuporte, ChamadoAgente, User, get_brazil_time, NotificacaoAgente, HistoricoAtendimento
from sqlalchemy import func
import logging
import traceback
import pytz
import json
from datetime import datetime

agente_api_bp = Blueprint('agente_api', __name__)

# Configurar logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def api_login_required(f):
    """Decorador que retorna erro JSON se não autenticado"""
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

def json_response(data, status=200):
    """Retorna resposta JSON padronizada"""
    response = jsonify(data)
    response.status_code = status
    response.headers['Content-Type'] = 'application/json'
    return response

def error_response(message, status=400):
    """Retorna erro JSON padronizado"""
    return json_response({'error': message}, status)

def criar_notificacao_agente(agente_id, titulo, mensagem, tipo, chamado_id=None, metadados=None, prioridade='normal'):
    """Cria uma nova notificação para o agente"""
    try:
        notificacao = NotificacaoAgente(
            agente_id=agente_id,
            titulo=titulo,
            mensagem=mensagem,
            tipo=tipo,
            chamado_id=chamado_id,
            prioridade=prioridade
        )

        if metadados:
            notificacao.set_metadados(metadados)

        db.session.add(notificacao)
        db.session.commit()

        return notificacao
    except Exception as e:
        logger.error(f"Erro ao criar notificação: {str(e)}")
        db.session.rollback()
        return None

def criar_historico_atendimento(chamado_id, agente_id, status_inicial='Aguardando', observacoes=None):
    """Cria um registro de histórico para um atendimento"""
    try:
        historico = HistoricoAtendimento(
            chamado_id=chamado_id,
            agente_id=agente_id,
            data_atribuicao=get_brazil_time().replace(tzinfo=None),
            status_inicial=status_inicial,
            observacoes_iniciais=observacoes
        )

        db.session.add(historico)
        db.session.commit()

        return historico
    except Exception as e:
        logger.error(f"Erro ao criar histórico de atendimento: {str(e)}")
        db.session.rollback()
        return None

@agente_api_bp.route('/api/chamados/<int:chamado_id>/detalhes', methods=['GET'])
@api_login_required
def detalhes_chamado(chamado_id):
    """Retorna detalhes completos de um chamado"""
    try:
        # Buscar chamado com informações do agente
        chamado = Chamado.query.get(chamado_id)
        if not chamado:
            return error_response('Chamado não encontrado', 404)

        # Buscar agente atribuído
        chamado_agente = ChamadoAgente.query.filter_by(
            chamado_id=chamado_id,
            ativo=True
        ).first()

        agente_info = None
        if chamado_agente and chamado_agente.agente:
            agente_info = {
                'id': chamado_agente.agente.id,
                'nome': f"{chamado_agente.agente.usuario.nome} {chamado_agente.agente.usuario.sobrenome}",
                'email': chamado_agente.agente.usuario.email,
                'nivel_experiencia': chamado_agente.agente.nivel_experiencia
            }

        data_abertura_brazil = chamado.get_data_abertura_brazil()
        
        chamado_data = {
            'id': chamado.id,
            'codigo': chamado.codigo,
            'protocolo': chamado.protocolo,
            'solicitante': chamado.solicitante,
            'email': chamado.email,
            'telefone': chamado.telefone,
            'unidade': chamado.unidade,
            'problema': chamado.problema,
            'descricao': chamado.descricao,
            'status': chamado.status,
            'prioridade': chamado.prioridade,
            'data_abertura': data_abertura_brazil.strftime('%d/%m/%Y %H:%M') if data_abertura_brazil else 'N/A',
            'agente': agente_info
        }

        return json_response(chamado_data)

    except Exception as e:
        logger.error(f"Erro ao buscar detalhes do chamado: {str(e)}")
        return error_response('Erro interno no servidor')

@agente_api_bp.route('/api/chamados/<int:chamado_id>/atualizar', methods=['PUT'])
@api_login_required
def atualizar_chamado_agente(chamado_id):
    """Atualiza um chamado pelo agente"""
    try:
        # Verificar se o usuário é um agente
        agente = AgenteSuporte.query.filter_by(usuario_id=current_user.id, ativo=True).first()
        if not agente:
            return error_response('Usuário não é um agente de suporte', 403)

        # Verificar se o chamado existe
        chamado = Chamado.query.get(chamado_id)
        if not chamado:
            return error_response('Chamado não encontrado', 404)

        # Verificar se o agente tem o chamado atribuído (opcional - pode permitir admin atualizar qualquer)
        if current_user.nivel_acesso != 'Administrador':
            chamado_agente = ChamadoAgente.query.filter_by(
                chamado_id=chamado_id,
                agente_id=agente.id,
                ativo=True
            ).first()
            if not chamado_agente:
                return error_response('Você não tem permissão para atualizar este chamado', 403)

        data = request.get_json()
        if not data:
            return error_response('Dados não fornecidos', 400)

        status_anterior = chamado.status
        novo_status = data.get('status')
        observacoes = data.get('observacoes', '')

        if novo_status and novo_status in ['Aberto', 'Aguardando', 'Em Atendimento', 'Concluido', 'Cancelado']:
            # ⚠️ IMPORTANTE: O TRIGGER trg_chamado_status_update no banco automaticamente:
            # 1. Fecha o período anterior em historico_status
            # 2. Cria novo período com o novo status
            # Portanto, apenas atualizamos o status aqui

            chamado.status = novo_status

            # Registrar evento na timeline
            try:
                from database import ChamadoTimelineEvent
                evento_status = ChamadoTimelineEvent(
                    chamado_id=chamado_id,
                    usuario_id=current_user.id,
                    tipo='status_change',
                    descricao=f'Status alterado de {status_anterior} para {novo_status}',
                    status_anterior=status_anterior,
                    status_novo=novo_status
                )
                db.session.add(evento_status)
            except Exception as e:
                logger.warning(f"Falha ao registrar timeline: {str(e)}")

            # Atualizar campos de SLA
            agora_brazil = get_brazil_time()

            # Registrar primeira resposta (quando sai de "Aberto")
            if status_anterior == 'Aberto' and novo_status != 'Aberto' and not chamado.data_primeira_resposta:
                chamado.data_primeira_resposta = agora_brazil.replace(tzinfo=None)

            # Registrar conclusão (quando fecha)
            if novo_status in ['Concluido', 'Cancelado']:
                if not chamado.data_conclusao:
                    chamado.data_conclusao = agora_brazil.replace(tzinfo=None)

                # Registrar informações de conclusão
                if novo_status == 'Concluido':
                    chamado.concluido_por_id = current_user.id
                    chamado.concluido_em = agora_brazil.replace(tzinfo=None)
                elif novo_status == 'Cancelado':
                    chamado.cancelado_por_id = current_user.id
                    chamado.cancelado_em = agora_brazil.replace(tzinfo=None)

                # Finalizar atribuição
                chamado_agente = ChamadoAgente.query.filter_by(
                    chamado_id=chamado_id,
                    ativo=True
                ).first()
                if chamado_agente:
                    chamado_agente.finalizar_atribuicao()

        db.session.commit()

        # Enviar e-mail de notificação
        try:
            from setores.ti.routes import enviar_email
            assunto = f"Atualização do Chamado {chamado.codigo}"
            corpo = f"""
Olá {chamado.solicitante},

Seu chamado {chamado.codigo} foi atualizado.

Detalhes da atualização:
- Status anterior: {status_anterior}
- Novo status: {novo_status}
- Responsável: {current_user.nome} {current_user.sobrenome}
"""
            if observacoes:
                corpo += f"\n- Observações: {observacoes}"
                
            corpo += f"""

Para acompanhar seu chamado, acesse o sistema ou entre em contato conosco.

Atenciosamente,
Equipe de Suporte TI - Evoque Fitness
"""
            enviar_email(assunto, corpo, [chamado.email])
        except Exception as email_error:
            logger.warning(f"Erro ao enviar e-mail de atualização: {str(email_error)}")

        logger.info(f"Chamado {chamado.codigo} atualizado por agente {current_user.nome} - Status: {status_anterior} -> {novo_status}")

        return json_response({
            'message': 'Chamado atualizado com sucesso',
            'status': chamado.status
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao atualizar chamado: {str(e)}")
        return error_response('Erro interno no servidor')

@agente_api_bp.route('/api/chamados/<int:chamado_id>/transferir', methods=['POST'])
@api_login_required
def transferir_chamado(chamado_id):
    """Transfere um chamado para outro agente"""
    try:
        # Verificar se o usuário é um agente
        agente_origem = AgenteSuporte.query.filter_by(usuario_id=current_user.id, ativo=True).first()
        if not agente_origem:
            return error_response('Usuário não é um agente de suporte', 403)

        data = request.get_json()
        if not data or 'agente_destino_id' not in data:
            return error_response('ID do agente destino é obrigatório', 400)

        agente_destino_id = data['agente_destino_id']
        observacoes = data.get('observacoes', '')

        # Verificar se o chamado existe
        chamado = Chamado.query.get(chamado_id)
        if not chamado:
            return error_response('Chamado não encontrado', 404)

        # Verificar se o agente destino existe e está ativo
        agente_destino = AgenteSuporte.query.filter_by(id=agente_destino_id, ativo=True).first()
        if not agente_destino:
            return error_response('Agente destino não encontrado ou inativo', 404)

        # Verificar se o agente destino pode receber mais chamados
        if not agente_destino.pode_receber_chamado():
            return error_response(f'Agente {agente_destino.usuario.nome} já atingiu o limite máximo de chamados simultâneos')

        # Verificar se existe atribuição atual
        atribuicao_atual = ChamadoAgente.query.filter_by(
            chamado_id=chamado_id,
            ativo=True
        ).first()

        if not atribuicao_atual:
            return error_response('Chamado não possui agente atribuído', 400)

        # Verificar se o agente atual é o mesmo que está fazendo a transferência (ou admin)
        if current_user.nivel_acesso != 'Administrador' and atribuicao_atual.agente_id != agente_origem.id:
            return error_response('Você não tem permissão para transferir este chamado', 403)

        # Finalizar atribuição atual
        atribuicao_atual.ativo = False
        atribuicao_atual.data_conclusao = get_brazil_time().replace(tzinfo=None)
        if observacoes:
            atribuicao_atual.observacoes = f"{atribuicao_atual.observacoes or ''}\n[TRANSFERÊNCIA] {observacoes}"

        # Criar nova atribuição
        nova_atribuicao = ChamadoAgente(
            chamado_id=chamado_id,
            agente_id=agente_destino_id,
            atribuido_por=current_user.id,
            observacoes=f'Transferido de {agente_origem.usuario.nome} {agente_origem.usuario.sobrenome}. {observacoes}'
        )

        db.session.add(nova_atribuicao)
        db.session.commit()

        # Enviar e-mails de notificação
        try:
            from setores.ti.routes import enviar_email
            logger.info(f"🔄 Iniciando envio de e-mails para transferência do chamado {chamado.codigo}")
            logger.info(f"📧 Email do solicitante: {chamado.email}")
            logger.info(f"📧 Email do agente destino: {agente_destino.usuario.email}")

            # E-mail para o solicitante
            assunto_cliente = f"Chamado {chamado.codigo} - Transferência de Agente"
            corpo_cliente = f"""
Olá {chamado.solicitante},

Seu chamado {chamado.codigo} foi transferido para um novo agente.

Detalhes da transferência:
- Agente anterior: {agente_origem.usuario.nome} {agente_origem.usuario.sobrenome}
- Novo agente responsável: {agente_destino.usuario.nome} {agente_destino.usuario.sobrenome}
- E-mail do novo agente: {agente_destino.usuario.email}
"""
            if observacoes:
                corpo_cliente += f"\n- Motivo da transferência: {observacoes}"

            corpo_cliente += f"""

O novo agente entrará em contato em breve para dar continuidade ao atendimento.

Para acompanhar seu chamado ou fornecer informações adicionais, você pode responder a este e-mail.

Atenciosamente,
Equipe de Suporte TI - Evoque Fitness
"""
            logger.info(f"📤 Enviando e-mail para solicitante: {chamado.email}")
            resultado_cliente = enviar_email(assunto_cliente, corpo_cliente, [chamado.email])
            logger.info(f"📥 Resultado do envio para solicitante: {'✅ Sucesso' if resultado_cliente else '❌ Falha'}")

            # E-mail para o agente destino
            assunto_agente = f"Novo Chamado Atribuído por Transferência - {chamado.codigo}"
            corpo_agente = f"""
Olá {agente_destino.usuario.nome},

Você recebeu um novo chamado por transferência.

📋 DETALHES DO CHAMADO:
- Código: {chamado.codigo}
- Protocolo: {chamado.protocolo}
- Solicitante: {chamado.solicitante}
- E-mail: {chamado.email}
- Telefone: {chamado.telefone or 'Não informado'}
- Problema: {chamado.problema}
- Prioridade: {chamado.prioridade}
- Status: {chamado.status}
- Transferido por: {agente_origem.usuario.nome} {agente_origem.usuario.sobrenome}
"""
            if observacoes:
                corpo_agente += f"\n💬 OBSERVAÇÕES DA TRANSFERÊNCIA:\n{observacoes}\n"

            corpo_agente += f"""

📝 DESCRIÇÃO DO PROBLEMA:
{chamado.descricao or 'Não informada'}

🚀 PRÓXIMOS PASSOS:
- Acesse o painel de agente para gerenciar este chamado
- Entre em contato com o solicitante para dar início ao atendimento
- Se necessário, consulte o agente anterior para mais informações

Atenciosamente,
Sistema de Suporte TI - Evoque Fitness
"""
            logger.info(f"📤 Enviando e-mail para agente destino: {agente_destino.usuario.email}")
            resultado_agente = enviar_email(assunto_agente, corpo_agente, [agente_destino.usuario.email])
            logger.info(f"📥 Resultado do envio para agente: {'✅ Sucesso' if resultado_agente else '❌ Falha'}")

            if resultado_cliente and resultado_agente:
                logger.info("✅ Todos os e-mails de transferência enviados com sucesso")
            elif resultado_cliente:
                logger.warning("⚠️ E-mail enviado para solicitante, mas falhou para o agente")
            elif resultado_agente:
                logger.warning("⚠️ E-mail enviado para agente, mas falhou para o solicitante")
            else:
                logger.error("❌ Falha no envio de ambos os e-mails")

        except Exception as email_error:
            logger.error(f"❌ Erro crítico ao enviar e-mails de transferência: {str(email_error)}")
            import traceback
            logger.error(f"🔍 Stack trace: {traceback.format_exc()}")

        # Criar notificação para o agente que recebeu a transferência
        try:
            criar_notificacao_agente(
                agente_id=agente_destino.id,
                titulo=f"Chamado Transferido - {chamado.codigo}",
                mensagem=f"Você recebeu o chamado {chamado.codigo} por transferência de {agente_origem.usuario.nome}",
                tipo='chamado_transferido',
                chamado_id=chamado.id,
                metadados={
                    'agente_origem': f"{agente_origem.usuario.nome} {agente_origem.usuario.sobrenome}",
                    'agente_origem_email': agente_origem.usuario.email,
                    'solicitante': chamado.solicitante,
                    'problema': chamado.problema,
                    'prioridade': chamado.prioridade,
                    'unidade': chamado.unidade,
                    'observacoes': observacoes
                },
                prioridade='alta' if chamado.prioridade in ['Crítica', 'Alta'] else 'normal'
            )

        except Exception as notif_error:
            logger.warning(f"Erro ao criar notificação de transferência: {str(notif_error)}")

        # Emitir evento Socket.IO para notificação em tempo real
        try:
            from flask import current_app
            if hasattr(current_app, 'socketio'):
                current_app.socketio.emit('chamado_transferido', {
                    'chamado_id': chamado.id,
                    'codigo': chamado.codigo,
                    'protocolo': chamado.protocolo,
                    'solicitante': chamado.solicitante,
                    'problema': chamado.problema,
                    'prioridade': chamado.prioridade,
                    'agente_origem_id': agente_origem.id,
                    'agente_origem_nome': f"{agente_origem.usuario.nome} {agente_origem.usuario.sobrenome}",
                    'agente_origem_email': agente_origem.usuario.email,
                    'agente_destino_id': agente_destino.id,
                    'agente_destino_nome': f"{agente_destino.usuario.nome} {agente_destino.usuario.sobrenome}",
                    'agente_destino_email': agente_destino.usuario.email,
                    'transferido_por': f"{current_user.nome} {current_user.sobrenome}",
                    'observacoes': observacoes,
                    'timestamp': get_brazil_time().isoformat()
                }, room=f'agente_{agente_destino.id}')
                
                # Emitir também para administradores
                current_app.socketio.emit('chamado_transferido_admin', {
                    'chamado_id': chamado.id,
                    'codigo': chamado.codigo,
                    'protocolo': chamado.protocolo,
                    'solicitante': chamado.solicitante,
                    'problema': chamado.problema,
                    'prioridade': chamado.prioridade,
                    'agente_origem_nome': f"{agente_origem.usuario.nome} {agente_origem.usuario.sobrenome}",
                    'agente_destino_nome': f"{agente_destino.usuario.nome} {agente_destino.usuario.sobrenome}",
                    'transferido_por': f"{current_user.nome} {current_user.sobrenome}",
                    'observacoes': observacoes,
                    'timestamp': get_brazil_time().isoformat()
                }, room='admin')
        except Exception as socket_error:
            logger.warning(f"Erro ao emitir evento Socket.IO: {str(socket_error)}")

        logger.info(f"Chamado {chamado.codigo} transferido de {agente_origem.usuario.nome} para {agente_destino.usuario.nome}")

        return json_response({
            'message': f'Chamado transferido com sucesso para {agente_destino.usuario.nome}'
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao transferir chamado: {str(e)}")
        return error_response('Erro interno no servidor')

@agente_api_bp.route('/api/agentes/ativos', methods=['GET'])
@api_login_required
def listar_agentes_ativos():
    """Lista agentes ativos para transferência"""
    try:
        agentes = db.session.query(AgenteSuporte, User).join(
            User, AgenteSuporte.usuario_id == User.id
        ).filter(
            AgenteSuporte.ativo == True
        ).all()

        agentes_list = []
        for agente, usuario in agentes:
            chamados_ativos = agente.get_chamados_ativos()
            
            agentes_list.append({
                'id': agente.id,
                'nome': f"{usuario.nome} {usuario.sobrenome}",
                'email': usuario.email,
                'nivel_experiencia': agente.nivel_experiencia,
                'max_chamados': agente.max_chamados_simultaneos,
                'chamados_ativos': chamados_ativos,
                'pode_receber': agente.pode_receber_chamado()
            })

        return json_response(agentes_list)

    except Exception as e:
        logger.error(f"Erro ao listar agentes ativos: {str(e)}")
        return error_response('Erro interno no servidor')

@agente_api_bp.route('/api/agente/estatisticas-detalhadas', methods=['GET'])
@api_login_required
def estatisticas_detalhadas_agente():
    """Retorna estatísticas detalhadas do agente logado"""
    try:
        # Verificar se o usuário é um agente
        agente = AgenteSuporte.query.filter_by(usuario_id=current_user.id, ativo=True).first()
        if not agente:
            return error_response('Usuário não é um agente de suporte', 403)

        # Estatísticas do mês atual
        hoje = get_brazil_time().date()
        inicio_mes = hoje.replace(day=1)
        
        total_atendidos = ChamadoAgente.query.filter_by(
            agente_id=agente.id
        ).join(Chamado).filter(
            Chamado.status.in_(['Concluido', 'Cancelado']),
            func.date(ChamadoAgente.data_atribuicao) >= inicio_mes
        ).count()

        # Atendimentos hoje
        atendimentos_hoje = ChamadoAgente.query.filter_by(
            agente_id=agente.id
        ).join(Chamado).filter(
            Chamado.status == 'Concluido',
            func.date(Chamado.data_conclusao) == hoje
        ).count()

        # Tempo médio de resolução (placeholder)
        tempo_medio = '2.5h'
        
        # Avaliação média (placeholder)
        avaliacao_media = '4.8'

        estatisticas = {
            'total_atendidos': total_atendidos,
            'tempo_medio': tempo_medio,
            'atendimentos_hoje': atendimentos_hoje,
            'avaliacao_media': avaliacao_media
        }

        return json_response(estatisticas)

    except Exception as e:
        logger.error(f"Erro ao buscar estatísticas detalhadas: {str(e)}")
        return error_response('Erro interno no servidor')

@agente_api_bp.route('/api/agente/perfil', methods=['GET'])
@api_login_required
def perfil_agente():
    """Retorna perfil do agente logado"""
    try:
        # Verificar se o usuário é um agente
        agente = AgenteSuporte.query.filter_by(usuario_id=current_user.id, ativo=True).first()
        if not agente:
            return error_response('Usuário não é um agente de suporte', 403)

        perfil = {
            'nome': f"{current_user.nome} {current_user.sobrenome}",
            'email': current_user.email,
            'telefone': getattr(current_user, 'telefone', ''),
            'especialidades': ', '.join(agente.especialidades_list) if agente.especialidades_list else '',
            'nivel_experiencia': agente.nivel_experiencia,
            'max_chamados': agente.max_chamados_simultaneos,
            'notificacoes': True,  # Placeholder
            'auto_atribuicao': False  # Placeholder
        }

        return json_response(perfil)

    except Exception as e:
        logger.error(f"Erro ao buscar perfil do agente: {str(e)}")
        return error_response('Erro interno no servidor')

@agente_api_bp.route('/api/agente/estatisticas', methods=['GET'])
@api_login_required
def estatisticas_agente():
    """Retorna estatísticas básicas do agente logado"""
    try:
        # Verificar se o usuário é um agente
        agente = AgenteSuporte.query.filter_by(usuario_id=current_user.id, ativo=True).first()
        if not agente:
            return error_response('Usuário não é um agente de suporte', 403)

        # Chamados ativos do agente
        chamados_ativos = agente.get_chamados_ativos()

        # Chamados concluídos hoje
        hoje = get_brazil_time().date()
        concluidos_hoje = ChamadoAgente.query.filter_by(
            agente_id=agente.id
        ).join(Chamado).filter(
            Chamado.status == 'Concluido',
            func.date(Chamado.data_conclusao) == hoje
        ).count()

        # Novos chamados disponíveis
        chamados_disponiveis = Chamado.query.filter(
            Chamado.status == 'Aberto',
            ~Chamado.id.in_(
                db.session.query(ChamadoAgente.chamado_id).filter_by(ativo=True)
            )
        ).count()

        estatisticas = {
            'chamados_ativos': chamados_ativos,
            'concluidos_hoje': concluidos_hoje,
            'disponiveis': chamados_disponiveis,
            'limite_max': agente.max_chamados_simultaneos
        }

        return json_response(estatisticas)

    except Exception as e:
        logger.error(f"Erro ao buscar estatísticas básicas: {str(e)}")
        return error_response('Erro interno no servidor')

@agente_api_bp.route('/api/chamados/disponiveis', methods=['GET'])
@api_login_required
def chamados_disponiveis():
    """Lista chamados disponíveis para atribuição"""
    try:
        # Verificar se o usuário é um agente
        agente = AgenteSuporte.query.filter_by(usuario_id=current_user.id, ativo=True).first()
        if not agente:
            return error_response('Usuário não é um agente de suporte', 403)

        # Buscar chamados que não estão atribuídos
        chamados = Chamado.query.filter(
            Chamado.status == 'Aberto',
            ~Chamado.id.in_(
                db.session.query(ChamadoAgente.chamado_id).filter_by(ativo=True)
            )
        ).order_by(Chamado.prioridade.desc(), Chamado.data_abertura.asc()).all()

        chamados_list = []
        for chamado in chamados:
            data_abertura_brazil = chamado.get_data_abertura_brazil()

            chamados_list.append({
                'id': chamado.id,
                'codigo': chamado.codigo,
                'protocolo': chamado.protocolo,
                'solicitante': chamado.solicitante,
                'unidade': chamado.unidade,
                'problema': chamado.problema,
                'prioridade': chamado.prioridade,
                'data_abertura': data_abertura_brazil.strftime('%d/%m/%Y %H:%M') if data_abertura_brazil else 'N/A'
            })

        return json_response(chamados_list)

    except Exception as e:
        logger.error(f"Erro ao buscar chamados disponíveis: {str(e)}")
        return error_response('Erro interno no servidor')

@agente_api_bp.route('/api/agente/meus-chamados', methods=['GET'])
@api_login_required
def meus_chamados():
    """Lista chamados do agente logado com filtro por status"""
    try:
        # Verificar se o usuário é um agente
        agente = AgenteSuporte.query.filter_by(usuario_id=current_user.id, ativo=True).first()
        if not agente:
            return error_response('Usuário não é um agente de suporte', 403)

        filtro = request.args.get('filtro', 'ativos')

        # Base query para chamados do agente
        base_query = db.session.query(Chamado, ChamadoAgente).join(
            ChamadoAgente, Chamado.id == ChamadoAgente.chamado_id
        ).filter(
            ChamadoAgente.agente_id == agente.id
        )

        # Aplicar filtros
        if filtro == 'ativos':
            chamados = base_query.filter(
                ChamadoAgente.ativo == True,
                Chamado.status.in_(['Aguardando', 'Em Andamento'])
            ).order_by(Chamado.prioridade.desc(), Chamado.data_abertura.asc()).all()
        elif filtro == 'aguardando':
            chamados = base_query.filter(
                ChamadoAgente.ativo == True,
                Chamado.status == 'Aguardando'
            ).order_by(Chamado.data_abertura.asc()).all()
        elif filtro == 'concluidos':
            chamados = base_query.filter(
                Chamado.status == 'Concluido'
            ).order_by(Chamado.data_conclusao.desc()).limit(50).all()
        elif filtro == 'cancelados':
            chamados = base_query.filter(
                Chamado.status == 'Cancelado'
            ).order_by(Chamado.data_conclusao.desc()).limit(50).all()
        else:
            chamados = base_query.filter(
                ChamadoAgente.ativo == True
            ).order_by(Chamado.prioridade.desc(), Chamado.data_abertura.asc()).all()

        chamados_list = []
        for chamado, chamado_agente in chamados:
            data_abertura_brazil = chamado.get_data_abertura_brazil()

            chamado_data = {
                'id': chamado.id,
                'codigo': chamado.codigo,
                'protocolo': chamado.protocolo,
                'solicitante': chamado.solicitante,
                'unidade': chamado.unidade,
                'problema': chamado.problema,
                'prioridade': chamado.prioridade,
                'status': chamado.status,
                'data_abertura': data_abertura_brazil.strftime('%d/%m/%Y %H:%M') if data_abertura_brazil else 'N/A',
                'data_atribuicao': chamado_agente.data_atribuicao.strftime('%d/%m/%Y %H:%M') if chamado_agente.data_atribuicao else 'N/A'
            }

            if chamado.data_conclusao:
                data_conclusao_brazil = chamado.data_conclusao
                if hasattr(data_conclusao_brazil, 'replace'):
                    data_conclusao_brazil = pytz.timezone('America/Sao_Paulo').localize(data_conclusao_brazil)
                chamado_data['data_conclusao'] = data_conclusao_brazil.strftime('%d/%m/%Y %H:%M')

            chamados_list.append(chamado_data)

        return json_response(chamados_list)

    except Exception as e:
        logger.error(f"Erro ao buscar meus chamados: {str(e)}")
        return error_response('Erro interno no servidor')

@agente_api_bp.route('/api/chamados/<int:chamado_id>/atribuir-me', methods=['POST'])
@api_login_required
def atribuir_chamado_para_mim(chamado_id):
    """Atribui um chamado para o agente logado"""
    try:
        # Verificar se o usuário é um agente
        agente = AgenteSuporte.query.filter_by(usuario_id=current_user.id, ativo=True).first()
        if not agente:
            return error_response('Usuário não é um agente de suporte', 403)

        # Verificar se o chamado existe
        chamado = Chamado.query.get(chamado_id)
        if not chamado:
            return error_response('Chamado não encontrado', 404)

        # Verificar se o chamado já está atribuído
        atribuicao_existente = ChamadoAgente.query.filter_by(
            chamado_id=chamado_id,
            ativo=True
        ).first()

        if atribuicao_existente:
            return error_response('Chamado já está atribuído a outro agente', 400)

        # Verificar se o agente pode receber mais chamados
        if not agente.pode_receber_chamado():
            return error_response('Você já atingiu o limite máximo de chamados simultâneos', 400)

        # Verificar se o chamado está em um status que permite atribuição
        if chamado.status not in ['Aberto', 'Aguardando']:
            return error_response('Chamado não está disponível para atribuição', 400)

        # Criar nova atribuição
        nova_atribuicao = ChamadoAgente(
            chamado_id=chamado_id,
            agente_id=agente.id,
            atribuido_por=current_user.id,
            observacoes=f'Auto-atribuição pelo agente'
        )

        # Se o chamado estava "Aberto", muda para "Aguardando"
        if chamado.status == 'Aberto':
            chamado.status = 'Aguardando'

        db.session.add(nova_atribuicao)
        db.session.commit()

        # Criar notificação para o agente
        criar_notificacao_agente(
            agente_id=agente.id,
            titulo=f"Chamado {chamado.codigo} Atribuído",
            mensagem=f"Voc�� recebeu um novo chamado: {chamado.problema}",
            tipo='chamado_atribuido',
            chamado_id=chamado.id,
            metadados={
                'solicitante': chamado.solicitante,
                'prioridade': chamado.prioridade,
                'unidade': chamado.unidade
            },
            prioridade='alta' if chamado.prioridade == 'Alta' else 'normal'
        )

        # Criar histórico de atendimento
        criar_historico_atendimento(
            chamado_id=chamado.id,
            agente_id=agente.id,
            status_inicial=chamado.status,
            observacoes='Auto-atribuição pelo agente'
        )

        # Enviar e-mails de notificação
        try:
            from setores.ti.routes import enviar_email
            logger.info(f"🔄 Iniciando envio de e-mail de atribuição para chamado {chamado.codigo}")
            logger.info(f"📧 Email do solicitante: {chamado.email}")

            # E-mail para o solicitante
            assunto_cliente = f"Chamado {chamado.codigo} - Agente Atribuído"
            corpo_cliente = f"""
Olá {chamado.solicitante},

Seu chamado {chamado.codigo} foi atribuído para atendimento.

📋 DETALHES DO CHAMADO:
- Código: {chamado.codigo}
- Protocolo: {chamado.protocolo}
- Problema: {chamado.problema}
- Prioridade: {chamado.prioridade}
- Status: {chamado.status}

👨‍💻 AGENTE RESPONSÁVEL:
- Nome: {current_user.nome} {current_user.sobrenome}
- E-mail: {current_user.email}

🚀 PRÓXIMOS PASSOS:
O agente responsável irá analisar seu chamado e entrará em contato em breve para dar início ao atendimento.

Para fornecer informações adicionais que possam ajudar na resolução, você pode responder a este e-mail.

Atenciosamente,
Equipe de Suporte TI - Evoque Fitness
"""
            logger.info(f"📤 Enviando e-mail de atribuição para: {chamado.email}")
            resultado = enviar_email(assunto_cliente, corpo_cliente, [chamado.email])
            logger.info(f"📥 Resultado do envio: {'✅ Sucesso' if resultado else '❌ Falha'}")

        except Exception as email_error:
            logger.error(f"❌ Erro ao enviar e-mail de atribuição: {str(email_error)}")
            import traceback
            logger.error(f"🔍 Stack trace: {traceback.format_exc()}")

        # Emitir evento Socket.IO para notificação em tempo real
        try:
            from flask import current_app
            if hasattr(current_app, 'socketio'):
                current_app.socketio.emit('chamado_atribuido', {
                    'chamado_id': chamado.id,
                    'codigo': chamado.codigo,
                    'protocolo': chamado.protocolo,
                    'solicitante': chamado.solicitante,
                    'problema': chamado.problema,
                    'prioridade': chamado.prioridade,
                    'agente_id': agente.id,
                    'agente_nome': f"{current_user.nome} {current_user.sobrenome}",
                    'agente_email': current_user.email,
                    'timestamp': get_brazil_time().isoformat()
                })
        except Exception as socket_error:
            logger.warning(f"Erro ao emitir evento Socket.IO: {str(socket_error)}")

        logger.info(f"Chamado {chamado.codigo} auto-atribuído para agente {current_user.nome}")

        return json_response({
            'message': 'Chamado atribuído com sucesso!',
            'chamado_id': chamado.id,
            'codigo': chamado.codigo
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao atribuir chamado: {str(e)}")
        logger.error(traceback.format_exc())
        return error_response('Erro interno no servidor')

@agente_api_bp.route('/api/agente/notificacoes', methods=['GET'])
@api_login_required
def listar_notificacoes():
    """Lista notificações do agente logado"""
    try:
        # Verificar se o usuário é um agente
        agente = AgenteSuporte.query.filter_by(usuario_id=current_user.id, ativo=True).first()
        if not agente:
            return error_response('Usuário não é um agente de suporte', 403)

        # Buscar notificações não lidas
        nao_lidas = request.args.get('nao_lidas', 'false').lower() == 'true'
        limite = int(request.args.get('limite', 20))

        query = NotificacaoAgente.query.filter_by(agente_id=agente.id)

        if nao_lidas:
            query = query.filter_by(lida=False)

        notificacoes = query.order_by(NotificacaoAgente.data_criacao.desc()).limit(limite).all()

        notificacoes_list = []
        for notif in notificacoes:
            notif_data = {
                'id': notif.id,
                'titulo': notif.titulo,
                'mensagem': notif.mensagem,
                'tipo': notif.tipo,
                'lida': notif.lida,
                'prioridade': notif.prioridade,
                'data_criacao': notif.data_criacao.strftime('%d/%m/%Y %H:%M'),
                'exibir_popup': notif.exibir_popup,
                'som_ativo': notif.som_ativo
            }

            # Adicionar dados do chamado se existir
            if notif.chamado_id:
                notif_data['chamado'] = {
                    'id': notif.chamado.id,
                    'codigo': notif.chamado.codigo,
                    'protocolo': notif.chamado.protocolo
                }

            # Adicionar metadados
            metadados = notif.get_metadados()
            if metadados:
                notif_data['metadados'] = metadados

            notificacoes_list.append(notif_data)

        return json_response(notificacoes_list)

    except Exception as e:
        logger.error(f"Erro ao listar notificações: {str(e)}")
        return error_response('Erro interno no servidor')

@agente_api_bp.route('/api/agente/notificacoes/<int:notificacao_id>/marcar-lida', methods=['POST'])
@api_login_required
def marcar_notificacao_lida(notificacao_id):
    """Marca uma notificação como lida"""
    try:
        # Verificar se o usuário é um agente
        agente = AgenteSuporte.query.filter_by(usuario_id=current_user.id, ativo=True).first()
        if not agente:
            return error_response('Usuário não é um agente de suporte', 403)

        # Buscar notificação
        notificacao = NotificacaoAgente.query.filter_by(
            id=notificacao_id,
            agente_id=agente.id
        ).first()

        if not notificacao:
            return error_response('Notificação não encontrada', 404)

        notificacao.marcar_como_lida()

        return json_response({'message': 'Notificação marcada como lida'})

    except Exception as e:
        logger.error(f"Erro ao marcar notificação como lida: {str(e)}")
        return error_response('Erro interno no servidor')

@agente_api_bp.route('/api/agente/notificacoes/marcar-todas-lidas', methods=['POST'])
@api_login_required
def marcar_todas_notificacoes_lidas():
    """Marca todas as notificações como lidas"""
    try:
        # Verificar se o usuário é um agente
        agente = AgenteSuporte.query.filter_by(usuario_id=current_user.id, ativo=True).first()
        if not agente:
            return error_response('Usuário não é um agente de suporte', 403)

        # Marcar todas como lidas
        NotificacaoAgente.query.filter_by(
            agente_id=agente.id,
            lida=False
        ).update({
            'lida': True,
            'data_leitura': get_brazil_time().replace(tzinfo=None)
        })

        db.session.commit()

        return json_response({'message': 'Todas as notificações foram marcadas como lidas'})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao marcar todas as notificações como lidas: {str(e)}")
        return error_response('Erro interno no servidor')

@agente_api_bp.route('/api/agente/historico', methods=['GET'])
@api_login_required
def historico_atendimentos():
    """Lista histórico de atendimentos do agente com filtros"""
    try:
        # Verificar se o usuário é um agente
        agente = AgenteSuporte.query.filter_by(usuario_id=current_user.id, ativo=True).first()
        if not agente:
            return error_response('Usuário não é um agente de suporte', 403)

        # Parâmetros de filtro
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        status = request.args.get('status')
        limite = int(request.args.get('limite', 50))

        # Base query
        query = HistoricoAtendimento.query.filter_by(agente_id=agente.id)

        # Aplicar filtros
        if data_inicio:
            try:
                data_inicio_dt = datetime.strptime(data_inicio, '%Y-%m-%d')
                query = query.filter(HistoricoAtendimento.data_atribuicao >= data_inicio_dt)
            except ValueError:
                return error_response('Formato de data início inválido. Use YYYY-MM-DD', 400)

        if data_fim:
            try:
                data_fim_dt = datetime.strptime(data_fim, '%Y-%m-%d')
                # Adicionar 1 dia para incluir todo o dia
                data_fim_dt = data_fim_dt.replace(hour=23, minute=59, second=59)
                query = query.filter(HistoricoAtendimento.data_atribuicao <= data_fim_dt)
            except ValueError:
                return error_response('Formato de data fim inválido. Use YYYY-MM-DD', 400)

        if status and status != 'Todos':
            query = query.filter(HistoricoAtendimento.status_final == status)

        historico = query.order_by(HistoricoAtendimento.data_atribuicao.desc()).limit(limite).all()

        historico_list = []
        for hist in historico:
            hist_data = {
                'id': hist.id,
                'chamado': {
                    'id': hist.chamado.id,
                    'codigo': hist.chamado.codigo,
                    'protocolo': hist.chamado.protocolo,
                    'solicitante': hist.chamado.solicitante,
                    'problema': hist.chamado.problema
                },
                'status_inicial': hist.status_inicial,
                'status_final': hist.status_final or 'Em Andamento',
                'data_atribuicao': hist.data_atribuicao.strftime('%d/%m/%Y %H:%M'),
                'data_conclusao': hist.data_conclusao.strftime('%d/%m/%Y %H:%M') if hist.data_conclusao else None,
                'tempo_resolucao_min': hist.tempo_total_resolucao_min,
                'observacoes_finais': hist.observacoes_finais,
                'solucao_aplicada': hist.solucao_aplicada,
                'avaliacao_cliente': hist.avaliacao_cliente
            }

            # Adicionar informações de transferência se houver
            if hist.transferido_de:
                hist_data['transferido_de'] = f"{hist.transferido_de.usuario.nome} {hist.transferido_de.usuario.sobrenome}"
            if hist.transferido_para:
                hist_data['transferido_para'] = f"{hist.transferido_para.usuario.nome} {hist.transferido_para.usuario.sobrenome}"
                hist_data['motivo_transferencia'] = hist.motivo_transferencia

            historico_list.append(hist_data)

        return json_response(historico_list)

    except Exception as e:
        logger.error(f"Erro ao buscar histórico de atendimentos: {str(e)}")
        return error_response('Erro interno no servidor')
