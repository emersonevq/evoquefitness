from functools import wraps
from flask import redirect, url_for, flash, request, current_app, jsonify
from flask_login import current_user, logout_user
from datetime import datetime, timedelta
from functools import wraps
from database import db

def is_api_request():
    """Verifica se a requisição é para a API"""
    return request.path.startswith('/api/')

def setor_required(*setores_necessarios):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                if is_api_request():
                    return jsonify({
                        'error': 'Não autorizado',
                        'message': 'Faça login para acessar este recurso'
                    }), 401
                flash('Faça login para acessar esta página.', 'warning')
                return redirect(url_for('auth.login', next=request.url))
            
            # Verificar inatividade (15 minutos)
            if current_user.ultimo_acesso is None or (datetime.utcnow() - current_user.ultimo_acesso) > timedelta(minutes=15):
                logout_user()
                if is_api_request():
                    return jsonify({
                        'error': 'Sessão expirada',
                        'message': 'Sua sessão expirou por inatividade'
                    }), 401
                flash('Sessão expirada por inatividade. Faça login novamente.', 'warning')
                return redirect(url_for('auth.login', next=request.url))
            
            # Atualizar último acesso
            current_user.ultimo_acesso = datetime.utcnow()
            try:
                db.session.commit()
            except Exception as e:
                current_app.logger.error(f"Erro ao atualizar último acesso: {str(e)}")
                db.session.rollback()
            
            # Recarregar o usuário do banco para refletir permissões atualizadas em tempo real
            try:
                db.session.refresh(current_user)
            except Exception:
                try:
                    from database import User
                    _ = User.query.get(current_user.id)
                except Exception:
                    pass

            # Verifica se o usuário tem acesso a algum dos setores necessários
            tem_acesso = any(
                current_user.tem_acesso_setor(setor)
                for setor in setores_necessarios
            )
            
            if not tem_acesso:
                current_app.logger.warning(
                    f'Usuário {current_user.usuario} tentou acessar {request.url} '
                    f'sem permissão. Setores necessários: {setores_necessarios}'
                )
                if is_api_request():
                    return jsonify({
                        'error': 'Acesso negado',
                        'message': 'Você não tem permissão para acessar este recurso',
                        'required_sectors': setores_necessarios
                    }), 403
                flash('Você não tem permissão para acessar esta área.', 'danger')
                return redirect(url_for('main.acesso_negado'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def nivel_acesso_requerido(nivel_minimo):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                if is_api_request():
                    return jsonify({
                        'error': 'Não autorizado',
                        'message': 'Faça login para acessar este recurso'
                    }), 401
                flash('Faça login para acessar esta página.', 'warning')
                return redirect(url_for('auth.login', next=request.url))
            
            if not current_user.tem_permissao(nivel_minimo):
                current_app.logger.warning(
                    f'Usuário {current_user.usuario} tentou acessar {request.url} '
                    f'sem nível adequado. Nível necessário: {nivel_minimo}'
                )
                if is_api_request():
                    return jsonify({
                        'error': 'Acesso negado',
                        'message': 'Nível de acesso insuficiente',
                        'required_level': nivel_minimo
                    }), 403
                flash('Você não tem permissão para acessar esta página.', 'danger')
                return redirect(url_for('main.acesso_negado'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
