"""Limpa a fila de queries do RabbitMQ."""
import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

from src.lib.queue import get_rabbitmq_channel
from colorama import init, Fore

init(autoreset=True)

def main():
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.CYAN}{'Limpando Fila RabbitMQ'.center(80)}")
    print(f"{Fore.CYAN}{'='*80}\n")

    try:
        channel = get_rabbitmq_channel()

        # Purge queue
        result = channel.queue_purge('queries')

        print(f"{Fore.GREEN}✓ Fila 'queries' limpa com sucesso!")
        print(f"{Fore.YELLOW}  Mensagens removidas: {result}")

        channel.close()
        print(f"\n{Fore.CYAN}{'='*80}\n")

    except Exception as e:
        print(f"{Fore.RED}✗ Erro ao limpar fila: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
