"""
RagFlow - Interface Streamlit para Q&A sobre Reviews da Olist

Aplicação web para fazer perguntas sobre reviews de e-commerce
e receber respostas geradas por IA com evidências de suporte.
"""

import streamlit as st
import requests
import time
from datetime import datetime
from typing import Dict, List, Optional

# Configuração da página
st.set_page_config(
    page_title="RagFlow - Q&A sobre Reviews Olist",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configurações da API
API_BASE_URL = st.sidebar.text_input(
    "URL da API",
    value="http://localhost:8000",
    help="URL base da API FastAPI"
)

# Estilo customizado
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .query-box {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .answer-box {
        background-color: #e8f4f8;
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
        border-left: 4px solid #1f77b4;
    }
    .confidence-high {
        color: #28a745;
        font-weight: bold;
    }
    .confidence-medium {
        color: #ffc107;
        font-weight: bold;
    }
    .confidence-low {
        color: #dc3545;
        font-weight: bold;
    }
    .source-box {
        background-color: #fff3cd;
        padding: 0.8rem;
        border-radius: 0.3rem;
        margin: 0.5rem 0;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="main-header">🤖 RagFlow - Q&A sobre Reviews Olist</div>', unsafe_allow_html=True)
st.markdown("Faça perguntas sobre reviews de e-commerce e receba respostas geradas por IA")

# Inicializar session state
if 'query_history' not in st.session_state:
    st.session_state.query_history = []
if 'current_query_id' not in st.session_state:
    st.session_state.current_query_id = None


def check_api_health() -> bool:
    """Verifica se a API está disponível."""
    try:
        response = requests.get(f"{API_BASE_URL}/health/", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def submit_query_async(question: str, collection: str = "olist_reviews", max_chunks: int = 5, confidence_threshold: float = 0.7) -> Optional[Dict]:
    """Submete uma query para a API."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/query/async",
            json={
                "question": question,
                "collection": collection,
                "max_chunks": max_chunks,
                "confidence_threshold": confidence_threshold
            },
            timeout=10
        )

        if response.status_code == 202:
            return response.json()
        else:
            st.error(f"Erro ao enviar query: {response.status_code}")
            return None

    except Exception as e:
        st.error(f"Erro ao conectar com a API: {e}")
        return None


def submit_query_demo(question: str, collection: str = "olist_reviews") -> Optional[Dict]:
    """Submete uma query em modo demo (resposta instantânea)."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/query/demo",
            json={
                "question": question,
                "collection": collection
            },
            timeout=10
        )

        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Erro ao enviar query: {response.status_code}")
            return None

    except Exception as e:
        st.error(f"Erro ao conectar com a API: {e}")
        return None


def get_query_status(query_id: str) -> Optional[Dict]:
    """Obtém o status e resultado de uma query."""
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
        st.error(f"Erro ao consultar status: {e}")
        return None


def wait_for_answer(query_id: str, max_wait: int = 60, poll_interval: int = 2) -> Optional[Dict]:
    """Aguarda a resposta da query com polling."""
    start_time = time.time()
    progress_bar = st.progress(0, text="Processando sua pergunta...")
    status_text = st.empty()

    while time.time() - start_time < max_wait:
        result = get_query_status(query_id)

        if result:
            status = result.get('status')

            if status == 'completed':
                progress_bar.progress(100, text="✅ Resposta pronta!")
                time.sleep(0.5)
                progress_bar.empty()
                status_text.empty()
                return result
            elif status == 'failed':
                progress_bar.empty()
                status_text.empty()
                st.error("❌ Falha ao processar a query")
                return None
            else:
                # Atualizar progresso
                elapsed = int(time.time() - start_time)
                progress = min(int((elapsed / max_wait) * 100), 90)
                progress_bar.progress(progress, text=f"🔄 Processando... ({elapsed}s)")
                status_text.info(f"Status: {status}")

        time.sleep(poll_interval)

    progress_bar.empty()
    status_text.empty()
    st.warning("⏱️ Timeout: A query está demorando mais do que o esperado. Tente novamente mais tarde.")
    return None


def get_confidence_class(confidence: float) -> str:
    """Retorna a classe CSS baseada no score de confiança."""
    if confidence >= 0.8:
        return "confidence-high"
    elif confidence >= 0.6:
        return "confidence-medium"
    else:
        return "confidence-low"


def get_confidence_emoji(confidence: float) -> str:
    """Retorna emoji baseado no score de confiança."""
    if confidence >= 0.8:
        return "✅"
    elif confidence >= 0.6:
        return "⚠️"
    else:
        return "❌"


def display_answer(result: Dict):
    """Exibe a resposta de forma formatada."""
    st.markdown('<div class="answer-box">', unsafe_allow_html=True)

    # Pergunta
    st.markdown(f"**❓ Pergunta:** {result['question']}")
    st.markdown("---")

    # Resposta
    if result.get('answer'):
        st.markdown(f"**💡 Resposta:**")
        st.markdown(result['answer'])

        # Score de confiança
        if result.get('confidence_score') is not None:
            confidence = result['confidence_score']
            confidence_class = get_confidence_class(confidence)
            confidence_emoji = get_confidence_emoji(confidence)

            st.markdown(f"""
            **{confidence_emoji} Confiança:**
            <span class="{confidence_class}">{confidence:.1%}</span>
            """, unsafe_allow_html=True)

            # Barra de progresso visual
            st.progress(confidence)

        # Fontes/Chunks
        if result.get('sources'):
            st.markdown("---")
            st.markdown(f"**📚 Fontes ({len(result['sources'])} chunks):**")

            for idx, source in enumerate(result['sources'][:3], 1):
                similarity = source.get('similarity_score', 0)
                st.markdown(
                    f'<div class="source-box">'
                    f'📄 Fonte {idx} - Similaridade: {similarity:.1%}<br>'
                    f'<small>Chunk ID: {source.get("chunk_id", "N/A")[:8]}...</small>'
                    f'</div>',
                    unsafe_allow_html=True
                )
    else:
        st.warning("⏳ Resposta ainda não está disponível")

    # Metadados
    with st.expander("ℹ️ Informações da Query"):
        st.json({
            "Query ID": result.get('query_id'),
            "Status": result.get('status'),
            "Criado em": result.get('created_at'),
            "Completado em": result.get('completed_at')
        })

    st.markdown('</div>', unsafe_allow_html=True)


def display_statistics():
    """Exibe estatísticas do sistema."""
    try:
        response = requests.get(f"{API_BASE_URL}/health/metrics", timeout=5)
        if response.status_code == 200:
            metrics = response.json()

            col1, col2, col3, col4 = st.columns(4)

            db_metrics = metrics.get('database', {})

            with col1:
                st.metric(
                    "📄 Documentos",
                    db_metrics.get('total_documents', 0)
                )

            with col2:
                st.metric(
                    "📝 Chunks",
                    db_metrics.get('total_chunks', 0)
                )

            with col3:
                st.metric(
                    "❓ Queries Total",
                    db_metrics.get('total_queries', 0)
                )

            with col4:
                st.metric(
                    "📚 Coleções",
                    db_metrics.get('total_collections', 0)
                )
    except Exception:
        pass


# Sidebar - Informações e configurações
with st.sidebar:
    st.header("⚙️ Configurações")

    # Status da API
    api_status = check_api_health()
    if api_status:
        st.success("✅ API Online")
    else:
        st.error("❌ API Offline")
        st.info(f"Certifique-se que a API está rodando em {API_BASE_URL}")

    st.markdown("---")

    # Modo de processamento
    processing_mode = st.radio(
        "Modo de Processamento",
        ["⚡ Rápido (Demo)", "🔍 Completo (RAG Real)"],
        help="Modo Rápido: resposta instantânea com dados simulados\nModo Completo: processamento RAG completo (~1min)"
    )

    use_demo_mode = processing_mode.startswith("⚡")

    if use_demo_mode:
        st.info("💡 Modo Rápido: Respostas instantâneas baseadas em padrões comuns")
    else:
        st.warning("⏱️ Modo Completo: Processamento pode levar até 1 minuto")

    st.markdown("---")

    # Coleção
    collection = st.selectbox(
        "Coleção",
        ["olist_reviews"],
        help="Selecione a coleção de documentos"
    )

    # Configurações avançadas
    with st.expander("🔧 Configurações Avançadas"):
        max_chunks = st.slider(
            "Máximo de chunks",
            min_value=1,
            max_value=10,
            value=5,
            help="Número máximo de chunks a recuperar"
        )

        confidence_threshold = st.slider(
            "Limiar de confiança",
            min_value=0.0,
            max_value=1.0,
            value=0.7,
            step=0.05,
            help="Limiar mínimo de confiança"
        )

        max_wait_time = st.slider(
            "Tempo máximo de espera (s)",
            min_value=10,
            max_value=120,
            value=60,
            step=10,
            help="Tempo máximo para aguardar resposta"
        )

    st.markdown("---")
    st.markdown("### 📊 Estatísticas")
    if api_status:
        display_statistics()

    st.markdown("---")
    st.markdown("### ℹ️ Sobre")
    st.markdown("""
    **RagFlow** é um sistema RAG que permite fazer perguntas sobre reviews
    de e-commerce e receber respostas geradas por IA.

    🔗 [GitHub](https://github.com/mfnogueira/ragflow.git)
    """)


# Interface principal
st.markdown("### 💬 Faça sua pergunta")

# Exemplos de perguntas
with st.expander("💡 Exemplos de perguntas"):
    example_queries = [
        "Quais são os principais motivos de avaliações negativas?",
        "O que os clientes mais elogiam nos produtos?",
        "Quais categorias de produtos têm melhores avaliações?",
        "Quais são as principais reclamações sobre entrega?",
        "O que os clientes falam sobre a qualidade dos produtos?"
    ]

    for query in example_queries:
        if st.button(f"📌 {query}", key=f"example_{hash(query)}", use_container_width=True):
            st.session_state.question_input = query

# Campo de entrada
question = st.text_area(
    "Digite sua pergunta:",
    height=100,
    placeholder="Ex: Quais são os principais problemas relatados pelos clientes?",
    value=st.session_state.get('question_input', ''),
    key="question_area"
)

# Botão de envio
col1, col2 = st.columns([1, 4])
with col1:
    submit_button = st.button("🚀 Enviar Pergunta", type="primary", disabled=not api_status)

if submit_button and question.strip():
    # Limpar input
    if 'question_input' in st.session_state:
        del st.session_state.question_input

    st.markdown("---")

    # Salvar pergunta no session state
    st.session_state.current_question = question

    if use_demo_mode:
        # Modo Demo - Resposta instantânea
        with st.spinner("Gerando resposta..."):
            result = submit_query_demo(question, collection)

        if result:
            # Exibir resposta
            display_answer(result)

            # Adicionar ao histórico
            st.session_state.query_history.insert(0, {
                'timestamp': datetime.now(),
                'question': question,
                'result': result
            })
    else:
        # Modo Completo - Processamento assíncrono
        with st.spinner("Enviando pergunta..."):
            response = submit_query_async(
                question,
                collection,
                max_chunks=max_chunks,
                confidence_threshold=confidence_threshold
            )

        if response:
            query_id = response.get('query_id')
            st.info(f"✅ Query submetida! ID: `{query_id}`")

            # Aguardar resposta
            result = wait_for_answer(query_id, max_wait=max_wait_time)

            if result:
                # Exibir resposta
                display_answer(result)

                # Adicionar ao histórico
                st.session_state.query_history.insert(0, {
                    'timestamp': datetime.now(),
                    'question': question,
                    'result': result
                })

# Histórico
if st.session_state.query_history:
    st.markdown("---")
    st.markdown("### 📜 Histórico de Perguntas")

    for idx, item in enumerate(st.session_state.query_history[:5]):
        with st.expander(f"🕐 {item['timestamp'].strftime('%H:%M:%S')} - {item['question'][:60]}..."):
            display_answer(item['result'])

    if len(st.session_state.query_history) > 5:
        st.info(f"Mostrando 5 de {len(st.session_state.query_history)} perguntas")

    # Botão para limpar histórico
    if st.button("🗑️ Limpar Histórico"):
        st.session_state.query_history = []
        st.rerun()

# Footer
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #888; font-size: 0.9rem;">
        Desenvolvido com ❤️ usando Python, FastAPI, OpenAI e Streamlit<br>
        <a href="https://github.com/mfnogueira/ragflow.git" target="_blank">⭐ Dê uma estrela no GitHub!</a>
    </div>
    """,
    unsafe_allow_html=True
)
