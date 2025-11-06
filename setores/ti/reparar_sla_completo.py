#!/usr/bin/env python3
"""
Script Completo de Reparação do Sistema SLA
===========================================

Executa os três passos necessários para reparar o sistema:
1. Diagnóstico - identifica problemas
2. Correção - cria/corrige o trigger e dados
3. Validação - verifica se tudo está funcionando

Uso:
    python setores/ti/reparar_sla_completo.py
"""

import subprocess
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def executar_script(nome, arquivo):
    """Executa um script Python"""
    print(f"\n{'='*80}")
    print(f"▶️  Executando: {nome}")
    print(f"{'='*80}\n")
    
    try:
        resultado = subprocess.run(
            [sys.executable, arquivo],
            check=True,
            capture_output=False
        )
        return resultado.returncode == 0
    except subprocess.CalledProcessError as e:
        logger.error(f"Erro ao executar {nome}: {e}")
        return False
    except Exception as e:
        logger.error(f"Erro geral ao executar {nome}: {e}")
        return False

def main():
    """Executa todo o processo de reparação"""
    
    print("\n" + "="*80)
    print("🔧 REPARAÇÃO COMPLETA DO SISTEMA DE SLA")
    print("="*80)
    print("""
Este script irá:
1. 🔍 Diagnosticar problemas no trigger e dados
2. 🛠️  Criar/corrigir o trigger automático
3. ✅ Validar que tudo está funcionando

Tempo estimado: 2-3 minutos
""")
    
    input("Pressione ENTER para continuar ou Ctrl+C para cancelar...")
    
    # Passo 1: Diagnóstico
    print("\n" + "="*80)
    print("PASSO 1: DIAGNÓSTICO")
    print("="*80)
    
    sucesso_diagnostico = executar_script(
        "Diagnóstico",
        "setores/ti/diagnostico_sla_trigger.py"
    )
    
    if not sucesso_diagnostico:
        print("⚠️  Diagnóstico teve erro, mas continuando...")
    
    # Passo 2: Correção
    print("\n" + "="*80)
    print("PASSO 2: CORREÇÃO")
    print("="*80)
    
    sucesso_correcao = executar_script(
        "Correção",
        "setores/ti/corrigir_sla_trigger.py"
    )
    
    if not sucesso_correcao:
        print("❌ ERRO na correção! Abortando.")
        return False
    
    # Passo 3: Validação
    print("\n" + "="*80)
    print("PASSO 3: VALIDAÇÃO")
    print("="*80)
    
    sucesso_validacao = executar_script(
        "Validação",
        "setores/ti/verificacao_migracao_sla.py"
    )
    
    if not sucesso_validacao:
        print("⚠️  Validação teve erro, verificar manualmente")
    
    # Resumo final
    print("\n" + "="*80)
    if sucesso_correcao and sucesso_validacao:
        print("✅ REPARAÇÃO CONCLUÍDA COM SUCESSO!")
        print("="*80)
        print("""
📋 Próximas ações:

1. Reiniciar o servidor:
   - Ctrl+C para parar o servidor
   - Execute: npm run dev (ou seu comando de dev)

2. Testar no painel:
   - Vá para o painel de TI
   - Abra um chamado existente
   - Mude o status do chamado
   - Verifique se o histórico foi atualizado

3. Confirmar métricas:
   - Vá para Setor de TI > Painéis > SLA
   - Verifique se as métricas estão atualizadas
   - Confirme que tempos em "Aguardando" estão sendo descontados

4. Se ainda houver problemas:
   - Limpe o cache do navegador (Ctrl+Shift+Delete)
   - Force um recarregamento (Ctrl+Shift+R)
""")
        return True
    else:
        print("⚠️  REPARAÇÃO COM AVISO!")
        print("="*80)
        print("""
Alguns passos tiveram avisos. Verifique os logs acima
e execute:

    python setores/ti/diagnostico_sla_trigger.py

Para mais detalhes.
""")
        return True  # Ainda consideramos sucesso parcial

if __name__ == '__main__':
    try:
        sucesso = main()
        print("\n")
        sys.exit(0 if sucesso else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Operação cancelada pelo usuário")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Erro geral: {e}")
        raise
