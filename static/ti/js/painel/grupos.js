// ==================== GERENCIAMENTO DE GRUPOS ====================

let gruposData = [];
let emailsHistoricoData = [];

// Inicialização da seção de grupos
function inicializarGrupos() {
    console.log('Inicializando seção de grupos...');

    // Carregar dados iniciais
    carregarGrupos();
    carregarEmailsHistorico();

    // Configurar event listeners
    configurarEventListenersGrupos();
}

// Função de debug para verificar dados de grupos
async function debugVerificarGrupos() {
    console.log('=== DEBUG: Verificando dados de grupos ===');

    try {
        console.log('Buscando grupos...');
        const responseGrupos = await fetch('/ti/painel/api/grupos');
        console.log('Status da resposta grupos:', responseGrupos.status);

        if (responseGrupos.ok) {
            const grupos = await responseGrupos.json();
            console.log('Total de grupos encontrados:', grupos.length);
            console.log('Grupos encontrados:', grupos);

            if (grupos.length === 0) {
                console.log('NENHUM GRUPO ENCONTRADO! Verificar se existem grupos criados no banco');
            }
        } else {
            console.error('Erro ao buscar grupos:', responseGrupos.status, responseGrupos.statusText);
        }

    } catch (error) {
        console.error('Erro no debug de grupos:', error);
    }

    console.log('=== FIM DEBUG GRUPOS ===');
}

// Adicionar à janela global para fácil acesso
window.debugVerificarGrupos = debugVerificarGrupos;

// Auto-inicializar quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM carregado - grupos.js inicializado');

    // Executar debug automaticamente
    setTimeout(debugVerificarGrupos, 2000);
});

function configurarEventListenersGrupos() {
    // Modal de criação de grupo
    const btnCriarGrupo = document.getElementById('btnCriarGrupo');
    const modalCriarGrupo = document.getElementById('modalCriarGrupo');
    const btnSalvarGrupo = document.getElementById('btnSalvarGrupo');
    const btnCancelarGrupo = document.getElementById('btnCancelarGrupo');
    const modalCriarGrupoClose = document.getElementById('modalCriarGrupoClose');
    
    if (btnCriarGrupo) {
        btnCriarGrupo.addEventListener('click', abrirModalCriarGrupo);
    }
    
    if (btnSalvarGrupo) {
        btnSalvarGrupo.addEventListener('click', salvarGrupo);
    }
    
    if (btnCancelarGrupo) {
        btnCancelarGrupo.addEventListener('click', fecharModalCriarGrupo);
    }
    
    if (modalCriarGrupoClose) {
        modalCriarGrupoClose.addEventListener('click', fecharModalCriarGrupo);
    }
    
    // Modal de envio de email
    const modalEnviarEmail = document.getElementById('modalEnviarEmail');
    const btnCancelarEmail = document.getElementById('btnCancelarEmail');
    const btnEnviarEmail = document.getElementById('btnEnviarEmail');
    const modalEnviarEmailClose = document.getElementById('modalEnviarEmailClose');
    
    if (btnCancelarEmail) {
        btnCancelarEmail.addEventListener('click', fecharModalEnviarEmail);
    }
    
    if (btnEnviarEmail) {
        btnEnviarEmail.addEventListener('click', enviarEmailGrupo);
    }
    
    if (modalEnviarEmailClose) {
        modalEnviarEmailClose.addEventListener('click', fecharModalEnviarEmail);
    }
    
    // Fechar modals clicando fora
    if (modalCriarGrupo) {
        modalCriarGrupo.addEventListener('click', (e) => {
            if (e.target === modalCriarGrupo) {
                fecharModalCriarGrupo();
            }
        });
    }
    
    if (modalEnviarEmail) {
        modalEnviarEmail.addEventListener('click', (e) => {
            if (e.target === modalEnviarEmail) {
                fecharModalEnviarEmail();
            }
        });
    }
    
    // Botão atualizar
    const btnAtualizarGrupos = document.getElementById('btnAtualizarGrupos');
    if (btnAtualizarGrupos) {
        btnAtualizarGrupos.addEventListener('click', () => {
            carregarGrupos();
            carregarEmailsHistorico();
            
            if (window.advancedNotificationSystem) {
                window.advancedNotificationSystem.showInfo('Atualizado', 'Dados de grupos atualizados');
            }
        });
    }
}

// Carregar grupos
async function carregarGrupos() {
    try {
        console.log('Carregando grupos...');
        const response = await fetch('/ti/painel/api/grupos');
        if (!response.ok) throw new Error('Erro ao carregar grupos');

        gruposData = await response.json();
        console.log('Grupos carregados:', gruposData);
        renderizarGrupos();

    } catch (error) {
        console.error('Erro ao carregar grupos:', error);
        if (window.advancedNotificationSystem) {
            window.advancedNotificationSystem.showError('Erro', 'Erro ao carregar grupos');
        }
    }
}

// Renderizar grupos
function renderizarGrupos() {
    const container = document.getElementById('gruposGrid');
    if (!container) return;
    
    if (!gruposData || gruposData.length === 0) {
        console.log('Nenhum grupo encontrado para renderização');
        container.innerHTML = `
            <div class="text-center py-4">
                <i class="fas fa-users fa-3x text-muted mb-3"></i>
                <h5 class="text-muted">Nenhum grupo de usuários encontrado</h5>
                <p class="text-muted">
                    Clique em "Criar Grupo" para criar o primeiro grupo de usuários
                </p>
                <button class="btn btn-primary" onclick="window.debugVerificarGrupos()">
                    <i class="fas fa-bug me-1"></i>Debug: Verificar Grupos
                </button>
            </div>
        `;
        return;
    }
    
    const html = gruposData.map(grupo => `
        <div class="card mb-3">
            <div class="card-body">
                <div class="row align-items-center">
                    <div class="col-md-6">
                        <h5 class="card-title mb-1">${grupo.nome}</h5>
                        <p class="card-text text-muted mb-2">${grupo.descricao || 'Sem descrição'}</p>
                        <small class="text-muted">
                            <i class="fas fa-users"></i> ${grupo.membros_count} membros •
                            <i class="fas fa-building"></i> ${grupo.unidades_count} unidades •
                            <i class="fas fa-calendar"></i> ${grupo.data_criacao}
                        </small>
                    </div>
                    <div class="col-md-3">
                        <span class="badge ${grupo.ativo ? 'bg-success' : 'bg-secondary'} mb-2">
                            ${grupo.ativo ? 'Ativo' : 'Inativo'}
                        </span>
                        <br><small class="text-muted">Por: ${grupo.criador.nome}</small>
                    </div>
                    <div class="col-md-3 text-end">
                        <div class="btn-group">
                            <button class="btn btn-sm btn-primary" onclick="editarGrupo(${grupo.id})" title="Editar">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button class="btn btn-sm btn-info" onclick="verDetalhesGrupo(${grupo.id})" title="Ver detalhes">
                                <i class="fas fa-eye"></i>
                            </button>
                            <button class="btn btn-sm btn-success" onclick="abrirModalEnviarEmail(${grupo.id})" title="Enviar email">
                                <i class="fas fa-envelope"></i>
                            </button>
                            <button class="btn btn-sm btn-danger" onclick="excluirGrupo(${grupo.id})" title="Excluir">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `).join('');
    
    container.innerHTML = html;
}

// Abrir modal de criar grupo
async function abrirModalCriarGrupo() {
    // Carregar usuários e unidades para seleção
    await carregarUsuariosParaGrupo();
    await carregarUnidadesParaGrupo();
    
    const modal = document.getElementById('modalCriarGrupo');
    if (modal) {
        modal.classList.add('active');
        
        // Limpar formulário
        document.getElementById('formCriarGrupo').reset();
        document.getElementById('grupoId').value = '';
        document.getElementById('modalCriarGrupoTitle').textContent = 'Criar Grupo';
    }
}

// Fechar modal de criar grupo
function fecharModalCriarGrupo() {
    const modal = document.getElementById('modalCriarGrupo');
    if (modal) {
        modal.classList.remove('active');
    }
}

// Salvar grupo
async function salvarGrupo() {
    try {
        const grupoId = document.getElementById('grupoId').value;
        const isEdit = grupoId !== '';
        
        const dados = {
            nome: document.getElementById('nomeGrupo').value.trim(),
            descricao: document.getElementById('descricaoGrupo').value.trim(),
            membros: Array.from(document.getElementById('membrosGrupo').selectedOptions).map(opt => parseInt(opt.value)),
            unidades: Array.from(document.getElementById('unidadesGrupo').selectedOptions).map(opt => parseInt(opt.value))
        };
        
        // Validação
        if (!dados.nome) {
            throw new Error('Nome do grupo é obrigatório');
        }
        
        const url = isEdit ? `/ti/painel/api/grupos/${grupoId}` : '/ti/painel/api/grupos';
        const method = isEdit ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(dados)
        });
        
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.error || 'Erro ao salvar grupo');
        }
        
        if (window.advancedNotificationSystem) {
            window.advancedNotificationSystem.showSuccess(
                'Sucesso', 
                isEdit ? 'Grupo atualizado com sucesso' : 'Grupo criado com sucesso'
            );
        }
        
        fecharModalCriarGrupo();
        carregarGrupos();
        
    } catch (error) {
        console.error('Erro ao salvar grupo:', error);
        if (window.advancedNotificationSystem) {
            window.advancedNotificationSystem.showError('Erro', error.message);
        }
    }
}

// Editar grupo
async function editarGrupo(grupoId) {
    try {
        const response = await fetch(`/ti/painel/api/grupos/${grupoId}`);
        if (!response.ok) throw new Error('Erro ao carregar grupo');
        
        const grupo = await response.json();
        
        // Carregar usuários e unidades
        await carregarUsuariosParaGrupo();
        await carregarUnidadesParaGrupo();
        
        // Preencher formulário
        document.getElementById('grupoId').value = grupo.id;
        document.getElementById('nomeGrupo').value = grupo.nome;
        document.getElementById('descricaoGrupo').value = grupo.descricao || '';
        
        // Selecionar membros
        const selectMembros = document.getElementById('membrosGrupo');
        Array.from(selectMembros.options).forEach(option => {
            option.selected = grupo.membros.some(m => m.usuario_id === parseInt(option.value));
        });
        
        // Selecionar unidades
        const selectUnidades = document.getElementById('unidadesGrupo');
        Array.from(selectUnidades.options).forEach(option => {
            option.selected = grupo.unidades.some(u => u.unidade_id === parseInt(option.value));
        });
        
        // Abrir modal
        document.getElementById('modalCriarGrupoTitle').textContent = 'Editar Grupo';
        document.getElementById('modalCriarGrupo').classList.add('active');
        
    } catch (error) {
        console.error('Erro ao editar grupo:', error);
        if (window.advancedNotificationSystem) {
            window.advancedNotificationSystem.showError('Erro', 'Erro ao carregar dados do grupo');
        }
    }
}

// Ver detalhes do grupo
async function verDetalhesGrupo(grupoId) {
    try {
        const response = await fetch(`/ti/painel/api/grupos/${grupoId}`);
        if (!response.ok) throw new Error('Erro ao carregar grupo');
        
        const grupo = await response.json();
        
        const detalhes = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Detalhes do Grupo: ${grupo.nome}</h3>
                    <button class="modal-close" onclick="fecharDetalhesGrupo()">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="row">
                        <div class="col-md-6">
                            <h5>Informações Gerais</h5>
                            <p><strong>Nome:</strong> ${grupo.nome}</p>
                            <p><strong>Descrição:</strong> ${grupo.descricao || 'Sem descrição'}</p>
                            <p><strong>Status:</strong> ${grupo.ativo ? 'Ativo' : 'Inativo'}</p>
                            <p><strong>Criado por:</strong> ${grupo.criador.nome}</p>
                            <p><strong>Data de criação:</strong> ${grupo.data_criacao}</p>
                        </div>
                        <div class="col-md-6">
                            <h5>Membros (${grupo.membros.length})</h5>
                            <ul class="list-unstyled">
                                ${grupo.membros.map(m => `
                                    <li><i class="fas fa-user"></i> ${m.nome} (${m.email})</li>
                                `).join('')}
                            </ul>
                        </div>
                    </div>
                    <div class="row mt-3">
                        <div class="col-12">
                            <h5>Unidades (${grupo.unidades.length})</h5>
                            <div class="row">
                                ${grupo.unidades.map(u => `
                                    <div class="col-md-6">
                                        <span class="badge bg-primary">${u.nome}</span>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Criar modal dinamicamente
        const modalDetalhes = document.createElement('div');
        modalDetalhes.id = 'modalDetalhesGrupo';
        modalDetalhes.className = 'modal active';
        modalDetalhes.innerHTML = detalhes;
        
        document.body.appendChild(modalDetalhes);
        
    } catch (error) {
        console.error('Erro ao ver detalhes:', error);
        if (window.advancedNotificationSystem) {
            window.advancedNotificationSystem.showError('Erro', 'Erro ao carregar detalhes do grupo');
        }
    }
}

// Fechar modal de detalhes
function fecharDetalhesGrupo() {
    const modal = document.getElementById('modalDetalhesGrupo');
    if (modal) {
        modal.remove();
    }
}

// Excluir grupo
async function excluirGrupo(grupoId) {
    const grupo = gruposData.find(g => g.id === grupoId);
    if (!grupo) return;
    
    if (!confirm(`Tem certeza que deseja excluir o grupo "${grupo.nome}"?`)) {
        return;
    }
    
    try {
        const response = await fetch(`/ti/painel/api/grupos/${grupoId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) throw new Error('Erro ao excluir grupo');
        
        if (window.advancedNotificationSystem) {
            window.advancedNotificationSystem.showSuccess('Sucesso', 'Grupo excluído com sucesso');
        }
        
        carregarGrupos();
        
    } catch (error) {
        console.error('Erro ao excluir grupo:', error);
        if (window.advancedNotificationSystem) {
            window.advancedNotificationSystem.showError('Erro', 'Erro ao excluir grupo');
        }
    }
}

// Abrir modal de enviar email
async function abrirModalEnviarEmail(grupoId) {
    const grupo = gruposData.find(g => g.id === grupoId);
    if (!grupo) return;
    
    document.getElementById('emailGrupoId').value = grupoId;
    document.getElementById('emailGrupoNome').textContent = grupo.nome;
    document.getElementById('emailMembrosCount').textContent = grupo.membros_count;
    
    // Limpar formulário
    document.getElementById('formEnviarEmail').reset();
    document.getElementById('emailGrupoId').value = grupoId;
    
    const modal = document.getElementById('modalEnviarEmail');
    if (modal) {
        modal.classList.add('active');
    }
}

// Fechar modal de enviar email
function fecharModalEnviarEmail() {
    const modal = document.getElementById('modalEnviarEmail');
    if (modal) {
        modal.classList.remove('active');
    }
}

// Enviar email para grupo
async function enviarEmailGrupo() {
    try {
        const grupoId = document.getElementById('emailGrupoId').value;
        const assunto = document.getElementById('emailAssunto').value.trim();
        const mensagem = document.getElementById('emailMensagem').value.trim();
        const tipo = document.getElementById('emailTipo').value;
        
        // Validação
        if (!assunto || !mensagem) {
            throw new Error('Assunto e mensagem são obrigatórios');
        }
        
        const dados = {
            assunto: assunto,
            mensagem: mensagem,
            tipo: tipo
        };
        
        const response = await fetch(`/ti/painel/api/grupos/${grupoId}/enviar-email`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(dados)
        });
        
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.error || 'Erro ao enviar email');
        }
        
        if (window.advancedNotificationSystem) {
            window.advancedNotificationSystem.showSuccess(
                'Email Enviado', 
                `${result.sucessos} emails enviados com sucesso${result.falhas > 0 ? `, ${result.falhas} falharam` : ''}`
            );
        }
        
        fecharModalEnviarEmail();
        carregarEmailsHistorico();
        
    } catch (error) {
        console.error('Erro ao enviar email:', error);
        if (window.advancedNotificationSystem) {
            window.advancedNotificationSystem.showError('Erro', error.message);
        }
    }
}

// Carregar usuários para seleção no grupo
async function carregarUsuariosParaGrupo() {
    try {
        const response = await fetch('/ti/painel/api/usuarios');
        if (!response.ok) throw new Error('Erro ao carregar usuários');
        
        const usuarios = await response.json();
        const select = document.getElementById('membrosGrupo');
        
        if (select) {
            select.innerHTML = usuarios.map(u => `
                <option value="${u.id}">${u.nome} ${u.sobrenome} (${u.email})</option>
            `).join('');
        }
        
    } catch (error) {
        console.error('Erro ao carregar usuários:', error);
    }
}

// Carregar unidades para seleção no grupo
async function carregarUnidadesParaGrupo() {
    try {
        const response = await fetch('/ti/painel/api/unidades');
        if (!response.ok) throw new Error('Erro ao carregar unidades');
        
        const unidades = await response.json();
        const select = document.getElementById('unidadesGrupo');
        
        if (select) {
            select.innerHTML = unidades.map(u => `
                <option value="${u.id}">${u.nome}</option>
            `).join('');
        }
        
    } catch (error) {
        console.error('Erro ao carregar unidades:', error);
    }
}

// Carregar histórico de emails
async function carregarEmailsHistorico() {
    try {
        const response = await fetch('/ti/painel/api/grupos/emails-massa');
        if (!response.ok) throw new Error('Erro ao carregar histórico de emails');
        
        emailsHistoricoData = await response.json();
        renderizarEmailsHistorico();
        
    } catch (error) {
        console.error('Erro ao carregar histórico de emails:', error);
        if (window.advancedNotificationSystem) {
            window.advancedNotificationSystem.showError('Erro', 'Erro ao carregar histórico de emails');
        }
    }
}

// Renderizar histórico de emails
function renderizarEmailsHistorico() {
    const container = document.getElementById('emailsHistoricoContainer');
    if (!container) return;
    
    if (!emailsHistoricoData || emailsHistoricoData.length === 0) {
        container.innerHTML = `
            <div class="text-center py-4">
                <i class="fas fa-envelope fa-3x text-muted mb-3"></i>
                <h5 class="text-muted">Nenhum email enviado</h5>
                <p class="text-muted">Histórico de emails em massa aparecerá aqui</p>
            </div>
        `;
        return;
    }
    
    const html = emailsHistoricoData.map(email => `
        <div class="card mb-2">
            <div class="card-body py-2">
                <div class="row align-items-center">
                    <div class="col-md-4">
                        <strong>${email.assunto}</strong>
                        <br><small class="text-muted">${email.grupo?.nome || 'Grupo removido'}</small>
                    </div>
                    <div class="col-md-2">
                        <span class="badge ${email.status === 'concluido' ? 'bg-success' : email.status === 'erro' ? 'bg-danger' : 'bg-warning'}">
                            ${email.status}
                        </span>
                        <br><small class="text-muted">${email.tipo}</small>
                    </div>
                    <div class="col-md-2">
                        <i class="fas fa-users"></i> ${email.destinatarios_count} destinatários
                    </div>
                    <div class="col-md-2">
                        <i class="fas fa-check text-success"></i> ${email.enviados_count}
                        ${email.falhas_count > 0 ? `<i class="fas fa-times text-danger ms-2"></i> ${email.falhas_count}` : ''}
                    </div>
                    <div class="col-md-2">
                        <small class="text-muted">
                            ${email.data_envio || email.data_criacao}
                            <br>Por: ${email.criador.nome}
                        </small>
                    </div>
                </div>
            </div>
        </div>
    `).join('');
    
    container.innerHTML = html;
}

// Exportar funções para uso global
window.carregarGrupos = carregarGrupos;
window.inicializarGrupos = inicializarGrupos;
window.editarGrupo = editarGrupo;
window.verDetalhesGrupo = verDetalhesGrupo;
window.fecharDetalhesGrupo = fecharDetalhesGrupo;
window.excluirGrupo = excluirGrupo;
window.abrirModalEnviarEmail = abrirModalEnviarEmail;
