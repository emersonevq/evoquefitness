from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from database import db, LogAcesso, LogAcao, SessaoAtiva, User, get_brazil_time
from auth.auth_helpers import setor_required
from setores.ti.painel import json_response, error_response
import logging
from datetime import datetime, timedelta
import pytz

auditoria_bp = Blueprint('auditoria', __name__)
logger = logging.getLogger(__name__)

BRAZIL_TZ = pytz.timezone('America/Sao_Paulo')

@auditoria_bp.route('/api/auditoria/logs-acesso', methods=['GET'])
@login_required
@setor_required('Administrador')
def listar_logs_acesso():
    """Lista logs de acesso com filtros opcionais e paginação"""
    try:
        # Parâmetros de filtro e paginação
        dias = request.args.get('dias', 7, type=int)
        usuario_id = request.args.get('usuario_id', type=int)
        ip_address = request.args.get('ip')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 5, type=int)

        # Data limite
        data_limite = get_brazil_time().replace(tzinfo=None) - timedelta(days=dias)

        # Query base - usar LEFT JOIN para incluir logs mesmo quando usuário foi deletado
        query = db.session.query(LogAcesso, User).outerjoin(User, LogAcesso.usuario_id == User.id)
        query = query.filter(LogAcesso.data_acesso >= data_limite)

        # Aplicar filtros
        if usuario_id:
            query = query.filter(LogAcesso.usuario_id == usuario_id)
        if ip_address:
            query = query.filter(LogAcesso.ip_address.like(f'%{ip_address}%'))

        # Ordenar por data mais recente e paginar
        logs_paginated = query.order_by(LogAcesso.data_acesso.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        logs_data = []
        for log, usuario in logs_paginated.items:
            # Calcular duração da sessão se ainda ativa
            duracao = log.duracao_sessao
            if log.ativo and not log.data_logout and log.data_acesso:
                delta = get_brazil_time().replace(tzinfo=None) - log.data_acesso
                duracao = int(delta.total_seconds() / 60)
            
            logs_data.append({
                'id': log.id,
                'usuario': {
                    'id': usuario.id if usuario else None,
                    'nome': f"{usuario.nome} {usuario.sobrenome}" if usuario else 'Usuário removido',
                    'email': usuario.email if usuario else 'N/A',
                    'nivel_acesso': usuario.nivel_acesso if usuario else 'N/A'
                },
                'data_acesso': log.data_acesso.strftime('%d/%m/%Y %H:%M:%S') if log.data_acesso else None,
                'data_logout': log.data_logout.strftime('%d/%m/%Y %H:%M:%S') if log.data_logout else None,
                'ip_address': log.ip_address,
                'navegador': log.navegador,
                'sistema_operacional': log.sistema_operacional,
                'dispositivo': log.dispositivo,
                'pais': log.pais,
                'cidade': log.cidade,
                'provedor_internet': log.provedor_internet,
                'duracao_minutos': duracao,
                'ativo': log.ativo,
                'session_id': log.session_id[:10] + '...' if log.session_id else None  # Truncar por segurança
            })

        return json_response({
            'logs': logs_data,
            'pagination': {
                'page': logs_paginated.page,
                'pages': logs_paginated.pages,
                'per_page': logs_paginated.per_page,
                'total': logs_paginated.total,
                'has_next': logs_paginated.has_next,
                'has_prev': logs_paginated.has_prev
            }
        })

    except Exception as e:
        logger.error(f"Erro ao listar logs de acesso: {str(e)}")
        return error_response('Erro interno do servidor')

@auditoria_bp.route('/api/auditoria/sessoes-ativas', methods=['GET'])
@login_required
@setor_required('Administrador')
def listar_sessoes_ativas():
    """Lista sessões ativas dos usuários"""
    try:
        # Considerar sessões ativas nas últimas 24 horas
        data_limite = get_brazil_time().replace(tzinfo=None) - timedelta(hours=24)
        
        sessoes = db.session.query(SessaoAtiva, User).join(User).filter(
            SessaoAtiva.ativo == True,
            SessaoAtiva.ultima_atividade >= data_limite
        ).order_by(SessaoAtiva.ultima_atividade.desc()).all()
        
        sessoes_data = []
        for sessao, usuario in sessoes:
            # Calcular tempo desde última atividade
            if sessao.ultima_atividade:
                delta = get_brazil_time().replace(tzinfo=None) - sessao.ultima_atividade
                minutos_inativo = int(delta.total_seconds() / 60)
                status = 'ativo' if minutos_inativo < 30 else 'inativo'
            else:
                minutos_inativo = 0
                status = 'desconhecido'
            
            sessoes_data.append({
                'id': sessao.id,
                'usuario': {
                    'id': usuario.id,
                    'nome': f"{usuario.nome} {usuario.sobrenome}",
                    'email': usuario.email,
                    'nivel_acesso': usuario.nivel_acesso
                },
                'data_inicio': sessao.data_inicio.strftime('%d/%m/%Y %H:%M:%S') if sessao.data_inicio else None,
                'ultima_atividade': sessao.ultima_atividade.strftime('%d/%m/%Y %H:%M:%S') if sessao.ultima_atividade else None,
                'ip_address': sessao.ip_address,
                'navegador': sessao.navegador,
                'sistema_operacional': sessao.sistema_operacional,
                'dispositivo': sessao.dispositivo,
                'pais': sessao.pais,
                'cidade': sessao.cidade,
                'duracao_minutos': sessao.get_duracao_minutos(),
                'minutos_inativo': minutos_inativo,
                'status': status
            })
        
        return json_response(sessoes_data)
        
    except Exception as e:
        logger.error(f"Erro ao listar sessões ativas: {str(e)}")
        return error_response('Erro interno do servidor')

@auditoria_bp.route('/api/auditoria/logs-acoes', methods=['GET'])
@login_required
@setor_required('Administrador')
def listar_logs_acoes():
    """Lista logs de ações dos usuários"""
    try:
        # Parâmetros de filtro
        dias = request.args.get('dias', 7, type=int)
        categoria = request.args.get('categoria')
        usuario_id = request.args.get('usuario_id', type=int)
        
        # Data limite
        data_limite = get_brazil_time().replace(tzinfo=None) - timedelta(days=dias)
        
        # Query base
        query = db.session.query(LogAcao, User).outerjoin(User, LogAcao.usuario_id == User.id)
        query = query.filter(LogAcao.data_acao >= data_limite)
        
        # Aplicar filtros
        if categoria:
            query = query.filter(LogAcao.categoria == categoria)
        if usuario_id:
            query = query.filter(LogAcao.usuario_id == usuario_id)
        
        # Ordenar por data mais recente
        logs = query.order_by(LogAcao.data_acao.desc()).limit(200).all()
        
        logs_data = []
        for log, usuario in logs:
            logs_data.append({
                'id': log.id,
                'usuario': {
                    'id': usuario.id if usuario else None,
                    'nome': f"{usuario.nome} {usuario.sobrenome}" if usuario else 'Sistema',
                    'email': usuario.email if usuario else None
                } if usuario else {'nome': 'Sistema'},
                'acao': log.acao,
                'categoria': log.categoria,
                'detalhes': log.detalhes,
                'data_acao': log.data_acao.strftime('%d/%m/%Y %H:%M:%S') if log.data_acao else None,
                'ip_address': log.ip_address,
                'sucesso': log.sucesso,
                'recurso_afetado': log.recurso_afetado,
                'tipo_recurso': log.tipo_recurso
            })
        
        return json_response(logs_data)
        
    except Exception as e:
        logger.error(f"Erro ao listar logs de ações: {str(e)}")
        return error_response('Erro interno do servidor')

@auditoria_bp.route('/api/auditoria/estatisticas', methods=['GET'])
@login_required
@setor_required('Administrador')
def obter_estatisticas_auditoria():
    """Obter estatísticas de auditoria"""
    try:
        agora = get_brazil_time().replace(tzinfo=None)
        hoje = agora.date()
        ontem = hoje - timedelta(days=1)
        ultima_semana = agora - timedelta(days=7)
        ultimo_mes = agora - timedelta(days=30)
        
        # Acessos hoje
        acessos_hoje = LogAcesso.query.filter(
            db.func.date(LogAcesso.data_acesso) == hoje
        ).count()
        
        # Acessos ontem
        acessos_ontem = LogAcesso.query.filter(
            db.func.date(LogAcesso.data_acesso) == ontem
        ).count()
        
        # Usuários únicos última semana
        usuarios_unicos_semana = db.session.query(LogAcesso.usuario_id).filter(
            LogAcesso.data_acesso >= ultima_semana
        ).distinct().count()
        
        # Sessões ativas agora (últimos 30 minutos)
        trinta_min_atras = agora - timedelta(minutes=30)
        sessoes_ativas_agora = SessaoAtiva.query.filter(
            SessaoAtiva.ativo == True,
            SessaoAtiva.ultima_atividade >= trinta_min_atras
        ).count()
        
        # Ações do sistema último mês
        acoes_ultimo_mes = LogAcao.query.filter(
            LogAcao.data_acao >= ultimo_mes
        ).count()
        
        # Top 5 IPs mais ativos
        top_ips = db.session.query(
            LogAcesso.ip_address,
            db.func.count(LogAcesso.id).label('total')
        ).filter(
            LogAcesso.data_acesso >= ultima_semana
        ).group_by(LogAcesso.ip_address).order_by(
            db.func.count(LogAcesso.id).desc()
        ).limit(5).all()
        
        estatisticas = {
            'acessos_hoje': acessos_hoje,
            'acessos_ontem': acessos_ontem,
            'usuarios_unicos_semana': usuarios_unicos_semana,
            'sessoes_ativas_agora': sessoes_ativas_agora,
            'acoes_ultimo_mes': acoes_ultimo_mes,
            'top_ips': [{'ip': ip, 'total': total} for ip, total in top_ips],
            'data_atualizacao': agora.strftime('%d/%m/%Y %H:%M:%S')
        }
        
        return json_response(estatisticas)
        
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {str(e)}")
        return error_response('Erro interno do servidor')

@auditoria_bp.route('/api/auditoria/encerrar-sessao/<int:sessao_id>', methods=['POST'])
@login_required
@setor_required('Administrador')
def encerrar_sessao(sessao_id):
    """Encerrar uma sessão ativa específica"""
    try:
        sessao = SessaoAtiva.query.get(sessao_id)
        if not sessao:
            return error_response('Sessão não encontrada', 404)
        
        # Marcar sessão como inativa
        sessao.ativo = False
        
        # Registrar log da ação
        from database import registrar_log_acao
        registrar_log_acao(
            usuario_id=current_user.id,
            acao=f'Sessão encerrada administrativamente',
            categoria='seguranca',
            detalhes=f'Sessão do usuário {sessao.usuario.nome} encerrada',
            ip_address=request.remote_addr,
            recurso_afetado=str(sessao_id),
            tipo_recurso='sessao'
        )
        
        db.session.commit()
        
        return json_response({'message': 'Sessão encerrada com sucesso'})
        
    except Exception as e:
        logger.error(f"Erro ao encerrar sessão: {str(e)}")
        db.session.rollback()
        return error_response('Erro interno do servidor')
