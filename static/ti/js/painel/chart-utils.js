/**
 * Utilitário para gerenciamento adequado de gráficos Chart.js
 * Previne erros de canvas já em uso
 */

// Armazenar referências de todos os gráficos
window.chartInstances = window.chartInstances || {};

/**
 * Destroi um gráfico de forma segura
 * @param {string} chartId - ID único do gráfico
 */
function destroyChartSafely(chartId) {
    try {
        // Verificar instância no nosso registro
        if (window.chartInstances[chartId]) {
            window.chartInstances[chartId].destroy();
            delete window.chartInstances[chartId];
        }
        
        // Verificar instância global do Chart.js
        const canvas = document.getElementById(chartId);
        if (canvas) {
            const chartInstance = Chart.getChart(canvas);
            if (chartInstance) {
                chartInstance.destroy();
            }
        }
        
        // Verificar variáveis globais legadas
        const globalVarNames = [
            `chart${chartId.charAt(0).toUpperCase() + chartId.slice(1)}`,
            `window.chart${chartId.charAt(0).toUpperCase() + chartId.slice(1)}`,
            chartId
        ];
        
        globalVarNames.forEach(varName => {
            if (window[varName] && typeof window[varName].destroy === 'function') {
                try {
                    window[varName].destroy();
                    window[varName] = null;
                } catch (e) {
                    console.warn(`Erro ao destruir ${varName}:`, e);
                }
            }
        });
        
    } catch (error) {
        console.warn(`Erro ao destruir gráfico ${chartId}:`, error);
    }
}

/**
 * Cria um gráfico de forma segura
 * @param {string} canvasId - ID do elemento canvas
 * @param {object} config - Configuração do Chart.js
 * @param {string} instanceName - Nome da instância global (opcional)
 * @returns {Chart} Instância do gráfico criado
 */
function createChartSafely(canvasId, config, instanceName = null) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) {
        console.error(`Canvas com ID '${canvasId}' não encontrado`);
        return null;
    }
    
    // Destruir qualquer gráfico existente primeiro
    destroyChartSafely(canvasId);
    
    try {
        // Criar novo gráfico
        const chart = new Chart(canvas, config);
        
        // Registrar a instância
        window.chartInstances[canvasId] = chart;
        
        // Também salvar como variável global se especificado
        if (instanceName) {
            window[instanceName] = chart;
        }
        
        return chart;
        
    } catch (error) {
        console.error(`Erro ao criar gráfico para ${canvasId}:`, error);
        return null;
    }
}

/**
 * Destroi todos os gráficos registrados
 */
function destroyAllCharts() {
    Object.keys(window.chartInstances).forEach(chartId => {
        destroyChartSafely(chartId);
    });
    window.chartInstances = {};
}

/**
 * Lista todos os gráficos ativos
 */
function listActiveCharts() {
    console.log('Gráficos ativos:', Object.keys(window.chartInstances));
    return Object.keys(window.chartInstances);
}

// Disponibilizar globalmente
window.destroyChartSafely = destroyChartSafely;
window.createChartSafely = createChartSafely;
window.destroyAllCharts = destroyAllCharts;
window.listActiveCharts = listActiveCharts;

/**
 * Parse JSON de forma segura, lidando com respostas HTML de erro
 * @param {Response} response - Response object do fetch
 * @returns {Promise} Promise que resolve com os dados JSON ou rejeita com erro apropriado
 */
async function safeJsonParse(response) {
    const contentType = response.headers.get('content-type');

    if (!contentType || !contentType.includes('application/json')) {
        // Se não é JSON, provavelmente é uma página de erro HTML
        const text = await response.text();
        throw new Error(`Servidor retornou HTML em vez de JSON. Status: ${response.status}`);
    }

    try {
        return await response.json();
    } catch (error) {
        throw new Error(`Erro ao fazer parse do JSON: ${error.message}`);
    }
}

// Auto-cleanup ao sair da página
window.addEventListener('beforeunload', function() {
    destroyAllCharts();
});

// Disponibilizar utilitário JSON também
window.safeJsonParse = safeJsonParse;

console.log('Chart Utils carregado - funções disponíveis: destroyChartSafely, createChartSafely, destroyAllCharts, listActiveCharts, safeJsonParse');
