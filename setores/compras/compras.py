from flask import Blueprint, render_template, request, jsonify, current_app, redirect, url_for, flash
from flask_login import login_required, current_user
from auth.auth_helpers import setor_required
from datetime import datetime, date
from database import db, SolicitacaoCompra, User
from setores.ti.email_service import email_service
from jinja2 import Template
import os

compras_bp = Blueprint(
    'compras',
    __name__,
    template_folder='templates'
)

@compras_bp.route('/')
@login_required
@setor_required('Compras')
def index():
    try:
        return render_template('compras/index.html', current_year=datetime.now().year)
    except Exception as e:
        current_app.logger.error(f"Erro ao renderizar template de compras: {str(e)}")
        return redirect(url_for('main.index'))

@compras_bp.route('/nova-solicitacao')
@login_required
@setor_required('Compras')
def nova_solicitacao():
    """Página para criar nova solicitação de compra"""
    return render_template('compras/nova_solicitacao.html')

@compras_bp.route('/solicitacoes')
@login_required
@setor_required('Compras')
def solicitacoes():
    """Página de listagem de solicitações"""
    return render_template('compras/acompanhar_pedidos.html')

@compras_bp.route('/acompanhar-pedidos')
@login_required
@setor_required('Compras')
def acompanhar_pedidos():
    """Página para acompanhar pedidos de compra"""
    return render_template('compras/acompanhar_pedidos.html')

@compras_bp.route('/fornecedores')
@login_required
@setor_required('Compras')
def fornecedores():
    """Página de gerenciamento de fornecedores"""
    return render_template('compras/fornecedores.html')

@compras_bp.route('/relatorios')
@login_required
@setor_required('Compras')
def relatorios():
    """Página de relatórios de compras"""
    return render_template('compras/relatorios.html')

@compras_bp.route('/painel-admin')
@login_required
def painel_admin():
    """Painel administrativo do setor de compras"""
    # Verificar se é administrador ou tem acesso a compras
    if not (current_user.nivel_acesso == 'Administrador' or current_user.tem_acesso_setor('Compras')):
        flash('Acesso negado.', 'error')
        return redirect(url_for('main.index'))

    return render_template('compras/painel_admin.html')

@compras_bp.route('/api/solicitacao', methods=['POST'])
@login_required
@setor_required('Compras')
def criar_solicitacao():
    """API para criar nova solicitação de compra"""
    try:
        dados = request.get_json()

        # Validar dados obrigatórios
        campos_obrigatorios = ['produto', 'quantidade', 'justificativa']
        for campo in campos_obrigatorios:
            if not dados.get(campo):
                return jsonify({'erro': f'Campo {campo} é obrigatório'}), 400

        # Gerar protocolo único
        protocolo = f'COMP-{datetime.now().strftime("%Y%m%d%H%M%S")}'

        # Converter data de entrega se fornecida
        data_entrega_desejada = None
        if dados.get('dataEntrega'):
            try:
                data_entrega_desejada = datetime.strptime(dados['dataEntrega'], '%Y-%m-%d').date()
            except ValueError:
                pass

        # Definir prioridade baseada na urgência
        prioridade = dados.get('prioridade', 'normal')
        if dados.get('urgente'):
            prioridade = 'urgente'

        # Criar solicitação
        solicitacao = SolicitacaoCompra(
            protocolo=protocolo,
            solicitante_id=current_user.id,
            produto=dados['produto'],
            quantidade=int(dados['quantidade']),
            categoria=dados.get('categoria'),
            prioridade=prioridade.title(),
            valor_estimado=float(dados['valorEstimado']) if dados.get('valorEstimado') else None,
            data_entrega_desejada=data_entrega_desejada,
            justificativa=dados['justificativa'],
            observacoes=dados.get('observacoes'),
            urgente=dados.get('urgente', False)
        )

        db.session.add(solicitacao)
        db.session.commit()

        # Enviar email de notificação
        enviar_email_nova_solicitacao(solicitacao)

        current_app.logger.info(f'Nova solicitação de compra criada: {protocolo} pelo usuário {current_user.usuario}')

        return jsonify({
            'sucesso': True,
            'mensagem': 'Solicitação criada com sucesso!',
            'protocolo': protocolo
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Erro ao criar solicitação: {str(e)}')
        return jsonify({'erro': 'Erro interno do servidor'}), 500

def enviar_email_nova_solicitacao(solicitacao):
    """Envia email de notificação para nova solicitação de compra"""
    try:
        template_html = Template("""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background-color: #FF6200; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }
                .content { background-color: #f8f9fa; padding: 20px; border-radius: 0 0 8px 8px; }
                .info-box { background-color: white; padding: 15px; margin: 10px 0; border-left: 4px solid #FF6200; border-radius: 4px; }
                .priority-high { border-left-color: #dc3545; }
                .priority-urgent { border-left-color: #ff0000; background-color: #fff5f5; }
                .footer { text-align: center; margin-top: 20px; font-size: 12px; color: #666; }
                .btn { background-color: #FF6200; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; display: inline-block; }
                .status-badge { background-color: #28a745; color: white; padding: 4px 8px; border-radius: 12px; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📋 Nova Solicitação de Compra</h1>
                </div>

                <div class="content">
                    <p>Uma nova solicitação de compra foi criada no sistema:</p>

                    <div class="info-box {% if solicitacao.prioridade == 'Alta' %}priority-high{% elif solicitacao.prioridade == 'Urgente' %}priority-urgent{% endif %}">
                        <h3>📄 Detalhes da Solicitação</h3>
                        <p><strong>Protocolo:</strong> {{ solicitacao.protocolo }}</p>
                        <p><strong>Solicitante:</strong> {{ solicitacao.solicitante.nome }} {{ solicitacao.solicitante.sobrenome }}</p>
                        <p><strong>Email:</strong> {{ solicitacao.solicitante.email }}</p>
                        <p><strong>Setor:</strong> {{ solicitacao.solicitante.setor }}</p>
                        <p><strong>Data:</strong> {{ data_atual }}</p>
                        <p><strong>Status:</strong> <span class="status-badge">{{ solicitacao.status }}</span></p>
                    </div>

                    <div class="info-box">
                        <h3>🛍�� Produto/Serviço</h3>
                        <p><strong>Item:</strong> {{ solicitacao.produto }}</p>
                        <p><strong>Quantidade:</strong> {{ solicitacao.quantidade }}</p>
                        {% if solicitacao.categoria %}<p><strong>Categoria:</strong> {{ solicitacao.categoria|title }}</p>{% endif %}
                        {% if solicitacao.valor_estimado %}<p><strong>Valor Estimado:</strong> R$ {{ "%.2f"|format(solicitacao.valor_estimado) }}</p>{% endif %}
                        {% if solicitacao.data_entrega_desejada %}<p><strong>Data Desejada:</strong> {{ solicitacao.data_entrega_desejada.strftime('%d/%m/%Y') }}</p>{% endif %}
                    </div>

                    <div class="info-box">
                        <h3>📝 Justificativa</h3>
                        <p>{{ solicitacao.justificativa }}</p>
                        {% if solicitacao.observacoes %}
                        <h4>💬 Observações Adicionais</h4>
                        <p>{{ solicitacao.observacoes }}</p>
                        {% endif %}
                    </div>

                    <div class="info-box">
                        <h3>⚡ Prioridade</h3>
                        <p><strong>{{ solicitacao.prioridade }}</strong> {% if solicitacao.urgente %} - <span style="color: red;">URGENTE</span>{% endif %}</p>
                    </div>

                    <p style="text-align: center; margin: 30px 0;">
                        <a href="#" class="btn">Acessar Sistema de Compras</a>
                    </p>
                </div>

                <div class="footer">
                    <p>Este é um email automático do sistema de compras da Evoque Fitness.</p>
                    <p>{{ data_atual }}</p>
                </div>
            </div>
        </body>
        </html>
        """)

        # Preparar dados para o template
        from database import get_brazil_time
        data_atual = get_brazil_time().strftime('%d/%m/%Y às %H:%M')

        corpo_html = template_html.render(
            solicitacao=solicitacao,
            data_atual=data_atual
        )

        # Versão texto
        corpo_texto = f"""
Nova Solicitação de Compra - Evoque Fitness

PROTOCOLO: {solicitacao.protocolo}

SOLICITANTE:
- Nome: {solicitacao.solicitante.nome} {solicitacao.solicitante.sobrenome}
- Email: {solicitacao.solicitante.email}
- Setor: {solicitacao.solicitante.setor}

PRODUTO/SERVIÇO:
- Item: {solicitacao.produto}
- Quantidade: {solicitacao.quantidade}
- Categoria: {solicitacao.categoria or 'Não especificada'}
- Valor Estimado: R$ {solicitacao.valor_estimado or 'Não informado'}
- Data Desejada: {solicitacao.data_entrega_desejada.strftime('%d/%m/%Y') if solicitacao.data_entrega_desejada else 'Não especificada'}

JUSTIFICATIVA:
{solicitacao.justificativa}

OBSERVAÇÕES:
{solicitacao.observacoes or 'Nenhuma'}

PRIORIDADE: {solicitacao.prioridade} {'- URGENTE' if solicitacao.urgente else ''}

---
Sistema de Compras Evoque Fitness
{data_atual}
        """

        assunto = f"📋 Nova Solicitação de Compra - {solicitacao.protocolo}"

        # Enviar para o setor de compras e administradores
        destinatarios = []

        # Adicionar usuários do setor de compras
        users_compras = User.query.filter(User._setores.like('%Compras%')).all()
        for user in users_compras:
            if user.id != solicitacao.solicitante_id:  # Não enviar para o próprio solicitante
                destinatarios.append(user.email)

        # Adicionar administradores
        admins = User.query.filter_by(nivel_acesso='Administrador').all()
        for admin in admins:
            if admin.email not in destinatarios:
                destinatarios.append(admin.email)

        # Enviar email para cada destinatário
        for destinatario in destinatarios:
            email_service.enviar_email(destinatario, assunto, corpo_html, corpo_texto)

        # Enviar email de confirmação para o solicitante
        assunto_confirmacao = f"✅ Solicitação de Compra Criada - {solicitacao.protocolo}"
        email_service.enviar_email(solicitacao.solicitante.email, assunto_confirmacao, corpo_html, corpo_texto)

        return True

    except Exception as e:
        current_app.logger.error(f"Erro ao enviar email de nova solicitação: {str(e)}")
        return False
