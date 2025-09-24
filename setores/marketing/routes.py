from flask import Blueprint, render_template
from flask_login import login_required
from auth.auth_helpers import setor_required  # Importar decorador de permissão por setor

marketing = Blueprint('marketing', __name__, 
                     url_prefix='/marketing',
                     template_folder='templates')

@marketing.route('/')
@login_required
@setor_required('Marketing')
def index():
    return render_template('marketing/index.html')

@marketing.route('/campanhas')
@login_required
@setor_required('Marketing')
def campanhas():
    return render_template('marketing/campanhas.html')

@marketing.route('/redes-sociais')
@login_required
@setor_required('Marketing')
def redes_sociais():
    return render_template('marketing/redes_sociais.html')

@marketing.route('/analytics')
@login_required
@setor_required('Marketing')
def analytics():
    return render_template('marketing/analytics.html')

@marketing.route('/conteudo')
@login_required
@setor_required('Marketing')
def conteudo():
    return render_template('marketing/conteudo.html')

@marketing.route('/contato')
@login_required
@setor_required('Marketing')
def contato():
    return render_template('marketing/contato.html')
