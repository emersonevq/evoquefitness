import os
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
        medias = Media.query.filter_by(status='ativo').order_by(Media.data_criacao.desc()).all()
        resultado = []
        for m in medias:
            resultado.append({
                'id': m.id,
                'tipo': m.tipo,
                'titulo': m.titulo,
                'descricao': m.descricao,
                'download_url': url_for('ti_media.download', media_id=m.id)
            })
        return jsonify(resultado)
    except Exception as e:
        current_app.logger.error(f'Erro ao listar mídias ativas: {str(e)}')
        return jsonify([]), 500

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
        db.session.rollback()
        return jsonify({'error': 'Erro interno'}), 500
