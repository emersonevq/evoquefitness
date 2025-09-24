from flask import render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_user, logout_user, current_user, login_required
from database import db, User, Chamado, Unidade, AgenteSuporte, ResetSenha, get_brazil_time
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import secrets
import string
import random
from datetime import datetime, timedelta
from . import auth_bp

def get_user_redirect_url(user):
    """
    Determina para onde redirecionar o usuário após o login baseado no seu perfil
    """
    # 1. Administradores vão para o painel administrativo
    if user.nivel_acesso == 'Administrador':
        return url_for('ti.painel')

    # 2. Verificar se é agente de suporte ativo
    agente = AgenteSuporte.query.filter_by(usuario_id=user.id, ativo=True).first()
    if agente:
        return url_for('ti.painel_agente')

    # 3. Usuários do setor de TI vão para a página do TI
    if 'TI' in user.setores:
        return url_for('ti.index')

    # 4. Outros usuários vão para a página inicial
    return url_for('main.index')

def nivel_acesso_requerido(nivel_minimo):
    """
    Decorador para verificar nível de acesso do usuário.
    Níveis: Gestor (1) < Gerente (2) < Gerente Regional (3) < Administrador (4)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Faça login para acessar esta página.', 'warning')
                return redirect(url_for('auth.login', next=request.url))
            
            niveis = {
                'Gestor': 1,
                'Gerente': 2,
                'Gerente Regional': 3,
                'Administrador': 4
            }
            
            nivel_usuario = niveis.get(current_user.nivel_acesso, 0)
            nivel_necessario = niveis.get(nivel_minimo, 0)
            
            if nivel_usuario < nivel_necessario:
                flash('Você não tem permissão para acessar esta página.', 'danger')
                return redirect(url_for('main.index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def validar_senha(senha):
    """
    Valida a força da senha.
    Retorna (bool, str) - (senha é válida, mensagem de erro)
    """
    if len(senha) < 8:
        return False, 'A senha deve ter pelo menos 8 caracteres.'
    
    if not any(c.isupper() for c in senha):
        return False, 'A senha deve conter pelo menos uma letra maiúscula.'
    
    if not any(c.islower() for c in senha):
        return False, 'A senha deve conter pelo menos uma letra minúscula.'
    
    if not any(c.isdigit() for c in senha):
        return False, 'A senha deve conter pelo menos um número.'
    
    return True, ''

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        usuario = request.form.get('usuario', '').strip()
        senha = request.form.get('senha', '')
        lembrar = request.form.get('lembrar', False)
        
        if not usuario or not senha:
            flash('Por favor, preencha todos os campos.', 'danger')
            return render_template('login.html')
        
        user = User.query.filter_by(usuario=usuario).first()
        
        if user and user.check_password(senha):
            if user.bloqueado:
                flash('Sua conta está bloqueada. Entre em contato com o administrador.', 'danger')
                current_app.logger.warning(f'Tentativa de login em conta bloqueada: {usuario}')
                return render_template('login.html')
            
            if user.alterar_senha_primeiro_acesso:
                return render_template('login.html', alterar_senha=True, usuario=user.usuario)
            
            login_user(user, remember=True)

            # Registrar último acesso
            user.ultimo_acesso = datetime.utcnow()
            db.session.commit()

            current_app.logger.info(f'Login bem-sucedido: {usuario}')

            # Verificar se existe uma página específica solicitada
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):  # Previne redirect malicioso
                return redirect(next_page)

            # Redirecionamento inteligente baseado no tipo de usuário
            redirect_url = get_user_redirect_url(user)
            return redirect(redirect_url)
        else:
            current_app.logger.warning(f'Tentativa de login falha: {usuario}')
            flash('Usuário ou senha inválidos', 'danger')
    
    return render_template('login.html')

@auth_bp.route('/first_login', methods=['POST'])
def first_login():
    usuario = request.form.get('usuario')
    nova_senha = request.form.get('nova_senha')
    confirmar_senha = request.form.get('confirmar_senha')
    
    user = User.query.filter_by(usuario=usuario).first()
    if not user:
        flash('Usuário não encontrado', 'danger')
        return redirect(url_for('auth.login'))
    
    if not nova_senha or nova_senha != confirmar_senha:
        flash('As senhas não coincidem', 'danger')
        return render_template('login.html', alterar_senha=True, usuario=usuario)
    
    senha_valida, mensagem = validar_senha(nova_senha)
    if not senha_valida:
        flash(mensagem, 'danger')
        return render_template('login.html', alterar_senha=True, usuario=usuario)
    
    try:
        user.senha_hash = generate_password_hash(nova_senha)
        user.alterar_senha_primeiro_acesso = False
        db.session.commit()
        
        current_app.logger.info(f'Senha alterada com sucesso para usuário: {usuario}')
        flash('Senha alterada com sucesso. Faça login com sua nova senha.', 'success')
        return redirect(url_for('auth.login'))
    
    except Exception as e:
        current_app.logger.error(f'Erro ao alterar senha: {str(e)}')
        db.session.rollback()
        flash('Erro ao alterar senha. Tente novamente.', 'danger')
        return render_template('login.html', alterar_senha=True, usuario=usuario)

@auth_bp.route('/logout')
@login_required
def logout():
    reason = request.args.get('reason')

    if current_user.is_authenticated:
        usuario = current_user.usuario
        logout_user()

        if reason == 'timeout':
            current_app.logger.info(f'Logout por timeout de sessão: {usuario}')
            flash('Sua sessão foi encerrada por inatividade (15 minutos). Faça login novamente.', 'warning')
        else:
            current_app.logger.info(f'Logout bem-sucedido: {usuario}')
            flash('Você foi desconectado com sucesso.', 'info')

    return redirect(url_for('auth.login'))

@auth_bp.route('/perfil')
@login_required
def perfil():
    return render_template('perfil.html')

@auth_bp.route('/alterar_senha', methods=['POST'])
@login_required
def alterar_senha():
    senha_atual = request.form.get('senha_atual')
    nova_senha = request.form.get('nova_senha')
    confirmar_senha = request.form.get('confirmar_senha')

    if not current_user.check_password(senha_atual):
        flash('Senha atual incorreta', 'danger')
        return redirect(url_for('auth.perfil'))

    if nova_senha != confirmar_senha:
        flash('As novas senhas não coincidem', 'danger')
        return redirect(url_for('auth.perfil'))

    senha_valida, mensagem = validar_senha(nova_senha)
    if not senha_valida:
        flash(mensagem, 'danger')
        return redirect(url_for('auth.perfil'))

    try:
        current_user.senha_hash = generate_password_hash(nova_senha)
        db.session.commit()
        flash('Senha alterada com sucesso', 'success')
        current_app.logger.info(f'Senha alterada com sucesso para usuário: {current_user.usuario}')
    except Exception as e:
        current_app.logger.error(f'Erro ao alterar senha: {str(e)}')
        db.session.rollback()
        flash('Erro ao alterar senha', 'danger')

    return redirect(url_for('auth.perfil'))

@auth_bp.route('/extend_session', methods=['POST'])
@login_required
def extend_session():
    """Endpoint para estender a sessão do usuário"""
    try:
        from flask import session
        from datetime import datetime

        # Atualizar última atividade na sessão
        session['_last_activity'] = datetime.utcnow().timestamp()

        current_app.logger.info(f'Sessão estendida para usuário: {current_user.usuario}')

        return jsonify({
            'success': True,
            'message': 'Sessão estendida com sucesso',
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        current_app.logger.error(f'Erro ao estender sessão: {str(e)}')
        return jsonify({
            'success': False,
            'message': 'Erro ao estender sessão'
        }), 500

# ====================== FUNÇÕES DE RESET DE SENHA ======================

def gerar_codigo_6_digitos():
    """Gera um código de 6 dígitos aleatório"""
    return ''.join([str(random.randint(0, 9)) for _ in range(6)])

def gerar_token_seguro():
    """Gera um token seguro para o link de reset"""
    return secrets.token_urlsafe(32)

def enviar_email_reset_senha(user, codigo, token):
    """Envia email com código de reset de senha"""
    try:
        from setores.ti.email_service import email_service

        return email_service.enviar_codigo_reset_senha(
            usuario=user,
            codigo=codigo,
            token=token,
            url_base=request.url_root
        )

    except Exception as e:
        current_app.logger.error(f"Erro ao enviar email de reset: {str(e)}")
        return False

@auth_bp.route('/esqueci-senha', methods=['POST'])
def esqueci_senha():
    """Rota para solicitar reset de senha"""
    try:
        data = request.get_json()
        usuario_email = data.get('usuario_email', '').strip()

        if not usuario_email:
            return jsonify({
                'success': False,
                'message': 'Por favor, digite seu usuário ou email.'
            }), 400

        # Buscar usuário por nome de usuário ou email
        user = User.query.filter(
            (User.usuario == usuario_email) | (User.email == usuario_email)
        ).first()

        if not user:
            # Por segurança, não revelar se o usuário existe ou não
            return jsonify({
                'success': True,
                'message': 'Se o usuário existir, um código foi enviado para o email cadastrado.'
            })

        if user.bloqueado:
            return jsonify({
                'success': False,
                'message': 'Esta conta está bloqueada. Entre em contato com o administrador.'
            }), 400

        # Invalidar tentativas anteriores não utilizadas
        ResetSenha.query.filter_by(usuario_id=user.id, usado=False).update({'usado': True})

        # Gerar código e token
        codigo = gerar_codigo_6_digitos()
        token = gerar_token_seguro()

        # Criar registro de reset
        reset_senha = ResetSenha(
            usuario_id=user.id,
            codigo=codigo,
            token=token,
            data_expiracao=get_brazil_time().replace(tzinfo=None) + timedelta(minutes=30),
            ip_solicitacao=request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr),
            user_agent=request.headers.get('User-Agent', '')
        )

        db.session.add(reset_senha)
        db.session.commit()

        # Enviar email
        if enviar_email_reset_senha(user, codigo, token):
            current_app.logger.info(f"Reset de senha solicitado para usuário: {user.usuario}")

            return jsonify({
                'success': True,
                'message': 'Código enviado para seu email!',
                'token': token
            })
        else:
            # Se falhou o envio do email, remover o registro
            db.session.delete(reset_senha)
            db.session.commit()

            return jsonify({
                'success': False,
                'message': 'Erro ao enviar email. Verifique se o email está correto ou tente novamente em alguns minutos.'
            }), 500

    except Exception as e:
        current_app.logger.error(f"Erro em esqueci_senha: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'Erro interno do servidor. Tente novamente.'
        }), 500

@auth_bp.route('/validar-codigo', methods=['POST'])
def validar_codigo():
    """Rota para validar código de 6 dígitos"""
    try:
        data = request.get_json()
        codigo = data.get('codigo', '').strip()
        token = data.get('token', '').strip()

        if not codigo or not token:
            return jsonify({
                'success': False,
                'message': 'Código e token são obrigatórios.'
            }), 400

        if len(codigo) != 6 or not codigo.isdigit():
            return jsonify({
                'success': False,
                'message': 'O código deve ter exatamente 6 dígitos.'
            }), 400

        # Buscar registro de reset
        reset_senha = ResetSenha.query.filter_by(
            token=token,
            codigo=codigo,
            usado=False
        ).first()

        if not reset_senha:
            return jsonify({
                'success': False,
                'message': 'Código inválido ou já utilizado.'
            }), 400

        if not reset_senha.esta_valido():
            return jsonify({
                'success': False,
                'message': 'Código expirado. Solicite um novo código.'
            }), 400

        # Incrementar tentativas (para auditoria)
        reset_senha.incrementar_tentativa()

        current_app.logger.info(f"Código validado com sucesso para usuário: {reset_senha.usuario.usuario}")

        return jsonify({
            'success': True,
            'message': 'Código validado com sucesso!'
        })

    except Exception as e:
        current_app.logger.error(f"Erro em validar_codigo: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Erro interno do servidor.'
        }), 500

@auth_bp.route('/redefinir-senha', methods=['POST'])
def redefinir_senha():
    """Rota para redefinir a senha"""
    try:
        data = request.get_json()
        nova_senha = data.get('nova_senha', '')
        confirmar_senha = data.get('confirmar_senha', '')
        token = data.get('token', '').strip()

        if not nova_senha or not confirmar_senha or not token:
            return jsonify({
                'success': False,
                'message': 'Todos os campos são obrigatórios.'
            }), 400

        if nova_senha != confirmar_senha:
            return jsonify({
                'success': False,
                'message': 'As senhas não coincidem.'
            }), 400

        # Validar força da senha
        senha_valida, mensagem = validar_senha(nova_senha)
        if not senha_valida:
            return jsonify({
                'success': False,
                'message': mensagem
            }), 400

        # Buscar registro de reset válido
        reset_senha = ResetSenha.query.filter_by(
            token=token,
            usado=False
        ).first()

        if not reset_senha:
            return jsonify({
                'success': False,
                'message': 'Token inválido ou já utilizado.'
            }), 400

        if not reset_senha.esta_valido():
            return jsonify({
                'success': False,
                'message': 'Token expirado. Solicite um novo código.'
            }), 400

        # Atualizar senha do usuário
        user = reset_senha.usuario
        user.senha_hash = generate_password_hash(nova_senha)

        # Marcar reset como usado
        reset_senha.marcar_como_usado(
            ip_uso=request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        )

        db.session.commit()

        current_app.logger.info(f"Senha redefinida com sucesso para usuário: {user.usuario}")

        return jsonify({
            'success': True,
            'message': 'Senha alterada com sucesso!'
        })

    except Exception as e:
        current_app.logger.error(f"Erro em redefinir_senha: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'Erro interno do servidor.'
        }), 500

@auth_bp.route('/reset-senha')
def reset_senha_link():
    """Rota para acesso via link de email"""
    token = request.args.get('token')

    if not token:
        flash('Link inválido ou expirado.', 'danger')
        return redirect(url_for('auth.login'))

    # Verificar se o token existe e é válido
    reset_senha = ResetSenha.query.filter_by(token=token, usado=False).first()

    if not reset_senha or not reset_senha.esta_valido():
        flash('Link inválido ou expirado. Solicite um novo código.', 'danger')
        return redirect(url_for('auth.login'))

    # Renderizar página de login com modal de nova senha aberto
    return render_template('login.html', reset_token=token, abrir_modal_senha=True)
