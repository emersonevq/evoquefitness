// Sistema de Gerenciamento de Prioridades dos Problemas - Versão Corrigida

class PrioridadesManager {
    constructor() {
        this.problemas = [];
        this.isUpdating = false;
        this.cache = new Map();
        this.isInitialized = false;
        this.init();
    }

    init() {
        if (this.isInitialized) return;
        
        this.bindEvents();
        this.setupPerformanceOptimizations();
        this.isInitialized = true;
        console.log('PrioridadesManager inicializado com otimizações');
    }

    setupPerformanceOptimizations() {
        // Debounce para mudanças de prioridade
        this.debouncedUpdate = this.debounce(this.atualizarPrioridadeProblema.bind(this), 500);
        
        // Cache para requests
        this.cacheTimeout = 5 * 60 * 1000; // 5 minutos
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    bindEvents() {
        console.log('Configurando event listeners...');
        
        // Event listeners para botões de ação - usando delegação de eventos
        document.addEventListener('click', (e) => {
            console.log('Click detectado em:', e.target.id, e.target.className);
            
            if (e.target.id === 'btnSalvarTodasPrioridades') {
                e.preventDefault();
                this.salvarTodasPrioridades();
            } else if (e.target.id === 'btnResetarPrioridades') {
                e.preventDefault();
                this.resetarPrioridades();
            } else if (e.target.classList.contains('btn-remover-problema')) {
                e.preventDefault();
                const problemaId = e.target.dataset.problemaId;
                this.removerProblema(problemaId);
            }
        });

        // Event listener para mudanças de prioridade
        document.addEventListener('change', (e) => {
            if (e.target.classList.contains('select-prioridade-problema')) {
                const problemaId = e.target.dataset.problemaId;
                const novaPrioridade = e.target.value;
                const problemaNome = e.target.dataset.problemaNome;
                const prioridadeAnterior = e.target.dataset.prioridadeOriginal;
                
                this.marcarComoAlterado(e.target);
                
                // Auto-save com debounce
                this.debouncedUpdate(problemaId, novaPrioridade, problemaNome, prioridadeAnterior, true);
            }
        });
    }

    async carregarProblemas() {
        if (this.isUpdating) return;
        
        // Verificar cache primeiro
        const cacheKey = 'problemas_list';
        const cached = this.cache.get(cacheKey);
        if (cached && (Date.now() - cached.timestamp) < this.cacheTimeout) {
            this.problemas = cached.data;
            this.renderizarProblemas();
            return;
        }
        
        try {
            this.isUpdating = true;
            console.log('Carregando problemas...');
            
            const response = await fetch('/ti/painel/api/problemas', {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                },
                credentials: 'same-origin'
            });
            
            if (!response.ok) {
                let errorMessage = `Erro HTTP ${response.status}`;
                try {
                    const errorData = await response.json();
                    errorMessage = errorData.error || errorMessage;
                } catch (e) {
                    errorMessage = response.statusText || errorMessage;
                }
                throw new Error(errorMessage);
            }
            
            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                throw new Error('Resposta não é JSON válido - recebido: ' + contentType);
            }
            
            this.problemas = await response.json();
            
            if (!Array.isArray(this.problemas)) {
                throw new Error('Dados de problemas inválidos - esperado array');
            }
            
            // Atualizar cache
            this.cache.set(cacheKey, {
                data: this.problemas,
                timestamp: Date.now()
            });
            
            console.log('Problemas carregados com sucesso:', this.problemas.length);
            this.renderizarProblemas();
            
        } catch (error) {
            console.error('Erro ao carregar problemas:', error);
            this.showError('Erro ao carregar problemas', error.message);
            this.mostrarErroNoContainer(error.message);
        } finally {
            this.isUpdating = false;
        }
    }

    renderizarProblemas() {
        const container = document.getElementById('problemas-container');
        if (!container) {
            console.warn('Container problemas-container não encontrado');
            return;
        }
        
        // Usar DocumentFragment para melhor performance
        const fragment = document.createDocumentFragment();
        
        if (this.problemas.length === 0) {
            const emptyMessage = document.createElement('div');
            emptyMessage.className = 'empty-state text-center p-4';
            emptyMessage.innerHTML = `
                <div class="empty-icon mb-3">
                    <i class="fas fa-exclamation-triangle fa-3x text-warning"></i>
                </div>
                <p class="text-muted">Nenhum problema encontrado.</p>
            `;
            fragment.appendChild(emptyMessage);
        } else {
            console.log('Renderizando', this.problemas.length, 'problemas');
            
            this.problemas.forEach(problema => {
                const problemaElement = this.criarElementoProblema(problema);
                fragment.appendChild(problemaElement);
            });
        }
        
        // Limpar container e adicionar novos elementos
        container.innerHTML = '';
        container.appendChild(fragment);
        
        console.log('Problemas renderizados com sucesso');
    }

    criarElementoProblema(problema) {
        const div = document.createElement('div');
        div.className = 'problema-item card mb-3';
        div.setAttribute('data-problema-id', problema.id);
        
        div.innerHTML = `
            <div class="card-body">
                <div class="problema-header d-flex justify-content-between align-items-center mb-3">
                    <div class="problema-nome h6 mb-0" title="${problema.nome}">${problema.nome}</div>
                    <div class="problema-actions">
                        <button class="btn btn-danger btn-sm btn-remover-problema" 
                                data-problema-id="${problema.id}" 
                                title="Remover problema"
                                aria-label="Remover problema ${problema.nome}">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
                <div class="problema-info row">
                    <div class="col-md-6 problema-field">
                        <label for="prioridade-${problema.id}" class="form-label">Prioridade Padrão</label>
                        <select class="form-control select-prioridade-problema" 
                                id="prioridade-${problema.id}"
                                data-problema-id="${problema.id}"
                                data-problema-nome="${problema.nome}"
                                data-prioridade-original="${problema.prioridade_padrao}"
                                aria-label="Prioridade do problema ${problema.nome}">
                            <option value="Baixa" ${problema.prioridade_padrao === 'Baixa' ? 'selected' : ''}>Baixa</option>
                            <option value="Normal" ${problema.prioridade_padrao === 'Normal' ? 'selected' : ''}>Normal</option>
                            <option value="Alta" ${problema.prioridade_padrao === 'Alta' ? 'selected' : ''}>Alta</option>
                            <option value="Urgente" ${problema.prioridade_padrao === 'Urgente' ? 'selected' : ''}>Urgente</option>
                            <option value="Crítica" ${problema.prioridade_padrao === 'Crítica' ? 'selected' : ''}>Crítica</option>
                        </select>
                    </div>
                    <div class="col-md-6 problema-field">
                        <label class="form-label">Item de Internet</label>
                        <div class="mt-2">
                            ${problema.requer_item_internet ? 
                                '<span class="badge bg-info"><i class="fas fa-wifi"></i> Requer item de internet</span>' : 
                                '<span class="badge bg-secondary"><i class="fas fa-times"></i> Não requer item de internet</span>'
                            }
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        return div;
    }

    async atualizarPrioridadeProblema(problemaId, novaPrioridade, problemaNome, prioridadeAnterior, mostrarNotificacao = true) {
        try {
            console.log(`Atualizando prioridade do problema ${problemaId} para ${novaPrioridade}`);
            
            const response = await fetch(`/ti/painel/api/problemas/${problemaId}/prioridade`, {
                method: 'PUT',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                },
                credentials: 'same-origin',
                body: JSON.stringify({ prioridade: novaPrioridade })
            });
            
            if (!response.ok) {
                let errorMessage = `Erro HTTP ${response.status}`;
                try {
                    const contentType = response.headers.get('content-type');
                    if (contentType && contentType.includes('application/json')) {
                        const errorData = await response.json();
                        errorMessage = errorData.error || errorMessage;
                    } else {
                        const errorText = await response.text();
                        if (errorText.includes('<html>')) {
                            errorMessage = 'Erro de servidor - recebida página HTML ao invés de dados JSON';
                        } else {
                            errorMessage = errorText.substring(0, 100);
                        }
                    }
                } catch (parseError) {
                    console.error('Erro ao parsear resposta de erro:', parseError);
                    errorMessage = `Erro ${response.status}: ${response.statusText}`;
                }
                throw new Error(errorMessage);
            }
            
            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                throw new Error('Resposta inválida do servidor - esperado JSON');
            }
            
            const data = await response.json();
            
            // Atualizar dados locais
            const problema = this.problemas.find(p => p.id == problemaId);
            if (problema) {
                problema.prioridade_padrao = novaPrioridade;
            }
            
            // Invalidar cache
            this.cache.delete('problemas_list');

            // Atualizar o atributo data-prioridade-original
            const select = document.querySelector(`[data-problema-id="${problemaId}"]`);
            if (select) {
                select.dataset.prioridadeOriginal = novaPrioridade;
                select.classList.remove('is-warning');
            }

            console.log(`Prioridade do problema "${problemaNome}" atualizada para "${novaPrioridade}"`);

            // IMPORTANTE: Sincronizar configurações SLA após mudança de prioridade
            this.sincronizarSLAComPrioridades();

            if (mostrarNotificacao) {
                this.showSuccess(
                    'Prioridade Atualizada',
                    `Prioridade do problema "${problemaNome}" atualizada para "${novaPrioridade}" - SLA atualizado automaticamente`
                );
            }
            
            return data;
            
        } catch (error) {
            console.error('Erro ao atualizar prioridade:', error);
            
            let errorMessage = this.getErrorMessage(error.message);
            
            this.showError('Erro', errorMessage);
            
            // Reverter o select para o valor anterior
            const select = document.querySelector(`[data-problema-id="${problemaId}"]`);
            if (select && prioridadeAnterior) {
                select.value = prioridadeAnterior;
                select.classList.remove('is-warning');
            }
            
            throw error;
        }
    }

    async removerProblema(problemaId) {
        const problema = this.problemas.find(p => p.id == problemaId);
        if (!problema) return;

        // Confirmação com mais detalhes
        const confirmMessage = `Tem certeza que deseja remover o problema "${problema.nome}"?\n\nEsta ação não pode ser desfeita.`;
        if (!confirm(confirmMessage)) {
            return;
        }

        try {
            const response = await fetch(`/ti/painel/api/problemas/${problemaId}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Erro ao remover problema');
            }

            // Remover dos dados locais
            this.problemas = this.problemas.filter(p => p.id != problemaId);
            
            // Invalidar cache
            this.cache.delete('problemas_list');
            
            // Re-renderizar
            this.renderizarProblemas();

            this.showSuccess('Problema Removido', `Problema "${problema.nome}" removido com sucesso`);
        } catch (error) {
            console.error('Erro ao remover problema:', error);
            this.showError('Erro', 'Erro ao remover problema: ' + error.message);
        }
    }

    async salvarTodasPrioridades() {
        if (this.isUpdating) {
            console.log('Já existe uma operação em andamento');
            return;
        }
        
        const selects = document.querySelectorAll('.select-prioridade-problema');
        const alteracoes = [];
        
        selects.forEach(select => {
            const problemaId = select.dataset.problemaId;
            const novaPrioridade = select.value;
            const prioridadeOriginal = select.dataset.prioridadeOriginal;
            const problema = this.problemas.find(p => p.id == problemaId);
            
            if (problema && prioridadeOriginal !== novaPrioridade) {
                alteracoes.push({
                    id: problemaId,
                    prioridade: novaPrioridade,
                    nome: problema.nome,
                    prioridadeAnterior: prioridadeOriginal
                });
            }
        });
        
        if (alteracoes.length === 0) {
            this.showInfo('Informação', 'Nenhuma alteração detectada.');
            return;
        }
        
        // Desabilitar botão de salvar durante a operação
        const btnSalvar = document.getElementById('btnSalvarTodasPrioridades');
        if (btnSalvar) {
            btnSalvar.disabled = true;
            btnSalvar.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Salvando...';
        }
        
        try {
            this.isUpdating = true;
            
            console.log(`Salvando ${alteracoes.length} alteração(ões)...`);
            
            this.showInfo('Salvando', `Salvando ${alteracoes.length} alteração(ões)...`);
            
            // Processar alterações em paralelo (limitado)
            const batchSize = 3;
            const sucessos = [];
            const erros = [];
            
            for (let i = 0; i < alteracoes.length; i += batchSize) {
                const batch = alteracoes.slice(i, i + batchSize);
                const promises = batch.map(alt => 
                    this.atualizarPrioridadeProblema(
                        alt.id, 
                        alt.prioridade, 
                        alt.nome, 
                        alt.prioridadeAnterior, 
                        false
                    ).then(() => sucessos.push(alt))
                     .catch(error => erros.push({ ...alt, erro: error.message }))
                );
                
                await Promise.allSettled(promises);
                
                // Pequena pausa entre batches
                if (i + batchSize < alteracoes.length) {
                    await new Promise(resolve => setTimeout(resolve, 200));
                }
            }
            
            // Mostrar resultado final
            if (erros.length === 0) {
                this.showSuccess('Sucesso', `${sucessos.length} prioridade(s) atualizada(s) com sucesso!`);
            } else if (sucessos.length > 0) {
                const mensagem = `${sucessos.length} prioridade(s) salva(s) com sucesso, ${erros.length} falharam.`;
                this.showWarning('Parcialmente Salvo', mensagem);
            } else {
                const mensagem = `Nenhuma prioridade foi salva. ${erros.length} erro(s) encontrado(s).`;
                this.showError('Erro', mensagem);
            }
            
            // Recarregar dados para garantir consistência
            await this.carregarProblemas();

            // Sincronizar configurações SLA após alterações em lote
            if (sucessos.length > 0) {
                console.log('Sincronizando SLA após alterações em lote...');
                this.sincronizarSLAComPrioridades();
            }

        } catch (error) {
            console.error('Erro geral ao salvar prioridades:', error);
            this.showError('Erro', 'Erro inesperado ao salvar prioridades');
        } finally {
            this.isUpdating = false;
            
            // Reabilitar botão de salvar
            if (btnSalvar) {
                btnSalvar.disabled = false;
                btnSalvar.innerHTML = '<i class="fas fa-save"></i> Salvar Todas';
            }
        }
    }

    async resetarPrioridades() {
        const confirmMessage = 'Tem certeza que deseja resetar todas as prioridades para os valores padrão?\n\nEsta ação não pode ser desfeita.';
        if (!confirm(confirmMessage)) {
            return;
        }
        
        // Valores padrão
        const valoresPadrao = {
            'Catraca': 'Crítica',
            'Sistema EVO': 'Normal',
            'Notebook/Desktop': 'Alta',
            'TVs': 'Normal',
            'Internet': 'Alta'
        };
        
        const selects = document.querySelectorAll('.select-prioridade-problema');
        let alteracoes = 0;
        
        selects.forEach(select => {
            const problemaId = select.dataset.problemaId;
            const problema = this.problemas.find(p => p.id == problemaId);
            
            if (problema && valoresPadrao[problema.nome]) {
                select.value = valoresPadrao[problema.nome];
                this.marcarComoAlterado(select);
                alteracoes++;
            }
        });
        
        if (alteracoes > 0) {
            this.showInfo(
                'Informação', 
                `${alteracoes} prioridade(s) resetada(s) para os valores padrão. Clique em "Salvar Todas" para confirmar.`
            );
        } else {
            this.showInfo('Informação', 'Nenhuma prioridade foi alterada.');
        }
    }

    marcarComoAlterado(select) {
        select.classList.add('is-warning');
        console.log(`Prioridade do problema "${select.dataset.problemaNome}" alterada para "${select.value}" (não salvo ainda)`);
    }

    mostrarErroNoContainer(errorMessage) {
        const container = document.getElementById('problemas-container');
        if (container) {
            container.innerHTML = `
                <div class="alert alert-danger" role="alert">
                    <div class="d-flex align-items-center">
                        <i class="fas fa-exclamation-triangle me-3"></i>
                        <div>
                            <h6 class="mb-1">Erro ao carregar problemas</h6>
                            <p class="mb-2">${errorMessage}</p>
                            <button class="btn btn-outline-danger btn-sm" onclick="window.prioridadesManager.carregarProblemas()">
                                <i class="fas fa-refresh me-1"></i>Tentar novamente
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }
    }

    getErrorMessage(message) {
        if (message.includes('JSON')) {
            return 'Erro de comunicação com o servidor. Tente novamente.';
        } else if (message.includes('401')) {
            return 'Sessão expirada. Faça login novamente.';
        } else if (message.includes('403')) {
            return 'Acesso negado. Você não tem permissão para esta operação.';
        } else if (message.includes('500')) {
            return 'Erro interno do servidor. Tente novamente em alguns minutos.';
        }
        return message;
    }

    showNotification(message, type = 'info') {
        // Usar sistema de notificações existente se disponível
        if (window.advancedNotificationSystem) {
            const title = type === 'error' ? 'Erro' : 
                         type === 'success' ? 'Sucesso' : 
                         type === 'warning' ? 'Aviso' : 'Informação';
            
            if (type === 'error') {
                window.advancedNotificationSystem.showError(title, message);
            } else if (type === 'success') {
                window.advancedNotificationSystem.showSuccess(title, message);
            } else if (type === 'warning') {
                window.advancedNotificationSystem.showWarning(title, message);
            } else {
                window.advancedNotificationSystem.showInfo(title, message);
            }
        } else {
            // Fallback para alert simples
            alert(message);
        }
    }

    showSuccess(title, message) {
        this.showNotification(message, 'success');
    }

    showError(title, message) {
        this.showNotification(message, 'error');
    }

    showWarning(title, message) {
        this.showNotification(message, 'warning');
    }

    showInfo(title, message) {
        this.showNotification(message, 'info');
    }

    // Método para limpar cache
    clearCache() {
        this.cache.clear();
        console.log('Cache de prioridades limpo');
    }

    // Método para obter estatísticas
    getStats() {
        return {
            totalProblemas: this.problemas.length,
            porPrioridade: this.problemas.reduce((acc, p) => {
                acc[p.prioridade_padrao] = (acc[p.prioridade_padrao] || 0) + 1;
                return acc;
            }, {}),
            comItemInternet: this.problemas.filter(p => p.requer_item_internet).length
        };
    }

    // NOVA FUNÇÃO: Sincronizar configurações SLA com prioridades atualizadas
    async sincronizarSLAComPrioridades() {
        console.log('Sincronizando configurações SLA com prioridades...');

        try {
            // Buscar configurações atuais de SLA
            const response = await fetch('/ti/painel/api/configuracoes', {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                },
                credentials: 'same-origin'
            });

            if (!response.ok) {
                throw new Error(`Erro ao buscar configurações: ${response.status}`);
            }

            const configuracoes = await response.json();

            // Forçar recarregamento completo das configurações SLA
            if (typeof window.forcarRecarregamentoSLA === 'function') {
                console.log('Forçando recarregamento completo dos dados SLA...');
                window.forcarRecarregamentoSLA();
            } else if (typeof window.carregarSLA === 'function') {
                console.log('Recarregando dados SLA (fallback)...');
                window.carregarSLA();
            }

            console.log('Sincronização SLA concluída');

        } catch (error) {
            console.error('Erro ao sincronizar SLA:', error);
            // Não mostrar erro para não confundir o usuário, já que a prioridade foi salva
        }
    }
}

// Função global para carregar configurações de prioridades
function carregarConfiguracoesPrioridades() {
    console.log('Função carregarConfiguracoesPrioridades chamada');
    if (window.prioridadesManager) {
        window.prioridadesManager.carregarProblemas();
    } else {
        console.warn('prioridadesManager não está disponível');
    }
}

// Inicializar quando o DOM estiver carregado
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM carregado, inicializando PrioridadesManager...');
    
    // Verificar se já foi inicializado para evitar duplicação
    if (!window.prioridadesManager) {
        window.prioridadesManager = new PrioridadesManager();
        console.log('PrioridadesManager criado e anexado ao window');
        
        // Carregar problemas automaticamente quando entrar na seção de configurações
        const configLink = document.querySelector('a[href="#configuracoes"]');
        if (configLink) {
            configLink.addEventListener('click', () => {
                setTimeout(() => {
                    window.prioridadesManager.carregarProblemas();
                }, 300);
            });
        }
    } else {
        console.log('PrioridadesManager já existe');
    }
});

// Exportar para uso global
window.carregarConfiguracoesPrioridades = carregarConfiguracoesPrioridades;

// Função adicional para debug
window.debugPrioridades = function() {
    console.log('=== DEBUG PRIORIDADES ===');
    console.log('Manager existe:', !!window.prioridadesManager);
    console.log('Problemas carregados:', window.prioridadesManager?.problemas?.length || 0);
    console.log('Container existe:', !!document.getElementById('problemas-container'));
    console.log('Formulário existe:', !!document.getElementById('novoProblemaForm'));
};
