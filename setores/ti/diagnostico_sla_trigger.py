#!/usr/bin/env python3
"""
Script de Diagnóstico do Trigger SLA
====================================

Verifica se o trigger trg_chamado_status_update está funcionando
corretamente e identifica problemas de sincronização.

Uso:
    python setores/ti/diagnostico_sla_trigger.py
"""

from app import app
from database import db, Chamado, HistoricoStatus
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def executar_diagnostico():
    """Executa diagnóstico completo do trigger de SLA"""
    
    with app.app_context():
        print("\n" + "="*80)
        print("🔍 DIAGNÓSTICO COMPLETO DO TRIGGER DE SLA")
        print("="*80 + "\n")
        
        problemas_encontrados = []
        
        # 1. Verificar se trigger existe
        print("1️⃣  VERIFICANDO EXISTÊNCIA DO TRIGGER...")
        try:
            result = db.session.execute(text("""
                SELECT TRIGGER_NAME 
                FROM INFORMATION_SCHEMA.TRIGGERS 
                WHERE TRIGGER_NAME = 'trg_chamado_status_update'
            """)).fetchone()
            
            if result:
                print("   ✅ Trigger 'trg_chamado_status_update' EXISTE no banco")
            else:
                print("   ❌ PROBLEMA ENCONTRADO: Trigger 'trg_chamado_status_update' NÃO EXISTE")
                problemas_encontrados.append("trigger_nao_existe")
        except Exception as e:
            print(f"   ⚠️  Erro ao verificar trigger: {e}")
            problemas_encontrados.append("erro_ao_verificar_trigger")
        
        # 2. Contar períodos abertos
        print("\n2️⃣  VERIFICANDO PERÍODOS ABERTOS...")
        try:
            result = db.session.execute(text("""
                SELECT 
                    status,
                    COUNT(*) as total
                FROM historico_status 
                WHERE data_fim IS NULL
                GROUP BY status
            """)).fetchall()
            
            if result:
                print("   ⚠️  Períodos ainda abertos (sem data_fim):")
                for status, total in result:
                    print(f"      • {status}: {total} períodos")
                    if total > 0:
                        problemas_encontrados.append("periodos_abertos")
            else:
                print("   ✅ Nenhum período aberto encontrado")
        except Exception as e:
            print(f"   ⚠️  Erro ao contar períodos: {e}")
        
        # 3. Verificar chamados com múltiplos períodos abertos
        print("\n3️⃣  VERIFICANDO INCONSISTÊNCIAS (múltiplos períodos abertos)...")
        try:
            result = db.session.execute(text("""
                SELECT 
                    hs.chamado_id,
                    c.codigo,
                    COUNT(*) as periodos_abertos,
                    GROUP_CONCAT(hs.status) as statuses
                FROM historico_status hs
                JOIN chamado c ON hs.chamado_id = c.id
                WHERE hs.data_fim IS NULL
                GROUP BY hs.chamado_id
                HAVING COUNT(*) > 1
            """)).fetchall()
            
            if result:
                print(f"   ❌ PROBLEMA ENCONTRADO: {len(result)} chamados com múltiplos períodos abertos:")
                for chamado_id, codigo, qty, statuses in result:
                    print(f"      • {codigo}: {qty} períodos ({statuses})")
                    problemas_encontrados.append("multiplos_periodos_abertos")
            else:
                print("   ✅ Nenhum chamado com múltiplos períodos abertos")
        except Exception as e:
            print(f"   ⚠️  Erro ao verificar: {e}")
        
        # 4. Verificar desincronização entre status
        print("\n4️⃣  VERIFICANDO DESINCRONIZAÇÃO (chamado.status vs historico_status)...")
        try:
            result = db.session.execute(text("""
                SELECT 
                    c.id,
                    c.codigo,
                    c.status as status_chamado,
                    hs.status as status_historico
                FROM chamado c
                LEFT JOIN historico_status hs ON c.id = hs.chamado_id AND hs.data_fim IS NULL
                WHERE c.status != COALESCE(hs.status, c.status)
                LIMIT 20
            """)).fetchall()
            
            if result:
                print(f"   ❌ PROBLEMA ENCONTRADO: {len(result)} chamados com status desincronizado:")
                for chamado_id, codigo, status_chamado, status_historico in result:
                    print(f"      • {codigo}: status={status_chamado}, histórico={status_historico}")
                    problemas_encontrados.append("desincronizacao_status")
            else:
                print("   ✅ Todos os chamados estão sincronizados")
        except Exception as e:
            print(f"   ⚠️  Erro ao verificar: {e}")
        
        # 5. Contagem total de registros
        print("\n5️⃣  CONTAGEM DE REGISTROS...")
        try:
            total_chamados = db.session.query(Chamado).count()
            total_historicos = db.session.query(HistoricoStatus).count()
            total_abertos = db.session.execute(text(
                "SELECT COUNT(*) FROM historico_status WHERE data_fim IS NULL"
            )).scalar()
            
            print(f"   • Chamados: {total_chamados}")
            print(f"   • Históricos: {total_historicos}")
            print(f"   • Períodos abertos: {total_abertos}")
            
            if total_chamados > 0 and total_historicos == 0:
                problemas_encontrados.append("sem_historicos")
        except Exception as e:
            print(f"   ⚠️  Erro ao contar: {e}")
        
        # 6. Amostra de últimos registros
        print("\n6️⃣  AMOSTRA DOS ÚLTIMOS 5 REGISTROS...")
        try:
            result = db.session.execute(text("""
                SELECT 
                    c.codigo,
                    hs.status,
                    hs.data_inicio,
                    hs.data_fim,
                    DATE_FORMAT(hs.created_at, '%d/%m %H:%i') as criado
                FROM historico_status hs
                JOIN chamado c ON hs.chamado_id = c.id
                ORDER BY hs.created_at DESC
                LIMIT 5
            """)).fetchall()
            
            for codigo, status, data_inicio, data_fim, criado in result:
                fim_str = data_fim.strftime('%d/%m %H:%i') if data_fim else '(aberto)'
                print(f"   • {codigo:15s} | {status:15s} | {criado}")
        except Exception as e:
            print(f"   ⚠️  Erro ao obter amostra: {e}")
        
        # Relatório final
        print("\n" + "="*80)
        if problemas_encontrados:
            print("❌ PROBLEMAS IDENTIFICADOS:")
            for problema in set(problemas_encontrados):
                descricoes = {
                    "trigger_nao_existe": "O trigger não existe no banco de dados",
                    "erro_ao_verificar_trigger": "Erro ao verificar existência do trigger",
                    "periodos_abertos": "Há períodos ainda abertos (data_fim IS NULL)",
                    "multiplos_periodos_abertos": "Chamados com múltiplos períodos abertos (inconsistência)",
                    "desincronizacao_status": "Status do chamado diferente do histórico",
                    "sem_historicos": "Não há históricos para alguns chamados"
                }
                print(f"   • {descricoes.get(problema, problema)}")
            
            print("\n📋 AÇÕES RECOMENDADAS:")
            print("   1. Execute: python setores/ti/diagnostico_sla_trigger.py")
            print("   2. Analise os problemas acima")
            print("   3. Execute: python setores/ti/corrigir_sla_trigger.py")
            print("   4. Execute: python setores/ti/verificacao_migracao_sla.py")
        else:
            print("✅ NENHUM PROBLEMA ENCONTRADO!")
            print("   O trigger está funcionando corretamente")
        
        print("="*80 + "\n")
        
        return len(problemas_encontrados) == 0

if __name__ == '__main__':
    try:
        sucesso = executar_diagnostico()
        exit(0 if sucesso else 1)
    except Exception as e:
        logger.error(f"Erro geral no diagnóstico: {e}")
        raise
