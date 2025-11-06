-- =====================================================
-- DIAGNÓSTICO E CORREÇÃO DO TRIGGER DE SLA
-- =====================================================
-- Este script diagnostica e corrige problemas com
-- sincronização automática de histórico_status

-- ============= DIAGNÓSTICO =============

-- 1. Verificar se trigger existe
SELECT '1. VERIFICANDO TRIGGER' as passo;
SELECT TRIGGER_NAME, TRIGGER_SCHEMA, EVENT_OBJECT_TABLE, ACTION_STATEMENT
FROM INFORMATION_SCHEMA.TRIGGERS 
WHERE TRIGGER_NAME = 'trg_chamado_status_update';

-- Se não retornar nada, o trigger não existe

-- 2. Contar períodos abertos (potencial problema)
SELECT '2. PERÍODOS ABERTOS (SEM data_fim)' as passo;
SELECT 
    status,
    COUNT(*) as total_abertos
FROM historico_status 
WHERE data_fim IS NULL
GROUP BY status
ORDER BY total_abertos DESC;

-- 3. Verificar chamados com múltiplos períodos abertos (inconsistência)
SELECT '3. CHAMADOS COM MÚLTIPLOS PERÍODOS ABERTOS (ERRO)' as passo;
SELECT 
    hs.chamado_id,
    c.codigo,
    COUNT(*) as periodos_abertos,
    GROUP_CONCAT(hs.status) as statuses
FROM historico_status hs
JOIN chamado c ON hs.chamado_id = c.id
WHERE hs.data_fim IS NULL
GROUP BY hs.chamado_id
HAVING COUNT(*) > 1;

-- 4. Verificar desincronização entre chamado.status e historico_status
SELECT '4. DESINCRONIZAÇÃO ENTRE chamado.status E historico_status' as passo;
SELECT 
    c.id,
    c.codigo,
    c.status as status_chamado,
    hs.status as status_historico,
    hs.data_inicio,
    hs.data_fim
FROM chamado c
LEFT JOIN historico_status hs ON c.id = hs.chamado_id AND hs.data_fim IS NULL
WHERE c.status != hs.status OR hs.status IS NULL
LIMIT 20;

-- 5. Contar registros por estrutura
SELECT '5. CONTAGEM DE REGISTROS' as passo;
SELECT 'chamado' as tabela, COUNT(*) as total FROM chamado
UNION ALL
SELECT 'historico_status', COUNT(*) FROM historico_status
UNION ALL
SELECT 'historico_status (abertos)', COUNT(*) FROM historico_status WHERE data_fim IS NULL
UNION ALL
SELECT 'historico_status (fechados)', COUNT(*) FROM historico_status WHERE data_fim IS NOT NULL;

-- ============= CORREÇÃO =============

-- Não executar automaticamente! São instruções de correção manual.
-- Descomente conforme necessário após análise.

-- 1. Remover trigger antigo se existir
-- DROP TRIGGER IF EXISTS trg_chamado_status_update;

-- 2. Criar trigger corrigido
-- DELIMITER $$
-- CREATE TRIGGER trg_chamado_status_update
-- AFTER UPDATE ON chamado
-- FOR EACH ROW
-- BEGIN
--   -- Apenas executar se status realmente mudou
--   IF COALESCE(OLD.status, '') != COALESCE(NEW.status, '') THEN
--     
--     -- 1) Fechar qualquer período anterior aberto para este chamado
--     UPDATE historico_status
--     SET data_fim = NEW.updated_at
--     WHERE chamado_id = NEW.id
--       AND data_fim IS NULL
--       AND status != NEW.status;
--     
--     -- 2) Criar novo período para o novo status (se não existir já)
--     -- Verifica se já há um período aberto com o novo status
--     IF NOT EXISTS (
--       SELECT 1 FROM historico_status 
--       WHERE chamado_id = NEW.id 
--       AND status = NEW.status 
--       AND data_fim IS NULL
--     ) THEN
--       INSERT INTO historico_status
--         (chamado_id, status, data_inicio, data_fim, usuario_id, descricao, created_at, updated_at)
--       VALUES
--         (
--           NEW.id,
--           NEW.status,
--           IFNULL(NEW.updated_at, NOW()),
--           NULL,
--           NULL,
--           CONCAT('Mudança automática: ', COALESCE(OLD.status, 'Novo'), ' → ', NEW.status),
--           NOW(),
--           NOW()
--         );
--     END IF;
--   END IF;
-- END$$
-- DELIMITER ;

-- 3. Corrigir desincronizações manualmente (CUIDADO - analisar antes!)
-- Para chamados com status diferente:
-- 1. Encontrar o período aberto mais recente
-- 2. Fechar com data_fim apropriada
-- 3. Criar novo período com status correto

-- Exemplo para um chamado específico:
-- UPDATE historico_status 
-- SET data_fim = NOW() 
-- WHERE chamado_id = 123 
-- AND data_fim IS NULL;
-- 
-- INSERT INTO historico_status (chamado_id, status, data_inicio, data_fim, created_at, updated_at)
-- VALUES (123, 'Concluido', NOW(), NOW(), NOW(), NOW());
