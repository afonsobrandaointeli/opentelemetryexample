import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import time
import os

# Configuração da página
st.set_page_config(
    page_title="Painel de Telemetria - Soma API",
    page_icon="📊",
    layout="wide"
)

# Caminho do banco de dados
DB_PATH = '/workspaces/opentelemetryexample/soma-api/target/soma_logs.db'

# Função para carregar dados
@st.cache_data(ttl=5)
def load_data():
    try:
        if not os.path.exists(DB_PATH):
            return pd.DataFrame(), f"Banco não encontrado: {DB_PATH}"
            
        conn = sqlite3.connect(DB_PATH)
        
        query = """
        SELECT 
            id,
            timestamp,
            operation_type,
            input_a,
            input_b,
            result,
            execution_time_ms,
            trace_id,
            span_id
        FROM operations 
        ORDER BY timestamp DESC
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            return df, "OK"
        else:
            return pd.DataFrame(), "Tabela vazia"
        
    except Exception as e:
        return pd.DataFrame(), f"Erro: {str(e)}"

# Título
st.title("📊 Painel de Telemetria - Soma API")
st.markdown("---")

# Sidebar
st.sidebar.header("⚙️ Controles")
auto_refresh = st.sidebar.checkbox("🔄 Auto-refresh (5s)", value=False)
limit_records = st.sidebar.slider("📊 Registros", 5, 50, 20)

if auto_refresh:
    time.sleep(5)
    st.rerun()

# Carregar dados
df, status = load_data()

# Status do banco
if status != "OK":
    st.error(f"❌ {status}")
    st.stop()

if df.empty:
    st.warning("⚠️ Nenhum dado encontrado!")
    st.stop()

# Filtrar dados
df_filtered = df.head(limit_records)

# Métricas básicas
st.subheader("📈 Métricas")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Operações", len(df))

with col2:
    avg_time = df['execution_time_ms'].mean()
    st.metric("Tempo Médio (ms)", f"{avg_time:.1f}")

with col3:
    st.metric("Maior Resultado", df['result'].max())

with col4:
    st.metric("Traces Únicos", df['trace_id'].nunique())

st.markdown("---")

# Gráficos simples com matplotlib
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("⏱️ Tempo de Execução")
    
    # Gráfico de linha simples
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Usar índice numérico em vez de timestamp para evitar problemas
    x_data = range(len(df_filtered))
    y_data = df_filtered['execution_time_ms'].values
    
    ax.plot(x_data, y_data, marker='o', linewidth=2, markersize=6)
    ax.set_xlabel('Operação (mais recente → mais antiga)')
    ax.set_ylabel('Tempo (ms)')
    ax.set_title('Tempo de Execução por Operação')
    ax.grid(True, alpha=0.3)
    
    # Adicionar valores nos pontos
    for i, v in enumerate(y_data):
        ax.annotate(f'{v}ms', (i, v), textcoords="offset points", xytext=(0,10), ha='center')
    
    st.pyplot(fig)
    plt.close()

with col_right:
    st.subheader("📈 Distribuição dos Resultados")
    
    # Histograma simples
    fig, ax = plt.subplots(figsize=(10, 6))
    
    results = df_filtered['result'].values
    ax.hist(results, bins=min(10, len(set(results))), alpha=0.7, color='skyblue', edgecolor='black')
    ax.set_xlabel('Resultado da Soma')
    ax.set_ylabel('Frequência')
    ax.set_title('Distribuição dos Resultados')
    ax.grid(True, alpha=0.3)
    
    st.pyplot(fig)
    plt.close()

# Gráfico de barras - Operações mais lentas
st.subheader("🐌 Top 5 Operações Mais Lentas")

top_slow = df.nlargest(5, 'execution_time_ms')

fig, ax = plt.subplots(figsize=(12, 6))

# Criar labels para as operações
labels = [f"{row['input_a']}+{row['input_b']}={row['result']}" for _, row in top_slow.iterrows()]
times = top_slow['execution_time_ms'].values

bars = ax.bar(range(len(labels)), times, color='lightcoral', alpha=0.8)
ax.set_xlabel('Operações')
ax.set_ylabel('Tempo (ms)')
ax.set_title('Top 5 Operações Mais Lentas')
ax.set_xticks(range(len(labels)))
ax.set_xticklabels(labels, rotation=45)

# Adicionar valores nas barras
for bar, time_val in zip(bars, times):
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
            f'{time_val}ms', ha='center', va='bottom')

plt.tight_layout()
st.pyplot(fig)
plt.close()

# Tabela de dados
st.subheader("📋 Dados Recentes")

# Preparar dados para exibição
display_df = df_filtered.copy()
display_df['Horário'] = display_df['timestamp'].dt.strftime('%H:%M:%S')
display_df['A'] = display_df['input_a']
display_df['B'] = display_df['input_b']
display_df['Resultado'] = display_df['result']
display_df['Tempo (ms)'] = display_df['execution_time_ms']
display_df['Trace ID'] = display_df['trace_id'].str[:8] + "..."

# Mostrar apenas colunas relevantes
columns_to_show = ['Horário', 'A', 'B', 'Resultado', 'Tempo (ms)', 'Trace ID']
st.dataframe(display_df[columns_to_show], use_container_width=True)

# Estatísticas detalhadas
st.subheader("📊 Estatísticas Detalhadas")

col_stats1, col_stats2, col_stats3 = st.columns(3)

with col_stats1:
    st.write("**Tempo de Execução:**")
    st.write(f"• Mínimo: {df['execution_time_ms'].min()} ms")
    st.write(f"• Máximo: {df['execution_time_ms'].max()} ms")
    st.write(f"• Mediana: {df['execution_time_ms'].median()} ms")
    st.write(f"• Desvio Padrão: {df['execution_time_ms'].std():.2f} ms")

with col_stats2:
    st.write("**Resultados:**")
    st.write(f"• Menor: {df['result'].min()}")
    st.write(f"• Maior: {df['result'].max()}")
    st.write(f"• Média: {df['result'].mean():.1f}")
    st.write(f"• Mediana: {df['result'].median()}")

with col_stats3:
    st.write("**Operações:**")
    st.write(f"• Total: {len(df)}")
    st.write(f"• Traces únicos: {df['trace_id'].nunique()}")
    
    if len(df) > 0:
        first_op = df['timestamp'].min()
        last_op = df['timestamp'].max()
        st.write(f"• Primeira: {first_op.strftime('%H:%M:%S')}")
        st.write(f"• Última: {last_op.strftime('%H:%M:%S')}")

# Informações de debug na sidebar
st.sidebar.markdown("---")
st.sidebar.subheader("🔍 Debug")
st.sidebar.write(f"**Registros carregados:** {len(df)}")
st.sidebar.write(f"**Banco existe:** {os.path.exists(DB_PATH)}")
st.sidebar.write(f"**Última atualização:** {datetime.now().strftime('%H:%M:%S')}")

# Botão de refresh manual
if st.sidebar.button("🔄 Atualizar Agora"):
    st.cache_data.clear()
    st.rerun()

# Rodapé
st.markdown("---")
st.info(f"📊 Painel atualizado em: {datetime.now().strftime('%H:%M:%S')}")
