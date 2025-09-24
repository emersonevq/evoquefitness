/**
 * Sistema de Timeout de Sessão
 * Monitora a atividade do usuário e exibe alertas quando a sessão está próxima do timeout
 */

// Guard to prevent duplicate class declaration
if (typeof window.SessionTimeoutManager === 'undefined') {
    window.SessionTimeoutManager = class SessionTimeoutManager {
    constructor() {
        this.sessionTimeout = 15 * 60 * 1000; // 15 minutos em milissegundos
        this.warningTime = 2 * 60 * 1000; // Avisar com 2 minutos restantes
        this.lastActivity = Date.now();
        this.warningShown = false;
        this.timeoutInterval = null;
        this.warningInterval = null;
        this.isActive = true;
        
        this.init();
    }
    
    init() {
        console.log('Sistema de timeout de sessão inicializado');
        this.bindActivityEvents();
        this.startTimeoutTimer();
    }
    
    bindActivityEvents() {
        // Eventos que resetam o timer de inatividade
        const events = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'];
        
        events.forEach(event => {
            document.addEventListener(event, () => {
                this.resetTimer();
            }, true);
        });
    }
    
    resetTimer() {
        if (!this.isActive) return;
        
        this.lastActivity = Date.now();
        this.warningShown = false;
        this.hideWarning();
        
        // Limpar timers existentes
        if (this.timeoutInterval) {
            clearTimeout(this.timeoutInterval);
        }
        if (this.warningInterval) {
            clearTimeout(this.warningInterval);
        }
        
        this.startTimeoutTimer();
    }
    
    startTimeoutTimer() {
        // Timer para o aviso (13 minutos)
        this.warningInterval = setTimeout(() => {
            this.showWarning();
        }, this.sessionTimeout - this.warningTime);
        
        // Timer para o logout automático (15 minutos)
        this.timeoutInterval = setTimeout(() => {
            this.forceLogout();
        }, this.sessionTimeout);
    }
    
    showWarning() {
        if (this.warningShown || !this.isActive) return;
        
        this.warningShown = true;
        
        // Criar modal de aviso
        const warningModal = this.createWarningModal();
        document.body.appendChild(warningModal);
        
        // Mostrar modal
        const modal = new bootstrap.Modal(warningModal);
        modal.show();
        
        // Countdown nos últimos 2 minutos
        this.startCountdown();
    }
    
    createWarningModal() {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.id = 'sessionTimeoutWarning';
        modal.setAttribute('data-bs-backdrop', 'static');
        modal.setAttribute('data-bs-keyboard', 'false');
        modal.innerHTML = `
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header bg-warning text-dark">
                        <h5 class="modal-title">
                            <i class="fas fa-exclamation-triangle me-2"></i>
                            Sessão expirando
                        </h5>
                    </div>
                    <div class="modal-body text-center">
                        <p class="mb-3">Sua sessão expirará em:</p>
                        <div class="countdown-timer">
                            <span id="countdown-minutes">02</span>:
                            <span id="countdown-seconds">00</span>
                        </div>
                        <p class="mt-3 text-muted">
                            Por motivos de segurança, você será desconectado automaticamente 
                            por inatividade.
                        </p>
                    </div>
                    <div class="modal-footer justify-content-center">
                        <button type="button" class="btn btn-primary" onclick="sessionManager.extendSession()">
                            <i class="fas fa-refresh me-2"></i>
                            Continuar sessão
                        </button>
                        <button type="button" class="btn btn-secondary" onclick="sessionManager.forceLogout()">
                            <i class="fas fa-sign-out-alt me-2"></i>
                            Sair agora
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        // Adicionar estilos para o countdown
        const style = document.createElement('style');
        style.textContent = `
            .countdown-timer {
                font-size: 2.5rem;
                font-weight: bold;
                color: #dc3545;
                font-family: 'Courier New', monospace;
            }
        `;
        document.head.appendChild(style);
        
        return modal;
    }
    
    startCountdown() {
        let timeLeft = this.warningTime; // 2 minutos em ms
        
        const countdownInterval = setInterval(() => {
            if (!this.warningShown) {
                clearInterval(countdownInterval);
                return;
            }
            
            timeLeft -= 1000;
            
            const minutes = Math.floor(timeLeft / 60000);
            const seconds = Math.floor((timeLeft % 60000) / 1000);
            
            const minutesEl = document.getElementById('countdown-minutes');
            const secondsEl = document.getElementById('countdown-seconds');
            
            if (minutesEl && secondsEl) {
                minutesEl.textContent = minutes.toString().padStart(2, '0');
                secondsEl.textContent = seconds.toString().padStart(2, '0');
            }
            
            if (timeLeft <= 0) {
                clearInterval(countdownInterval);
                this.forceLogout();
            }
        }, 1000);
    }
    
    extendSession() {
        console.log('Estendendo sessão...');
        this.hideWarning();
        this.resetTimer();
        
        // Fazer chamada AJAX para estender a sessão no servidor
        fetch('/auth/extend_session', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log('Sessão estendida com sucesso');
                this.showNotification('Sessão estendida com sucesso!', 'success');
            }
        })
        .catch(error => {
            console.error('Erro ao estender sessão:', error);
        });
    }
    
    forceLogout() {
        console.log('Forçando logout por timeout...');
        this.isActive = false;
        this.hideWarning();
        
        // Mostrar modal de logout
        this.showLogoutModal();
        
        // Redirecionar após 3 segundos
        setTimeout(() => {
            window.location.href = '/auth/logout?reason=timeout';
        }, 3000);
    }
    
    showLogoutModal() {
        // Remover modal de aviso se existir
        const warningModal = document.getElementById('sessionTimeoutWarning');
        if (warningModal) {
            warningModal.remove();
        }
        
        const logoutModal = document.createElement('div');
        logoutModal.className = 'modal fade show';
        logoutModal.style.display = 'block';
        logoutModal.setAttribute('data-bs-backdrop', 'static');
        logoutModal.innerHTML = `
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header bg-danger text-white">
                        <h5 class="modal-title">
                            <i class="fas fa-clock me-2"></i>
                            Sessão encerrada
                        </h5>
                    </div>
                    <div class="modal-body text-center">
                        <div class="mb-3">
                            <i class="fas fa-user-clock fa-3x text-muted"></i>
                        </div>
                        <h6>Sua sessão foi encerrada por inatividade</h6>
                        <p class="text-muted">
                            Por motivos de segurança, você foi desconectado automaticamente 
                            após 15 minutos de inatividade.
                        </p>
                        <p class="text-info">
                            <i class="fas fa-spinner fa-spin me-2"></i>
                            Redirecionando para a tela de login...
                        </p>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(logoutModal);
    }
    
    hideWarning() {
        const modal = document.getElementById('sessionTimeoutWarning');
        if (modal) {
            const bsModal = bootstrap.Modal.getInstance(modal);
            if (bsModal) {
                bsModal.hide();
            }
            modal.remove();
        }
    }
    
    showNotification(message, type = 'info') {
        // Usar sistema de notificações existente se disponível
        if (typeof showAlert === 'function') {
            showAlert(message, type);
        } else {
            // Fallback para console
            console.log(`${type.toUpperCase()}: ${message}`);
        }
    }
    
    getCSRFToken() {
        const token = document.querySelector('meta[name="csrf-token"]');
        return token ? token.getAttribute('content') : '';
    }
    
    destroy() {
        this.isActive = false;
        if (this.timeoutInterval) clearTimeout(this.timeoutInterval);
        if (this.warningInterval) clearTimeout(this.warningInterval);
        this.hideWarning();
    }
    }
}

// Inicializar o gerenciador de sessão quando o DOM estiver carregado
document.addEventListener('DOMContentLoaded', function() {
    // Verificar se já existe uma instância ativa
    if (typeof window.SessionTimeoutManager !== 'undefined' && (!window.sessionManager || window.sessionManager.isActive === false)) {
        window.sessionManager = new window.SessionTimeoutManager();
    }
});

// Limpar quando a página for descarregada
window.addEventListener('beforeunload', function() {
    if (window.sessionManager) {
        window.sessionManager.destroy();
    }
});
