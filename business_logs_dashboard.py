import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import time
import os

# Configuração da página
st.set_page_config(
    page_title="Painel de Logs de Negócio - Soma API",
    page_icon="📈",
    layout="wide"
)

# Caminho do banco de dados
DB_PATH = '/workspaces/opentelemetryexample/soma-api/target/soma_logs.db'

# Função para carregar logs de negócio
@st.cache_data(ttl=5)
def load_business_logs():
    try:
        if not os.path.exists(DB_PATH):
            return pd.DataFrame(), f"Banco não encontrado: {DB_PATH}"
            
        conn = sqlite3.connect(DB_PATH)
        
        query = """
        SELECT 
            id,
            operation_id,
            user_id,
            timestamp,
            hour_of_day,
            day_period,
            operation_type,
            input_values,
            result_value,
            execution_time_ms,
            trace_id,
            ip_address,
            status,
            message
        FROM business_logs 
        ORDER BY timestamp DESC
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            return df, "OK"
        else:
            return pd.DataFrame(), "Tabela business_logs vazia"
        
    except Exception as e:
        return pd.DataFrame(), f"Erro: {str(e)}"

# Função para carregar estatísticas por usuário
@st.cache_data(ttl=5)
def load_user_stats():
    try:
        conn = sqlite3.connect(DB_PATH)
        
        query = """
        SELECT 
            user_id,
            COUNT(*) as total_operations,
            AVG(execution_time_ms) as avg_execution_time,
            SUM(result_value) as total_sum_results,
            MIN(timestamp) as first_operation,
            MAX(timestamp) as last_operation
        FROM business_logs 
        GROUP BY user_id
        ORDER BY total_operations DESC
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        return df
        
    except Exception as e:
        return pd.DataFrame()

# Título principal
st.title("📈 Painel de Logs de Negócio - Soma API")
st.markdown("Análise detalhada das operações por usuário e comportamento de uso")
st.markdown("---")

# Sidebar para controles
st.sidebar.header("⚙️ Controles")
auto_refresh = st.sidebar.checkbox("🔄 Auto-refresh (5s)", value=False)
limit_records = st.sidebar.slider("📊 Registros", 10, 100, 30)

# Filtros
st.sidebar.subheader("🔍 Filtros")
selected_users = st.sidebar.multiselect("Usuários:", options=[], default=[])
selected_periods = st.sidebar.multiselect("Períodos do dia:", 
                                         options=["MORNING", "AFTERNOON", "EVENING", "NIGHT"],
                                         default=["MORNING", "AFTERNOON", "EVENING", "NIGHT"])

if auto_refresh:
    time.sleep(5)
    st.rerun()

# Carregar dados
df_logs, status = load_business_logs()
df_user_stats = load_user_stats()

# Status do banco
if status != "OK":
    st.error(f"❌ {status}")
    st.info("Execute algumas operações na API com parâmetro user_id para gerar logs de negócio:")
    st.code('curl "http://localhost:8080/soma/10/5?user_id=user123"')
    st.stop()

if df_logs.empty:
    st.warning("⚠️ Nenhum log de negócio encontrado!")
    st.stop()

# Atualizar opções de filtro na sidebar
if not df_logs.empty:
    all_users = df_logs['user_id'].unique().tolist()
    selected_users = st.sidebar.multiselect("Usuários:", options=all_users, default=all_users)

# Aplicar filtros
df_filtered = df_logs[
    (df_logs['user_id'].isin(selected_users)) &
    (df_logs['day_period'].isin(selected_periods))
].head(limit_records)

# Métricas principais
st.subheader("📊 Métricas de Negócio")
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    total_operations = len(df_logs)
    st.metric("Total de Operações", total_operations)

with col2:
    unique_users = df_logs['user_id'].nunique()
    st.metric("Usuários Únicos", unique_users)

with col3:
    avg_result = df_logs['result_value'].mean()
    st.metric("Resultado Médio", f"{avg_result:.1f}")

with col4:
    most_active_user = df_logs['user_id'].value_counts().index[0]
    user_operations = df_logs['user_id'].value_counts().iloc[0]
    st.metric("Usuário Mais Ativo", most_active_user, f"{user_operations} ops")

with col5:
    peak_period = df_logs['day_period'].value_counts().index[0]
    period_count = df_logs['day_period'].value_counts().iloc[0]
    st.metric("Período de Pico", peak_period, f"{period_count} ops")

st.markdown("---")

# Tabs principais
tab1, tab2, tab3, tab4 = st.tabs(["📊 Análise por Usuário", "⏰ Análise Temporal", "📋 Logs Detalhados", "📈 Estatísticas"])

with tab1:
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("👥 Operações por Usuário")
        
        # Gráfico de barras - operações por usuário
        user_counts = df_filtered['user_id'].value_counts()
        
        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(range(len(user_counts)), user_counts.values, color='lightblue', alpha=0.8)
        ax.set_xlabel('Usuários')
        ax.set_ylabel('Número de Operações')
        ax.set_title('Operações por Usuário')
        ax.set_xticks(range(len(user_counts)))
        ax.set_xticklabels(user_counts.index, rotation=45)
        
        # Adicionar valores nas barras
        for bar, count in zip(bars, user_counts.values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                    f'{count}', ha='center', va='bottom')
        
        plt.tight_layout()
        st.pyplot(fig)
        plt.close()
        
        # Top usuários
        st.subheader("🏆 Top Usuários")
        for i, (user, count) in enumerate(user_counts.head(5).items(), 1):
            avg_time = df_logs[df_logs['user_id'] == user]['execution_time_ms'].mean()
            st.write(f"{i}. **{user}**: {count} operações (⏱️ {avg_time:.1f}ms médio)")
    
    with col_right:
        st.subheader("⚡ Performance por Usuário")
        
        # Gráfico de tempo médio por usuário
        if not df_user_stats.empty:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            users = df_user_stats['user_id'].values
            avg_times = df_user_stats['avg_execution_time'].values
            
            bars = ax.bar(range(len(users)), avg_times, color='lightcoral', alpha=0.8)
            ax.set_xlabel('Usuários')
            ax.set_ylabel('Tempo Médio (ms)')
            ax.set_title('Tempo Médio de Execução por Usuário')
            ax.set_xticks(range(len(users)))
            ax.set_xticklabels(users, rotation=45)
            
            # Adicionar valores nas barras
            for bar, time_val in zip(bars, avg_times):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                        f'{time_val:.1f}ms', ha='center', va='bottom')
            
            plt.tight_layout()
            st.pyplot(fig)
            plt.close()
        
        # Estatísticas de usuários
        st.subheader("📊 Resumo por Usuário")
        if not df_user_stats.empty:
            display_stats = df_user_stats[['user_id', 'total_operations', 'avg_execution_time', 'total_sum_results']].copy()
            display_stats['avg_execution_time'] = display_stats['avg_execution_time'].round(2)
            display_stats.columns = ['Usuário', 'Operações', 'Tempo Médio (ms)', 'Soma Total']
            st.dataframe(display_stats, use_container_width=True)

with tab2:
    col_time1, col_time2 = st.columns(2)
    
    with col_time1:
        st.subheader("🕐 Distribuição por Hora do Dia")
        
        # Gráfico de distribuição por hora
        hour_counts = df_filtered['hour_of_day'].value_counts().sort_index()
        
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(hour_counts.index, hour_counts.values, marker='o', linewidth=2, markersize=6)
        ax.set_xlabel('Hora do Dia')
        ax.set_ylabel('Número de Operações')
        ax.set_title('Distribuição de Operações por Hora')
        ax.set_xticks(range(0, 24, 2))
        ax.grid(True, alpha=0.3)
        
        # Destacar picos
        max_hour = hour_counts.idxmax()
        max_count = hour_counts.max()
        ax.annotate(f'Pico: {max_count} ops\nàs {max_hour}h', 
                   xy=(max_hour, max_count), 
                   xytext=(max_hour+2, max_count+1),
                   arrowprops=dict(arrowstyle='->', color='red'))
        
        st.pyplot(fig)
        plt.close()
    
    with col_time2:
        st.subheader("🌅 Distribuição por Período do Dia")
        
        # Gráfico de pizza - períodos do dia
        period_counts = df_filtered['day_period'].value_counts()
        
        fig, ax = plt.subplots(figsize=(8, 8))
        colors = ['#FFD700', '#FF6347', '#4169E1', '#2F4F4F']  # Cores para manhã, tarde, noite, madrugada
        wedges, texts, autotexts = ax.pie(period_counts.values, 
                                         labels=period_counts.index, 
                                         autopct='%1.1f%%',
                                         colors=colors,
                                         startangle=90)
        ax.set_title('Distribuição por Período do Dia')
        
        st.pyplot(fig)
        plt.close()
        
        # Estatísticas temporais
        st.subheader("📅 Estatísticas Temporais")
        st.write("**Por Período:**")
        for period, count in period_counts.items():
            percentage = (count / len(df_filtered)) * 100
            st.write(f"• {period}: {count} operações ({percentage:.1f}%)")

with tab3:
    st.subheader("📋 Logs de Negócio Detalhados")
    
    # Preparar dados para exibição
    if not df_filtered.empty:
        display_df = df_filtered.copy()
        display_df['Horário'] = display_df['timestamp'].dt.strftime('%H:%M:%S')
        display_df['Usuário'] = display_df['user_id']
        display_df['Operação'] = display_df['input_values']
        display_df['Resultado'] = display_df['result_value']
        display_df['Tempo (ms)'] = display_df['execution_time_ms']
        display_df['Período'] = display_df['day_period']
        display_df['IP'] = display_df['ip_address']
        display_df['Status'] = display_df['status']
        
        # Mostrar tabela
        columns_to_show = ['Horário', 'Usuário', 'Operação', 'Resultado', 'Tempo (ms)', 'Período', 'IP', 'Status']
        st.dataframe(display_df[columns_to_show], use_container_width=True, height=400)
        
        # Detalhes de log específico
        st.subheader("🔍 Detalhes do Log")
        
        if len(df_filtered) > 0:
            # Seletor de log
            log_options = []
            for _, row in df_filtered.iterrows():
                label = f"{row['user_id']} - {row['input_values']} = {row['result_value']} ({row['timestamp'].strftime('%H:%M:%S')})"
                log_options.append((row['id'], label))
            
            selected_log_id = st.selectbox(
                "Selecione um log:",
                options=[log[0] for log in log_options],
                format_func=lambda x: next(log[1] for log in log_options if log[0] == x)
            )
            
            if selected_log_id:
                selected_log = df_filtered[df_filtered['id'] == selected_log_id].iloc[0]
                
                detail_col1, detail_col2 = st.columns(2)
                
                with detail_col1:
                    st.write(f"**🆔 ID do Log:** {selected_log['id']}")
                    st.write(f"**👤 Usuário:** {selected_log['user_id']}")
                    st.write(f"**📅 Timestamp:** {selected_log['timestamp']}")
                    st.write(f"**🕐 Hora:** {selected_log['hour_of_day']}h")
                    st.write(f"**🌅 Período:** {selected_log['day_period']}")
                    st.write(f"**🔗 Operation ID:** {selected_log['operation_id']}")
                
                with detail_col2:
                    st.write(f"**⚙️ Operação:** {selected_log['input_values']}")
                    st.write(f"**✅ Resultado:** {selected_log['result_value']}")
                    st.write(f"**⏱️ Tempo:** {selected_log['execution_time_ms']} ms")
                    st.write(f"**🌐 IP:** {selected_log['ip_address']}")
                    st.write(f"**✔️ Status:** {selected_log['status']}")
                    st.write(f"**🔍 Trace ID:** `{selected_log['trace_id'][:16]}...`")
                
                st.write(f"**💬 Mensagem:** {selected_log['message']}")

with tab4:
    st.subheader("📈 Estatísticas Avançadas")
    
    col_stat1, col_stat2 = st.columns(2)
    
    with col_stat1:
        st.write("**📊 Resumo Geral:**")
        st.write(f"• Total de logs: {len(df_logs)}")
        st.write(f"• Usuários únicos: {df_logs['user_id'].nunique()}")
        st.write(f"• Período mais ativo: {df_logs['day_period'].value_counts().index[0]}")
        st.write(f"• Resultado médio: {df_logs['result_value'].mean():.2f}")
        st.write(f"• Tempo médio: {df_logs['execution_time_ms'].mean():.2f} ms")
        
        st.write("**⏰ Por Hora:**")
        busiest_hour = df_logs['hour_of_day'].value_counts().index[0]
        busiest_count = df_logs['hour_of_day'].value_counts().iloc[0]
        st.write(f"• Hora mais movimentada: {busiest_hour}h ({busiest_count} operações)")
        
        quietest_hours = df_logs['hour_of_day'].value_counts().tail(3)
        st.write("• Horas mais calmas:")
        for hour, count in quietest_hours.items():
            st.write(f"  - {hour}h: {count} operações")
    
    with col_stat2:
        st.write("**🎯 Análise de Comportamento:**")
        
        # Usuário mais produtivo
        most_productive = df_logs.groupby('user_id')['result_value'].sum().sort_values(ascending=False)
        st.write(f"• Usuário com maior soma total: **{most_productive.index[0]}** ({most_productive.iloc[0]})")
        
        # Usuário mais rápido
        fastest_user = df_logs.groupby('user_id')['execution_time_ms'].mean().sort_values()
        st.write(f"• Usuário mais rápido: **{fastest_user.index[0]}** ({fastest_user.iloc[0]:.1f}ms médio)")
        
        # Análise temporal por usuário
        st.write("**📅 Padrões de Uso:**")
        user_periods = df_logs.groupby(['user_id', 'day_period']).size().unstack(fill_value=0)
        
        for user in user_periods.index[:3]:  # Top 3 usuários
            preferred_period = user_periods.loc[user].idxmax()
            period_count = user_periods.loc[user].max()
            st.write(f"• **{user}**: prefere {preferred_period} ({period_count} ops)")

# Rodapé
st.markdown("---")
footer_col1, footer_col2, footer_col3 = st.columns(3)

with footer_col1:
    st.info(f"📊 Última atualização: {datetime.now().strftime('%H:%M:%S')}")

with footer_col2:
    if st.button("🔄 Atualizar Dados"):
        st.cache_data.clear()
        st.rerun()

with footer_col3:
    if not df_logs.empty:
        st.success(f"✅ {len(df_logs)} logs de negócio carregados")

# Informações na sidebar
st.sidebar.markdown("---")
st.sidebar.subheader("ℹ️ Informações")
st.sidebar.write(f"**Banco:** business_logs")
st.sidebar.write(f"**Registros:** {len(df_logs) if not df_logs.empty else 0}")

if not df_logs.empty:
    first_log = df_logs['timestamp'].min()
    last_log = df_logs['timestamp'].max()
    st.sidebar.write(f"**Primeiro log:** {first_log.strftime('%H:%M:%S')}")
    st.sidebar.write(f"**Último log:** {last_log.strftime('%H:%M:%S')}")