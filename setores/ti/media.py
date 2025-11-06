import os
import traceback
from flask import Blueprint, request, jsonify, current_app, send_file, abort, url_for
from werkzeug.utils import secure_filename
from io import BytesIO
from flask_login import login_required, current_user
from database import db, Media, get_brazil_time

media_bp = Blueprint('ti_media', __name__)

# Retorna mídias ativas (meta) para exibir no login
@media_bp.route('/active', methods=['GET'])
def active_medias():
    try:
        medias = Media.query.filter_by(status='ativo').order_by(Media.ordem.desc(), Media.data_criacao.desc()).all()
        resultado = []
        for m in medias:
            resultado.append({
                'id': m.id,
                'tipo': m.tipo,
                'titulo': m.titulo,
                'descricao': m.descricao,
                'download_url': url_for('ti_media.download_public', media_id=m.id)
            })
        return jsonify(resultado)
    except Exception as e:
        current_app.logger.error(f'Erro ao listar mídias ativas: {str(e)}')
        return jsonify([]), 500

# Download público da mídia (para tela de login - SEM autenticação necessária)
@media_bp.route('/public/<int:media_id>', methods=['GET'])
def download_public(media_id):
    m = Media.query.get(media_id)
    if not m:
        abort(404)

    # Verificar se a mídia está ativa (apenas mídias ativas podem ser acessadas publicamente)
    if m.status != 'ativo':
        abort(403)

    # Preferir blob salvo no banco
    if m.arquivo_blob:
        try:
            return send_file(BytesIO(m.arquivo_blob), mimetype=m.mime_type or 'application/octet-stream', as_attachment=False, download_name=m.titulo or f'media_{m.id}')
        except Exception as e:
            current_app.logger.error(f'Erro ao enviar blob da mídia pública {m.id}: {e}')
            try:
                current_app.logger.error(traceback.format_exc())
            except Exception:
                pass
            abort(500)

    # Se não tiver blob, tentar redirecionar para url externa
    if m.url:
        return jsonify({'redirect': m.url}), 302

    abort(404)

# Download da mídia (servir blob armazenado no banco)
@media_bp.route('/download/<int:media_id>', methods=['GET'])
def download(media_id):
    m = Media.query.get(media_id)
    if not m:
        abort(404)

    # Preferir blob salvo no banco
    if m.arquivo_blob:
        try:
            return send_file(BytesIO(m.arquivo_blob), mimetype=m.mime_type or 'application/octet-stream', as_attachment=False, download_name=m.titulo or f'media_{m.id}')
        except Exception as e:
            current_app.logger.error(f'Erro ao enviar blob da mídia {m.id}: {e}')
            try:
                current_app.logger.error(traceback.format_exc())
            except Exception:
                pass
            abort(500)

    # Se não tiver blob, tentar redirecionar para url externa
    if m.url:
        return jsonify({'redirect': m.url}), 302

    abort(404)

# Upload de mídia (somente para administradores / agentes com permissão)
@media_bp.route('/upload', methods=['POST'])
@login_required
def upload_media():
    # Verificar permissão: apenas administradores ou agentes de suporte podem gerenciar mídias
    try:
        if not (current_user.tem_permissao('Administrador') or current_user.eh_agente_suporte_ativo() or current_user.tem_permissao_gerenciar_usuarios()):
            return jsonify({'error': 'Acesso negado'}), 403
    except Exception:
        return jsonify({'error': 'Acesso negado'}), 403

    try:
        tipo = request.form.get('tipo')
        titulo = request.form.get('titulo')
        descricao = request.form.get('descricao')
        status = request.form.get('status', 'ativo')

        arquivo = request.files.get('arquivo')

        if not tipo or tipo not in ('evento', 'foto', 'video'):
            return jsonify({'error': 'Tipo inválido'}), 400
        if not titulo:
            return jsonify({'error': 'Título obrigatório'}), 400

        novo = Media(tipo=tipo, titulo=titulo, descricao=descricao, status=status, data_criacao=get_brazil_time().replace(tzinfo=None))

        if arquivo:
            filename = secure_filename(arquivo.filename)
            data = arquivo.read()
            novo.arquivo_blob = data
            novo.tamanho_bytes = len(data)
            novo.mime_type = arquivo.mimetype
        else:
            # Se não enviar arquivo, aceitar URL externo
            url = request.form.get('url')
            if not url:
                return jsonify({'error': 'Arquivo ou URL obrigatório'}), 400
            novo.url = url

        db.session.add(novo)
        db.session.commit()

        return jsonify({'success': True, 'id': novo.id})

    except Exception as e:
        current_app.logger.error(f'Erro ao enviar mídia: {str(e)}')
        try:
            current_app.logger.error(traceback.format_exc())
        except Exception:
            pass
        db.session.rollback()
        # Em modo debug, retornar detalhes para ajudar no diagnóstico
        if current_app.debug:
            return jsonify({'error': 'Erro interno', 'details': str(e)}), 500
        return jsonify({'error': 'Erro interno'}), 500

# Lista completa de mídias (CRUD) - para o painel
@media_bp.route('/list', methods=['GET'])
@login_required
def list_medias():
    try:
        # Apenas usuários com permissão de gerenciar mídias
        if not (current_user.tem_permissao('Administrador') or current_user.eh_agente_suporte_ativo() or current_user.tem_permissao_gerenciar_usuarios()):
            return jsonify({'error': 'Acesso negado'}), 403

        medias = Media.query.order_by(Media.ordem.desc(), Media.data_criacao.desc()).all()
        resultado = []
        for m in medias:
            resultado.append({
                'id': m.id,
                'tipo': m.tipo,
                'titulo': m.titulo,
                'descricao': m.descricao,
                'url': m.url,
                'mime_type': m.mime_type,
                'tamanho_bytes': m.tamanho_bytes,
                'status': m.status,
                'ordem': m.ordem,
                'public_url': m.public_url(),
                'data_criacao': m.data_criacao.isoformat() if m.data_criacao else None
            })
        return jsonify(resultado)
    except Exception as e:
        current_app.logger.error(f'Erro ao listar mídias: {e}')
        try:
            current_app.logger.error(traceback.format_exc())
        except Exception:
            pass
        if current_app.debug:
            return jsonify({'error': 'Erro interno', 'details': str(e)}), 500
        return jsonify({'error': 'Erro interno'}), 500

# Remover mídia
@media_bp.route('/<int:media_id>', methods=['DELETE'])
@login_required
def delete_media(media_id):
    try:
        if not (current_user.tem_permissao('Administrador') or current_user.eh_agente_suporte_ativo() or current_user.tem_permissao_gerenciar_usuarios()):
            return jsonify({'error': 'Acesso negado'}), 403

        m = Media.query.get(media_id)
        if not m:
            return jsonify({'error': 'Mídia não encontrada'}), 404

        db.session.delete(m)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        current_app.logger.error(f'Erro ao deletar mídia: {e}')
        try:
            current_app.logger.error(traceback.format_exc())
        except Exception:
            pass
        db.session.rollback()
        if current_app.debug:
            return jsonify({'error': 'Erro interno', 'details': str(e)}), 500
        return jsonify({'error': 'Erro interno'}), 500

# Atualizar metadados da mídia
@media_bp.route('/update/<int:media_id>', methods=['POST'])
@login_required
def update_media(media_id):
    try:
        if not (current_user.tem_permissao('Administrador') or current_user.eh_agente_suporte_ativo() or current_user.tem_permissao_gerenciar_usuarios()):
            return jsonify({'error': 'Acesso negado'}), 403

        m = Media.query.get(media_id)
        if not m:
            return jsonify({'error': 'Mídia não encontrada'}), 404

        # Pode vir como form-data (com arquivo) ou JSON
        titulo = request.form.get('titulo') or (request.json and request.json.get('titulo'))
        descricao = request.form.get('descricao') or (request.json and request.json.get('descricao'))
        status = request.form.get('status') or (request.json and request.json.get('status'))
        tipo = request.form.get('tipo') or (request.json and request.json.get('tipo'))
        url = request.form.get('url') or (request.json and request.json.get('url'))

        arquivo = request.files.get('arquivo')

        if titulo is not None:
            m.titulo = titulo
        if descricao is not None:
            m.descricao = descricao
        if status is not None:
            m.status = status
        if tipo is not None and tipo in ('evento', 'foto', 'video'):
            m.tipo = tipo
        if url is not None:
            m.url = url

        if arquivo:
            data = arquivo.read()
            m.arquivo_blob = data
            m.tamanho_bytes = len(data)
            m.mime_type = arquivo.mimetype

        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        current_app.logger.error(f'Erro ao atualizar mídia: {e}')
        try:
            current_app.logger.error(traceback.format_exc())
        except Exception:
            pass
        db.session.rollback()
        if current_app.debug:
            return jsonify({'error': 'Erro interno', 'details': str(e)}), 500
        return jsonify({'error': 'Erro interno'}), 500

# Reordenar mídias (espera um JSON {order: [id1,id2,..]})
@media_bp.route('/reorder', methods=['POST'])
@login_required
def reorder_medias():
    try:
        if not (current_user.tem_permissao('Administrador') or current_user.eh_agente_suporte_ativo() or current_user.tem_permissao_gerenciar_usuarios()):
            return jsonify({'error': 'Acesso negado'}), 403

        data = request.get_json(force=True)
        order = data.get('order') if data else None
        if not order or not isinstance(order, list):
            return jsonify({'error': 'Order inválido'}), 400

        # atribuir ordem decrescente para o primeiro item ter maior prioridade
        ordem_val = len(order)
        for media_id in order:
            m = Media.query.get(media_id)
            if m:
                m.ordem = ordem_val
                ordem_val -= 1
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        current_app.logger.error(f'Erro ao reordenar mídias: {e}')
        try:
            current_app.logger.error(traceback.format_exc())
        except Exception:
            pass
        db.session.rollback()
        if current_app.debug:
            return jsonify({'error': 'Erro interno', 'details': str(e)}), 500
        return jsonify({'error': 'Erro interno'}), 500

# DEBUG: endpoint auxiliar para diagnosticar problemas com mídia / banco
@media_bp.route('/debug', methods=['GET'])
@login_required
def debug_media():
    try:
        # Permissão reduzida: apenas administradores/gestores/agentes
        if not (current_user.tem_permissao('Administrador') or current_user.eh_agente_suporte_ativo() or current_user.tem_permissao_gerenciar_usuarios()):
            return jsonify({'error': 'Acesso negado'}), 403

        info = {'ok': True}
        try:
            info['media_count'] = Media.query.count()
        except Exception as e:
            info['media_count_error'] = str(e)
            try:
                info['media_count_trace'] = traceback.format_exc()
            except Exception:
                pass

        try:
            m = Media.query.first()
            if m:
                info['first'] = {'id': m.id, 'titulo': m.titulo, 'tipo': str(m.tipo), 'status': m.status, 'tamanho_bytes': m.tamanho_bytes}
            else:
                info['first'] = None
        except Exception as e:
            info['first_error'] = str(e)
            try:
                info['first_trace'] = traceback.format_exc()
            except Exception:
                pass

        # DB engine info (non-sensitive)
        try:
            engine = getattr(db, 'engine', None)
            if engine:
                info['db_engine'] = str(engine.url)
        except Exception:
            pass

        return jsonify(info)
    except Exception as e:
        current_app.logger.error(f'Erro no debug_media: {e}')
        try:
            current_app.logger.error(traceback.format_exc())
        except Exception:
            pass
        if current_app.debug:
            return jsonify({'error': 'Erro interno', 'details': str(e)}), 500
        return jsonify({'error': 'Erro interno'}), 500
