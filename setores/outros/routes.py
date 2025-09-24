from flask import Blueprint, render_template, flash, redirect, url_for, request
from flask_login import login_required, current_user
from database import db

outros_bp = Blueprint('outros', __name__, 
                     template_folder='templates')

@outros_bp.route('/')
@login_required
def index():
    return render_template('outros/outros.html')

@outros_bp.route('/produtos-limpeza')
@login_required
def produtos_limpeza():
    return render_template('outros/produtos_limpeza.html')

@outros_bp.route('/contas-pagar')
@login_required
def contas_pagar():
    return render_template('outros/contas_pagar.html')

@outros_bp.route('/relatar-problema')
@login_required
def relatar_problema():
    return render_template('outros/relatar_problema.html')

@outros_bp.route('/contato')
@login_required
def contato():
    return render_template('outros/contato.html')