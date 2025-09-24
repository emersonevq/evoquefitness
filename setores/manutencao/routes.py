from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from auth.auth_helpers import setor_required  # Importa o decorador de controle por setor
import os 

manutencao = Blueprint('manutencao', __name__, 
                      url_prefix='/manutencao',
                      template_folder='templates')

# Rota principal
@manutencao.route('/')
@login_required
@setor_required('Manutenção')
def index():
    return render_template('manutencao/index.html')

# Rota para manutenção preventiva
@manutencao.route('/preventiva')
@login_required
@setor_required('Manutenção')
def preventiva():
    return render_template('manutencao/preventiva.html')

# Rota para manutenção corretiva
@manutencao.route('/corretiva')
@login_required
@setor_required('Manutenção')
def corretiva():
    return render_template('manutencao/corretiva.html')

# Rota para acompanhamento
@manutencao.route('/acompanhamento')
@login_required
@setor_required('Manutenção')
def acompanhamento():
    return render_template('manutencao/acompanhamento.html')

# Rota para histórico
@manutencao.route('/historico')
@login_required
@setor_required('Manutenção')
def historico():
    return render_template('manutencao/historico.html')

# API para status
@manutencao.route('/api/status')
@login_required
@setor_required('Manutenção')
def get_status():
    status = {
        'equipamentos_ativos': 95,
        'manutencoes_andamento': 12,
        'tempo_medio_resposta': 4,
        'solicitacoes_concluidas': 850
    }
    return jsonify(status)
