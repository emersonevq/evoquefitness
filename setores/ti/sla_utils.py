"""
Utilitários para cálculo correto de SLA considerando horário comercial
"""
from datetime import datetime, timedelta, time
from typing import Optional, Dict, Tuple
import pytz
import json
from database import get_brazil_time, Configuracao, db
import logging

logger = logging.getLogger(__name__)

# Timezone do Brasil
BRAZIL_TZ = pytz.timezone('America/Sao_Paulo')

# Configurações padrão de horário comercial
HORARIO_COMERCIAL = {
    'inicio': time(8, 0),      # 08:00
    'fim': time(18, 0),        # 18:00
    'dias_semana': [0, 1, 2, 3, 4],  # Segunda a sexta (0=segunda)
}

# Configurações padrão de SLA (em horas)
SLA_PADRAO = {
    'primeira_resposta': 4,
    'resolucao_critica': 2,
    'resolucao_urgente': 2,  # Urgente usa mesmo SLA que Crítica
    'resolucao_alta': 8,
    'resolucao_normal': 24,
    'resolucao_baixa': 72
}

def carregar_configuracoes_sla():
    """Carrega configurações de SLA do banco ou retorna padrões"""
    try:
        config_sla = Configuracao.query.filter_by(chave='sla').first()
        if config_sla:
            return json.loads(config_sla.valor)
        else:
            # Criar configuração padrão se não existir
            nova_config = Configuracao(
                chave='sla',
                valor=json.dumps(SLA_PADRAO)
            )
            db.session.add(nova_config)
            db.session.commit()
            logger.info("Configurações SLA padrão criadas no banco de dados")
            return SLA_PADRAO
    except Exception as e:
        logger.error(f"Erro ao carregar configurações SLA: {str(e)}")
        return SLA_PADRAO

def salvar_configuracoes_sla(config_sla: Dict):
    """Salva configurações de SLA no banco"""
    try:
        config_obj = Configuracao.query.filter_by(chave='sla').first()
        if config_obj:
            config_obj.valor = json.dumps(config_sla)
            config_obj.data_atualizacao = get_brazil_time().replace(tzinfo=None)
        else:
            config_obj = Configuracao(
                chave='sla',
                valor=json.dumps(config_sla)
            )
            db.session.add(config_obj)
        
        db.session.commit()
        logger.info("Configurações SLA salvas com sucesso")
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar configurações SLA: {str(e)}")
        db.session.rollback()
        return False

def carregar_configuracoes_horario_comercial():
    """Carrega configurações de horário comercial do banco ou retorna padrões"""
    try:
        config_horario = Configuracao.query.filter_by(chave='horario_comercial').first()
        if config_horario:
            dados = json.loads(config_horario.valor)
            # Converter strings de time de volta para objetos time
            if 'inicio' in dados:
                hora, minuto = map(int, dados['inicio'].split(':'))
                dados['inicio'] = time(hora, minuto)
            if 'fim' in dados:
                hora, minuto = map(int, dados['fim'].split(':'))
                dados['fim'] = time(hora, minuto)
            return dados
        else:
            # Criar configuração padrão se não existir
            config_para_salvar = HORARIO_COMERCIAL.copy()
            config_para_salvar['inicio'] = '08:00'
            config_para_salvar['fim'] = '18:00'
            
            nova_config = Configuracao(
                chave='horario_comercial',
                valor=json.dumps(config_para_salvar)
            )
            db.session.add(nova_config)
            db.session.commit()
            logger.info("Configurações de horário comercial padrão criadas no banco de dados")
            return HORARIO_COMERCIAL
    except Exception as e:
        logger.error(f"Erro ao carregar configurações de horário comercial: {str(e)}")
        return HORARIO_COMERCIAL

def eh_horario_comercial(dt: datetime, config_horario: Dict = None) -> bool:
    """Verifica se um datetime está dentro do horário comercial"""
    if config_horario is None:
        config_horario = carregar_configuracoes_horario_comercial()
    
    # Verificar dia da semana (0=segunda, 6=domingo)
    if dt.weekday() not in config_horario['dias_semana']:
        return False
    
    # Verificar horário
    hora_atual = dt.time()
    return config_horario['inicio'] <= hora_atual <= config_horario['fim']

def calcular_horas_uteis(inicio: datetime, fim: datetime, config_horario: Dict = None) -> float:
    """
    Calcula horas úteis entre duas datas considerando apenas horário comercial
    
    Args:
        inicio: Data/hora de início
        fim: Data/hora de fim
        config_horario: Configurações de horário comercial
    
    Returns:
        Número de horas úteis como float
    """
    if config_horario is None:
        config_horario = carregar_configuracoes_horario_comercial()
    
    # Garantir que as datas estão no timezone correto
    if inicio.tzinfo is None:
        inicio = BRAZIL_TZ.localize(inicio)
    elif inicio.tzinfo != BRAZIL_TZ:
        inicio = inicio.astimezone(BRAZIL_TZ)
    
    if fim.tzinfo is None:
        fim = BRAZIL_TZ.localize(fim)
    elif fim.tzinfo != BRAZIL_TZ:
        fim = fim.astimezone(BRAZIL_TZ)
    
    if inicio >= fim:
        return 0.0
    
    horas_uteis = 0.0
    data_atual = inicio.replace(hour=0, minute=0, second=0, microsecond=0)
    
    while data_atual.date() <= fim.date():
        # Pular fins de semana e feriados
        if data_atual.weekday() not in config_horario['dias_semana']:
            data_atual += timedelta(days=1)
            continue
        
        # Definir início e fim do horário comercial para este dia
        inicio_comercial = data_atual.replace(
            hour=config_horario['inicio'].hour,
            minute=config_horario['inicio'].minute
        )
        fim_comercial = data_atual.replace(
            hour=config_horario['fim'].hour,
            minute=config_horario['fim'].minute
        )
        
        # Ajustar para o período efetivo
        periodo_inicio = max(inicio, inicio_comercial)
        periodo_fim = min(fim, fim_comercial)
        
        if periodo_inicio < periodo_fim:
            delta = periodo_fim - periodo_inicio
            horas_uteis += delta.total_seconds() / 3600
        
        data_atual += timedelta(days=1)
    
    return round(horas_uteis, 2)

def obter_proximo_horario_comercial(dt: datetime, config_horario: Dict = None) -> datetime:
    """
    Retorna o próximo horário comercial após a data informada
    """
    if config_horario is None:
        config_horario = carregar_configuracoes_horario_comercial()
    
    # Garantir timezone correto
    if dt.tzinfo is None:
        dt = BRAZIL_TZ.localize(dt)
    elif dt.tzinfo != BRAZIL_TZ:
        dt = dt.astimezone(BRAZIL_TZ)
    
    # Se já está em horário comercial, retornar a própria data
    if eh_horario_comercial(dt, config_horario):
        return dt
    
    # Procurar próximo horário comercial
    data_teste = dt
    max_tentativas = 14  # Máximo 2 semanas
    tentativas = 0
    
    while tentativas < max_tentativas:
        # Se é um dia útil mas fora do horário, ir para início do próximo horário comercial
        if data_teste.weekday() in config_horario['dias_semana']:
            inicio_comercial = data_teste.replace(
                hour=config_horario['inicio'].hour,
                minute=config_horario['inicio'].minute,
                second=0,
                microsecond=0
            )
            
            if data_teste.time() < config_horario['inicio']:
                return inicio_comercial
            elif data_teste.time() > config_horario['fim']:
                # Ir para próximo dia útil
                data_teste += timedelta(days=1)
                data_teste = data_teste.replace(
                    hour=config_horario['inicio'].hour,
                    minute=config_horario['inicio'].minute,
                    second=0,
                    microsecond=0
                )
            else:
                return data_teste
        else:
            # Não é dia útil, ir para próximo dia
            data_teste += timedelta(days=1)
            data_teste = data_teste.replace(
                hour=config_horario['inicio'].hour,
                minute=config_horario['inicio'].minute,
                second=0,
                microsecond=0
            )
        
        # Verificar se encontrou um horário comercial
        if eh_horario_comercial(data_teste, config_horario):
            return data_teste
        
        tentativas += 1
    
    # Se não encontrou, retornar segunda-feira mais próxima
    dias_para_segunda = (7 - data_teste.weekday()) % 7
    if dias_para_segunda == 0:
        dias_para_segunda = 7
    
    proxima_segunda = data_teste + timedelta(days=dias_para_segunda)
    return proxima_segunda.replace(
        hour=config_horario['inicio'].hour,
        minute=config_horario['inicio'].minute,
        second=0,
        microsecond=0
    )

def calcular_prazo_sla(data_inicio: datetime, horas_sla: float, config_horario: Dict = None) -> datetime:
    """
    Calcula quando um SLA expira considerando apenas horas comerciais
    
    Args:
        data_inicio: Data/hora de início
        horas_sla: Número de horas do SLA
        config_horario: Configurações de horário comercial
    
    Returns:
        Data/hora quando o SLA expira
    """
    if config_horario is None:
        config_horario = carregar_configuracoes_horario_comercial()
    
    # Garantir timezone correto
    if data_inicio.tzinfo is None:
        data_inicio = BRAZIL_TZ.localize(data_inicio)
    elif data_inicio.tzinfo != BRAZIL_TZ:
        data_inicio = data_inicio.astimezone(BRAZIL_TZ)
    
    # Se não está em horário comercial, mover para próximo horário comercial
    if not eh_horario_comercial(data_inicio, config_horario):
        data_inicio = obter_proximo_horario_comercial(data_inicio, config_horario)
    
    horas_restantes = horas_sla
    data_atual = data_inicio
    
    while horas_restantes > 0:
        # Se não é horário comercial, pular para próximo
        if not eh_horario_comercial(data_atual, config_horario):
            data_atual = obter_proximo_horario_comercial(data_atual, config_horario)
            continue
        
        # Calcular quantas horas restam no dia comercial atual
        fim_comercial_hoje = data_atual.replace(
            hour=config_horario['fim'].hour,
            minute=config_horario['fim'].minute,
            second=0,
            microsecond=0
        )
        
        horas_disponiveis_hoje = (fim_comercial_hoje - data_atual).total_seconds() / 3600
        
        if horas_restantes <= horas_disponiveis_hoje:
            # SLA expira hoje
            return data_atual + timedelta(hours=horas_restantes)
        else:
            # Descontar horas de hoje e ir para próximo dia útil
            horas_restantes -= horas_disponiveis_hoje
            data_atual += timedelta(days=1)
            data_atual = obter_proximo_horario_comercial(data_atual, config_horario)
    
    return data_atual

def calcular_sla_chamado_correto(chamado, config_sla: Dict = None, config_horario: Dict = None) -> Dict:
    """
    Calcula informações corretas de SLA para um chamado considerando horário comercial
    
    Args:
        chamado: Objeto do chamado
        config_sla: Configurações de SLA
        config_horario: Configurações de horário comercial
    
    Returns:
        Dicionário com informações detalhadas de SLA
    """
    if config_sla is None:
        config_sla = carregar_configuracoes_sla()
    
    if config_horario is None:
        config_horario = carregar_configuracoes_horario_comercial()
    
    agora_brazil = get_brazil_time()
    
    # Se não tem data de abertura, retornar valores padrão
    if not chamado.data_abertura:
        return {
            'horas_decorridas': 0,
            'horas_uteis_decorridas': 0,
            'tempo_primeira_resposta': None,
            'tempo_primeira_resposta_uteis': None,
            'tempo_resolucao': None,
            'tempo_resolucao_uteis': None,
            'sla_limite': config_sla.get('resolucao_normal', 24),
            'sla_prazo_expiracao': None,
            'sla_status': 'Indefinido',
            'violacao_primeira_resposta': False,
            'violacao_resolucao': False,
            'prioridade': getattr(chamado, 'prioridade', 'Normal'),
            'percentual_tempo_usado': 0
        }
    
    # Obter data de abertura no timezone do Brasil
    data_abertura_brazil = chamado.get_data_abertura_brazil()
    if not data_abertura_brazil:
        if chamado.data_abertura.tzinfo is None:
            data_abertura_brazil = BRAZIL_TZ.localize(chamado.data_abertura)
        else:
            data_abertura_brazil = chamado.data_abertura.astimezone(BRAZIL_TZ)
    
    # Determinar prioridade e SLA correspondente
    prioridade = getattr(chamado, 'prioridade', 'Normal')
    sla_map = {
        'Crítica': config_sla.get('resolucao_critica', 2),
        'Urgente': config_sla.get('resolucao_urgente', 2),
        'Alta': config_sla.get('resolucao_alta', 8),
        'Normal': config_sla.get('resolucao_normal', 24),
        'Baixa': config_sla.get('resolucao_baixa', 72)
    }
    sla_limite = sla_map.get(prioridade, config_sla.get('resolucao_normal', 24))
    
    # Calcular prazo de expiração do SLA
    sla_prazo_expiracao = calcular_prazo_sla(data_abertura_brazil, sla_limite, config_horario)
    
    # Calcular tempo decorrido (total e útil)
    # Para chamados concluídos, usar data de conclusão; para abertos, usar data atual
    if chamado.status in ['Concluido', 'Cancelado'] and chamado.data_conclusao:
        data_conclusao_brazil = chamado.get_data_conclusao_brazil()
        if not data_conclusao_brazil:
            if chamado.data_conclusao.tzinfo is None:
                data_conclusao_brazil = BRAZIL_TZ.localize(chamado.data_conclusao)
            else:
                data_conclusao_brazil = chamado.data_conclusao.astimezone(BRAZIL_TZ)
        data_fim_calculo = data_conclusao_brazil
    else:
        data_fim_calculo = agora_brazil

    tempo_decorrido = data_fim_calculo - data_abertura_brazil
    horas_decorridas = tempo_decorrido.total_seconds() / 3600
    horas_uteis_decorridas = calcular_horas_uteis(data_abertura_brazil, data_fim_calculo, config_horario)
    
    # Calcular percentual do tempo SLA usado
    if sla_limite > 0:
        percentual_tempo_usado = (horas_uteis_decorridas / sla_limite) * 100
    else:
        percentual_tempo_usado = 0
    
    # Calcular tempo de primeira resposta
    tempo_primeira_resposta = None
    tempo_primeira_resposta_uteis = None
    violacao_primeira_resposta = False
    
    data_primeira_resposta = None
    if chamado.data_primeira_resposta:
        data_primeira_resposta = chamado.get_data_primeira_resposta_brazil()
        if not data_primeira_resposta:
            if chamado.data_primeira_resposta.tzinfo is None:
                data_primeira_resposta = BRAZIL_TZ.localize(chamado.data_primeira_resposta)
            else:
                data_primeira_resposta = chamado.data_primeira_resposta.astimezone(BRAZIL_TZ)
        
        tempo_primeira_resposta_delta = data_primeira_resposta - data_abertura_brazil
        tempo_primeira_resposta = tempo_primeira_resposta_delta.total_seconds() / 3600
        tempo_primeira_resposta_uteis = calcular_horas_uteis(data_abertura_brazil, data_primeira_resposta, config_horario)
        
        limite_primeira_resposta = config_sla.get('primeira_resposta', 4)
        violacao_primeira_resposta = tempo_primeira_resposta_uteis > limite_primeira_resposta
        
    elif chamado.status != 'Aberto':
        # Se mudou de status mas não tem data_primeira_resposta, assumir agora
        tempo_primeira_resposta = horas_decorridas
        tempo_primeira_resposta_uteis = horas_uteis_decorridas
        
        limite_primeira_resposta = config_sla.get('primeira_resposta', 4)
        violacao_primeira_resposta = tempo_primeira_resposta_uteis > limite_primeira_resposta
    else:
        # Ainda está aberto, verificar se já passou do limite de primeira resposta
        limite_primeira_resposta = config_sla.get('primeira_resposta', 4)
        violacao_primeira_resposta = horas_uteis_decorridas > limite_primeira_resposta
    
    # Calcular tempo de resolução
    tempo_resolucao = None
    tempo_resolucao_uteis = None
    violacao_resolucao = False
    
    if chamado.status in ['Concluido', 'Cancelado']:
        data_conclusao = None
        if chamado.data_conclusao:
            data_conclusao = chamado.get_data_conclusao_brazil()
            if not data_conclusao:
                if chamado.data_conclusao.tzinfo is None:
                    data_conclusao = BRAZIL_TZ.localize(chamado.data_conclusao)
                else:
                    data_conclusao = chamado.data_conclusao.astimezone(BRAZIL_TZ)
            
            tempo_resolucao_delta = data_conclusao - data_abertura_brazil
            tempo_resolucao = tempo_resolucao_delta.total_seconds() / 3600
            tempo_resolucao_uteis = calcular_horas_uteis(data_abertura_brazil, data_conclusao, config_horario)
        else:
            tempo_resolucao = horas_decorridas
            tempo_resolucao_uteis = horas_uteis_decorridas
        
        violacao_resolucao = tempo_resolucao_uteis > sla_limite
    else:
        # Chamado ainda não resolvido
        violacao_resolucao = horas_uteis_decorridas > sla_limite
    
    # Determinar status do SLA
    if chamado.status in ['Concluido', 'Cancelado']:
        if violacao_resolucao:
            sla_status = 'Violado'
        else:
            sla_status = 'Cumprido'
    else:
        if violacao_resolucao:
            sla_status = 'Violado'
        elif percentual_tempo_usado >= 80:
            sla_status = 'Em Risco'
        else:
            sla_status = 'Dentro do Prazo'
    
    return {
        'horas_decorridas': round(horas_decorridas, 2),
        'horas_uteis_decorridas': round(horas_uteis_decorridas, 2),
        'tempo_primeira_resposta': round(tempo_primeira_resposta, 2) if tempo_primeira_resposta else None,
        'tempo_primeira_resposta_uteis': round(tempo_primeira_resposta_uteis, 2) if tempo_primeira_resposta_uteis else None,
        'tempo_resolucao': round(tempo_resolucao, 2) if tempo_resolucao else None,
        'tempo_resolucao_uteis': round(tempo_resolucao_uteis, 2) if tempo_resolucao_uteis else None,
        'sla_limite': sla_limite,
        'sla_prazo_expiracao': sla_prazo_expiracao.strftime('%d/%m/%Y %H:%M:%S') if sla_prazo_expiracao else None,
        'sla_status': sla_status,
        'violacao_primeira_resposta': violacao_primeira_resposta,
        'violacao_resolucao': violacao_resolucao,
        'prioridade': prioridade,
        'percentual_tempo_usado': round(percentual_tempo_usado, 1)
    }

def obter_metricas_sla_consolidadas(period_days: int = 30) -> Dict:
    """
    Obtém métricas consolidadas de SLA para o período especificado
    
    Args:
        period_days: Número de dias para análise
    
    Returns:
        Dicionário com métricas consolidadas
    """
    from database import Chamado
    from sqlalchemy import func, and_
    
    config_sla = carregar_configuracoes_sla()
    config_horario = carregar_configuracoes_horario_comercial()
    
    # Data de corte
    data_corte = get_brazil_time() - timedelta(days=period_days)
    
    # Buscar chamados do período
    chamados = Chamado.query.filter(
        Chamado.data_abertura >= data_corte.replace(tzinfo=None)
    ).all()
    
    total_chamados = len(chamados)
    chamados_cumpridos = 0
    chamados_violados = 0
    chamados_em_risco = 0
    chamados_abertos = 0

    tempo_total_resolucao = 0
    tempo_total_primeira_resposta = 0
    count_resolvidos = 0
    count_primeira_resposta = 0
    
    for chamado in chamados:
        sla_info = calcular_sla_chamado_correto(chamado, config_sla, config_horario)
        
        if sla_info['sla_status'] == 'Cumprido':
            chamados_cumpridos += 1
        elif sla_info['sla_status'] == 'Violado':
            chamados_violados += 1
        elif sla_info['sla_status'] == 'Em Risco':
            chamados_em_risco += 1
        
        if sla_info['tempo_resolucao_uteis']:
            tempo_total_resolucao += sla_info['tempo_resolucao_uteis']
            count_resolvidos += 1
        
        if sla_info['tempo_primeira_resposta_uteis']:
            tempo_total_primeira_resposta += sla_info['tempo_primeira_resposta_uteis']
            count_primeira_resposta += 1

        # Contar chamados abertos
        if chamado.status in ['Aberto', 'Aguardando']:
            chamados_abertos += 1
    
    # Calcular médias
    tempo_medio_resolucao = (tempo_total_resolucao / count_resolvidos) if count_resolvidos > 0 else 0
    tempo_medio_primeira_resposta = (tempo_total_primeira_resposta / count_primeira_resposta) if count_primeira_resposta > 0 else 0
    
    # Calcular percentual de cumprimento
    if total_chamados > 0:
        percentual_cumprimento = (chamados_cumpridos / total_chamados) * 100
    else:
        percentual_cumprimento = 100
    
    return {
        'total_chamados': total_chamados,
        'chamados_cumpridos': chamados_cumpridos,
        'chamados_violados': chamados_violados,
        'chamados_em_risco': chamados_em_risco,
        'chamados_abertos': chamados_abertos,
        'percentual_cumprimento': round(percentual_cumprimento, 1),
        'tempo_medio_resolucao': round(tempo_medio_resolucao, 2),
        'tempo_medio_primeira_resposta': round(tempo_medio_primeira_resposta, 2),
        'period_days': period_days
    }
