from flask import Flask
from config import get_config
from database import db, Chamado, AnexoArquivo, HistoricoTicket

# Import inside app context for model definition
from database import ChamadoTimelineEvent


def create_app():
    app = Flask(__name__)
    app.config.from_object(get_config())
    db.init_app(app)
    return app


def ensure_tables(app):
    with app.app_context():
        db.create_all()


def backfill_timeline(app):
    with app.app_context():
        criados = 0
        anexos_recebidos = 0
        tickets = 0
        anexos_enviados = 0

        # 1) Evento de criação para cada chamado sem evento 'created'
        chamados = Chamado.query.all()
        for ch in chamados:
            existe = (
                ChamadoTimelineEvent.query
                .filter_by(chamado_id=ch.id, tipo='created')
                .first()
            )
            if not existe:
                ev = ChamadoTimelineEvent(
                    chamado_id=ch.id,
                    usuario_id=getattr(ch, 'usuario_id', None),
                    tipo='created',
                    descricao='Chamado criado',
                    status_anterior=None,
                    status_novo=ch.status or 'Aberto',
                    criado_em=(ch.data_abertura or None)
                )
                db.session.add(ev)
                criados += 1
        db.session.commit()

        # 2) Anexos recebidos na abertura (AnexoArquivo com chamado_id e sem historico_ticket_id)
        anexos = AnexoArquivo.query.filter(
            AnexoArquivo.chamado_id.isnot(None)
        ).all()
        for a in anexos:
            # Evitar duplicidade
            existe = (
                ChamadoTimelineEvent.query
                .filter_by(chamado_id=a.chamado_id, tipo='attachment_received', anexo_id=a.id)
                .first()
            )
            if not existe and (not getattr(a, 'historico_ticket_id', None)):
                ev = ChamadoTimelineEvent(
                    chamado_id=a.chamado_id,
                    usuario_id=getattr(a, 'usuario_id', None),
                    tipo='attachment_received',
                    descricao=f'Anexo recebido: {a.nome_original}',
                    anexo_id=a.id,
                    criado_em=(a.data_upload or None)
                )
                db.session.add(ev)
                anexos_recebidos += 1
        db.session.commit()

        # 3) Tickets enviados (HistoricoTicket)
        historicos = HistoricoTicket.query.all()
        import json as _json
        for h in historicos:
            existe = (
                ChamadoTimelineEvent.query
                .filter_by(chamado_id=h.chamado_id, tipo='ticket_sent')
                .filter(ChamadoTimelineEvent.descricao.like(f"%{h.assunto}%"))
                .first()
            )
            if not existe:
                ev = ChamadoTimelineEvent(
                    chamado_id=h.chamado_id,
                    usuario_id=h.usuario_id,
                    tipo='ticket_sent',
                    descricao=f'E-mail enviado: {h.assunto} para {h.destinatarios}',
                    metadados=_json.dumps({
                        'assunto': h.assunto,
                        'mensagem': h.mensagem,
                        'destinatarios': (h.destinatarios or '').split(',') if h.destinatarios else []
                    }),
                    criado_em=(h.data_envio or None)
                )
                db.session.add(ev)
                tickets += 1
        db.session.commit()

        # 4) Anexos enviados em tickets (AnexoArquivo com historico_ticket_id)
        anexos_tickets = AnexoArquivo.query.filter(
            AnexoArquivo.historico_ticket_id.isnot(None)
        ).all()
        for a in anexos_tickets:
            existe = (
                ChamadoTimelineEvent.query
                .filter_by(chamado_id=a.chamado_id, tipo='attachment_sent', anexo_id=a.id)
                .first()
            )
            if not existe:
                ev = ChamadoTimelineEvent(
                    chamado_id=a.chamado_id,
                    usuario_id=getattr(a, 'usuario_id', None),
                    tipo='attachment_sent',
                    descricao=f'Anexo enviado: {a.nome_original}',
                    metadados=_json.dumps({
                        'arquivo_nome': a.nome_original,
                        'mime_type': a.mime_type,
                        'tamanho_bytes': a.tamanho_bytes,
                        'origem': 'suporte'
                    }),
                    anexo_id=a.id,
                    criado_em=(a.data_upload or None)
                )
                db.session.add(ev)
                anexos_enviados += 1
        db.session.commit()

        print('Backfill concluído:')
        print(f' - Eventos de criação inseridos: {criados}')
        print(f' - Anexos recebidos inseridos: {anexos_recebidos}')
        print(f' - Tickets enviados inseridos: {tickets}')
        print(f' - Anexos enviados inseridos: {anexos_enviados}')


if __name__ == '__main__':
    app = create_app()
    ensure_tables(app)
    backfill_timeline(app)
