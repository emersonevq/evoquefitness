from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required
from datetime import datetime
from auth.auth_helpers import setor_required  # Importar decorador de controle por setor

# Criar o Blueprint
produtos = Blueprint('produtos', __name__,
                    url_prefix='/produtos',
                    template_folder='templates')

# Rota principal do setor de produtos
@produtos.route('/')
@login_required
@setor_required('Produtos')
def index():
    return render_template('produtos/index.html')

# Rota para cadastro de produtos
@produtos.route('/cadastro', methods=['GET', 'POST'])
@login_required
@setor_required('Produtos')
def cadastro():
    if request.method == 'POST':
        # Aqui você implementaria a lógica de cadastro
        produto = {
            'nome': request.form.get('nome'),
            'categoria': request.form.get('categoria'),
            'quantidade': request.form.get('quantidade'),
            'preco': request.form.get('preco')
        }
        # Salvar no banco de dados (implemente conforme seu ORM ou banco)
        flash('Produto cadastrado com sucesso!', 'success')
        return redirect(url_for('produtos.index'))
    return render_template('produtos/cadastro.html')

# Rota para controle de estoque
@produtos.route('/estoque', methods=['GET', 'POST'])
@login_required
@setor_required('Produtos')
def estoque():
    if request.method == 'POST':
        # Implementar lógica de movimentação de estoque
        movimento = {
            'produto_id': request.form.get('produto_id'),
            'tipo': request.form.get('tipo'),  # entrada ou saída
            'quantidade': request.form.get('quantidade'),
            'data': datetime.now()
        }
        # Salvar no banco de dados
        flash('Movimentação registrada com sucesso!', 'success')
        return redirect(url_for('produtos.estoque'))
    return render_template('produtos/estoque.html')

# Rota para inventário
@produtos.route('/inventario', methods=['GET', 'POST'])
@login_required
@setor_required('Produtos')
def inventario():
    if request.method == 'POST':
        # Implementar lógica de inventário
        inventario_data = {
            'data': datetime.now(),
            'responsavel': request.form.get('responsavel'),
            'observacoes': request.form.get('observacoes')
        }
        # Salvar no banco de dados
        flash('Inventário iniciado com sucesso!', 'success')
        return redirect(url_for('produtos.inventario'))
    return render_template('produtos/inventario.html')

# Rota para relatórios
@produtos.route('/relatorios')
@login_required
@setor_required('Produtos')
def relatorios():
    return render_template('produtos/relatorios.html')

# API Routes

# Rota para buscar status do estoque
@produtos.route('/api/status')
@login_required
@setor_required('Produtos')
def get_status():
    status = {
        'total_produtos': 1500,
        'disponibilidade': 95,
        'giro_mensal': 4.2,
        'valor_estoque': 250000
    }
    return jsonify(status)

# Rota para buscar produtos em destaque
@produtos.route('/api/produtos-destaque')
@login_required
@setor_required('Produtos')
def get_produtos_destaque():
    produtos_lista = [
        {
            'nome': 'Whey Protein Premium',
            'estoque': 150,
            'avaliacao': 4.8,
            'demanda': 85
        },
        {
            'nome': 'BCAA Advanced',
            'estoque': 200,
            'avaliacao': 4.6,
            'demanda': 75
        },
        {
            'nome': 'Creatina Pure',
            'estoque': 180,
            'avaliacao': 4.9,
            'demanda': 90
        }
    ]
    return jsonify(produtos_lista)

# Rota para buscar movimentações recentes
@produtos.route('/api/movimentacoes')
@login_required
@setor_required('Produtos')
def get_movimentacoes():
    movimentacoes = [
        {
            'data': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'tipo': 'entrada',
            'produto': 'Whey Protein',
            'quantidade': 50
        }
        # Adicione mais movimentações conforme necessário
    ]
    return jsonify(movimentacoes)

# Rota para buscar alertas de estoque
@produtos.route('/api/alertas')
@login_required
@setor_required('Produtos')
def get_alertas():
    alertas = [
        {
            'produto': 'BCAA',
            'tipo': 'estoque_baixo',
            'quantidade_atual': 10,
            'quantidade_minima': 20
        }
        # Adicione mais alertas conforme necessário
    ]
    return jsonify(alertas)
