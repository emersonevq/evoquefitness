from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from database import db, User, AgenteSuporte, ChamadoAgente, Chamado
from auth.auth_helpers import setor_required
import json
import logging

logger = logging.getLogger(__name__)

agentes_bp = Blueprint('agentes', __name__)

def json_response(data, status=200):
    """Padroniza respostas JSON"""
    return jsonify(data), status

def error_response(message, status=400):
    """Padroniza respostas de erro"""
    return jsonify({'error': message}), status

@agentes_bp.route('/api/agentes', methods=['GET'])
@login_required
@setor_required('Administrador')
def listar_agentes():
    """Lista todos os agentes de suporte"""
    try:
        agentes = db.session.query(AgenteSuporte, User).join(User).all()
        
        agentes_data = []
        for agente, usuario in agentes:
            agentes_data.append({
                'id': agente.id,
                'usuario_id': agente.usuario_id,
                'nome': f"{usuario.nome} {usuario.sobrenome}",
                'email': usuario.email,
                'ativo': agente.ativo,
                'especialidades': agente.especialidades_list,
                'nivel_experiencia': agente.nivel_experiencia,
                'max_chamados_simultaneos': agente.max_chamados_simultaneos,
                'chamados_ativos': agente.get_chamados_ativos(),
                'pode_receber_chamado': agente.pode_receber_chamado(),
                'data_criacao': agente.data_criacao.strftime('%d/%m/%Y %H:%M') if agente.data_criacao else None
            })
        
        return json_response(agentes_data)
        
    except Exception as e:
        logger.error(f"Erro ao listar agentes: {str(e)}")
        return error_response('Erro interno no servidor')

@agentes_bp.route('/api/agentes', methods=['POST'])
@login_required
@setor_required('Administrador')
def criar_agente():
    """Cria um novo agente de suporte"""
    try:
        data = request.get_json()
        
        if not data:
            return error_response('Dados não fornecidos')
        
        usuario_id = data.get('usuario_id')
        if not usuario_id:
            return error_response('ID do usuário é obrigatório')
        
        # Verificar se usuário existe
        usuario = User.query.get(usuario_id)
        if not usuario:
            return error_response('Usuário não encontrado')
        
        # Verificar se já é agente
        agente_existente = AgenteSuporte.query.filter_by(usuario_id=usuario_id).first()
        if agente_existente:
            return error_response('Usuário já é um agente de suporte')
        
        # Criar agente
        agente = AgenteSuporte(
            usuario_id=usuario_id,
            ativo=data.get('ativo', True),
            nivel_experiencia=data.get('nivel_experiencia', 'junior'),
            max_chamados_simultaneos=data.get('max_chamados_simultaneos', 10)
        )
        
        # Definir especialidades
        especialidades = data.get('especialidades', [])
        if isinstance(especialidades, list):
            agente.especialidades_list = especialidades
        
        db.session.add(agente)
        db.session.commit()
        
        logger.info(f"Agente criado: {usuario.nome} por {current_user.nome}")
        
        return json_response({
            'id': agente.id,
            'message': f'Agente {usuario.nome} criado com sucesso'
        }, 201)
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao criar agente: {str(e)}")
        return error_response('Erro interno no servidor')

@agentes_bp.route('/api/agentes/<int:agente_id>', methods=['PUT'])
@login_required
@setor_required('Administrador')
def atualizar_agente(agente_id):
    """Atualiza informações de um agente"""
    try:
        agente = AgenteSuporte.query.get(agente_id)
        if not agente:
            return error_response('Agente não encontrado', 404)
        
        data = request.get_json()
        if not data:
            return error_response('Dados não fornecidos')
        
        # Atualizar campos
        if 'ativo' in data:
            agente.ativo = data['ativo']
        
        if 'nivel_experiencia' in data:
            agente.nivel_experiencia = data['nivel_experiencia']
        
        if 'max_chamados_simultaneos' in data:
            max_chamados = data['max_chamados_simultaneos']
            if isinstance(max_chamados, int) and max_chamados > 0:
                agente.max_chamados_simultaneos = max_chamados
        
        if 'especialidades' in data:
            especialidades = data['especialidades']
            if isinstance(especialidades, list):
                agente.especialidades_list = especialidades
        
        agente.data_atualizacao = db.func.now()
        db.session.commit()
        
        logger.info(f"Agente {agente.usuario.nome} atualizado por {current_user.nome}")
        
        return json_response({'message': 'Agente atualizado com sucesso'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao atualizar agente: {str(e)}")
        return error_response('Erro interno no servidor')

@agentes_bp.route('/api/agentes/<int:agente_id>', methods=['DELETE'])
@login_required
@setor_required('Administrador')
def excluir_agente(agente_id):
    """Remove um agente de suporte"""
    try:
        agente = AgenteSuporte.query.get(agente_id)
        if not agente:
            return error_response('Agente não encontrado', 404)
        
        # Verificar se há chamados ativos atribuídos
        chamados_ativos = agente.get_chamados_ativos()
        if chamados_ativos > 0:
            return error_response(f'Não é possível excluir agente com {chamados_ativos} chamado(s) ativo(s)')
        
        nome_agente = agente.usuario.nome
        
        # Finalizar todas as atribuições antigas
        ChamadoAgente.query.filter_by(agente_id=agente_id, ativo=True).update({
            'ativo': False,
            'data_conclusao': db.func.now()
        })
        
        db.session.delete(agente)
        db.session.commit()
        
        logger.info(f"Agente {nome_agente} excluído por {current_user.nome}")
        
        return json_response({'message': f'Agente {nome_agente} excluído com sucesso'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao excluir agente: {str(e)}")
        return error_response('Erro interno no servidor')

@agentes_bp.route('/api/agentes/<int:agente_id>/chamados', methods=['GET'])
@login_required
@setor_required('Administrador')
def listar_chamados_agente(agente_id):
    """Lista chamados atribuídos a um agente"""
    try:
        agente = AgenteSuporte.query.get(agente_id)
        if not agente:
            return error_response('Agente não encontrado', 404)
        
        # Buscar chamados atribuídos
        chamados_query = db.session.query(ChamadoAgente, Chamado).join(Chamado).filter(
            ChamadoAgente.agente_id == agente_id
        )
        
        # Filtrar por status se especificado
        status_filtro = request.args.get('status')
        if status_filtro:
            if status_filtro == 'ativos':
                chamados_query = chamados_query.filter(
                    ChamadoAgente.ativo == True,
                    Chamado.status.in_(['Aberto', 'Aguardando'])
                )
            elif status_filtro == 'concluidos':
                chamados_query = chamados_query.filter(
                    Chamado.status.in_(['Concluido', 'Cancelado'])
                )
        
        chamados_data = []
        for atribuicao, chamado in chamados_query.all():
            chamados_data.append({
                'chamado_id': chamado.id,
                'codigo': chamado.codigo,
                'solicitante': chamado.solicitante,
                'problema': chamado.problema,
                'status': chamado.status,
                'prioridade': chamado.prioridade,
                'data_abertura': chamado.data_abertura.strftime('%d/%m/%Y %H:%M') if chamado.data_abertura else None,
                'data_atribuicao': atribuicao.data_atribuicao.strftime('%d/%m/%Y %H:%M') if atribuicao.data_atribuicao else None,
                'ativo': atribuicao.ativo,
                'observacoes': atribuicao.observacoes
            })
        
        return json_response(chamados_data)
        
    except Exception as e:
        logger.error(f"Erro ao listar chamados do agente: {str(e)}")
        return error_response('Erro interno no servidor')

@agentes_bp.route('/api/chamados/<int:chamado_id>/atribuir', methods=['POST'])
@login_required
@setor_required('Administrador')
def atribuir_chamado(chamado_id):
    """Atribui um chamado a um agente"""
    try:
        data = request.get_json()
        if not data:
            return error_response('Dados não fornecidos')
        
        agente_id = data.get('agente_id')
        if not agente_id:
            return error_response('ID do agente é obrigatório')
        
        chamado = Chamado.query.get(chamado_id)
        if not chamado:
            return error_response('Chamado não encontrado', 404)
        
        agente = AgenteSuporte.query.get(agente_id)
        if not agente:
            return error_response('Agente não encontrado', 404)
        
        if not agente.ativo:
            return error_response('Agente não está ativo')
        
        if not agente.pode_receber_chamado():
            return error_response('Agente já atingiu o limite máximo de chamados simultâneos')
        
        # Verificar se já há atribuição ativa
        atribuicao_existente = ChamadoAgente.query.filter_by(
            chamado_id=chamado_id,
            ativo=True
        ).first()
        
        if atribuicao_existente:
            # Finalizar atribuição anterior
            atribuicao_existente.finalizar_atribuicao()
        
        # Criar nova atribuição
        nova_atribuicao = ChamadoAgente(
            chamado_id=chamado_id,
            agente_id=agente_id,
            atribuido_por=current_user.id,
            observacoes=data.get('observacoes', '')
        )
        
        db.session.add(nova_atribuicao)
        db.session.commit()
        
        logger.info(f"Chamado {chamado.codigo} atribuído ao agente {agente.usuario.nome} por {current_user.nome}")
        
        return json_response({
            'message': f'Chamado {chamado.codigo} atribuído ao agente {agente.usuario.nome}'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao atribuir chamado: {str(e)}")
        return error_response('Erro interno no servidor')

@agentes_bp.route('/api/usuarios-disponiveis', methods=['GET'])
@login_required
@setor_required('Administrador')
def usuarios_disponiveis():
    """Lista usuários que podem se tornar agentes"""
    try:
        # Buscar usuários que não são agentes
        usuarios_query = db.session.query(User).outerjoin(AgenteSuporte).filter(
            AgenteSuporte.id.is_(None),
            User.bloqueado == False
        )

        usuarios_data = []
        for usuario in usuarios_query.all():
            usuarios_data.append({
                'id': usuario.id,
                'nome': f"{usuario.nome} {usuario.sobrenome}",
                'email': usuario.email,
                'nivel_acesso': usuario.nivel_acesso,
                'setores': usuario.setores
            })

        return json_response(usuarios_data)

    except Exception as e:
        logger.error(f"Erro ao listar usuários disponíveis: {str(e)}")
        return error_response('Erro interno no servidor')

@agentes_bp.route('/api/agentes/estatisticas', methods=['GET'])
@login_required
@setor_required('Administrador')
def obter_estatisticas_agentes():
    """Obtém estatísticas dos agentes de suporte"""
    try:
        # Total de agentes
        total_agentes = AgenteSuporte.query.count()

        # Agentes ativos
        agentes_ativos = AgenteSuporte.query.filter_by(ativo=True).count()

        # Chamados atribuídos (total de chamados ativos atribuídos a agentes)
        chamados_atribuidos = ChamadoAgente.query.filter_by(ativo=True).count()

        # Agentes disponíveis (ativos que podem receber mais chamados)
        agentes = AgenteSuporte.query.filter_by(ativo=True).all()
        agentes_disponiveis = 0
        for agente in agentes:
            if agente.pode_receber_chamado():
                agentes_disponiveis += 1

        estatisticas = {
            'total_agentes': total_agentes,
            'agentes_ativos': agentes_ativos,
            'chamados_atribuidos': chamados_atribuidos,
            'agentes_disponiveis': agentes_disponiveis
        }

        return json_response(estatisticas)

    except Exception as e:
        logger.error(f"Erro ao obter estatísticas dos agentes: {str(e)}")
        return error_response('Erro interno no servidor')
