#!/usr/bin/env python3
"""
Script de debug para analisar violações de SLA
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

from app import app
from database import db, Chamado, HistoricoSLA
from setores.ti.sla_utils import calcular_sla_chamado_correto, carregar_configuracoes_sla, carregar_configuracoes_horario_comercial

def debug_sla_violations():
    """Analisa violações de SLA em detalhes"""
    with app.app_context():
        try:
            print("🔍 ANÁLISE DETALHADA DE VIOLAÇÕES SLA")
            print("=" * 50)
            
            # Carregar configurações
            config_sla = carregar_configuracoes_sla()
            config_horario = carregar_configuracoes_horario_comercial()
            
            print(f"📋 Configurações SLA: {config_sla}")
            print(f"⏰ Horário comercial: {config_horario}")
            print()
            
            # Buscar chamados concluídos/cancelados
            chamados_finalizados = Chamado.query.filter(
                Chamado.status.in_(['Concluido', 'Cancelado'])
            ).order_by(Chamado.data_abertura.desc()).limit(20).all()
            
            print(f"📊 Analisando {len(chamados_finalizados)} chamados finalizados...")
            print()
            
            violacoes_encontradas = 0
            cumprimentos_encontrados = 0
            sem_data_conclusao = 0
            
            for chamado in chamados_finalizados:
                sla_info = calcular_sla_chamado_correto(chamado, config_sla, config_horario)
                
                # Verificar se tem data de conclusão
                if not chamado.data_conclusao:
                    sem_data_conclusao += 1
                    print(f"❌ Chamado {chamado.codigo}: SEM DATA DE CONCLUSÃO")
                    print(f"   Status: {chamado.status}, Prioridade: {chamado.prioridade}")
                    print(f"   Data abertura: {chamado.data_abertura}")
                    print()
                    continue
                
                if sla_info['sla_status'] == 'Violado':
                    violacoes_encontradas += 1
                    print(f"🚨 VIOLAÇÃO: Chamado {chamado.codigo}")
                    print(f"   Status: {chamado.status}, Prioridade: {chamado.prioridade}")
                    print(f"   Data abertura: {chamado.data_abertura}")
                    print(f"   Data conclusão: {chamado.data_conclusao}")
                    print(f"   Tempo resolução (úteis): {sla_info['horas_uteis_decorridas']:.2f}h")
                    print(f"   Limite SLA: {sla_info['sla_limite']}h")
                    print(f"   Status SLA: {sla_info['sla_status']}")
                    print()
                elif sla_info['sla_status'] == 'Cumprido':
                    cumprimentos_encontrados += 1
            
            print("📈 RESUMO DA ANÁLISE:")
            print(f"   ✅ Cumprimentos: {cumprimentos_encontrados}")
            print(f"   🚨 Violações: {violacoes_encontradas}")
            print(f"   ❌ Sem data conclusão: {sem_data_conclusao}")
            print()
            
            # Verificar histórico de correções SLA
            historicos = HistoricoSLA.query.order_by(HistoricoSLA.data_criacao.desc()).limit(10).all()
            print(f"📝 Últimas {len(historicos)} correções no histórico SLA:")
            for hist in historicos:
                print(f"   {hist.data_criacao.strftime('%d/%m/%Y %H:%M')} - Chamado {hist.chamado_id} - {hist.acao}")
            
            if violacoes_encontradas > 0:
                print("\n⚠️  AINDA EXISTEM VIOLAÇÕES DETECTADAS!")
                print("   Isso pode indicar que:")
                print("   1. Alguns chamados ainda não têm data de conclusão")
                print("   2. Algumas datas de conclusão são posteriores ao limite SLA")
                print("   3. O cache do frontend precisa ser limpo")
            else:
                print("\n🎉 TODAS AS VIOLAÇÕES FORAM CORRIGIDAS!")
                
        except Exception as e:
            print(f"❌ Erro durante an��lise: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    debug_sla_violations()
