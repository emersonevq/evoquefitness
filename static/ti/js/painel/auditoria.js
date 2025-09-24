// ==================== AUDITORIA E LOGS ====================

let logsAcessoData = [];
let sessoesAtivasData = [];
let logsAcoesData = [];

// Inicialização da seção de auditoria
function inicializarAuditoria() {
    console.log('Inicializando seção de auditoria...');
    
    // Carregar dados iniciais
    carregarEstatisticasAuditoria();
    carregarLogsAcesso();
    carregarSessoesAtivas();
    carregarLogsAcoes();
    
    // Configurar event listeners
    configurarEventListenersAuditoria();
    
    // Atualizar dados a cada 30 segundos
    setInterval(() => {
        carregarEstatisticasAuditoria();
        carregarSessoesAtivas();
    }, 30000);
}

function configurarEventListenersAuditoria() {
    // Filtros de logs de acesso
    const filtroAcessoDias = document.getElementById('filtroAcessoDias');
    const filtroAcessoUsuario = document.getElementById('filtroAcessoUsuario');
    const filtroAcessoIP = document.getElementById('filtroAcessoIP');
    
    if (filtroAcessoDias) {
        filtroAcessoDias.addEventListener('change', carregarLogsAcesso);
    }
    
    if (filtroAcessoUsuario) {
        filtroAcessoUsuario.addEventListener('change', carregarLogsAcesso);
    }
    
    if (filtroAcessoIP) {
        filtroAcessoIP.addEventListener('input', debounce(carregarLogsAcesso, 500));
    }
    
    // Filtros de logs de ações
    const filtroAcoesDias = document.getElementById('filtroAcoesDias');
    const filtroAcoesCategoria = document.getElementById('filtroAcoesCategoria');
    const filtroAcoesUsuario = document.getElementById('filtroAcoesUsuario');
    
    if (filtroAcoesDias) {
        filtroAcoesDias.addEventListener('change', carregarLogsAcoes);
    }
    
    if (filtroAcoesCategoria) {
        filtroAcoesCategoria.addEventListener('change', carregarLogsAcoes);
    }
    
    if (filtroAcoesUsuario) {
        filtroAcoesUsuario.addEventListener('change', carregarLogsAcoes);
    }
    
    // Botões de atualização
    const btnAtualizarAuditoria = document.getElementById('btnAtualizarAuditoria');
    if (btnAtualizarAuditoria) {
        btnAtualizarAuditoria.addEventListener('click', () => {
            carregarEstatisticasAuditoria();
            carregarLogsAcesso();
            carregarSessoesAtivas();
            carregarLogsAcoes();
            
            if (window.advancedNotificationSystem) {
                window.advancedNotificationSystem.showInfo('Atualizado', 'Dados de auditoria atualizados');
            }
        });
    }
}

// Carregar estatísticas de auditoria
async function carregarEstatisticasAuditoria() {
    try {
        const response = await fetch('/ti/painel/api/auditoria/estatisticas');
        if (!response.ok) throw new Error('Erro ao carregar estatísticas');
        
        const stats = await response.json();
        
        // Atualizar elementos na tela
        const elementos = {
            'acessosHoje': stats.acessos_hoje,
            'acessosOntem': stats.acessos_ontem,
            'usuariosUnicosSemanaa': stats.usuarios_unicos_semana,
            'sessoesAtivasAgora': stats.sessoes_ativas_agora,
            'acoesUltimoMes': stats.acoes_ultimo_mes
        };
        
        Object.entries(elementos).forEach(([id, valor]) => {
            const elemento = document.getElementById(id);
            if (elemento) {
                elemento.textContent = valor || '0';
            }
        });
        
        // Atualizar top IPs
        const topIPsContainer = document.getElementById('topIPsContainer');
        if (topIPsContainer && stats.top_ips) {
            topIPsContainer.innerHTML = stats.top_ips.map(item => `
                <div class="d-flex justify-content-between">
                    <span>${item.ip}</span>
                    <span class="badge bg-primary">${item.total}</span>
                </div>
            `).join('');
        }
        
        // Atualizar timestamp
        const timestampElement = document.getElementById('statsTimestamp');
        if (timestampElement) {
            timestampElement.textContent = `Atualizado: ${stats.data_atualizacao}`;
        }
        
    } catch (error) {
        console.error('Erro ao carregar estatísticas:', error);
        if (window.advancedNotificationSystem) {
            window.advancedNotificationSystem.showError('Erro', 'Erro ao carregar estatísticas de auditoria');
        }
    }
}

// Carregar logs de acesso
async function carregarLogsAcesso() {
    try {
        const params = new URLSearchParams();
        
        const filtroAcessoDias = document.getElementById('filtroAcessoDias');
        const filtroAcessoUsuario = document.getElementById('filtroAcessoUsuario');
        const filtroAcessoIP = document.getElementById('filtroAcessoIP');
        
        if (filtroAcessoDias && filtroAcessoDias.value) {
            params.append('dias', filtroAcessoDias.value);
        }
        
        if (filtroAcessoUsuario && filtroAcessoUsuario.value) {
            params.append('usuario_id', filtroAcessoUsuario.value);
        }
        
        if (filtroAcessoIP && filtroAcessoIP.value) {
            params.append('ip', filtroAcessoIP.value);
        }
        
        const response = await fetch(`/ti/painel/api/auditoria/logs-acesso?${params}`);
        if (!response.ok) throw new Error('Erro ao carregar logs de acesso');
        
        logsAcessoData = await response.json();
        renderizarLogsAcesso();
        
    } catch (error) {
        console.error('Erro ao carregar logs de acesso:', error);
        if (window.advancedNotificationSystem) {
            window.advancedNotificationSystem.showError('Erro', 'Erro ao carregar logs de acesso');
        }
    }
}

// Renderizar logs de acesso
function renderizarLogsAcesso() {
    const container = document.getElementById('logsAcessoContainer');
    if (!container) return;
    
    if (!logsAcessoData || logsAcessoData.length === 0) {
        container.innerHTML = `
            <div class="text-center py-4">
                <i class="fas fa-history fa-3x text-muted mb-3"></i>
                <h5 class="text-muted">Nenhum log de acesso encontrado</h5>
                <p class="text-muted">Tente ajustar os filtros</p>
            </div>
        `;
        return;
    }
    
    const html = logsAcessoData.map(log => `
        <div class="card mb-2">
            <div class="card-body py-2">
                <div class="row align-items-center">
                    <div class="col-md-3">
                        <strong>${log.usuario.nome}</strong>
                        <br><small class="text-muted">${log.usuario.email}</small>
                    </div>
                    <div class="col-md-2">
                        <span class="badge ${log.ativo ? 'bg-success' : 'bg-secondary'}">
                            ${log.ativo ? 'Ativo' : 'Finalizado'}
                        </span>
                        <br><small class="text-muted">${log.dispositivo || 'Desconhecido'}</small>
                    </div>
                    <div class="col-md-2">
                        <i class="fas fa-clock"></i> ${log.data_acesso}
                        ${log.data_logout ? `<br><small class="text-muted">Logout: ${log.data_logout}</small>` : ''}
                    </div>
                    <div class="col-md-2">
                        <i class="fas fa-globe"></i> ${log.ip_address || 'N/A'}
                        ${log.cidade ? `<br><small class="text-muted">${log.cidade}</small>` : ''}
                    </div>
                    <div class="col-md-2">
                        <i class="fas fa-browser"></i> ${log.navegador || 'N/A'}
                        <br><small class="text-muted">${log.sistema_operacional || 'N/A'}</small>
                    </div>
                    <div class="col-md-1 text-center">
                        ${log.duracao_minutos ? `${log.duracao_minutos}min` : 'N/A'}
                    </div>
                </div>
            </div>
        </div>
    `).join('');
    
    container.innerHTML = html;
}

// Carregar sessões ativas
async function carregarSessoesAtivas() {
    try {
        const response = await fetch('/ti/painel/api/auditoria/sessoes-ativas');
        if (!response.ok) throw new Error('Erro ao carregar sessões ativas');
        
        sessoesAtivasData = await response.json();
        renderizarSessoesAtivas();
        
    } catch (error) {
        console.error('Erro ao carregar sessões ativas:', error);
        if (window.advancedNotificationSystem) {
            window.advancedNotificationSystem.showError('Erro', 'Erro ao carregar sessões ativas');
        }
    }
}

// Renderizar sessões ativas
function renderizarSessoesAtivas() {
    const container = document.getElementById('sessoesAtivasContainer');
    if (!container) return;
    
    if (!sessoesAtivasData || sessoesAtivasData.length === 0) {
        container.innerHTML = `
            <div class="text-center py-4">
                <i class="fas fa-users fa-3x text-muted mb-3"></i>
                <h5 class="text-muted">Nenhuma sessão ativa</h5>
                <p class="text-muted">Não há usuários online no momento</p>
            </div>
        `;
        return;
    }
    
    const html = sessoesAtivasData.map(sessao => `
        <div class="card mb-2">
            <div class="card-body py-2">
                <div class="row align-items-center">
                    <div class="col-md-3">
                        <strong>${sessao.usuario.nome}</strong>
                        <br><small class="text-muted">${sessao.usuario.email}</small>
                    </div>
                    <div class="col-md-2">
                        <span class="badge ${sessao.status === 'ativo' ? 'bg-success' : 'bg-warning'}">
                            ${sessao.status}
                        </span>
                        <br><small class="text-muted">${sessao.dispositivo || 'Desktop'}</small>
                    </div>
                    <div class="col-md-2">
                        <i class="fas fa-sign-in-alt"></i> ${sessao.data_inicio}
                        <br><small class="text-muted">Última: ${sessao.ultima_atividade}</small>
                    </div>
                    <div class="col-md-2">
                        <i class="fas fa-globe"></i> ${sessao.ip_address || 'N/A'}
                        ${sessao.cidade ? `<br><small class="text-muted">${sessao.cidade}</small>` : ''}
                    </div>
                    <div class="col-md-2">
                        <i class="fas fa-browser"></i> ${sessao.navegador || 'N/A'}
                        <br><small class="text-muted">${sessao.sistema_operacional || 'N/A'}</small>
                    </div>
                    <div class="col-md-1">
                        ${sessao.status === 'ativo' ? `
                            <button class="btn btn-sm btn-danger" onclick="encerrarSessao(${sessao.id})" title="Encerrar sessão">
                                <i class="fas fa-times"></i>
                            </button>
                        ` : `${sessao.duracao_minutos}min`}
                    </div>
                </div>
            </div>
        </div>
    `).join('');
    
    container.innerHTML = html;
}

// Carregar logs de ações
async function carregarLogsAcoes() {
    try {
        const params = new URLSearchParams();
        
        const filtroAcoesDias = document.getElementById('filtroAcoesDias');
        const filtroAcoesCategoria = document.getElementById('filtroAcoesCategoria');
        const filtroAcoesUsuario = document.getElementById('filtroAcoesUsuario');
        
        if (filtroAcoesDias && filtroAcoesDias.value) {
            params.append('dias', filtroAcoesDias.value);
        }
        
        if (filtroAcoesCategoria && filtroAcoesCategoria.value) {
            params.append('categoria', filtroAcoesCategoria.value);
        }
        
        if (filtroAcoesUsuario && filtroAcoesUsuario.value) {
            params.append('usuario_id', filtroAcoesUsuario.value);
        }
        
        const response = await fetch(`/ti/painel/api/auditoria/logs-acoes?${params}`);
        if (!response.ok) throw new Error('Erro ao carregar logs de ações');
        
        logsAcoesData = await response.json();
        renderizarLogsAcoes();
        
    } catch (error) {
        console.error('Erro ao carregar logs de ações:', error);
        if (window.advancedNotificationSystem) {
            window.advancedNotificationSystem.showError('Erro', 'Erro ao carregar logs de ações');
        }
    }
}

// Renderizar logs de ações
function renderizarLogsAcoes() {
    const container = document.getElementById('logsAcoesContainer');
    if (!container) return;
    
    if (!logsAcoesData || logsAcoesData.length === 0) {
        container.innerHTML = `
            <div class="text-center py-4">
                <i class="fas fa-clipboard-list fa-3x text-muted mb-3"></i>
                <h5 class="text-muted">Nenhum log de ação encontrado</h5>
                <p class="text-muted">Tente ajustar os filtros</p>
            </div>
        `;
        return;
    }
    
    const html = logsAcoesData.map(log => `
        <div class="card mb-2">
            <div class="card-body py-2">
                <div class="row align-items-center">
                    <div class="col-md-3">
                        <strong>${log.usuario.nome}</strong>
                        <br><small class="text-muted">${log.categoria || 'Geral'}</small>
                    </div>
                    <div class="col-md-4">
                        <span class="text-truncate d-block">${log.acao}</span>
                        ${log.detalhes ? `<small class="text-muted">${log.detalhes}</small>` : ''}
                    </div>
                    <div class="col-md-2">
                        <i class="fas fa-clock"></i> ${log.data_acao}
                    </div>
                    <div class="col-md-2">
                        <i class="fas fa-globe"></i> ${log.ip_address || 'N/A'}
                    </div>
                    <div class="col-md-1 text-center">
                        <span class="badge ${log.sucesso ? 'bg-success' : 'bg-danger'}">
                            <i class="fas ${log.sucesso ? 'fa-check' : 'fa-times'}"></i>
                        </span>
                    </div>
                </div>
            </div>
        </div>
    `).join('');
    
    container.innerHTML = html;
}

// Encerrar sessão específica
async function encerrarSessao(sessaoId) {
    if (!confirm('Tem certeza que deseja encerrar esta sessão?')) {
        return;
    }
    
    try {
        const response = await fetch(`/ti/painel/api/auditoria/encerrar-sessao/${sessaoId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) throw new Error('Erro ao encerrar sessão');
        
        if (window.advancedNotificationSystem) {
            window.advancedNotificationSystem.showSuccess('Sucesso', 'Sessão encerrada com sucesso');
        }
        
        // Recarregar dados
        carregarSessoesAtivas();
        
    } catch (error) {
        console.error('Erro ao encerrar sessão:', error);
        if (window.advancedNotificationSystem) {
            window.advancedNotificationSystem.showError('Erro', 'Erro ao encerrar sessão');
        }
    }
}

// Exportar dados de auditoria
function exportarDadosAuditoria(tipo) {
    let dados = [];
    let filename = '';
    
    switch (tipo) {
        case 'acesso':
            dados = logsAcessoData;
            filename = 'logs_acesso';
            break;
        case 'sessoes':
            dados = sessoesAtivasData;
            filename = 'sessoes_ativas';
            break;
        case 'acoes':
            dados = logsAcoesData;
            filename = 'logs_acoes';
            break;
        default:
            return;
    }
    
    if (!dados || dados.length === 0) {
        if (window.advancedNotificationSystem) {
            window.advancedNotificationSystem.showWarning('Aviso', 'Não há dados para exportar');
        }
        return;
    }
    
    // Converter para CSV
    const csv = converterParaCSV(dados);
    
    // Fazer download
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `${filename}_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
    
    if (window.advancedNotificationSystem) {
        window.advancedNotificationSystem.showSuccess('Sucesso', 'Dados exportados com sucesso');
    }
}

// Converter dados para CSV
function converterParaCSV(dados) {
    if (!dados || dados.length === 0) return '';
    
    const headers = Object.keys(dados[0]);
    const csvRows = [];
    
    // Adicionar cabeçalhos
    csvRows.push(headers.join(','));
    
    // Adicionar dados
    for (const row of dados) {
        const values = headers.map(header => {
            const value = row[header];
            if (typeof value === 'object' && value !== null) {
                return JSON.stringify(value).replace(/"/g, '""');
            }
            return `"${String(value || '').replace(/"/g, '""')}"`;
        });
        csvRows.push(values.join(','));
    }
    
    return csvRows.join('\n');
}

// Função para debounce
function debounce(func, wait) {
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

// Exportar funções para uso global
window.inicializarAuditoria = inicializarAuditoria;
window.encerrarSessao = encerrarSessao;
window.exportarDadosAuditoria = exportarDadosAuditoria;
