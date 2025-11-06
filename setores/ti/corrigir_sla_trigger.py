#!/usr/bin/env python3
"""
Script para Criar/Corrigir Trigger de SLA
==========================================

Cria ou corrige o trigger trg_chamado_status_update para:
1. Fechar períodos anteriores quando status muda
2. Criar novo período com novo status
3. Sincronizar dados históricos

Uso:
    python setores/ti/corrigir_sla_trigger.py
"""

from app import app
from database import db, Chamado, HistoricoStatus, get_brazil_time
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

TRIGGER_SQL = """
CREATE TRIGGER trg_chamado_status_update
AFTER UPDATE ON chamado
FOR EACH ROW
BEGIN
  -- Apenas executar se status realmente mudou
  IF COALESCE(OLD.status, '') != COALESCE(NEW.status, '') THEN

    -- 1) Fechar qualquer período anterior aberto para este chamado
    UPDATE historico_status
    SET data_fim = NOW()
    WHERE chamado_id = NEW.id
      AND data_fim IS NULL
      AND status != NEW.status;

    -- 2) Criar novo período para o novo status (se não existir já)
    IF NOT EXISTS (
      SELECT 1 FROM historico_status
      WHERE chamado_id = NEW.id
      AND status = NEW.status
      AND data_fim IS NULL
    ) THEN
      INSERT INTO historico_status
        (chamado_id, status, data_inicio, data_fim, usuario_id, descricao, created_at, updated_at)
      VALUES
        (
          NEW.id,
          NEW.status,
          NOW(),
          NULL,
          NULL,
          CONCAT('Mudança automática: ', COALESCE(OLD.status, 'Novo'), ' → ', NEW.status),
          NOW(),
          NOW()
        );
    END IF;
  END IF;
END
"""

def criar_trigger():
    """Cria o trigger no banco de dados"""
    
    with app.app_context():
        print("\n" + "="*80)
        print("🔧 CRIANDO/CORRIGINDO TRIGGER DE SLA")
        print("="*80 + "\n")
        
        try:
            # 1. Remover trigger antigo se existir
            print("1️⃣  Removendo trigger antigo se existir...")
            db.session.execute(text("DROP TRIGGER IF EXISTS trg_chamado_status_update"))
            db.session.commit()
            print("   ✅ Trigger antigo removido (ou não existia)")
            
            # 2. Criar novo trigger
            print("\n2️⃣  Criando novo trigger...")
            db.session.execute(text(TRIGGER_SQL))
            db.session.commit()
            print("   ✅ Novo trigger criado com sucesso")
            
            # 3. Verificar se trigger foi criado
            print("\n3️⃣  Verificando se trigger foi criado...")
            result = db.session.execute(text("""
                SELECT TRIGGER_NAME 
                FROM INFORMATION_SCHEMA.TRIGGERS 
                WHERE TRIGGER_NAME = 'trg_chamado_status_update'
            """)).fetchone()
            
            if result:
                print("   ✅ Trigger verificado e ativo")
            else:
                print("   ❌ ERRO: Trigger não foi criado")
                return False
            
            # 4. Corrigir desincronizações
            print("\n4️⃣  Corrigindo desincronizações de status...")
            
            # Buscar chamados com histórico incompleto
            chamados_problema = db.session.execute(text("""
                SELECT c.id, c.codigo, c.status
                FROM chamado c
                WHERE NOT EXISTS (
                    SELECT 1 FROM historico_status hs 
                    WHERE hs.chamado_id = c.id
                )
                LIMIT 100
            """)).fetchall()
            
            if chamados_problema:
                print(f"   ⚠️  Encontrados {len(chamados_problema)} chamados sem histórico")
                print("   🔧 Corrigindo...")
                
                for chamado_id, codigo, status in chamados_problema:
                    # Buscar o chamado
                    chamado = Chamado.query.get(chamado_id)
                    if chamado:
                        # Criar histórico inicial
                        historico = HistoricoStatus(
                            chamado_id=chamado_id,
                            status=status,
                            data_inicio=chamado.data_abertura or get_brazil_time(),
                            data_fim=chamado.data_conclusao if status in ['Concluido', 'Cancelado'] else None,
                            descricao='Inicializado por correção do trigger'
                        )
                        db.session.add(historico)
                        print(f"      • {codigo}: histórico criado")
                
                db.session.commit()
                print(f"   ✅ {len(chamados_problema)} históricos criados")
            else:
                print("   ✅ Todos os chamados têm histórico")
            
            # 5. Fechar períodos abertos incorretamente
            print("\n5️⃣  Fechando períodos abertos incorretos...")
            
            # Buscar períodos abertos de chamados finalizados
            periodos_problema = db.session.execute(text("""
                SELECT hs.id, hs.chamado_id, c.codigo, hs.status, c.status as chamado_status
                FROM historico_status hs
                JOIN chamado c ON hs.chamado_id = c.id
                WHERE hs.data_fim IS NULL
                  AND c.status IN ('Concluido', 'Cancelado')
                LIMIT 100
            """)).fetchall()
            
            if periodos_problema:
                print(f"   ⚠️  Encontrados {len(periodos_problema)} períodos abertos de chamados finalizados")
                print("   🔧 Corrigindo...")
                
                for periodo_id, chamado_id, codigo, status, chamado_status in periodos_problema:
                    # Buscar data de conclusão do chamado
                    chamado = Chamado.query.get(chamado_id)
                    if chamado and chamado.data_conclusao:
                        # Fechar período com a data de conclusão
                        db.session.execute(text("""
                            UPDATE historico_status 
                            SET data_fim = :data_fim 
                            WHERE id = :id
                        """), {'data_fim': chamado.data_conclusao, 'id': periodo_id})
                        print(f"      • {codigo}: período {status} fechado")
                
                db.session.commit()
                print(f"   ✅ {len(periodos_problema)} períodos fechados")
            else:
                print("   ✅ Nenhum período aberto incorreto encontrado")
            
            # 6. Resumo final
            print("\n" + "="*80)
            print("✅ TRIGGER CRIADO/CORRIGIDO COM SUCESSO!")
            print("="*80)
            print("\n📋 Próximas ações:")
            print("   1. Execute: python setores/ti/diagnostico_sla_trigger.py")
            print("   2. Confirme que nenhum problema foi encontrado")
            print("   3. Execute: python setores/ti/verificacao_migracao_sla.py")
            print("   4. Teste a atualização de um chamado para verificar se o trigger funciona")
            print("\n")
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao criar trigger: {e}")
            db.session.rollback()
            print(f"\n❌ ERRO: {e}")
            return False

if __name__ == '__main__':
    try:
        sucesso = criar_trigger()
        exit(0 if sucesso else 1)
    except Exception as e:
        logger.error(f"Erro geral: {e}")
        raise
