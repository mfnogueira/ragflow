"""
Script para verificar o status das queries no banco de dados.
"""

import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

from src.lib.database import get_db
from src.repositories.query_repo import QueryRepository
from sqlalchemy import text
from colorama import init, Fore

init(autoreset=True)

def main():
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.CYAN}{'Status das Queries no Banco de Dados'.center(80)}")
    print(f"{Fore.CYAN}{'='*80}\n")

    db = next(get_db())

    # Verificar queries recentes
    result = db.execute(text("""
        SELECT id, query_text, status, submitted_at, completed_at
        FROM queries
        ORDER BY submitted_at DESC
        LIMIT 15
    """))

    queries = result.fetchall()

    if not queries:
        print(f"{Fore.YELLOW}Nenhuma query encontrada no banco de dados.\n")
        return

    print(f"{Fore.GREEN}Total de queries recentes: {len(queries)}\n")

    # Contar por status
    from collections import Counter
    status_count = Counter([q[2] for q in queries])

    print(f"{Fore.CYAN}Status das Queries:")
    for status, count in status_count.items():
        color = Fore.GREEN if status == 'completed' else Fore.YELLOW if status == 'pending' else Fore.RED
        print(f"  {color}{status:12} : {count}")

    print(f"\n{Fore.CYAN}{'-'*80}")
    print(f"{Fore.CYAN}Detalhes das Queries:\n")

    for idx, q in enumerate(queries, 1):
        query_id, query_text, status, submitted_at, completed_at = q

        # Cor baseada no status
        if status == 'completed':
            color = Fore.GREEN
            emoji = "✅"
        elif status == 'processing':
            color = Fore.YELLOW
            emoji = "🔄"
        elif status == 'failed':
            color = Fore.RED
            emoji = "❌"
        else:
            color = Fore.BLUE
            emoji = "⏳"

        print(f"{color}[{idx:2d}] {emoji} {query_id[:8]}... | {status:12}")
        print(f"     Pergunta: {query_text[:70]}...")
        print(f"     Enviado: {submitted_at} | Completado: {completed_at}")

        # Verificar se tem resposta
        if status == 'completed':
            answer_result = db.execute(text("""
                SELECT answer_text, confidence_score, model_name
                FROM answers
                WHERE query_id = :query_id
                LIMIT 1
            """), {"query_id": query_id})

            answer = answer_result.fetchone()
            if answer:
                answer_text, confidence, model = answer
                print(f"     Resposta: {answer_text[:70]}...")
                print(f"     Confiança: {confidence:.1%} | Modelo: {model}")

        print()

    print(f"{Fore.CYAN}{'='*80}\n")

    db.close()

if __name__ == "__main__":
    main()
