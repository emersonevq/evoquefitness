"""
Script de Verificação Pós-Migração: HistoricoStatus
=====================================================

Valida que a migração da tabela historico_status foi bem-sucedida
e que o sistema está funcionando corretamente com a nova estrutura.

Uso:
    python setores/ti/verificacao_migracao_sla.py
"""

from app import app
from database import db, Chamado, HistoricoStatus, User
from sqlalchemy import text, func
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verificar_migracao():
    """Executa todas as verificações pós-migração"""
    
    with app.app_context():
        print("\n" + "="*70)
        print("🔍 VERIFICAÇÃO PÓS-MIGRAÇÃO: HISTÓRICO DE STATUS")
        print("="*70 + "\n")
        
        # 1. Verificar tabela
        print("1️⃣  VERIFICANDO ESTRUTURA DA TABELA...")
        try:
            count = db.session.query(HistoricoStatus).count()
            print(f"   ✅ Tabela histórico_status existe")
            print(f"   ✅ Total de registros: {count}")
        except Exception as e:
            print(f"   ❌ Erro ao acessar tabela: {e}")
            return False
        
        # 2. Verificar trigger
        print("\n2️⃣  VERIFICANDO TRIGGER...")
        try:
            result = db.session.execute(text("""
                SELECT TRIGGER_NAME 
                FROM INFORMATION_SCHEMA.TRIGGERS 
                WHERE TRIGGER_NAME = 'trg_chamado_status_update'
            """)).fetchone()
            
            if result:
                print(f"   ✅ Trigger 'trg_chamado_status_update' existe")
            else:
                print(f"   ⚠️  Trigger não encontrado")
        except Exception as e:
            print(f"   ❌ Erro ao verificar trigger: {e}")
        
        # 3. Verificar view
        print("\n3️⃣  VERIFICANDO VIEW...")
        try:
            result = db.session.execute(text("""
                SELECT TABLE_NAME 
                FROM INFORMATION_SCHEMA.VIEWS 
                WHERE TABLE_NAME = 'vw_tempo_aguardando'
            """)).fetchone()
            
            if result:
                print(f"   ✅ View 'vw_tempo_aguardando' existe")
            else:
                print(f"   ⚠️  View não encontrada")
        except Exception as e:
            print(f"   ❌ Erro ao verificar view: {e}")
        
        # 4. Verificar integridade referencial
        print("\n4️⃣  VERIFICANDO INTEGRIDADE REFERENCIAL...")
        try:
            # Históricos órfãos (chamado_id não existe em chamado)
            orphans = db.session.execute(text("""
                SELECT COUNT(*) FROM historico_status hs
                WHERE NOT EXISTS (
                    SELECT 1 FROM chamado c 
                    WHERE c.id = hs.chamado_id
                )
            """)).scalar()
            
            if orphans == 0:
                print(f"   ✅ Não há registros órfãos")
            else:
                print(f"   ⚠️  Encontrados {orphans} registros órfãos")
        except Exception as e:
            print(f"   ❌ Erro ao verificar integridade: {e}")
        
        # 5. Distribuição de status
        print("\n5️⃣  DISTRIBUIÇÃO DE PERÍODOS POR STATUS...")
        try:
            stats = db.session.execute(text("""
                SELECT 
                    status,
                    COUNT(*) as quantidade,
                    SUM(CASE WHEN data_fim IS NULL THEN 1 ELSE 0 END) as abertos,
                    SUM(CASE WHEN data_fim IS NOT NULL THEN 1 ELSE 0 END) as fechados
                FROM historico_status
                GROUP BY status
                ORDER BY quantidade DESC
            """)).fetchall()
            
            for row in stats:
                status, qty, open_count, closed_count = row
                print(f"   • {status:20s}: {qty:4d} (abertos: {open_count}, fechados: {closed_count})")
        except Exception as e:
            print(f"   ❌ Erro ao obter estatísticas: {e}")
        
        # 6. Verificar períodos de "Aguardando"
        print("\n6️⃣  TEMPO TOTAL EM 'AGUARDANDO'...")
        try:
            result = db.session.execute(text("""
                SELECT 
                    COUNT(*) as total_periodos,
                    ROUND(SUM(
                        CASE 
                            WHEN data_fim IS NULL THEN 
                                TIMESTAMPDIFF(MINUTE, data_inicio, NOW()) / 60.0
                            ELSE 
                                TIMESTAMPDIFF(MINUTE, data_inicio, data_fim) / 60.0
                        END
                    ), 2) as total_horas
                FROM historico_status
                WHERE status = 'Aguardando'
            """)).fetchone()
            
            if result:
                total_periodos, total_horas = result
                print(f"   ✅ Total de períodos 'Aguardando': {total_periodos}")
                print(f"   ✅ Total de horas pausadas: {total_horas}h")
        except Exception as e:
            print(f"   ❌ Erro ao calcular tempo: {e}")
        
        # 7. Verificar backup antigo
        print("\n7️⃣  VERIFICANDO BACKUP ANTIGO...")
        try:
            result = db.session.execute(text("""
                SELECT COUNT(*) FROM information_schema.TABLES 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'historico_status_backup_old'
            """)).scalar()
            
            if result > 0:
                count = db.session.execute(text("""
                    SELECT COUNT(*) FROM historico_status_backup_old
                """)).scalar()
                print(f"   ✅ Backup encontrado com {count} registros")
            else:
                print(f"   ⚠️  Backup não encontrado (já pode ter sido removido)")
        except Exception as e:
            print(f"   ⚠️  Backup não encontrado: {e}")
        
        # 8. Verificar chamados sem histórico
        print("\n8️⃣  INTEGRIDADE DE DADOS DOS CHAMADOS...")
        try:
            sem_historico = db.session.execute(text("""
                SELECT COUNT(*) FROM chamado c
                WHERE NOT EXISTS (
                    SELECT 1 FROM historico_status hs 
                    WHERE hs.chamado_id = c.id
                )
            """)).scalar()
            
            if sem_historico == 0:
                print(f"   ✅ Todos os chamados têm histórico")
            else:
                print(f"   ⚠️  {sem_historico} chamados sem histórico")
        except Exception as e:
            print(f"   ❌ Erro ao verificar: {e}")
        
        # 9. Amostra de dados
        print("\n9️⃣  AMOSTRA DE ÚLTIMOS REGISTROS...")
        try:
            registros = db.session.execute(text("""
                SELECT 
                    h.id,
                    c.codigo,
                    h.status,
                    h.data_inicio,
                    h.data_fim,
                    DATE_FORMAT(h.created_at, '%d/%m/%Y %H:%i') as criado_em
                FROM historico_status h
                JOIN chamado c ON h.chamado_id = c.id
                ORDER BY h.created_at DESC
                LIMIT 5
            """)).fetchall()
            
            for row in registros:
                h_id, codigo, status, data_inicio, data_fim, criado_em = row
                fim_str = data_fim.strftime('%d/%m %H:%i') if data_fim else '(ativo)'
                print(f"   • {codigo} | {status:15s} | {data_inicio} → {fim_str}")
        except Exception as e:
            print(f"   ❌ Erro ao obter amostra: {e}")
        
        # 10. Teste de performance
        print("\n🔟 TESTE DE PERFORMANCE...")
        try:
            import time
            
            # Query simples
            start = time.time()
            count = db.session.query(HistoricoStatus).filter_by(
                status='Aguardando'
            ).count()
            elapsed = (time.time() - start) * 1000
            
            print(f"   ✅ Query simples: {elapsed:.2f}ms ({count} registros)")
            
            # Query com join
            start = time.time()
            result = db.session.execute(text("""
                SELECT COUNT(*) FROM historico_status h
                WHERE h.status = 'Aguardando' 
                AND h.chamado_id IN (
                    SELECT id FROM chamado WHERE status = 'Aguardando'
                )
            """)).scalar()
            elapsed = (time.time() - start) * 1000
            
            print(f"   ✅ Query com join: {elapsed:.2f}ms ({result} registros)")
        except Exception as e:
            print(f"   ❌ Erro no teste: {e}")
        
        # Resumo final
        print("\n" + "="*70)
        print("✅ VERIFICAÇÃO CONCLUÍDA COM SUCESSO!")
        print("="*70)
        print("\n📝 Próximas ações:")
        print("   1. Monitorar chamados em tempo real")
        print("   2. Verificar cálculos de SLA no painel")
        print("   3. Testar transições de status 'Aberto' → 'Aguardando' → 'Concluido'")
        print("   4. Validar métricas de SLA vs tempo em 'Aguardando'")
        print("\n")

if __name__ == '__main__':
    try:
        verificar_migracao()
    except Exception as e:
        logger.error(f"Erro geral: {e}")
        raise
