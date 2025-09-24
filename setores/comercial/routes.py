from flask import Blueprint, render_template, jsonify
from flask_login import login_required
from auth.auth_helpers import setor_required  # Importação do decorador setor_required

# Criar o Blueprint
comercial = Blueprint('comercial', __name__, 
                     url_prefix='/comercial',
                     template_folder='templates')

@comercial.route('/')
@login_required
@setor_required('comercial')  # Adicionado proteção de setor
def index():
    return render_template('comercial/index.html')

@comercial.route('/vendas')
@login_required
@setor_required('comercial')  # Adicionado proteção de setor
def vendas():
    return render_template('comercial/vendas.html')

@comercial.route('/metas')
@login_required
@setor_required('comercial')  # Adicionado proteção de setor
def metas():
    return render_template('comercial/metas.html')

@comercial.route('/clientes')
@login_required
@setor_required('comercial')  # Adicionado proteção de setor
def clientes():
    return render_template('comercial/clientes.html')

@comercial.route('/relatorios')
@login_required
@setor_required('comercial')  # Adicionado proteção de setor
def relatorios():
    return render_template('comercial/relatorios.html')