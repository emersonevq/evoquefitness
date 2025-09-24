from flask import Blueprint

financeiro_bp = Blueprint(
    'financeiro',
    __name__,
    template_folder='templates',
    static_folder='static'
)

from . import routes  # Isso deve vir DEPOIS da criação do blueprint
