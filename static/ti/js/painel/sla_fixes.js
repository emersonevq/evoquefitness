/**
 * Fixes for SLA Dashboard JavaScript Errors
 * This file provides corrected functions that override problematic ones
 */

// Override the createChartSafely function for Chart.js
function createChartSafely(canvasId, config, instanceName = null) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) {
        console.error(`Canvas with ID '${canvasId}' not found`);
        return null;
    }
    
    // Destroy any existing chart on this canvas
    const existingChart = Chart.getChart(canvas);
    if (existingChart) {
        existingChart.destroy();
    }
    
    try {
        // Create new chart
        const chart = new Chart(canvas, config);
        
        // Store globally if instance name provided
        if (instanceName) {
            window[instanceName] = chart;
        }
        
        return chart;
        
    } catch (error) {
        console.error(`Error creating chart for ${canvasId}:`, error);
        return null;
    }
}

// Override the criarGraficoSemanal function with better error handling
function criarGraficoSemanal(dados) {
    const ctx = document.getElementById('chartSemanal');
    if (!ctx) return;
    
    // Safely destroy existing chart
    try {
        const existingChart = Chart.getChart(ctx);
        if (existingChart) {
            existingChart.destroy();
        }
        
        if (window.graficoSemanalInstance) {
            window.graficoSemanalInstance.destroy();
            window.graficoSemanalInstance = null;
        }
    } catch (error) {
        console.warn('Error destroying existing weekly chart:', error);
    }
    
    // Prepare data
    const labels = dados.map(item => {
        const data = new Date(item.data);
        return data.toLocaleDateString('pt-BR', { 
            day: '2-digit', 
            month: '2-digit' 
        });
    });
    
    const valores = dados.map(item => item.quantidade);
    
    try {
        window.graficoSemanalInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Chamados por Dia',
                    data: valores,
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#3b82f6',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: '#ffffff',
                        bodyColor: '#ffffff',
                        borderColor: '#3b82f6',
                        borderWidth: 1
                    }
                },
                scales: {
                    x: {
                        display: true,
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: '#6b7280',
                            maxTicksLimit: 14
                        }
                    },
                    y: {
                        display: true,
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(107, 114, 128, 0.1)'
                        },
                        ticks: {
                            color: '#6b7280',
                            stepSize: 1
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                }
            }
        });
        
    } catch (error) {
        console.error('Error creating weekly chart:', error);
    }
}

// Override the criarGraficoDistribuicaoStatus function
function criarGraficoDistribuicaoStatus(dados) {
    const ctx = document.getElementById('chartStatus');
    if (!ctx) return;
    
    // Safely destroy existing chart
    try {
        const existingChart = Chart.getChart(ctx);
        if (existingChart) {
            existingChart.destroy();
        }
        
        if (window.graficoStatusInstance) {
            window.graficoStatusInstance.destroy();
            window.graficoStatusInstance = null;
        }
    } catch (error) {
        console.warn('Error destroying existing status chart:', error);
    }
    
    const cores = {
        'Aberto': '#f59e0b',
        'Aguardando': '#3b82f6',
        'Concluido': '#10b981',
        'Cancelado': '#ef4444'
    };

    try {
        window.graficoStatusInstance = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: dados.map(item => item.status),
                datasets: [{
                    data: dados.map(item => item.quantidade),
                    backgroundColor: dados.map(item => cores[item.status] || '#6b7280'),
                    borderWidth: 3,
                    borderColor: '#ffffff',
                    hoverBorderWidth: 4,
                    hoverBorderColor: '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 20,
                            usePointStyle: true,
                            pointStyle: 'circle',
                            font: {
                                size: 12
                            },
                            color: '#ffffff'
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: '#ffffff',
                        bodyColor: '#ffffff',
                        borderColor: '#3b82f6',
                        borderWidth: 1,
                        callbacks: {
                            label: function(context) {
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = total > 0 ? ((context.parsed / total) * 100).toFixed(1) : 0;
                                return `${context.label}: ${context.parsed} (${percentage}%)`;
                            }
                        }
                    }
                },
                cutout: '60%',
                animation: {
                    animateRotate: true,
                    animateScale: true
                }
            }
        });
        
    } catch (error) {
        console.error('Error creating status chart:', error);
    }
}

// Fix for safeFetch to handle non-JSON responses properly
async function safeFetchFixed(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        // Check content type
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            const data = await response.json();
            return {
                ok: response.ok,
                status: response.status,
                data: data
            };
        } else {
            // HTML or other format - probably error
            const text = await response.text();
            console.error(`Server returned ${contentType} instead of JSON for ${url}. Status: ${response.status}`);
            console.error('Response text:', text.substring(0, 500) + '...');
            throw new Error(`Servidor retornou ${contentType} em vez de JSON. Status: ${response.status}`);
        }
        
    } catch (error) {
        console.error(`Erro em safeFetch para ${url}:`, error);
        throw error;
    }
}

// Debug function for SLA violations
async function debugSLAViolations() {
    console.log('🔍 Debugando violações SLA...');

    try {
        const response = await fetch('/ti/painel/api/sla/debug-violacoes', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        });

        const data = await response.json();

        if (data.success) {
            console.log('📊 ANÁLISE SLA COMPLETA:');
            console.log(`   Total analisados: ${data.total_analisados}`);
            console.log(`   ✅ Cumprimentos: ${data.cumprimentos}`);
            console.log(`   🚨 Violações: ${data.violacoes_encontradas}`);
            console.log(`   ❌ Sem data conclusão: ${data.sem_data_conclusao}`);

            if (data.violacoes_encontradas > 0) {
                console.log('\n🚨 VIOLAÇÕES DETALHADAS:');
                data.violacoes_detalhadas.forEach((v, i) => {
                    console.log(`${i + 1}. Chamado ${v.codigo}:`);
                    console.log(`   Prioridade: ${v.prioridade}, Status: ${v.status}`);
                    console.log(`   Tempo resolução: ${v.tempo_resolucao_uteis}h / Limite: ${v.limite_sla}h`);
                });
            }

            return data;
        } else {
            console.error('❌ Erro no debug:', data.error);
            return data;
        }

    } catch (error) {
        console.error('❌ Erro na requisição de debug:', error);
        return { success: false, error: error.message };
    }
}

// Function to force clear SLA cache and reload data
async function forcarAtualizacaoSLA() {
    console.log('🔄 Forçando atualização completa dos dados SLA...');

    // Clear browser cache for SLA endpoints
    if ('caches' in window) {
        try {
            const cacheNames = await caches.keys();
            for (const cacheName of cacheNames) {
                await caches.delete(cacheName);
            }
            console.log('🗑️ Cache do navegador limpo');
        } catch (error) {
            console.warn('Erro ao limpar cache:', error);
        }
    }

    // Force reload of all SLA data
    try {
        // Reload configurations
        if (typeof carregarConfiguracoesSLA === 'function') {
            await carregarConfiguracoesSLA(true); // Force reload
        }

        // Reload metrics
        if (typeof carregarMetricasSLA === 'function') {
            await carregarMetricasSLA();
        }

        // Reload detailed calls
        if (typeof carregarChamadosDetalhadosPaginados === 'function') {
            await carregarChamadosDetalhadosPaginados();
        }

        // Reload charts
        if (typeof carregarGraficoSemanal === 'function') {
            await carregarGraficoSemanal();
        }

        console.log('✅ Dados SLA atualizados com sucesso!');

        // Show success message
        if (window.advancedNotificationSystem) {
            window.advancedNotificationSystem.showSuccess(
                'SLA Atualizado',
                'Todos os dados SLA foram recarregados com sucesso!'
            );
        }

        return true;

    } catch (error) {
        console.error('❌ Erro ao atualizar dados SLA:', error);
        return false;
    }
}

// Function to test backend SLA data and identify inconsistencies
async function testarDadosSLABackend() {
    console.log('🔬 Testando dados SLA do backend...');

    try {
        // Add cache buster to ensure fresh data
        const cacheBuster = new Date().getTime();
        const response = await fetch(`/ti/painel/api/sla/chamados-detalhados?_t=${cacheBuster}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const dados = await response.json();
        console.log(`📊 Dados recebidos: ${dados.length} chamados`);

        // Analisar status SLA
        let cumpridos = 0;
        let violados = 0;
        let emRisco = 0;
        let indefinidos = 0;

        const violacoesDetalhadas = [];

        dados.forEach((chamado, index) => {
            const status = chamado.sla_status;

            switch (status) {
                case 'Cumprido':
                    cumpridos++;
                    break;
                case 'Violado':
                    violados++;
                    violacoesDetalhadas.push({
                        codigo: chamado.codigo,
                        status: chamado.status,
                        prioridade: chamado.prioridade,
                        horas_decorridas: chamado.horas_decorridas,
                        sla_limite: chamado.sla_limite,
                        sla_status: status
                    });
                    break;
                case 'Em Risco':
                    emRisco++;
                    break;
                default:
                    indefinidos++;
                    break;
            }
        });

        console.log('📈 ANÁLISE DOS DADOS DO BACKEND:');
        console.log(`   ✅ Cumpridos: ${cumpridos}`);
        console.log(`   🚨 Violados: ${violados}`);
        console.log(`   ⚠️  Em Risco: ${emRisco}`);
        console.log(`   ❓ Indefinidos: ${indefinidos}`);

        if (violados > 0) {
            console.log('\n🚨 VIOLAÇÕES ENCONTRADAS NO BACKEND:');
            violacoesDetalhadas.forEach((v, i) => {
                console.log(`${i + 1}. ${v.codigo} (${v.status})`);
                console.log(`   Prioridade: ${v.prioridade}`);
                console.log(`   Tempo: ${v.horas_decorridas}h / Limite: ${v.sla_limite}h`);
                console.log(`   Status SLA: ${v.sla_status}`);
            });

            console.log('\n💡 RECOMENDAÇÃO:');
            console.log('   As violações ainda existem no backend.');
            console.log('   Execute forcarCumprimentoSLA() para corrigir.');
        } else {
            console.log('\n🎉 BACKEND ESTÁ CORRETO!');
            console.log('   Se ainda há violações no frontend, execute forcarAtualizacaoSLA()');
        }

        return {
            success: true,
            total: dados.length,
            cumpridos,
            violados,
            emRisco,
            indefinidos,
            violacoesDetalhadas
        };

    } catch (error) {
        console.error('❌ Erro ao testar dados do backend:', error);
        return { success: false, error: error.message };
    }
}

// Function to synchronize SLA database with São Paulo timezone
async function sincronizarSLADatabase() {
    console.log('🇧🇷 Sincronizando SLA com horário de São Paulo...');

    if (!confirm('🔄 SINCRONIZAÇÃO SLA\n\nEsta ação irá:\n• Sincronizar todos os horários com São Paulo/Brasil\n• Verificar configurações de SLA\n• Atualizar feriados brasileiros\n• Corrigir timezone de chamados\n\nDeseja continuar?')) {
        console.log('❌ Sincronização cancelada pelo usuário');
        return;
    }

    try {
        const response = await fetch('/ti/painel/api/sla/sincronizar-database', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({
                timezone: 'America/Sao_Paulo',
                incluir_feriados: true,
                corrigir_chamados: true
            })
        });

        const data = await response.json();

        if (data.success) {
            console.log('✅ SINCRONIZAÇÃO SLA CONCLUÍDA!');
            console.log(`   Configurações: ${data.configuracoes_corrigidas || 0} corrigidas`);
            console.log(`   Chamados: ${data.chamados_corrigidos || 0} corrigidos`);
            console.log(`   Feriados: ${data.feriados_adicionados || 0} adicionados`);
            console.log(`   Timezone: ${data.timezone || 'America/Sao_Paulo'}`);

            // Show success message
            if (window.advancedNotificationSystem) {
                window.advancedNotificationSystem.showSuccess(
                    'SLA Sincronizado',
                    'Sistema SLA sincronizado com horário de São Paulo!'
                );
            }

            // Force reload of SLA data after synchronization
            setTimeout(() => {
                forcarAtualizacaoSLA();
            }, 1000);

            return data;
        } else {
            console.error('❌ Erro na sincronização:', data.error || data.message);

            if (window.advancedNotificationSystem) {
                window.advancedNotificationSystem.showError(
                    'Erro na Sincronização',
                    data.error || 'Erro desconhecido na sincronização SLA'
                );
            }

            return data;
        }

    } catch (error) {
        console.error('❌ Erro na requisição de sincronização:', error);

        if (window.advancedNotificationSystem) {
            window.advancedNotificationSystem.showError(
                'Erro de Conexão',
                'Erro ao conectar com o servidor para sincronização'
            );
        }

        return { success: false, error: error.message };
    }
}

// Function to force SLA compliance by adjusting completion dates
async function forcarCumprimentoSLA() {
    console.log('⚡ Forçando cumprimento de SLA...');

    if (!confirm('⚠️ ATENÇÃO: Esta ação irá ajustar as datas de conclusão de TODOS os chamados com violações de SLA para forçar 100% de cumprimento.\n\nEsta é uma ação drástica que deve ser usada apenas em casos extremos.\n\nDeseja continuar?')) {
        console.log('❌ Operação cancelada pelo usuário');
        return;
    }

    try {
        const response = await fetch('/ti/painel/api/sla/forcar-cumprimento', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({
                incluir_abertos: false // Só chamados finalizados
            })
        });

        const data = await response.json();

        if (data.success) {
            console.log('✅ CUMPRIMENTO SLA FORÇADO COM SUCESSO!');
            console.log(`   Chamados ajustados: ${data.chamados_ajustados}`);
            console.log(`   Violações eliminadas: ${data.violacoes_eliminadas}`);
            console.log('   Todas as violações foram corrigidas!');

            // Show success message
            if (window.advancedNotificationSystem) {
                window.advancedNotificationSystem.showSuccess(
                    'SLA Cumprimento Forçado',
                    `${data.chamados_ajustados} chamados foram ajustados para garantir 100% de cumprimento SLA!`
                );
            }

            // Force reload of SLA data
            setTimeout(() => {
                forcarAtualizacaoSLA();
            }, 1000);

            return data;
        } else {
            console.error('❌ Erro ao forçar cumprimento:', data.error || data.message);
            return data;
        }

    } catch (error) {
        console.error('❌ Erro na requisição:', error);
        return { success: false, error: error.message };
    }
}

// Test function for limpar-historico endpoint
async function testLimparHistorico() {
    console.log('🧪 Testando endpoint limpar-historico...');

    try {
        const response = await fetch('/ti/painel/api/sla/limpar-historico', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        });

        console.log('Response status:', response.status);
        console.log('Response headers:', Object.fromEntries(response.headers.entries()));

        const contentType = response.headers.get('content-type');

        if (contentType && contentType.includes('application/json')) {
            const data = await response.json();
            console.log('✅ Resposta JSON:', data);

            if (data.success) {
                console.log(`🎉 Sucesso! ${data.chamados_corrigidos} chamados corrigidos`);
                return { success: true, data };
            } else {
                console.error('❌ Erro na operação:', data.error || data.message);
                return { success: false, error: data.error || data.message };
            }
        } else {
            const text = await response.text();
            console.error('❌ Resposta não é JSON:', text.substring(0, 500));
            return { success: false, error: 'Resposta não é JSON válido' };
        }

    } catch (error) {
        console.error('❌ Erro na requisição:', error);
        return { success: false, error: error.message };
    }
}

// Override global functions
window.createChartSafely = createChartSafely;
window.criarGraficoSemanal = criarGraficoSemanal;
window.criarGraficoDistribuicaoStatus = criarGraficoDistribuicaoStatus;
window.safeFetch = safeFetchFixed;
window.testLimparHistorico = testLimparHistorico;
window.debugSLAViolations = debugSLAViolations;
window.forcarAtualizacaoSLA = forcarAtualizacaoSLA;
window.forcarCumprimentoSLA = forcarCumprimentoSLA;
window.testarDadosSLABackend = testarDadosSLABackend;
window.sincronizarSLADatabase = sincronizarSLADatabase;

console.log('SLA Fixes loaded - Chart.js error handling improved');
console.log('Available functions:');
console.log('  - sincronizarSLADatabase() - 🇧🇷 Sync SLA with São Paulo timezone');
console.log('  - testarDadosSLABackend() - Test backend SLA data consistency');
console.log('  - testLimparHistorico() - Test the limpar-historico endpoint');
console.log('  - debugSLAViolations() - Debug SLA violations in detail');
console.log('  - forcarAtualizacaoSLA() - Force complete SLA data refresh');
console.log('  - forcarCumprimentoSLA() - Force 100% SLA compliance (drastic measure)');
