// Script para testar sistema de email
class EmailTester {
    constructor() {
        this.baseUrl = '/ti';
    }

    async testEmailConfig() {
        try {
            console.log('🔍 Verificando configurações de email...');
            const response = await fetch(`${this.baseUrl}/debug-email-config`);
            const result = await response.json();
            
            console.log('📧 Configurações de Email:', result);
            
            if (result.success) {
                if (result.config_ok) {
                    console.log('✅ Configurações de email OK!');
                    return true;
                } else {
                    console.log('❌ Configurações de email com problemas:', result.missing_vars);
                    return false;
                }
            } else {
                console.log('❌ Erro ao verificar configurações:', result.message);
                return false;
            }
        } catch (error) {
            console.error('❌ Erro ao verificar configurações de email:', error);
            return false;
        }
    }

    async sendTestEmail() {
        try {
            console.log('📤 Enviando email de teste...');
            const response = await fetch(`${this.baseUrl}/test-email`);
            const result = await response.json();
            
            console.log('📧 Resultado do teste de email:', result);
            
            if (result.success) {
                console.log('✅ Email de teste enviado com sucesso!');
                this.showNotification(result.message, 'success');
                return true;
            } else {
                console.log('❌ Falha no envio do email de teste:', result.message);
                this.showNotification(result.message, 'error');
                return false;
            }
        } catch (error) {
            console.error('❌ Erro ao enviar email de teste:', error);
            this.showNotification('Erro ao enviar email de teste', 'error');
            return false;
        }
    }

    async runFullTest() {
        console.log('🚀 Iniciando teste completo do sistema de email...');
        
        // 1. Verificar configurações
        const configOk = await this.testEmailConfig();
        if (!configOk) {
            console.log('❌ Teste interrompido - configurações inválidas');
            return false;
        }
        
        // 2. Tentar enviar email de teste
        const emailOk = await this.sendTestEmail();
        
        if (emailOk) {
            console.log('🎉 Teste completo do sistema de email concluído com sucesso!');
            return true;
        } else {
            console.log('❌ Teste completo falhou no envio de email');
            return false;
        }
    }

    showNotification(message, type = 'info') {
        // Usar sistema de notificação do painel se disponível
        if (window.painelAgente && window.painelAgente.showNotification) {
            window.painelAgente.showNotification(message, type);
        } else {
            // Fallback para console
            console.log(`[${type.toUpperCase()}] ${message}`);
        }
    }

    // Teste específico de transferência
    async testTransferEmailNotification(chamadoId, agenteDestinoId, observacoes = 'Teste de transferência') {
        try {
            console.log(`🔄 Testando notificação de transferência para chamado ${chamadoId}...`);
            
            const response = await fetch(`/ti/painel/api/chamados/${chamadoId}/transferir`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    agente_destino_id: agenteDestinoId,
                    observacoes: observacoes
                })
            });

            const result = await response.json();
            
            if (result.success || response.ok) {
                console.log('✅ Transferência realizada - emails devem ter sido enviados');
                this.showNotification('Transferência realizada com sucesso! Verifique os emails.', 'success');
                return true;
            } else {
                console.log('❌ Falha na transferência:', result.message || result.error);
                this.showNotification(`Falha na transferência: ${result.message || result.error}`, 'error');
                return false;
            }
        } catch (error) {
            console.error('❌ Erro no teste de transferência:', error);
            this.showNotification('Erro no teste de transferência', 'error');
            return false;
        }
    }
}

// Instância global para uso em console
window.emailTester = new EmailTester();

// Função de conveniência para teste rápido
window.testEmail = async function() {
    return await window.emailTester.runFullTest();
};

// Função para testar transferência específica
window.testTransferEmail = async function(chamadoId, agenteDestinoId, observacoes) {
    return await window.emailTester.testTransferEmailNotification(chamadoId, agenteDestinoId, observacoes);
};

console.log('📧 EmailTester carregado! Use window.testEmail() para testar o sistema de email');
