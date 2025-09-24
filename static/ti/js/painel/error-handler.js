/**
 * Sistema global de tratamento de erros JavaScript
 * Previne erros não capturados e fornece logs detalhados
 */

// Interceptar todos os erros não capturados
window.addEventListener('error', function(event) {
    console.group('🚨 ERRO JAVASCRIPT NÃO CAPTURADO');
    console.error('Erro:', event.error);
    console.error('Mensagem:', event.message);
    console.error('Arquivo:', event.filename);
    console.error('Linha:', event.lineno);
    console.error('Coluna:', event.colno);
    console.groupEnd();
    
    // Não bloquear execução
    return false;
});

// Interceptar promises rejeitadas não capturadas
window.addEventListener('unhandledrejection', function(event) {
    console.group('🚨 PROMISE REJEITADA NÃO CAPTURADA');
    console.error('Razão:', event.reason);
    console.error('Promise:', event.promise);
    console.groupEnd();
    
    // Prevenir que apareça no console como erro
    event.preventDefault();
});

/**
 * Wrapper seguro para chamadas fetch
 */
async function safeFetch(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        // Verificar se é JSON válido
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            const data = await response.json();
            return {
                ok: response.ok,
                status: response.status,
                data: data
            };
        } else {
            // HTML ou outro formato - provavelmente erro
            const text = await response.text();
            throw new Error(`Servidor retornou ${contentType} em vez de JSON. Status: ${response.status}`);
        }
        
    } catch (error) {
        console.error(`Erro em safeFetch para ${url}:`, error);
        throw error;
    }
}

/**
 * Função para executar código de forma segura
 */
function safeExecute(fn, errorMessage = 'Erro na execução') {
    try {
        return fn();
    } catch (error) {
        console.error(errorMessage, error);
        return null;
    }
}

/**
 * Verificar se função existe antes de chamar
 */
function safeCall(functionName, ...args) {
    if (typeof window[functionName] === 'function') {
        try {
            return window[functionName](...args);
        } catch (error) {
            console.error(`Erro ao chamar ${functionName}:`, error);
            return null;
        }
    } else {
        console.warn(`Função ${functionName} não existe`);
        return null;
    }
}

/**
 * Verificar se elemento existe antes de manipular
 */
function safeGetElement(selector, action = null) {
    const element = document.querySelector(selector);
    if (!element) {
        console.warn(`Elemento '${selector}' não encontrado`);
        return null;
    }
    
    if (action && typeof action === 'function') {
        try {
            return action(element);
        } catch (error) {
            console.error(`Erro ao executar ação em '${selector}':`, error);
            return null;
        }
    }
    
    return element;
}

// Disponibilizar globalmente
window.safeFetch = safeFetch;
window.safeExecute = safeExecute;
window.safeCall = safeCall;
window.safeGetElement = safeGetElement;

console.log('Error Handler carregado - funções disponíveis: safeFetch, safeExecute, safeCall, safeGetElement');
