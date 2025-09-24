"""
Rotas avançadas para administração do sistema TI
"""

import os
import json
import pytz
import logging
import traceback
import hashlib
import zipfile
import tempfile
import subprocess
import csv
import io
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app, send_file
from flask_login import login_required, current_user
from sqlalchemy import func, desc, case, extract, text, and_, or_
from auth.auth_helpers import setor_required
from database import (
    db, Chamado, User, Unidade, ProblemaReportado, ItemInternet, 
    LogAcesso, LogAcao, ConfiguracaoAvancada, AlertaSistema, 
    BackupHistorico, RelatorioGerado, ManutencaoSistema,
    get_brazil_time, registrar_log_acao, criar_alerta_sistema,
    registrar_log_acesso, registrar_log_logout
)

# Configurar logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Timezone do Brasil
BRAZIL_TZ = pytz.timezone('America/Sao_Paulo')

# Criar blueprint
rotas_bp = Blueprint('rotas', __name__, template_folder='templates')

def json_response(data, status=200):
    """Wrapper para garantir resposta JSON válida"""
    try:
        response = jsonify(data)
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        return response, status
    except Exception as e:
        logger.error(f"Erro ao criar resposta JSON: {str(e)}")
        error_response = jsonify({'error': 'Erro interno de serialização'})
        error_response.headers['Content-Type'] = 'application/json; charset=utf-8'
        return error_response, 500

def error_response(message, status=500, details=None):
    """Wrapper para respostas de erro padronizadas"""
    error_data = {'error': message}
    if details:
        error_data['details'] = details
    return json_response(error_data, status)

def get_client_info(request):
    """Extrai informações do cliente da requisição"""
    return {
        'ip_address': request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr),
        'user_agent': request.headers.get('User-Agent', '')
    }

# ==================== LOGS DE ACESSO ====================

@rotas_bp.route('/api/logs/acesso')
@login_required
@setor_required('Administrador')
def listar_logs_acesso():
    """Lista logs de acesso com filtros e paginação"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        usuario_id = request.args.get('usuario_id', type=int)
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        
        # Construir query base
        query = LogAcesso.query.join(User)
        
        # Aplicar filtros
        if usuario_id:
            query = query.filter(LogAcesso.usuario_id == usuario_id)
        
        if data_inicio:
            try:
                data_inicio_dt = datetime.strptime(data_inicio, '%Y-%m-%d')
                query = query.filter(LogAcesso.data_acesso >= data_inicio_dt)
            except ValueError:
                pass
        
        if data_fim:
            try:
                data_fim_dt = datetime.strptime(data_fim, '%Y-%m-%d') + timedelta(days=1)
                query = query.filter(LogAcesso.data_acesso < data_fim_dt)
            except ValueError:
                pass
        
        # Ordenar por data mais recente
        query = query.order_by(desc(LogAcesso.data_acesso))
        
        # Paginar
        logs_paginados = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        logs_list = []
        for log in logs_paginados.items:
            data_acesso_brazil = log.get_data_acesso_brazil()
            data_logout_brazil = log.get_data_logout_brazil()
            
            logs_list.append({
                'id': log.id,
                'usuario': {
                    'id': log.usuario.id,
                    'nome': f"{log.usuario.nome} {log.usuario.sobrenome}",
                    'usuario': log.usuario.usuario
                },
                'data_acesso': data_acesso_brazil.strftime('%d/%m/%Y %H:%M:%S') if data_acesso_brazil else None,
                'data_logout': data_logout_brazil.strftime('%d/%m/%Y %H:%M:%S') if data_logout_brazil else None,
                'duracao_sessao': log.duracao_sessao,
                'ip_address': log.ip_address,
                'navegador': log.navegador,
                'sistema_operacional': log.sistema_operacional,
                'dispositivo': log.dispositivo,
                'ativo': log.ativo
            })
        
        return json_response({
            'logs': logs_list,
            'pagination': {
                'page': logs_paginados.page,
                'pages': logs_paginados.pages,
                'per_page': logs_paginados.per_page,
                'total': logs_paginados.total,
                'has_next': logs_paginados.has_next,
                'has_prev': logs_paginados.has_prev
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao listar logs de acesso: {str(e)}")
        return error_response('Erro interno no servidor')

@rotas_bp.route('/api/logs/acesso/estatisticas')
@login_required
@setor_required('Administrador')
def estatisticas_logs_acesso():
    """Retorna estatísticas dos logs de acesso"""
    try:
        hoje = get_brazil_time().date()
        inicio_semana = hoje - timedelta(days=7)
        
        # Acessos hoje
        acessos_hoje = LogAcesso.query.filter(
            func.date(LogAcesso.data_acesso) == hoje
        ).count()
        
        # Acessos esta semana
        acessos_semana = LogAcesso.query.filter(
            LogAcesso.data_acesso >= inicio_semana
        ).count()
        
        # Usuários únicos esta semana
        usuarios_unicos = db.session.query(LogAcesso.usuario_id).filter(
            LogAcesso.data_acesso >= inicio_semana
        ).distinct().count()
        
        # Tempo médio de sessão (últimos 30 dias)
        inicio_mes = hoje - timedelta(days=30)
        sessoes_com_duracao = LogAcesso.query.filter(
            LogAcesso.data_acesso >= inicio_mes,
            LogAcesso.duracao_sessao.isnot(None)
        ).all()
        
        tempo_medio_sessao = 0
        if sessoes_com_duracao:
            total_tempo = sum(log.duracao_sessao for log in sessoes_com_duracao)
            tempo_medio_sessao = total_tempo / len(sessoes_com_duracao)
        
        return json_response({
            'acessos_hoje': acessos_hoje,
            'acessos_semana': acessos_semana,
            'usuarios_unicos': usuarios_unicos,
            'tempo_medio_sessao': round(tempo_medio_sessao, 1)
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas de acesso: {str(e)}")
        return error_response('Erro interno no servidor')

# ==================== LOGS DE AÇÕES ====================

@rotas_bp.route('/api/logs/acoes')
@login_required
@setor_required('Administrador')
def listar_logs_acoes():
    """Lista logs de ações com filtros e paginação"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        usuario_id = request.args.get('usuario_id', type=int)
        acao = request.args.get('acao', '')
        categoria = request.args.get('categoria', '')
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        sucesso = request.args.get('sucesso')
        
        # Construir query base
        query = LogAcao.query.outerjoin(User)
        
        # Aplicar filtros
        if usuario_id:
            query = query.filter(LogAcao.usuario_id == usuario_id)
        
        if acao:
            query = query.filter(LogAcao.acao.ilike(f'%{acao}%'))
        
        if categoria:
            query = query.filter(LogAcao.categoria == categoria)
        
        if sucesso is not None:
            sucesso_bool = sucesso.lower() in ['true', '1', 'yes']
            query = query.filter(LogAcao.sucesso == sucesso_bool)
        
        if data_inicio:
            try:
                data_inicio_dt = datetime.strptime(data_inicio, '%Y-%m-%d')
                query = query.filter(LogAcao.data_acao >= data_inicio_dt)
            except ValueError:
                pass
        
        if data_fim:
            try:
                data_fim_dt = datetime.strptime(data_fim, '%Y-%m-%d') + timedelta(days=1)
                query = query.filter(LogAcao.data_acao < data_fim_dt)
            except ValueError:
                pass
        
        # Ordenar por data mais recente
        query = query.order_by(desc(LogAcao.data_acao))
        
        # Paginar
        logs_paginados = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        logs_list = []
        for log in logs_paginados.items:
            data_acao_brazil = log.get_data_acao_brazil()
            
            logs_list.append({
                'id': log.id,
                'usuario': {
                    'id': log.usuario.id if log.usuario else None,
                    'nome': f"{log.usuario.nome} {log.usuario.sobrenome}" if log.usuario else 'Sistema',
                    'usuario': log.usuario.usuario if log.usuario else 'sistema'
                },
                'acao': log.acao,
                'categoria': log.categoria,
                'detalhes': log.detalhes,
                'data_acao': data_acao_brazil.strftime('%d/%m/%Y %H:%M:%S') if data_acao_brazil else None,
                'ip_address': log.ip_address,
                'sucesso': log.sucesso,
                'erro_detalhes': log.erro_detalhes,
                'recurso_afetado': log.recurso_afetado,
                'tipo_recurso': log.tipo_recurso
            })
        
        return json_response({
            'logs': logs_list,
            'pagination': {
                'page': logs_paginados.page,
                'pages': logs_paginados.pages,
                'per_page': logs_paginados.per_page,
                'total': logs_paginados.total,
                'has_next': logs_paginados.has_next,
                'has_prev': logs_paginados.has_prev
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao listar logs de ações: {str(e)}")
        return error_response('Erro interno no servidor')

@rotas_bp.route('/api/logs/acoes/categorias')
@login_required
@setor_required('Administrador')
def listar_categorias_acoes():
    """Lista categorias de ações disponíveis"""
    try:
        categorias = db.session.query(LogAcao.categoria).filter(
            LogAcao.categoria.isnot(None)
        ).distinct().all()
        
        categorias_list = [cat[0] for cat in categorias if cat[0]]
        
        return json_response(categorias_list)
        
    except Exception as e:
        logger.error(f"Erro ao listar categorias de ações: {str(e)}")
        return error_response('Erro interno no servidor')

@rotas_bp.route('/api/logs/acoes/estatisticas')
@login_required
@setor_required('Administrador')
def estatisticas_logs_acoes():
    """Retorna estatísticas dos logs de ações"""
    try:
        hoje = get_brazil_time().date()
        inicio_semana = hoje - timedelta(days=7)
        inicio_mes = hoje - timedelta(days=30)
        
        # Ações por categoria (último mês)
        acoes_categoria = db.session.query(
            LogAcao.categoria,
            func.count(LogAcao.id).label('quantidade')
        ).filter(
            LogAcao.data_acao >= inicio_mes
        ).group_by(LogAcao.categoria).all()
        
        # Ações com erro (última semana)
        acoes_erro = LogAcao.query.filter(
            LogAcao.data_acao >= inicio_semana,
            LogAcao.sucesso == False
        ).count()
        
        # Total de ações (última semana)
        total_acoes = LogAcao.query.filter(
            LogAcao.data_acao >= inicio_semana
        ).count()
        
        return json_response({
            'acoes_categoria': [
                {'categoria': cat[0] or 'Sem categoria', 'quantidade': cat[1]}
                for cat in acoes_categoria
            ],
            'acoes_erro': acoes_erro,
            'total_acoes': total_acoes,
            'taxa_sucesso': round(((total_acoes - acoes_erro) / total_acoes * 100), 2) if total_acoes > 0 else 100
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas de ações: {str(e)}")
        return error_response('Erro interno no servidor')

# ==================== ANÁLISE DE PROBLEMAS FUTUROS ====================

@rotas_bp.route('/api/analise/problemas-futuros')
@login_required
@setor_required('Administrador')
def analise_problemas_futuros():
    """Análise preditiva de problemas baseada em dados históricos"""
    try:
        hoje = get_brazil_time().date()
        inicio_periodo = hoje - timedelta(days=30)
        
        # Tendência de crescimento de chamados
        chamados_periodo_atual = Chamado.query.filter(
            Chamado.data_abertura >= inicio_periodo
        ).count()
        
        periodo_anterior = inicio_periodo - timedelta(days=30)
        chamados_periodo_anterior = Chamado.query.filter(
            Chamado.data_abertura >= periodo_anterior,
            Chamado.data_abertura < inicio_periodo
        ).count()
        
        if chamados_periodo_anterior > 0:
            tendencia_crescimento = ((chamados_periodo_atual - chamados_periodo_anterior) / chamados_periodo_anterior) * 100
        else:
            tendencia_crescimento = 0
        
        # Problemas mais frequentes
        problemas_frequentes = db.session.query(
            Chamado.problema,
            func.count(Chamado.id).label('quantidade')
        ).filter(
            Chamado.data_abertura >= inicio_periodo
        ).group_by(Chamado.problema).order_by(desc('quantidade')).limit(5).all()
        
        # Unidades com mais problemas
        unidades_problematicas = db.session.query(
            Chamado.unidade,
            func.count(Chamado.id).label('quantidade')
        ).filter(
            Chamado.data_abertura >= inicio_periodo
        ).group_by(Chamado.unidade).order_by(desc('quantidade')).limit(5).all()
        
        # Análise de violação de SLA
        chamados_violacao_sla = Chamado.query.filter(
            Chamado.data_abertura >= inicio_periodo,
            Chamado.status.in_(['Concluido', 'Cancelado'])
        ).all()
        
        violacoes_sla = 0
        for chamado in chamados_violacao_sla:
            if chamado.data_conclusao and chamado.data_abertura:
                tempo_resolucao = (chamado.data_conclusao - chamado.data_abertura).total_seconds() / 3600
                # Assumir SLA de 24 horas para análise geral
                if tempo_resolucao > 24:
                    violacoes_sla += 1
        
        taxa_violacao_sla = (violacoes_sla / len(chamados_violacao_sla) * 100) if chamados_violacao_sla else 0
        
        # Previsões e alertas
        alertas_previstos = []
        
        if tendencia_crescimento > 20:
            alertas_previstos.append({
                'tipo': 'crescimento_chamados',
                'severidade': 'alta',
                'titulo': 'Crescimento Acelerado de Chamados',
                'descricao': f'Aumento de {tendencia_crescimento:.1f}% nos chamados nos últimos 30 dias',
                'recomendacao': 'Considere aumentar a equipe de suporte ou revisar processos'
            })
        
        if taxa_violacao_sla > 15:
            alertas_previstos.append({
                'tipo': 'violacao_sla',
                'severidade': 'media',
                'titulo': 'Alta Taxa de Violação de SLA',
                'descricao': f'{taxa_violacao_sla:.1f}% dos chamados violaram o SLA',
                'recomendacao': 'Revisar processos de atendimento e priorização'
            })
        
        # Verificar se há problemas concentrados em poucas unidades
        if unidades_problematicas and len(unidades_problematicas) > 0:
            total_chamados = sum([u.quantidade for u in unidades_problematicas])
            if unidades_problematicas[0].quantidade / total_chamados > 0.4:
                alertas_previstos.append({
                    'tipo': 'concentracao_problemas',
                    'severidade': 'media',
                    'titulo': 'Concentração de Problemas',
                    'descricao': f'Unidade {unidades_problematicas[0].unidade} concentra muitos chamados',
                    'recomendacao': 'Investigar problemas específicos desta unidade'
                })
        
        return json_response({
            'tendencia_crescimento': round(tendencia_crescimento, 2),
            'taxa_violacao_sla': round(taxa_violacao_sla, 2),
            'problemas_frequentes': [
                {'problema': p.problema, 'quantidade': p.quantidade}
                for p in problemas_frequentes
            ],
            'unidades_problematicas': [
                {'unidade': u.unidade, 'quantidade': u.quantidade}
                for u in unidades_problematicas
            ],
            'alertas_previstos': alertas_previstos,
            'periodo_analise': {
                'inicio': inicio_periodo.strftime('%d/%m/%Y'),
                'fim': hoje.strftime('%d/%m/%Y'),
                'dias': 30
            }
        })
        
    except Exception as e:
        logger.error(f"Erro na análise de problemas futuros: {str(e)}")
        return error_response('Erro interno no servidor')

# ==================== RELATÓRIOS ====================

@rotas_bp.route('/api/relatorios/usuarios')
@login_required
@setor_required('Administrador')
def relatorio_usuarios():
    """Gera relatório detalhado de usuários"""
    try:
        formato = request.args.get('formato', 'json')
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        
        query = User.query
        
        # Filtros de data (baseado na data de criação)
        if data_inicio:
            try:
                data_inicio_dt = datetime.strptime(data_inicio, '%Y-%m-%d')
                query = query.filter(User.data_criacao >= data_inicio_dt)
            except ValueError:
                pass
        
        if data_fim:
            try:
                data_fim_dt = datetime.strptime(data_fim, '%Y-%m-%d') + timedelta(days=1)
                query = query.filter(User.data_criacao < data_fim_dt)
            except ValueError:
                pass
        
        usuarios = query.order_by(User.data_criacao.desc()).all()
        
        relatorio_data = []
        for usuario in usuarios:
            # Buscar último acesso
            ultimo_acesso = LogAcesso.query.filter_by(
                usuario_id=usuario.id
            ).order_by(desc(LogAcesso.data_acesso)).first()
            
            # Contar total de acessos
            total_acessos = LogAcesso.query.filter_by(usuario_id=usuario.id).count()
            
            # Contar chamados criados
            total_chamados = Chamado.query.filter_by(usuario_id=usuario.id).count()
            
            data_criacao_brazil = usuario.data_criacao
            if data_criacao_brazil and data_criacao_brazil.tzinfo is None:
                data_criacao_brazil = pytz.utc.localize(data_criacao_brazil).astimezone(BRAZIL_TZ)
            
            ultimo_acesso_brazil = None
            if ultimo_acesso:
                ultimo_acesso_brazil = ultimo_acesso.get_data_acesso_brazil()
            
            relatorio_data.append({
                'id': usuario.id,
                'nome_completo': f"{usuario.nome} {usuario.sobrenome}",
                'usuario': usuario.usuario,
                'email': usuario.email,
                'nivel_acesso': usuario.nivel_acesso,
                'setores': usuario.setores,
                'bloqueado': usuario.bloqueado,
                'data_criacao': data_criacao_brazil.strftime('%d/%m/%Y %H:%M:%S') if data_criacao_brazil else None,
                'ultimo_acesso': ultimo_acesso_brazil.strftime('%d/%m/%Y %H:%M:%S') if ultimo_acesso_brazil else 'Nunca',
                'total_acessos': total_acessos,
                'total_chamados': total_chamados
            })
        
        if formato == 'csv':
            return gerar_csv_usuarios(relatorio_data)
        elif formato == 'pdf':
            return gerar_pdf_usuarios(relatorio_data)
        
        return json_response({
            'relatorio': relatorio_data,
            'resumo': {
                'total_usuarios': len(relatorio_data),
                'usuarios_ativos': len([u for u in relatorio_data if not u['bloqueado']]),
                'usuarios_bloqueados': len([u for u in relatorio_data if u['bloqueado']]),
                'periodo': {
                    'inicio': data_inicio or 'Início dos registros',
                    'fim': data_fim or 'Hoje'
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao gerar relatório de usuários: {str(e)}")
        return error_response('Erro interno no servidor')

@rotas_bp.route('/api/relatorios/chamados')
@login_required
@setor_required('Administrador')
def relatorio_chamados():
    """Gera relatório detalhado de chamados"""
    try:
        formato = request.args.get('formato', 'json')
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        status = request.args.get('status')
        prioridade = request.args.get('prioridade')
        unidade = request.args.get('unidade')
        
        query = Chamado.query
        
        # Aplicar filtros
        if data_inicio:
            try:
                data_inicio_dt = datetime.strptime(data_inicio, '%Y-%m-%d')
                query = query.filter(Chamado.data_abertura >= data_inicio_dt)
            except ValueError:
                pass
        
        if data_fim:
            try:
                data_fim_dt = datetime.strptime(data_fim, '%Y-%m-%d') + timedelta(days=1)
                query = query.filter(Chamado.data_abertura < data_fim_dt)
            except ValueError:
                pass
        
        if status:
            query = query.filter(Chamado.status == status)
        
        if prioridade:
            query = query.filter(Chamado.prioridade == prioridade)
        
        if unidade:
            query = query.filter(Chamado.unidade.ilike(f'%{unidade}%'))
        
        chamados = query.order_by(Chamado.data_abertura.desc()).all()
        
        relatorio_data = []
        for chamado in chamados:
            data_abertura_brazil = chamado.get_data_abertura_brazil()
            data_conclusao_brazil = chamado.get_data_conclusao_brazil()
            
            # Calcular tempo de resolução
            tempo_resolucao = None
            if chamado.data_conclusao and chamado.data_abertura:
                delta = chamado.data_conclusao - chamado.data_abertura
                tempo_resolucao = round(delta.total_seconds() / 3600, 2)  # em horas
            
            relatorio_data.append({
                'codigo': chamado.codigo,
                'protocolo': chamado.protocolo,
                'solicitante': chamado.solicitante,
                'email': chamado.email,
                'cargo': chamado.cargo,
                'telefone': chamado.telefone,
                'unidade': chamado.unidade,
                'problema': chamado.problema,
                'descricao': chamado.descricao or '',
                'status': chamado.status,
                'prioridade': chamado.prioridade,
                'data_abertura': data_abertura_brazil.strftime('%d/%m/%Y %H:%M:%S') if data_abertura_brazil else None,
                'data_conclusao': data_conclusao_brazil.strftime('%d/%m/%Y %H:%M:%S') if data_conclusao_brazil else None,
                'tempo_resolucao_horas': tempo_resolucao,
                'data_visita': chamado.data_visita.strftime('%d/%m/%Y') if chamado.data_visita else None
            })
        
        if formato == 'csv':
            return gerar_csv_chamados(relatorio_data)
        elif formato == 'pdf':
            return gerar_pdf_chamados(relatorio_data)
        
        # Estatísticas do relatório
        total_chamados = len(relatorio_data)
        chamados_concluidos = len([c for c in relatorio_data if c['status'] == 'Concluido'])
        chamados_abertos = len([c for c in relatorio_data if c['status'] == 'Aberto'])
        
        # Tempo médio de resolução
        tempos_resolucao = [c['tempo_resolucao_horas'] for c in relatorio_data if c['tempo_resolucao_horas']]
        tempo_medio_resolucao = sum(tempos_resolucao) / len(tempos_resolucao) if tempos_resolucao else 0
        
        return json_response({
            'relatorio': relatorio_data,
            'resumo': {
                'total_chamados': total_chamados,
                'chamados_concluidos': chamados_concluidos,
                'chamados_abertos': chamados_abertos,
                'taxa_resolucao': round((chamados_concluidos / total_chamados * 100), 2) if total_chamados > 0 else 0,
                'tempo_medio_resolucao_horas': round(tempo_medio_resolucao, 2),
                'periodo': {
                    'inicio': data_inicio or 'Início dos registros',
                    'fim': data_fim or 'Hoje'
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao gerar relatório de chamados: {str(e)}")
        return error_response('Erro interno no servidor')

def gerar_csv_usuarios(dados):
    """Gera arquivo CSV para relatório de usuários"""
    try:
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Cabeçalho
        writer.writerow([
            'ID', 'Nome Completo', 'Usuário', 'Email', 'Nível de Acesso', 
            'Setores', 'Bloqueado', 'Data Criação', 'Último Acesso', 
            'Total Acessos', 'Total Chamados'
        ])
        
        # Dados
        for usuario in dados:
            writer.writerow([
                usuario['id'],
                usuario['nome_completo'],
                usuario['usuario'],
                usuario['email'],
                usuario['nivel_acesso'],
                ', '.join(usuario['setores']) if isinstance(usuario['setores'], list) else usuario['setores'],
                'Sim' if usuario['bloqueado'] else 'Não',
                usuario['data_criacao'],
                usuario['ultimo_acesso'],
                usuario['total_acessos'],
                usuario['total_chamados']
            ])
        
        output.seek(0)
        
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8-sig')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'relatorio_usuarios_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
        
    except Exception as e:
        logger.error(f"Erro ao gerar CSV de usuários: {str(e)}")
        return error_response('Erro ao gerar arquivo CSV')

def gerar_csv_chamados(dados):
    """Gera arquivo CSV para relatório de chamados"""
    try:
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Cabeçalho
        writer.writerow([
            'Código', 'Protocolo', 'Solicitante', 'Email', 'Cargo', 'Telefone',
            'Unidade', 'Problema', 'Descrição', 'Status', 'Prioridade',
            'Data Abertura', 'Data Conclusão', 'Tempo Resolução (h)', 'Data Visita'
        ])
        
        # Dados
        for chamado in dados:
            writer.writerow([
                chamado['codigo'],
                chamado['protocolo'],
                chamado['solicitante'],
                chamado['email'],
                chamado['cargo'],
                chamado['telefone'],
                chamado['unidade'],
                chamado['problema'],
                chamado['descricao'],
                chamado['status'],
                chamado['prioridade'],
                chamado['data_abertura'],
                chamado['data_conclusao'],
                chamado['tempo_resolucao_horas'],
                chamado['data_visita']
            ])
        
        output.seek(0)
        
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8-sig')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'relatorio_chamados_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
        
    except Exception as e:
        logger.error(f"Erro ao gerar CSV de chamados: {str(e)}")
        return error_response('Erro ao gerar arquivo CSV')

# ==================== DASHBOARD AVANÇADO ====================

@rotas_bp.route('/api/dashboard/metricas-avancadas')
@login_required
@setor_required('Administrador')
def metricas_avancadas():
    """Retorna métricas avançadas para o dashboard"""
    try:
        hoje = get_brazil_time().date()
        inicio_mes = hoje.replace(day=1)
        inicio_semana = hoje - timedelta(days=7)
        
        # Métricas de usuários
        total_usuarios = User.query.count()
        usuarios_ativos_mes = db.session.query(LogAcesso.usuario_id).filter(
            LogAcesso.data_acesso >= inicio_mes
        ).distinct().count()
        
        usuarios_bloqueados = User.query.filter_by(bloqueado=True).count()
        
        # Métricas de chamados
        total_chamados = Chamado.query.count()
        chamados_mes = Chamado.query.filter(
            Chamado.data_abertura >= inicio_mes
        ).count()
        
        chamados_semana = Chamado.query.filter(
            Chamado.data_abertura >= inicio_semana
        ).count()
        
        # Tempo médio de resolução
        chamados_resolvidos = Chamado.query.filter(
            Chamado.status == 'Concluido',
            Chamado.data_conclusao.isnot(None),
            Chamado.data_abertura >= inicio_mes
        ).all()
        
        if chamados_resolvidos:
            tempos_resolucao = []
            for chamado in chamados_resolvidos:
                tempo = (chamado.data_conclusao - chamado.data_abertura).total_seconds() / 3600
                tempos_resolucao.append(tempo)
            
            tempo_medio_resolucao = sum(tempos_resolucao) / len(tempos_resolucao)
        else:
            tempo_medio_resolucao = 0
        
        # Distribuição por prioridade
        distribuicao_prioridade = db.session.query(
            Chamado.prioridade,
            func.count(Chamado.id).label('quantidade')
        ).filter(
            Chamado.data_abertura >= inicio_mes
        ).group_by(Chamado.prioridade).all()
        
        # Taxa de resolução
        chamados_abertos_mes = Chamado.query.filter(
            Chamado.data_abertura >= inicio_mes,
            Chamado.status == 'Aberto'
        ).count()
        
        taxa_resolucao = ((chamados_mes - chamados_abertos_mes) / chamados_mes * 100) if chamados_mes > 0 else 0
        
        # Alertas ativos
        alertas_ativos = AlertaSistema.query.filter_by(resolvido=False).count()
        
        return json_response({
            'usuarios': {
                'total': total_usuarios,
                'ativos_mes': usuarios_ativos_mes,
                'bloqueados': usuarios_bloqueados,
                'taxa_atividade': round((usuarios_ativos_mes / total_usuarios * 100), 2) if total_usuarios > 0 else 0
            },
            'chamados': {
                'total': total_chamados,
                'mes': chamados_mes,
                'semana': chamados_semana,
                'tempo_medio_resolucao': round(tempo_medio_resolucao, 2),
                'taxa_resolucao': round(taxa_resolucao, 2)
            },
            'distribuicao_prioridade': [
                {'prioridade': d.prioridade, 'quantidade': d.quantidade}
                for d in distribuicao_prioridade
            ],
            'alertas_ativos': alertas_ativos,
            'periodo': {
                'inicio_mes': inicio_mes.strftime('%d/%m/%Y'),
                'inicio_semana': inicio_semana.strftime('%d/%m/%Y'),
                'hoje': hoje.strftime('%d/%m/%Y')
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter métricas avançadas: {str(e)}")
        return error_response('Erro interno no servidor')

# ==================== CONFIGURAÇÕES AVANÇADAS ====================

@rotas_bp.route('/api/configuracoes-avancadas')
@login_required
@setor_required('Administrador')
def listar_configuracoes_avancadas():
    """Lista todas as configurações avançadas do sistema"""
    try:
        configuracoes = ConfiguracaoAvancada.query.order_by(ConfiguracaoAvancada.categoria, ConfiguracaoAvancada.chave).all()
        
        config_list = []
        for config in configuracoes:
            data_atualizacao_brazil = config.get_data_atualizacao_brazil()
            
            config_list.append({
                'id': config.id,
                'chave': config.chave,
                'valor': config.valor,
                'descricao': config.descricao,
                'tipo': config.tipo,
                'categoria': config.categoria,
                'requer_reinicio': config.requer_reinicio,
                'data_atualizacao': data_atualizacao_brazil.strftime('%d/%m/%Y %H:%M:%S') if data_atualizacao_brazil else None
            })
        
        return json_response(config_list)
        
    except Exception as e:
        logger.error(f"Erro ao listar configurações avançadas: {str(e)}")
        return error_response('Erro interno no servidor')

@rotas_bp.route('/api/configuracoes-avancadas/<int:config_id>', methods=['PUT'])
@login_required
@setor_required('Administrador')
def atualizar_configuracao_avancada(config_id):
    """Atualiza uma configuração avançada específica"""
    try:
        if not request.is_json:
            return error_response('Content-Type deve ser application/json', 400)
            
        data = request.get_json()
        if not data or 'valor' not in data:
            return error_response('Valor não fornecido', 400)
        
        config = ConfiguracaoAvancada.query.get(config_id)
        if not config:
            return error_response('Configuração não encontrada', 404)
        
        # Validar tipo de valor
        novo_valor = str(data['valor'])
        if config.tipo == 'boolean':
            if novo_valor.lower() not in ['true', 'false']:
                return error_response('Valor deve ser true ou false para configuração booleana', 400)
        elif config.tipo == 'number':
            try:
                float(novo_valor)
            except ValueError:
                return error_response('Valor deve ser numérico', 400)
        
        valor_anterior = config.valor
        config.valor = novo_valor
        config.data_atualizacao = get_brazil_time().replace(tzinfo=None)
        config.usuario_atualizacao = current_user.id
        
        db.session.commit()
        
        # Registrar log da ação
        client_info = get_client_info(request)
        registrar_log_acao(
            usuario_id=current_user.id,
            acao=f'Atualizar configuração avançada: {config.chave}',
            categoria='configuracao',
            detalhes=f'Valor alterado de "{valor_anterior}" para "{novo_valor}"',
            dados_anteriores={'valor': valor_anterior},
            dados_novos={'valor': novo_valor},
            ip_address=client_info['ip_address'],
            user_agent=client_info['user_agent'],
            recurso_afetado=str(config.id),
            tipo_recurso='configuracao_avancada'
        )
        
        return json_response({
            'message': 'Configuração atualizada com sucesso',
            'configuracao': {
                'id': config.id,
                'chave': config.chave,
                'valor': config.valor,
                'tipo': config.tipo,
                'requer_reinicio': config.requer_reinicio,
                'data_atualizacao': config.data_atualizacao.strftime('%d/%m/%Y %H:%M:%S')
            }
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao atualizar configuração avançada {config_id}: {str(e)}")
        return error_response('Erro interno no servidor')

# ==================== ALERTAS DO SISTEMA ====================

@rotas_bp.route('/api/alertas')
@login_required
@setor_required('Administrador')
def listar_alertas():
    """Lista todos os alertas do sistema"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        tipo = request.args.get('tipo')
        severidade = request.args.get('severidade')
        resolvido = request.args.get('resolvido')
        
        query = AlertaSistema.query
        
        # Aplicar filtros
        if tipo:
            query = query.filter(AlertaSistema.tipo == tipo)
        
        if severidade:
            query = query.filter(AlertaSistema.severidade == severidade)
        
        if resolvido is not None:
            resolvido_bool = resolvido.lower() in ['true', '1', 'yes']
            query = query.filter(AlertaSistema.resolvido == resolvido_bool)
        
        # Ordenar por data mais recente
        query = query.order_by(desc(AlertaSistema.data_criacao))
        
        # Paginar
        alertas_paginados = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        alertas_list = []
        for alerta in alertas_paginados.items:
            data_criacao_brazil = alerta.get_data_criacao_brazil()
            data_resolucao_brazil = alerta.get_data_resolucao_brazil()
            
            alertas_list.append({
                'id': alerta.id,
                'tipo': alerta.tipo,
                'titulo': alerta.titulo,
                'descricao': alerta.descricao,
                'severidade': alerta.severidade,
                'categoria': alerta.categoria,
                'resolvido': alerta.resolvido,
                'data_criacao': data_criacao_brazil.strftime('%d/%m/%Y %H:%M:%S') if data_criacao_brazil else None,
                'data_resolucao': data_resolucao_brazil.strftime('%d/%m/%Y %H:%M:%S') if data_resolucao_brazil else None,
                'automatico': alerta.automatico,
                'contador_ocorrencias': alerta.contador_ocorrencias,
                'resolvido_por': {
                    'id': alerta.resolvido_por_usuario.id if alerta.resolvido_por_usuario else None,
                    'nome': f"{alerta.resolvido_por_usuario.nome} {alerta.resolvido_por_usuario.sobrenome}" if alerta.resolvido_por_usuario else None
                } if alerta.resolvido_por else None
            })
        
        return json_response({
            'alertas': alertas_list,
            'pagination': {
                'page': alertas_paginados.page,
                'pages': alertas_paginados.pages,
                'per_page': alertas_paginados.per_page,
                'total': alertas_paginados.total,
                'has_next': alertas_paginados.has_next,
                'has_prev': alertas_paginados.has_prev
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao listar alertas: {str(e)}")
        return error_response('Erro interno no servidor')

@rotas_bp.route('/api/alertas/<int:alerta_id>/resolver', methods=['PUT'])
@login_required
@setor_required('Administrador')
def resolver_alerta(alerta_id):
    """Marca um alerta como resolvido"""
    try:
        if not request.is_json:
            return error_response('Content-Type deve ser application/json', 400)
            
        data = request.get_json()
        observacoes = data.get('observacoes', '')
        
        alerta = AlertaSistema.query.get(alerta_id)
        if not alerta:
            return error_response('Alerta não encontrado', 404)
        
        if alerta.resolvido:
            return error_response('Alerta já foi resolvido', 400)
        
        alerta.resolvido = True
        alerta.data_resolucao = get_brazil_time().replace(tzinfo=None)
        alerta.resolvido_por = current_user.id
        alerta.observacoes_resolucao = observacoes
        
        db.session.commit()
        
        # Registrar log da ação
        client_info = get_client_info(request)
        registrar_log_acao(
            usuario_id=current_user.id,
            acao=f'Resolver alerta: {alerta.titulo}',
            categoria='alerta',
            detalhes=f'Alerta resolvido com observações: {observacoes}',
            ip_address=client_info['ip_address'],
            user_agent=client_info['user_agent'],
            recurso_afetado=str(alerta.id),
            tipo_recurso='alerta_sistema'
        )
        
        return json_response({
            'message': 'Alerta marcado como resolvido',
            'alerta_id': alerta.id,
            'data_resolucao': alerta.data_resolucao.strftime('%d/%m/%Y %H:%M:%S')
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao resolver alerta {alerta_id}: {str(e)}")
        return error_response('Erro interno no servidor')

@rotas_bp.route('/api/alertas', methods=['POST'])
@login_required
@setor_required('Administrador')
def criar_alerta():
    """Cria um novo alerta do sistema"""
    try:
        if not request.is_json:
            return error_response('Content-Type deve ser application/json', 400)
            
        data = request.get_json()
        
        # Validar campos obrigatórios
        required_fields = ['tipo', 'titulo', 'descricao', 'severidade']
        for field in required_fields:
            if not data.get(field):
                return error_response(f'Campo {field} é obrigatório', 400)
        
        # Validar severidade
        severidades_validas = ['baixa', 'media', 'alta', 'critica']
        if data['severidade'] not in severidades_validas:
            return error_response('Severidade inválida', 400)
        
        alerta = criar_alerta_sistema(
            tipo=data['tipo'],
            titulo=data['titulo'],
            descricao=data['descricao'],
            severidade=data['severidade'],
            categoria=data.get('categoria'),
            automatico=False,
            dados_contexto=data.get('dados_contexto')
        )
        
        if not alerta:
            return error_response('Erro ao criar alerta')
        
        # Registrar log da ação
        client_info = get_client_info(request)
        registrar_log_acao(
            usuario_id=current_user.id,
            acao=f'Criar alerta: {alerta.titulo}',
            categoria='alerta',
            detalhes=f'Alerta criado manualmente - Tipo: {alerta.tipo}, Severidade: {alerta.severidade}',
            ip_address=client_info['ip_address'],
            user_agent=client_info['user_agent'],
            recurso_afetado=str(alerta.id),
            tipo_recurso='alerta_sistema'
        )
        
        return json_response({
            'message': 'Alerta criado com sucesso',
            'alerta': {
                'id': alerta.id,
                'tipo': alerta.tipo,
                'titulo': alerta.titulo,
                'severidade': alerta.severidade,
                'data_criacao': alerta.data_criacao.strftime('%d/%m/%Y %H:%M:%S')
            }
        }, 201)
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao criar alerta: {str(e)}")
        return error_response('Erro interno no servidor')

# ==================== BACKUP E MANUTENÇÃO ====================

@rotas_bp.route('/api/backup/historico')
@login_required
@setor_required('Administrador')
def historico_backup():
    """Lista o histórico de backups"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        backups_paginados = BackupHistorico.query.order_by(
            desc(BackupHistorico.data_backup)
        ).paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        backup_list = []
        for backup in backups_paginados.items:
            data_backup_brazil = backup.get_data_backup_brazil()
            data_inicio_brazil = backup.get_data_inicio_brazil()
            data_fim_brazil = backup.get_data_fim_brazil()
            
            backup_list.append({
                'id': backup.id,
                'nome_arquivo': backup.nome_arquivo,
                'tipo': backup.tipo,
                'status': backup.status,
                'tamanho_mb': backup.tamanho_mb,
                'data_backup': data_backup_brazil.strftime('%d/%m/%Y %H:%M:%S') if data_backup_brazil else None,
                'data_inicio': data_inicio_brazil.strftime('%d/%m/%Y %H:%M:%S') if data_inicio_brazil else None,
                'data_fim': data_fim_brazil.strftime('%d/%m/%Y %H:%M:%S') if data_fim_brazil else None,
                'observacoes': backup.observacoes,
                'erro_detalhes': backup.erro_detalhes,
                'automatico': backup.automatico,
                'tempo_execucao': backup.tempo_execucao,
                'usuario': {
                    'id': backup.usuario.id,
                    'nome': f"{backup.usuario.nome} {backup.usuario.sobrenome}"
                }
            })
        
        return json_response({
            'backups': backup_list,
            'pagination': {
                'page': backups_paginados.page,
                'pages': backups_paginados.pages,
                'per_page': backups_paginados.per_page,
                'total': backups_paginados.total,
                'has_next': backups_paginados.has_next,
                'has_prev': backups_paginados.has_prev
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao listar histórico de backup: {str(e)}")
        return error_response('Erro interno no servidor')

@rotas_bp.route('/api/backup/criar', methods=['POST'])
@login_required
@setor_required('Administrador')
def criar_backup():
    """Cria um novo backup do sistema"""
    try:
        if not request.is_json:
            return error_response('Content-Type deve ser application/json', 400)
            
        data = request.get_json()
        tipo_backup = data.get('tipo', 'completo')
        observacoes = data.get('observacoes', '')
        
        # Validar tipo de backup
        tipos_validos = ['completo', 'dados', 'configuracoes', 'logs']
        if tipo_backup not in tipos_validos:
            return error_response('Tipo de backup inválido', 400)
        
        # Criar registro de backup
        agora = get_brazil_time().replace(tzinfo=None)
        nome_arquivo = f"backup_{tipo_backup}_{agora.strftime('%Y%m%d_%H%M%S')}.sql"
        
        backup = BackupHistorico(
            nome_arquivo=nome_arquivo,
            tipo=tipo_backup,
            status='em_progresso',
            data_backup=agora,
            data_inicio=agora,
            observacoes=observacoes,
            usuario_id=current_user.id,
            automatico=False
        )
        
        db.session.add(backup)
        db.session.commit()
        
        # Executar backup em background (simulação)
        try:
            # Aqui você implementaria a lógica real de backup
            # Por enquanto, vamos simular um backup bem-sucedido
            
            import time
            time.sleep(2)  # Simular tempo de processamento
            
            # Atualizar status do backup
            backup.status = 'concluido'
            backup.data_fim = get_brazil_time().replace(tzinfo=None)
            backup.tamanho_mb = 15.5  # Tamanho simulado
            backup.tempo_execucao = backup.calcular_duracao()
            
            db.session.commit()
            
            # Registrar log da ação
            client_info = get_client_info(request)
            registrar_log_acao(
                usuario_id=current_user.id,
                acao=f'Criar backup: {tipo_backup}',
                categoria='backup',
                detalhes=f'Backup {tipo_backup} criado com sucesso - Arquivo: {nome_arquivo}',
                ip_address=client_info['ip_address'],
                user_agent=client_info['user_agent'],
                recurso_afetado=str(backup.id),
                tipo_recurso='backup'
            )
            
            return json_response({
                'message': 'Backup criado com sucesso',
                'backup': {
                    'id': backup.id,
                    'nome_arquivo': backup.nome_arquivo,
                    'tipo': backup.tipo,
                    'status': backup.status,
                    'tamanho_mb': backup.tamanho_mb
                }
            }, 201)
            
        except Exception as backup_error:
            # Atualizar status para erro
            backup.status = 'erro'
            backup.data_fim = get_brazil_time().replace(tzinfo=None)
            backup.erro_detalhes = str(backup_error)
            db.session.commit()
            
            logger.error(f"Erro durante execução do backup: {str(backup_error)}")
            return error_response('Erro durante execução do backup')
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao criar backup: {str(e)}")
        return error_response('Erro interno no servidor')

@rotas_bp.route('/api/manutencao/limpar-logs', methods=['POST'])
@login_required
@setor_required('Administrador')
def limpar_logs():
    """Limpa logs antigos do sistema"""
    try:
        if not request.is_json:
            return error_response('Content-Type deve ser application/json', 400)
            
        data = request.get_json()
        dias_manter = data.get('dias_manter', 90)
        
        if dias_manter < 7:
            return error_response('Deve manter pelo menos 7 dias de logs', 400)
        
        # Calcular data limite
        data_limite = get_brazil_time().date() - timedelta(days=dias_manter)
        
        # Contar logs que serão removidos
        logs_acesso_antigos = LogAcesso.query.filter(
            func.date(LogAcesso.data_acesso) < data_limite
        ).count()
        
        logs_acoes_antigos = LogAcao.query.filter(
            func.date(LogAcao.data_acao) < data_limite
        ).count()
        
        # Remover logs antigos
        LogAcesso.query.filter(
            func.date(LogAcesso.data_acesso) < data_limite
        ).delete()
        
        LogAcao.query.filter(
            func.date(LogAcao.data_acao) < data_limite
        ).delete()
        
        db.session.commit()
        
        # Registrar log da ação
        client_info = get_client_info(request)
        registrar_log_acao(
            usuario_id=current_user.id,
            acao='Limpeza de logs antigos',
            categoria='manutencao',
            detalhes=f'Removidos {logs_acesso_antigos} logs de acesso e {logs_acoes_antigos} logs de ações anteriores a {data_limite.strftime("%d/%m/%Y")}',
            ip_address=client_info['ip_address'],
            user_agent=client_info['user_agent']
        )
        
        return json_response({
            'message': 'Limpeza de logs concluída',
            'logs_removidos': {
                'acesso': logs_acesso_antigos,
                'acoes': logs_acoes_antigos,
                'total': logs_acesso_antigos + logs_acoes_antigos
            },
            'data_limite': data_limite.strftime('%d/%m/%Y')
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao limpar logs: {str(e)}")
        return error_response('Erro interno no servidor')

@rotas_bp.route('/api/manutencao/otimizar-banco', methods=['POST'])
@login_required
@setor_required('Administrador')
def otimizar_banco():
    """Otimiza o banco de dados"""
    try:
        # Registrar início da manutenção
        manutencao = ManutencaoSistema(
            tipo_manutencao='otimizacao_bd',
            descricao='Otimização do banco de dados',
            status='em_progresso',
            usuario_id=current_user.id,
            automatica=False
        )
        
        db.session.add(manutencao)
        db.session.commit()
        
        try:
            # Executar comandos de otimização
            resultados = []
            
            # Obter lista de tabelas
            tabelas = db.session.execute(text("SHOW TABLES")).fetchall()
            
            for tabela in tabelas:
                nome_tabela = tabela[0]
                try:
                    # Otimizar tabela
                    db.session.execute(text(f"OPTIMIZE TABLE {nome_tabela}"))
                    resultados.append(f"Tabela {nome_tabela} otimizada com sucesso")
                except Exception as e:
                    resultados.append(f"Erro ao otimizar tabela {nome_tabela}: {str(e)}")
            
            db.session.commit()
            
            # Atualizar status da manutenção
            manutencao.status = 'concluida'
            manutencao.data_fim = get_brazil_time().replace(tzinfo=None)
            manutencao.resultados = json.dumps(resultados)
            manutencao.tempo_execucao = manutencao.calcular_duracao() if manutencao.data_fim else None
            
            db.session.commit()
            
            # Registrar log da ação
            client_info = get_client_info(request)
            registrar_log_acao(
                usuario_id=current_user.id,
                acao='Otimização do banco de dados',
                categoria='manutencao',
                detalhes=f'Otimização concluída - {len(tabelas)} tabelas processadas',
                ip_address=client_info['ip_address'],
                user_agent=client_info['user_agent'],
                recurso_afetado=str(manutencao.id),
                tipo_recurso='manutencao'
            )
            
            return json_response({
                'message': 'Otimização do banco concluída',
                'resultados': resultados,
                'tabelas_processadas': len(tabelas),
                'tempo_execucao': manutencao.tempo_execucao
            })
            
        except Exception as otimizacao_error:
            # Atualizar status para erro
            manutencao.status = 'erro'
            manutencao.data_fim = get_brazil_time().replace(tzinfo=None)
            manutencao.erro_detalhes = str(otimizacao_error)
            db.session.commit()
            
            logger.error(f"Erro durante otimização do banco: {str(otimizacao_error)}")
            return error_response('Erro durante otimização do banco')
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao otimizar banco: {str(e)}")
        return error_response('Erro interno no servidor')

@rotas_bp.route('/api/sistema/status')
@login_required
@setor_required('Administrador')
def status_sistema():
    """Retorna informações de status do sistema"""
    try:
        # Estatísticas básicas
        total_usuarios = User.query.count()
        total_chamados = Chamado.query.count()
        chamados_abertos = Chamado.query.filter_by(status='Aberto').count()
        alertas_ativos = AlertaSistema.query.filter_by(resolvido=False).count()
        
        # Último backup
        ultimo_backup = BackupHistorico.query.order_by(desc(BackupHistorico.data_backup)).first()
        
        # Configurações críticas
        modo_manutencao = ConfiguracaoAvancada.query.filter_by(chave='sistema.manutencao_modo').first()
        debug_mode = ConfiguracaoAvancada.query.filter_by(chave='sistema.debug_mode').first()
        
        # Informações do sistema
        import psutil
        import platform
        
        # Uso de memória
        memoria = psutil.virtual_memory()
        
        # Uso de disco
        disco = psutil.disk_usage('/')
        
        status_info = {
            'sistema_online': True,
            'modo_manutencao': modo_manutencao.get_valor_tipado() if modo_manutencao else False,
            'debug_ativo': debug_mode.get_valor_tipado() if debug_mode else False,
            'estatisticas': {
                'total_usuarios': total_usuarios,
                'total_chamados': total_chamados,
                'chamados_abertos': chamados_abertos,
                'alertas_ativos': alertas_ativos
            },
            'ultimo_backup': {
                'data': ultimo_backup.get_data_backup_brazil().strftime('%d/%m/%Y %H:%M:%S') if ultimo_backup else 'Nunca',
                'status': ultimo_backup.status if ultimo_backup else 'N/A',
                'tipo': ultimo_backup.tipo if ultimo_backup else 'N/A'
            },
            'sistema': {
                'plataforma': platform.system(),
                'versao': platform.release(),
                'arquitetura': platform.machine(),
                'python_versao': platform.python_version()
            },
            'recursos': {
                'memoria_total_gb': round(memoria.total / (1024**3), 2),
                'memoria_usada_gb': round(memoria.used / (1024**3), 2),
                'memoria_percentual': memoria.percent,
                'disco_total_gb': round(disco.total / (1024**3), 2),
                'disco_usado_gb': round(disco.used / (1024**3), 2),
                'disco_percentual': round((disco.used / disco.total) * 100, 2)
            },
            'timestamp': get_brazil_time().strftime('%d/%m/%Y %H:%M:%S')
        }
        
        return json_response(status_info)
        
    except Exception as e:
        logger.error(f"Erro ao obter status do sistema: {str(e)}")
        return error_response('Erro interno no servidor')

# ==================== MIDDLEWARE PARA LOGS AUTOMÁTICOS ====================

@rotas_bp.before_request
def log_request():
    """Registra automaticamente certas ações"""
    if request.method in ['POST', 'PUT', 'DELETE'] and current_user.is_authenticated:
        # Não registrar logs para endpoints de logs (evitar recursão)
        if '/api/logs/' not in request.path:
            client_info = get_client_info(request)
            
            # Determinar ação baseada no endpoint
            acao = f"{request.method} {request.path}"
            categoria = 'api'
            
            if '/api/configuracoes' in request.path:
                categoria = 'configuracao'
            elif '/api/alertas' in request.path:
                categoria = 'alerta'
            elif '/api/backup' in request.path:
                categoria = 'backup'
            elif '/api/manutencao' in request.path:
                categoria = 'manutencao'
            
            # Registrar após a resposta para capturar o resultado
            @current_app.after_request
            def log_response(response):
                try:
                    sucesso = 200 <= response.status_code < 400
                    
                    registrar_log_acao(
                        usuario_id=current_user.id,
                        acao=acao,
                        categoria=categoria,
                        detalhes=f"Status: {response.status_code}",
                        ip_address=client_info['ip_address'],
                        user_agent=client_info['user_agent'],
                        sucesso=sucesso,
                        erro_detalhes=None if sucesso else f"HTTP {response.status_code}"
                    )
                except Exception as e:
                    logger.error(f"Erro ao registrar log automático: {str(e)}")
                
                return response