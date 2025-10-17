from flask import Blueprint, request, make_response, jsonify
from flask_login import login_required, current_user
from flask import Blueprint, request, make_response, send_file, redirect, current_app
import os
from auth.auth_helpers import setor_required
from database import db, Chamado, ChamadoTimelineEvent, AnexoArquivo, User
from setores.ti.painel import json_response, error_response

timeline_bp = Blueprint('timeline', __name__)

@timeline_bp.route('/api/chamados/<int:id>/timeline', methods=['GET'])
@login_required
def obter_timeline_chamado(id):
    try:
        from datetime import datetime
        import hashlib
        chamado = Chamado.query.get_or_404(id)

        limit = min(int(request.args.get('limit', 100)), 500)
        since_id = request.args.get('since_id')
        since = request.args.get('since')

        q = ChamadoTimelineEvent.query.filter_by(chamado_id=chamado.id)
        if since_id and since_id.isdigit():
            q = q.filter(ChamadoTimelineEvent.id > int(since_id))
        elif since:
            try:
                try:
                    dt = datetime.strptime(since, '%d/%m/%Y %H:%M:%S')
                except ValueError:
                    dt = datetime.fromisoformat(since.replace('Z',''))
                q = q.filter(ChamadoTimelineEvent.criado_em > dt)
            except Exception:
                pass

        eventos = q.order_by(ChamadoTimelineEvent.criado_em.asc()).limit(limit).all()

        resultado = []
        last_modified = None
        last_id = 0
        for ev in eventos:
            if ev.criado_em and (last_modified is None or ev.criado_em > last_modified):
                last_modified = ev.criado_em
            if ev.id and ev.id > last_id:
                last_id = ev.id

            anexo_info = None
            if ev.anexo_id:
                anexo = AnexoArquivo.query.get(ev.anexo_id)
                if anexo:
                    anexo_info = {
                        'id': anexo.id,
                        'nome': anexo.nome_original,
                        'url': anexo.url_publica() if hasattr(anexo, 'url_publica') else ('/' + anexo.caminho_arquivo if anexo.caminho_arquivo else None)
                    }

            autor_id = ev.usuario_id
            autor_nome = None
            autor_tipo = None
            if autor_id:
                u = User.query.get(autor_id)
                if u:
                    autor_nome = f"{u.nome} {u.sobrenome}".strip()
                    try:
                        if hasattr(u, 'eh_agente_suporte_ativo') and u.eh_agente_suporte_ativo():
                            autor_tipo = 'Suporte'
                        elif u.nivel_acesso in ['Administrador', 'Gerente', 'Gerente Regional', 'Gestor']:
                            autor_tipo = 'Suporte'
                        else:
                            autor_tipo = 'Solicitante'
                    except Exception:
                        autor_tipo = 'Solicitante'
            # Fallback por tipo de evento
            if not autor_tipo:
                if ev.tipo in ['attachment_sent', 'ticket_sent', 'status_change']:
                    autor_tipo = 'Suporte'
                elif ev.tipo in ['attachment_received', 'created']:
                    autor_tipo = 'Solicitante'
                else:
                    autor_tipo = 'Sistema'

            # Tentar parsear metadados como JSON quando aplicável
            metadados_val = None
            if ev.metadados:
                try:
                    import json as _json
                    metadados_val = _json.loads(ev.metadados)
                except Exception:
                    metadados_val = ev.metadados

            item = {
                'id': ev.id,
                'tipo': ev.tipo,
                'usuario_id': autor_id,
                'usuario_nome': autor_nome,
                'autor_tipo': autor_tipo,
                'descricao': ev.descricao,
                'status_anterior': ev.status_anterior,
                'status_novo': ev.status_novo,
                'metadados': metadados_val,
                'criado_em': ev.criado_em.strftime('%d/%m/%Y %H:%M:%S') if ev.criado_em else None
            }
            if anexo_info:
                item['anexo'] = anexo_info
            resultado.append(item)

        etag_base = f"{chamado.id}:{last_id}:{len(resultado)}".encode('utf-8')
        etag = 'W/"' + hashlib.sha1(etag_base).hexdigest() + '"'

        inm = request.headers.get('If-None-Match')
        ims = request.headers.get('If-Modified-Since')

        if inm == etag:
            resp = make_response('', 304)
            resp.headers['ETag'] = etag
            if last_modified:
                resp.headers['Last-Modified'] = last_modified.strftime('%a, %d %b %Y %H:%M:%S GMT')
            resp.headers['Cache-Control'] = 'public, max-age=30, must-revalidate'
            return resp

        if ims and last_modified:
            try:
                from email.utils import parsedate_to_datetime
                ims_dt = parsedate_to_datetime(ims)
                if ims_dt and last_modified <= ims_dt:
                    resp = make_response('', 304)
                    resp.headers['ETag'] = etag
                    resp.headers['Last-Modified'] = last_modified.strftime('%a, %d %b %Y %H:%M:%S GMT')
                    resp.headers['Cache-Control'] = 'public, max-age=30, must-revalidate'
                    return resp
            except Exception:
                pass

        resp = make_response(json_response(resultado))
        resp.headers['ETag'] = etag
        if last_modified:
            resp.headers['Last-Modified'] = last_modified.strftime('%a, %d %b %Y %H:%M:%S GMT')
        resp.headers['Cache-Control'] = 'public, max-age=30, must-revalidate'
        return resp
    except Exception as e:
        return error_response('Erro interno no servidor')


@timeline_bp.route('/api/anexos/<int:anexo_id>/download', methods=['GET'])
@login_required
def download_anexo(anexo_id):
    try:
        anexo = AnexoArquivo.query.get_or_404(anexo_id)
        # Preferir blob em DB
        if anexo.arquivo_blob:
            from io import BytesIO
            buf = BytesIO(anexo.arquivo_blob)
            return send_file(buf, mimetype=anexo.mime_type or 'application/octet-stream', as_attachment=True, download_name=anexo.nome_original)
        # Fallback para caminho_arquivo (compatibilidade retroativa)
        if anexo.caminho_arquivo:
            # caminho_arquivo pode ser um caminho relativo que começa com 'static/'
            path = anexo.caminho_arquivo
            if path.startswith('static/'):
                # servir via flask.send_from_directory
                from flask import send_from_directory
                rel = os.path.relpath(path, 'static')
                dirpart = os.path.join('static', os.path.dirname(rel))
                filename = os.path.basename(path)
                return send_from_directory(dirpart, filename, mimetype=anexo.mime_type or 'application/octet-stream', as_attachment=True)
            else:
                # caminho público
                return redirect(anexo.caminho_arquivo)
        return error_response('Arquivo não encontrado', 404)
    except Exception as e:
        current_app.logger.error(f"Erro ao baixar anexo {anexo_id}: {str(e)}")
        return error_response('Erro ao baixar anexo', 500)
