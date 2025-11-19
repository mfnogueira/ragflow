"""
Script de teste para enviar 10 perguntas e monitorar o processamento via RabbitMQ.

Objetivo: Testar o pipeline completo RAG
- API recebe pergunta
- Publica na fila do RabbitMQ
- Worker consome da fila
- LLM busca na base vetorial
- Gera resposta e salva no banco

Uso:
    python scripts/test_10_queries.py
"""

import requests
import time
import json
import sys
from typing import Dict, List, Optional
from datetime import datetime
from colorama import init, Fore, Style

# Fix Windows encoding issues
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

init(autoreset=True)

API_BASE_URL = "http://localhost:8000"
POLL_INTERVAL = 2
MAX_WAIT_TIME = 120

# 10 perguntas de teste em português
TEST_QUESTIONS = [
    "Quais são os principais motivos de avaliações negativas nos reviews?",
    "O que os clientes mais elogiam nos produtos da Olist?",
    "Quais categorias de produtos têm as melhores avaliações?",
    "Quais são as principais reclamações sobre entrega?",
    "O que os clientes falam sobre a qualidade dos produtos?",
    "Existem reclamações sobre o atendimento ao cliente?",
    "Quais são os sentimentos mais comuns nos reviews positivos?",
    "Há menções sobre problemas com embalagem dos produtos?",
    "Os clientes reclamam sobre os prazos de entrega?",
    "Quais aspectos os clientes mais valorizam nas compras?"
]


def print_header(text: str):
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.CYAN}{text.center(80)}")
    print(f"{Fore.CYAN}{'='*80}\n")


def print_info(text: str):
    print(f"{Fore.BLUE}[INFO] {text}")


def print_success(text: str):
    print(f"{Fore.GREEN}[OK] {text}")


def print_error(text: str):
    print(f"{Fore.RED}[ERRO] {text}")


def print_warning(text: str):
    print(f"{Fore.YELLOW}[AVISO] {text}")


def check_api_health() -> bool:
    """Verifica se a API está disponível."""
    try:
        response = requests.get(f"{API_BASE_URL}/health/", timeout=5)
        return response.status_code == 200
    except Exception as e:
        print_error(f"API health check failed: {e}")
        return False


def submit_query(question: str) -> Optional[Dict]:
    """Envia uma pergunta para a API (endpoint async que usa RabbitMQ)."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/query/async",
            json={
                "question": question,
                "collection": "olist_reviews",
                "max_chunks": 5,
                "confidence_threshold": 0.7
            },
            timeout=10
        )

        if response.status_code == 202:
            return response.json()
        else:
            print_error(f"Erro ao enviar query: {response.status_code}")
            print_error(f"Response: {response.text}")
            return None

    except Exception as e:
        print_error(f"Exceção ao enviar query: {e}")
        return None


def get_query_status(query_id: str) -> Optional[Dict]:
    """Consulta o status de uma query."""
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/query/{query_id}",
            timeout=5
        )

        if response.status_code == 200:
            return response.json()
        else:
            return None

    except Exception as e:
        print_error(f"Erro ao consultar status: {e}")
        return None


def wait_for_query(query_id: str, max_wait: int = MAX_WAIT_TIME) -> Optional[Dict]:
    """Aguarda uma query ser processada."""
    start_time = time.time()
    last_status = None

    while time.time() - start_time < max_wait:
        result = get_query_status(query_id)

        if result:
            status = result.get('status')

            if status != last_status:
                elapsed = int(time.time() - start_time)
                print_info(f"[{elapsed}s] Query {query_id[:8]}... -> Status: {status}")
                last_status = status

            if status == 'completed':
                return result
            elif status == 'failed':
                print_error(f"Query {query_id[:8]}... falhou")
                return result

        time.sleep(POLL_INTERVAL)

    print_warning(f"Query {query_id[:8]}... timeout após {max_wait}s")
    return None


def display_result(result: Dict, index: int):
    """Exibe o resultado de uma query."""
    print(f"\n{Fore.MAGENTA}{'-'*80}")
    print(f"{Fore.MAGENTA}RESULTADO #{index + 1}")
    print(f"{Fore.MAGENTA}{'-'*80}")

    print(f"\n{Fore.CYAN}Pergunta: {result.get('question', 'N/A')}")

    status = result.get('status', 'unknown')
    print(f"{Fore.CYAN}Status: ", end="")
    if status == 'completed':
        print(f"{Fore.GREEN}[OK] {status}")
    elif status == 'failed':
        print(f"{Fore.RED}[ERRO] {status}")
    else:
        print(f"{Fore.YELLOW}[PENDENTE] {status}")

    if result.get('answer'):
        print(f"\n{Fore.CYAN}Resposta:")
        for line in result['answer'].split('\n'):
            print(f"   {line}")

        confidence = result.get('confidence_score')
        if confidence is not None:
            print(f"\n{Fore.CYAN}Confianca: ", end="")
            if confidence >= 0.8:
                print(f"{Fore.GREEN}{confidence:.1%}")
            elif confidence >= 0.6:
                print(f"{Fore.YELLOW}{confidence:.1%}")
            else:
                print(f"{Fore.RED}{confidence:.1%}")

        sources = result.get('sources', [])
        if sources:
            print(f"\n{Fore.CYAN}Fontes: {len(sources)} chunks")
            for idx, src in enumerate(sources[:3], 1):
                sim = src.get('similarity_score', 0)
                chunk = src.get('chunk_id', 'N/A')[:8]
                print(f"   {idx}. Chunk {chunk}... -> {sim:.1%}")


def main():
    print_header("TESTE DO PIPELINE RAG - 5 PERGUNTAS")
    print_info("Fluxo: API -> RabbitMQ -> Worker -> Qdrant -> OpenAI -> Database\n")

    # Verifica API
    print_info("Verificando API...")
    if not check_api_health():
        print_error("API offline. Execute: python -m src.main")
        return

    print_success("API online!\n")

    # Envia 5 perguntas
    print_header("ENVIANDO 5 PERGUNTAS PARA A FILA DO RABBITMQ")

    submitted = []
    for idx, question in enumerate(TEST_QUESTIONS, 1):
        print_info(f"[{idx}/5] {question[:60]}...")

        response = submit_query(question)
        if response:
            query_id = response.get('query_id')
            print_success(f"  ✓ Publicado na fila! Query ID: {query_id[:8]}...")
            submitted.append({
                'index': idx - 1,
                'query_id': query_id,
                'question': question
            })
        else:
            print_error(f"  ✗ Falha ao enviar")

        time.sleep(0.3)

    print_success(f"\n{len(submitted)}/5 perguntas enviadas para RabbitMQ!\n")

    if not submitted:
        print_error("Nenhuma query foi enviada. Encerrando.")
        return

    # Aguarda processamento
    print_header("MONITORANDO PROCESSAMENTO DAS QUERIES")
    print_info(f"O Worker deve consumir da fila 'queries' do RabbitMQ")
    print_info(f"Polling a cada {POLL_INTERVAL}s, timeout: {MAX_WAIT_TIME}s\n")

    results = []
    for query_data in submitted:
        idx = query_data['index']
        query_id = query_data['query_id']
        question = query_data['question']

        print_info(f"\n[{idx + 1}/5] Aguardando {query_id[:8]}...")
        result = wait_for_query(query_id)

        if result:
            results.append(result)
            if result.get('status') == 'completed':
                print_success(f"Completada!")

    # Exibe todos os resultados
    print_header("RESULTADOS DETALHADOS")
    for idx, result in enumerate(results):
        display_result(result, idx)

    # Sumário final
    print_header("SUMARIO DO TESTE")

    completed = sum(1 for r in results if r.get('status') == 'completed')
    failed = sum(1 for r in results if r.get('status') == 'failed')
    timeout = len(submitted) - len(results)

    print_info(f"Total enviadas: {len(submitted)}")
    print_success(f"Completadas: {completed}")
    if failed > 0:
        print_error(f"Falhas: {failed}")
    if timeout > 0:
        print_warning(f"Timeout: {timeout}")

    if completed == len(submitted):
        print_success("\nPIPELINE RAG FUNCIONANDO 100%!")
    elif completed > 0:
        print_warning(f"\nApenas {completed}/{len(submitted)} completadas")
        print_info("Verifique:")
        print_info("  1. Worker está rodando? python -m src.workers.query_worker")
        print_info("  2. RabbitMQ está acessível? (CloudAMQP)")
        print_info("  3. Qdrant Cloud está configurado?")
        print_info("  4. OpenAI API key está válida?")
    else:
        print_error("\nNENHUMA QUERY PROCESSADA")
        print_info("Diagnóstico:")
        print_info("  - RabbitMQ não está acessível")
        print_info("  - Query Worker não está rodando")
        print_info("  - Verifique as credenciais no .env")

    print(f"\n{Fore.CYAN}{'='*80}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_warning("\n\nInterrompido pelo usuário")
    except Exception as e:
        print_error(f"\nErro: {e}")
        import traceback
        traceback.print_exc()
