from flask import Blueprint, render_template
from flask_login import login_required  # Adicione esta importação
import os
from auth.auth_helpers import setor_required  # Importação do decorador setor_required


financeiro_bp = Blueprint(
    'financeiro', 
    __name__,
    template_folder='templates'  # Isso faz o blueprint procurar em /setores/financeiro/templates
)

@financeiro_bp.route('/')
@login_required
@setor_required('financeiro')  # Adicionado proteção d
def index():
    return render_template('financeiro/index.html')  # Procurará em /setores/financeiro/templates/financeiro/index.html