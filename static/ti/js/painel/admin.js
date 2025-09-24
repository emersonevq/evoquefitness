// ==================== SISTEMA DE ADMINISTRAÇÃO AVANÇADO ====================

// Variáveis globais para o sistema de administração
let currentLogsAcessoPage = 1;
let currentLogsAcoesPage = 1;
let currentAlertasPage = 1;
let currentBackupsPage = 1;

// ==================== LOGS DE ACESSO ====================

async function carregarLogsAcesso(page = 1, filtros = {}) {
    try {
        const params = new URLSearchParams({
            page: page,
            per_page: 20,
            ...filtros
        });

        const response = await fetch(`/ti/painel/api/logs/acesso?${params}`);
        if (!response.ok) {
            throw new Error('Erro ao carregar logs de acesso');
        }

        const data = await response.json();
        renderizarLogsAcesso(data.logs);
        renderizarPaginacaoLogsAcesso(data.pagination);
        
        // Carregar estatísticas
        carregarEstatisticasAcessos();
        
    } catch (error) {
        console.error('Erro ao carregar logs de acesso:', error);
        if (window.advancedNotificationSystem) {
            window.advancedNotificationSystem.showError('Erro', 'Erro ao carregar logs de acesso');
        }
    }
}

function renderizarLogsAcesso(logs) {
    const tbody = document.getElementById('tabelaLogsAcesso');
    if (!tbody) return;

    if (logs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center">Nenhum log de acesso encontrado</td></tr>';
        return;
    }

    tbody.innerHTML = logs.map(log => `
        <tr>
            <td>
                ${log.usuario ? `${log.usuario.nome} (${log.usuario.email})` : 'Usuário removido'}
            </td>
            <td>${log.data_acesso || 'N/A'}</td>
            <td>${log.data_logout || 'Ainda ativo'}</td>
            <td>${log.duracao_sessao ? `${log.duracao_sessao} min` : 'N/A'}</td>
            <td>${log.ip_address || 'N/A'}</td>
            <td>
                <span class="badge ${log.ativo ? 'bg-success' : 'bg-secondary'}">
                    ${log.ativo ? 'Ativo' : 'Finalizado'}
                </span>
            </td>
        </tr>
    `).join('');
}

function renderizarPaginacaoLogsAcesso(pagination) {
    const container = document.getElementById('paginationLogsAcesso');
    if (!container) return;

    let html = '';
    
    // Botão anterior
    if (pagination.has_prev) {
        html += `<button onclick="carregarLogsAcesso(${pagination.page - 1})" class="btn btn-sm btn-outline-primary">Anterior</button>`;
    }
    
    // Números das páginas
    for (let i = Math.max(1, pagination.page - 2); i <= Math.min(pagination.pages, pagination.page + 2); i++) {
        html += `<button onclick="carregarLogsAcesso(${i})" class="btn btn-sm ${i === pagination.page ? 'btn-primary' : 'btn-outline-primary'}">${i}</button>`;
    }
    
    // Botão próximo
    if (pagination.has_next) {
        html += `<button onclick="carregarLogsAcesso(${pagination.page + 1})" class="btn btn-sm btn-outline-primary">Próximo</button>`;
    }
    
    container.innerHTML = html;
}

async function carregarEstatisticasAcessos() {
    try {
        const response = await fetch('/ti/painel/api/logs/acesso/estatisticas');
        if (!response.ok) {
            throw new Error('Erro ao carregar estatísticas');
        }

        const stats = await response.json();
        
        document.getElementById('acessosHoje').textContent = stats.acessos_hoje;
        document.getElementById('acessosSemana').textContent = stats.acessos_semana;
        document.getElementById('usuariosUnicos').textContent = stats.usuarios_semana;
        document.getElementById('tempoMedioSessao').textContent = `${stats.tempo_medio_sessao}min`;
        
    } catch (error) {
        console.error('Erro ao carregar estatísticas de acesso:', error);
    }
}

// ==================== LOGS DE AÇÕES ====================

async function carregarLogsAcoes(page = 1, filtros = {}) {
    try {
        const params = new URLSearchParams({
            page: page,
            per_page: 20,
            ...filtros
        });

        const response = await fetch(`/ti/painel/api/logs/acoes?${params}`);
        if (!response.ok) {
            throw new Error('Erro ao carregar logs de ações');
        }

        const data = await response.json();
        renderizarLogsAcoes(data.logs);
        renderizarPaginacaoLogsAcoes(data.pagination);
        
    } catch (error) {
        console.error('Erro ao carregar logs de ações:', error);
        if (window.advancedNotificationSystem) {
            window.advancedNotificationSystem.showError('Erro', 'Erro ao carregar logs de ações');
        }
    }
}

function renderizarLogsAcoes(logs) {
    const tbody = document.getElementById('tabelaLogsAcoes');
    if (!tbody) return;

    if (logs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center">Nenhum log de ação encontrado</td></tr>';
        return;
    }

    tbody.innerHTML = logs.map(log => `
        <tr>
            <td>
                ${log.usuario ? `${log.usuario.nome} (${log.usuario.email})` : 'Sistema'}
            </td>
            <td><strong>${log.acao}</strong></td>
            <td>${log.detalhes || 'N/A'}</td>
            <td>${log.data_acao || 'N/A'}</td>
            <td>${log.ip_address || 'N/A'}</td>
        </tr>
    `).join('');
}

function renderizarPaginacaoLogsAcoes(pagination) {
    const container = document.getElementById('paginationLogsAcoes');
    if (!container) return;

    let html = '';
    
    if (pagination.has_prev) {
        html += `<button onclick="carregarLogsAcoes(${pagination.page - 1})" class="btn btn-sm btn-outline-primary">Anterior</button>`;
    }
    
    for (let i = Math.max(1, pagination.page - 2); i <= Math.min(pagination.pages, pagination.page + 2); i++) {
        html += `<button onclick="carregarLogsAcoes(${i})" class="btn btn-sm ${i === pagination.page ? 'btn-primary' : 'btn-outline-primary'}">${i}</button>`;
    }
    
    if (pagination.has_next) {
        html += `<button onclick="carregarLogsAcoes(${pagination.page + 1})" class="btn btn-sm btn-outline-primary">Próximo</button>`;
    }
    
    container.innerHTML = html;
}

async function carregarTiposAcoes() {
    try {
        const response = await fetch('/ti/admin/api/logs/acoes/tipos');
        if (!response.ok) {
            throw new Error('Erro ao carregar tipos de ações');
        }

        const tipos = await response.json();
        
        // Mostrar em modal ou seção específica
        let html = '<h5>Tipos de Ações Mais Comuns:</h5><ul>';
        tipos.forEach(tipo => {
            html += `<li><strong>${tipo.acao}</strong>: ${tipo.quantidade} ocorrências</li>`;
        });
        html += '</ul>';
        
        if (window.advancedNotificationSystem) {
            window.advancedNotificationSystem.showInfo('Tipos de Ações', html);
        }
        
    } catch (error) {
        console.error('Erro ao carregar tipos de ações:', error);
    }
}

// ==================== ANÁLISE DE PROBLEMAS FUTUROS ====================

async function carregarAnaliseProblemas() {
    try {
        const response = await fetch('/ti/admin/api/analise/problemas-futuros');
        if (!response.ok) {
            throw new Error('Erro ao carregar análise de problemas');
        }

        const analise = await response.json();
        renderizarAnaliseProblemas(analise);
        
    } catch (error) {
        console.error('Erro ao carregar análise de problemas:', error);
        if (window.advancedNotificationSystem) {
            window.advancedNotificationSystem.showError('Erro', 'Erro ao carregar análise de problemas');
        }
    }
}

function renderizarAnaliseProblemas(analise) {
    // Atualizar cards de tendências
    document.getElementById('tendenciaCrescimento').textContent = `${analise.tendencia_crescimento}%`;
    document.getElementById('taxaViolacaoSLA').textContent = `${analise.taxa_violacao_sla}%`;
    document.getElementById('problemasIdentificados').textContent = analise.alertas_previstos.length;
    document.getElementById('periodoAnalise').textContent = analise.periodo_analise.dias;

    // Renderizar gráfico de problemas frequentes
    if (analise.problemas_frequentes.length > 0) {
        renderizarGraficoProblemasFrequentes(analise.problemas_frequentes);
    }

    // Renderizar gráfico de unidades problemáticas
    if (analise.unidades_problematicas.length > 0) {
        renderizarGraficoUnidadesProblematicas(analise.unidades_problematicas);
    }

    // Renderizar alertas previstos
    renderizarAlertasPrevistos(analise.alertas_previstos);
}

function renderizarGraficoProblemasFrequentes(problemas) {
    const ctx = document.getElementById('chartProblemasFrequentes');
    if (!ctx) return;

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: problemas.map(p => p.problema),
            datasets: [{
                label: 'Quantidade',
                data: problemas.map(p => p.quantidade),
                backgroundColor: 'rgba(255, 98, 0, 0.8)',
                borderColor: 'rgba(255, 98, 0, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

function renderizarGraficoUnidadesProblematicas(unidades) {
    const ctx = document.getElementById('chartUnidadesProblematicas');
    if (!ctx) return;

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: unidades.map(u => u.unidade),
            datasets: [{
                data: unidades.map(u => u.quantidade),
                backgroundColor: [
                    '#FF6200',
                    '#FF914D',
                    '#FFA366',
                    '#FFB580',
                    '#FFC799'
                ]
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

function renderizarAlertasPrevistos(alertas) {
    const container = document.getElementById('alertasPrevistos');
    if (!container) return;

    if (alertas.length === 0) {
        container.innerHTML = '<div class="alert alert-success"><i class="fas fa-check-circle me-2"></i>Nenhum problema futuro identificado no momento.</div>';
        return;
    }

    container.innerHTML = alertas.map(alerta => `
        <div class="alert alert-${getSeveridadeClass(alerta.severidade)} mb-3">
            <div class="d-flex align-items-start">
                <i class="fas fa-${getSeveridadeIcon(alerta.severidade)} me-3 mt-1"></i>
                <div class="flex-grow-1">
                    <h6 class="alert-heading mb-2">${alerta.titulo}</h6>
                    <p class="mb-2">${alerta.descricao}</p>
                    <small><strong>Recomendação:</strong> ${alerta.recomendacao}</small>
                </div>
            </div>
        </div>
    `).join('');
}

function getSeveridadeClass(severidade) {
    const classes = {
        'baixa': 'info',
        'media': 'warning',
        'alta': 'danger',
        'critica': 'danger'
    };
    return classes[severidade] || 'info';
}

function getSeveridadeIcon(severidade) {
    const icons = {
        'baixa': 'info-circle',
        'media': 'exclamation-triangle',
        'alta': 'exclamation-circle',
        'critica': 'times-circle'
    };
    return icons[severidade] || 'info-circle';
}

// ==================== RELATÓRIOS ====================

function inicializarRelatorios() {
    // Configurar datas padrão (último mês)
    const hoje = new Date();
    const umMesAtras = new Date(hoje.getFullYear(), hoje.getMonth() - 1, hoje.getDate());
    
    document.getElementById('relatorioUsuarioDataInicio').value = umMesAtras.toISOString().split('T')[0];
    document.getElementById('relatorioUsuarioDataFim').value = hoje.toISOString().split('T')[0];
    document.getElementById('relatorioChamadoDataInicio').value = umMesAtras.toISOString().split('T')[0];
    document.getElementById('relatorioChamadoDataFim').value = hoje.toISOString().split('T')[0];
}

async function gerarRelatorioUsuarios() {
    try {
        const dataInicio = document.getElementById('relatorioUsuarioDataInicio').value;
        const dataFim = document.getElementById('relatorioUsuarioDataFim').value;
        
        const params = new URLSearchParams({
            formato: 'json',
            data_inicio: dataInicio,
            data_fim: dataFim
        });

        const response = await fetch(`/ti/admin/api/relatorios/usuarios?${params}`);
        if (!response.ok) {
            throw new Error('Erro ao gerar relatório');
        }

        const relatorio = await response.json();
        
        // Mostrar relatório em modal ou nova janela
        mostrarRelatorioUsuarios(relatorio);
        
    } catch (error) {
        console.error('Erro ao gerar relatório de usuários:', error);
        if (window.advancedNotificationSystem) {
            window.advancedNotificationSystem.showError('Erro', 'Erro ao gerar relatório de usuários');
        }
    }
}

function mostrarRelatorioUsuarios(relatorio) {
    let html = `
        <h4>Relatório de Usuários</h4>
        <p><strong>Período:</strong> ${relatorio.resumo.periodo.inicio} até ${relatorio.resumo.periodo.fim}</p>
        <p><strong>Total de usuários:</strong> ${relatorio.resumo.total_usuarios}</p>
        <p><strong>Usuários ativos:</strong> ${relatorio.resumo.usuarios_ativos}</p>
        <p><strong>Usuários bloqueados:</strong> ${relatorio.resumo.usuarios_bloqueados}</p>
        
        <div class="table-responsive mt-3">
            <table class="table table-sm">
                <thead>
                    <tr>
                        <th>Nome</th>
                        <th>Email</th>
                        <th>Nível</th>
                        <th>Último Acesso</th>
                        <th>Total Acessos</th>
                        <th>Chamados</th>
                    </tr>
                </thead>
                <tbody>
                    ${relatorio.relatorio.map(usuario => `
                        <tr>
                            <td>${usuario.nome_completo}</td>
                            <td>${usuario.email}</td>
                            <td>${usuario.nivel_acesso}</td>
                            <td>${usuario.ultimo_acesso}</td>
                            <td>${usuario.total_acessos}</td>
                            <td>${usuario.total_chamados}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;
    
    if (window.advancedNotificationSystem) {
        window.advancedNotificationSystem.showInfo('Relatório de Usuários', html);
    }
}

// ==================== ALERTAS DO SISTEMA ====================

async function carregarAlertasSistema(page = 1, filtros = {}) {
    try {
        const params = new URLSearchParams({
            page: page,
            per_page: 10,
            ...filtros
        });

        const response = await fetch(`/ti/painel/api/alertas?${params}`);
        if (!response.ok) {
            throw new Error('Erro ao carregar alertas');
        }

        const data = await response.json();
        renderizarAlertasSistema(data.alertas);
        renderizarPaginacaoAlertas(data.pagination);
        
    } catch (error) {
        console.error('Erro ao carregar alertas do sistema:', error);
        if (window.advancedNotificationSystem) {
            window.advancedNotificationSystem.showError('Erro', 'Erro ao carregar alertas do sistema');
        }
    }
}

function renderizarAlertasSistema(alertas) {
    const container = document.getElementById('alertasGrid');
    if (!container) return;

    if (alertas.length === 0) {
        container.innerHTML = '<div class="col-12"><div class="alert alert-info">Nenhum alerta encontrado.</div></div>';
        return;
    }

    container.innerHTML = alertas.map(alerta => `
        <div class="card alert-card alert-${getSeveridadeClass(alerta.severidade)}">
            <div class="card-header">
                <div class="d-flex justify-content-between align-items-center">
                    <h6 class="mb-0">
                        <i class="fas fa-${getSeveridadeIcon(alerta.severidade)} me-2"></i>
                        ${alerta.titulo}
                    </h6>
                    <span class="badge bg-${getSeveridadeClass(alerta.severidade)}">${alerta.severidade}</span>
                </div>
            </div>
            <div class="card-body">
                <p class="card-text">${alerta.descricao}</p>
                <small class="text-muted">
                    <strong>Criado em:</strong> ${alerta.data_criacao}<br>
                    <strong>Tipo:</strong> ${alerta.tipo}
                </small>
            </div>
            <div class="card-footer">
                ${alerta.resolvido ? 
                    `<span class="badge bg-success">Resolvido em ${alerta.data_resolucao}</span>` :
                    `<button class="btn btn-sm btn-success" onclick="resolverAlerta(${alerta.id})">
                        <i class="fas fa-check me-1"></i>Resolver
                    </button>`
                }
            </div>
        </div>
    `).join('');
}

function renderizarPaginacaoAlertas(pagination) {
    const container = document.getElementById('paginationAlertas');
    if (!container) return;

    let html = '';
    
    if (pagination.has_prev) {
        html += `<button onclick="carregarAlertasSistema(${pagination.page - 1})" class="btn btn-sm btn-outline-primary">Anterior</button>`;
    }
    
    for (let i = Math.max(1, pagination.page - 2); i <= Math.min(pagination.pages, pagination.page + 2); i++) {
        html += `<button onclick="carregarAlertasSistema(${i})" class="btn btn-sm ${i === pagination.page ? 'btn-primary' : 'btn-outline-primary'}">${i}</button>`;
    }
    
    if (pagination.has_next) {
        html += `<button onclick="carregarAlertasSistema(${pagination.page + 1})" class="btn btn-sm btn-outline-primary">Próximo</button>`;
    }
    
    container.innerHTML = html;
}

async function resolverAlerta(alertaId) {
    try {
        const response = await fetch(`/ti/admin/api/alertas/${alertaId}/resolver`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error('Erro ao resolver alerta');
        }

        const data = await response.json();
        
        if (window.advancedNotificationSystem) {
            window.advancedNotificationSystem.showSuccess('Alerta Resolvido', data.message);
        }
        
        // Recarregar alertas
        carregarAlertasSistema();
        
    } catch (error) {
        console.error('Erro ao resolver alerta:', error);
        if (window.advancedNotificationSystem) {
            window.advancedNotificationSystem.showError('Erro', 'Erro ao resolver alerta');
        }
    }
}

// ==================== BACKUP & MANUTENÇÃO ====================

async function carregarBackupManutencao() {
    carregarHistoricoBackups();
}

async function carregarHistoricoBackups(page = 1) {
    try {
        const params = new URLSearchParams({
            page: page,
            per_page: 10
        });

        const response = await fetch(`/ti/admin/api/backup/historico?${params}`);
        if (!response.ok) {
            throw new Error('Erro ao carregar histórico de backups');
        }

        const data = await response.json();
        renderizarHistoricoBackups(data.backups);
        renderizarPaginacaoBackups(data.pagination);
        
    } catch (error) {
        console.error('Erro ao carregar histórico de backups:', error);
        if (window.advancedNotificationSystem) {
            window.advancedNotificationSystem.showError('Erro', 'Erro ao carregar histórico de backups');
        }
    }
}

function renderizarHistoricoBackups(backups) {
    const tbody = document.getElementById('tabelaHistoricoBackups');
    if (!tbody) return;

    if (backups.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center">Nenhum backup encontrado</td></tr>';
        return;
    }

    tbody.innerHTML = backups.map(backup => `
        <tr>
            <td>${backup.nome_arquivo}</td>
            <td><span class="badge bg-info">${backup.tipo}</span></td>
            <td>${backup.tamanho_mb} MB</td>
            <td>
                <span class="badge bg-${getStatusBackupClass(backup.status)}">
                    ${backup.status}
                </span>
            </td>
            <td>${backup.data_backup}</td>
            <td>${backup.usuario ? backup.usuario.nome : 'Sistema'}</td>
            <td>${backup.observacoes || 'N/A'}</td>
        </tr>
    `).join('');
}

function getStatusBackupClass(status) {
    const classes = {
        'concluido': 'success',
        'em_progresso': 'warning',
        'erro': 'danger'
    };
    return classes[status] || 'secondary';
}

function renderizarPaginacaoBackups(pagination) {
    const container = document.getElementById('paginationBackups');
    if (!container) return;

    let html = '';
    
    if (pagination.has_prev) {
        html += `<button onclick="carregarHistoricoBackups(${pagination.page - 1})" class="btn btn-sm btn-outline-primary">Anterior</button>`;
    }
    
    for (let i = Math.max(1, pagination.page - 2); i <= Math.min(pagination.pages, pagination.page + 2); i++) {
        html += `<button onclick="carregarHistoricoBackups(${i})" class="btn btn-sm ${i === pagination.page ? 'btn-primary' : 'btn-outline-primary'}">${i}</button>`;
    }
    
    if (pagination.has_next) {
        html += `<button onclick="carregarHistoricoBackups(${pagination.page + 1})" class="btn btn-sm btn-outline-primary">Próximo</button>`;
    }
    
    container.innerHTML = html;
}

async function criarBackup() {
    try {
        const tipo = document.getElementById('tipoBackup').value;
        const observacoes = document.getElementById('observacoesBackup').value;

        const response = await fetch('/ti/admin/api/backup/criar', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                tipo: tipo,
                observacoes: observacoes
            })
        });

        if (!response.ok) {
            throw new Error('Erro ao criar backup');
        }

        const data = await response.json();
        
        if (window.advancedNotificationSystem) {
            window.advancedNotificationSystem.showSuccess('Backup Criado', data.message);
        }
        
        // Limpar formulário
        document.getElementById('observacoesBackup').value = '';
        
        // Recarregar histórico
        carregarHistoricoBackups();
        
    } catch (error) {
        console.error('Erro ao criar backup:', error);
        if (window.advancedNotificationSystem) {
            window.advancedNotificationSystem.showError('Erro', 'Erro ao criar backup');
        }
    }
}

// ==================== CONFIGURAÇÕES AVANÇADAS ====================

async function carregarConfiguracoesAvancadas() {
    try {
        const response = await fetch('/ti/painel/api/configuracoes-avancadas');
        if (!response.ok) {
            throw new Error('Erro ao carregar configurações avançadas');
        }

        const configuracoes = await response.json();
        preencherConfiguracoesAvancadas(configuracoes);
        
    } catch (error) {
        console.error('Erro ao carregar configurações avançadas:', error);
        if (window.advancedNotificationSystem) {
            window.advancedNotificationSystem.showError('Erro', 'Erro ao carregar configurações avançadas');
        }
    }
}

function preencherConfiguracoesAvancadas(configuracoes) {
    // Sistema
    if (configuracoes['sistema.manutencao_modo']) {
        document.getElementById('configManutencaoModo').checked = configuracoes['sistema.manutencao_modo'].valor === 'true';
    }
    if (configuracoes['sistema.debug_mode']) {
        document.getElementById('configDebugMode').checked = configuracoes['sistema.debug_mode'].valor === 'true';
    }
    if (configuracoes['sistema.max_upload_size']) {
        document.getElementById('configMaxUploadSize').value = configuracoes['sistema.max_upload_size'].valor;
    }
    if (configuracoes['sistema.session_timeout']) {
        document.getElementById('configSessionTimeout').value = configuracoes['sistema.session_timeout'].valor;
    }

    // Backup
    if (configuracoes['backup.automatico_habilitado']) {
        document.getElementById('configBackupAutomatico').checke = configuracoes['backup.automatico_habilitado'].valor === 'true';
    }
    if (configuracoes['backup.frequencia_horas']) {
        document.getElementById('configFrequenciaBackup').value = configuracoes['backup.frequencia_horas'].valor;
    }

    // Alertas
    if (configuracoes['alertas.email_habilitado']) {
        document.getElementById('configAlertasEmail').checked = configuracoes['alertas.email_habilitado'].valor === 'true';
    }

    // Performance
    if (configuracoes['performance.cache_habilitado']) {
        document.getElementById('configCacheHabilitado').checked = configuracoes['performance.cache_habilitado'].valor === 'true';
    }
}

async function salvarConfiguracoesAvancadas() {
    try {
        const configuracoes = {
            'sistema.manutencao_modo': {
                valor: document.getElementById('configManutencaoModo').checked,
                descricao: 'Ativa o modo de manutenção do sistema',
                tipo: 'boolean'
            },
            'sistema.debug_mode': {
                valor: document.getElementById('configDebugMode').checked,
                descricao: 'Ativa o modo de debug para desenvolvimento',
                tipo: 'boolean'
            },
            'sistema.max_upload_size': {
                valor: parseInt(document.getElementById('configMaxUploadSize').value),
                descricao: 'Tamanho máximo de upload em MB',
                tipo: 'number'
            },
            'sistema.session_timeout': {
                valor: parseInt(document.getElementById('configSessionTimeout').value),
                descricao: 'Timeout de sessão em minutos',
                tipo: 'number'
            },
            'backup.automatico_habilitado': {
                valor: document.getElementById('configBackupAutomatico').checked,
                descricao: 'Habilita backup automático',
                tipo: 'boolean'
            },
            'backup.frequencia_horas': {
                valor: parseInt(document.getElementById('configFrequenciaBackup').value),
                descricao: 'Frequência de backup automático em horas',
                tipo: 'number'
            },
            'alertas.email_habilitado': {
                valor: document.getElementById('configAlertasEmail').checked,
                descricao: 'Habilita envio de alertas por email',
                tipo: 'boolean'
            },
            'performance.cache_habilitado': {
                valor: document.getElementById('configCacheHabilitado').checked,
                descricao: 'Habilita cache do sistema',
                tipo: 'boolean'
            }
        };

        const response = await fetch('/ti/painel/api/configuracoes-avancadas', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(configuracoes)
        });

        if (!response.ok) {
            throw new Error('Erro ao salvar configurações avançadas');
        }

        const data = await response.json();
        
        if (window.advancedNotificationSystem) {
            window.advancedNotificationSystem.showSuccess('Configurações Salvas', data.message);
        }
        
    } catch (error) {
        console.error('Erro ao salvar configurações avançadas:', error);
        if (window.advancedNotificationSystem) {
            window.advancedNotificationSystem.showError('Erro', 'Erro ao salvar configurações avançadas');
        }
    }
}

// ==================== DASHBOARD AVANÇADO ====================

async function carregarDashboardAvancado() {
    try {
        const response = await fetch('/ti/api/dashboard/metricas-avancadas');
        if (!response.ok) {
            throw new Error('Erro ao carregar métricas avançadas');
        }

        const metricas = await response.json();
        renderizarDashboardAvancado(metricas);
        
    } catch (error) {
        console.error('Erro ao carregar dashboard avançado:', error);
        if (window.advancedNotificationSystem) {
            window.advancedNotificationSystem.showError('Erro', 'Erro ao carregar dashboard avançado');
        }
    }
}

function renderizarDashboardAvancado(metricas) {
    // Atualizar cards de métricas
    document.getElementById('dashTotalUsuarios').textContent = metricas.usuarios.total;
    document.getElementById('dashTaxaAtividade').textContent = `${metricas.usuarios.taxa_atividade}% ativos este mês`;
    document.getElementById('dashTaxaResolucao').textContent = `${metricas.chamados.taxa_resolucao}%`;
    document.getElementById('dashTempoMedioResolucao').textContent = `${metricas.chamados.tempo_medio_resolucao}h`;
    document.getElementById('dashAlertasAtivos').textContent = metricas.alertas_ativos;

    // Renderizar gráfico de distribuição por prioridade
    if (metricas.distribuicao_prioridade.length > 0) {
        renderizarGraficoDistribuicaoPrioridade(metricas.distribuicao_prioridade);
    }

    // Renderizar gráfico de status dos usuários
    renderizarGraficoStatusUsuarios(metricas.usuarios);
}

function renderizarGraficoDistribuicaoPrioridade(distribuicao) {
    const ctx = document.getElementById('chartDistribuicaoPrioridade');
    if (!ctx) return;

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: distribuicao.map(d => d.prioridade),
            datasets: [{
                label: 'Quantidade de Chamados',
                data: distribuicao.map(d => d.quantidade),
                borderColor: '#FF6200',
                backgroundColor: 'rgba(255, 98, 0, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

function renderizarGraficoStatusUsuarios(usuarios) {
    const ctx = document.getElementById('chartStatusUsuarios');
    if (!ctx) return;

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Ativos', 'Bloqueados'],
            datasets: [{
                data: [usuarios.ativos_mes, usuarios.bloqueados],
                backgroundColor: ['#28a745', '#dc3545']
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

// ==================== EVENT LISTENERS ====================

document.addEventListener('DOMContentLoaded', function() {
    // Logs de Acesso
    document.getElementById('btnAtualizarLogsAcesso')?.addEventListener('click', () => carregarLogsAcesso());
    document.getElementById('btnFiltrarAcessos')?.addEventListener('click', () => {
        const filtros = {
            usuario_id: document.getElementById('filtroUsuarioAcesso').value,
            data_inicio: document.getElementById('filtroDataInicioAcesso').value,
            data_fim: document.getElementById('filtroDataFimAcesso').value
        };
        carregarLogsAcesso(1, filtros);
    });

    // Logs de Ações
    document.getElementById('btnAtualizarLogsAcoes')?.addEventListener('click', () => carregarLogsAcoes());
    document.getElementById('btnFiltrarAcoes')?.addEventListener('click', () => {
        const filtros = {
            usuario_id: document.getElementById('filtroUsuarioAcao').value,
            acao: document.getElementById('filtroAcao').value,
            data_inicio: document.getElementById('filtroDataInicioAcao').value,
            data_fim: document.getElementById('filtroDataFimAcao').value
        };
        carregarLogsAcoes(1, filtros);
    });
    document.getElementById('btnTiposAcoes')?.addEventListener('click', carregarTiposAcoes);

    // Análise de Problemas
    document.getElementById('btnAtualizarAnalise')?.addEventListener('click', carregarAnaliseProblemas);

    // Relatórios
    document.getElementById('btnGerarRelatorioUsuarios')?.addEventListener('click', gerarRelatorioUsuarios);

    // Alertas do Sistema
    document.getElementById('btnFiltrarAlertas')?.addEventListener('click', () => {
        const filtros = {
            tipo: document.getElementById('filtroTipoAlerta').value,
            severidade: document.getElementById('filtroSeveridadeAlerta').value,
            resolvido: document.getElementById('filtroStatusAlerta').value
        };
        carregarAlertasSistema(1, filtros);
    });

    // Backup & Manutenção
    document.getElementById('btnCriarBackup')?.addEventListener('click', criarBackup);

    // Configurações Avançadas
    document.getElementById('btnSalvarConfigAvancadas')?.addEventListener('click', salvarConfiguracoesAvancadas);

    // Dashboard Avançado
    document.getElementById('btnAtualizarDashboard')?.addEventListener('click', carregarDashboardAvancado);
});

// Exportar funções para uso global
window.carregarLogsAcesso = carregarLogsAcesso;
window.carregarLogsAcoes = carregarLogsAcoes;
window.carregarAnaliseProblemas = carregarAnaliseProblemas;
window.inicializarRelatorios = inicializarRelatorios;
window.carregarAlertasSistema = carregarAlertasSistema;
window.carregarBackupManutencao = carregarBackupManutencao;
window.carregarConfiguracoesAvancadas = carregarConfiguracoesAvancadas;
window.carregarDashboardAvancado = carregarDashboardAvancado;
window.resolverAlerta = resolverAlerta;
