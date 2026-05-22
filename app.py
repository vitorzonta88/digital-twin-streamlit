import time
import requests
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_autorefresh import st_autorefresh

st.set_page_config(
    page_title="Monitoramento Temperatura",
    layout="wide"
)

FIREBASE_URL = "https://digitaltwim-default-rtdb.firebaseio.com/.json"

st.title("📊 Monitoramento de Temperatura")

response = requests.get(FIREBASE_URL, timeout=30)

if response.status_code != 200:
    st.error(f"Erro Firebase: {response.status_code}")
    st.stop()

json_data = response.json()

dados = json_data.get("digital_twin", {})

if not dados:
    st.warning("Sem dados")
    st.stop()

# -------------------------
# DATAFRAME BASE
# -------------------------
rows = []

for _, value in dados.items():
    rows.append({
        "timestamp": value.get("timestamp"),
        "ds18b201": value.get("ds18b201"),
        "ds18b202": value.get("ds18b202")
    })

df = pd.DataFrame(rows)

df["timestamp"] = pd.to_datetime(df["timestamp"])

df = df.sort_values("timestamp")

# -------------------------
# MÉTRICAS
# -------------------------
ultimo = df.iloc[-1]

col1, col2, col3 = st.columns(3)
corr = df[["ds18b201", "ds18b202"]].corr().iloc[0,1]

col1.metric("DS18B20 #1", f"{ultimo['ds18b201']:.2f} °C")
col2.metric("DS18B20 #2", f"{ultimo['ds18b202']:.2f} °C")
col3.metric("Correlação S1 vs S2", f"{corr:.2f}"
            )
# -------------------------
# GRÁFICO ORIGINAL (tempo real)
# -------------------------
fig = go.Figure()

fig.add_trace(go.Scatter(
    x=df["timestamp"],
    y=df["ds18b201"],
    mode="lines+markers",
    name="DS18B20 #1"
))

fig.add_trace(go.Scatter(
    x=df["timestamp"],
    y=df["ds18b202"],
    mode="lines+markers",
    name="DS18B20 #2"
))

fig.update_layout(
    title="Temperatura (tempo real)",
    height=450
)

st.plotly_chart(fig, use_container_width=True, key="real_time_chart")

# Média móvel (suaviza ruído)
df["s1_ma"] = df["ds18b201"].rolling(10).mean()
df["s2_ma"] = df["ds18b202"].rolling(10).mean()
fig_ma = go.Figure()

fig_ma.update_layout(
    title="Média Móvel",
    height=350
)
fig_ma.add_trace(go.Scatter(
    x=df["timestamp"],
    y=df["s1_ma"],
    name="S1 média móvel"
))

fig_ma.add_trace(go.Scatter(
    x=df["timestamp"],
    y=df["s2_ma"],
    name="S2 média móvel"
))

st.plotly_chart(fig_ma, use_container_width=True)

# -------------------------
# AGRUPAMENTO POR HORA
# -------------------------
df_hour = df.copy()

df_hour["hora"] = df_hour["timestamp"].dt.floor("h")

df_hour = df_hour.groupby("hora", as_index=False).mean(numeric_only=True)

fig2 = go.Figure()

fig2.add_trace(go.Scatter(
    x=df_hour["hora"],
    y=df_hour["ds18b201"],
    mode="lines+markers",
    name="DS18B20 #1 (média hora)"
))

fig2.add_trace(go.Scatter(
    x=df_hour["hora"],
    y=df_hour["ds18b202"],
    mode="lines+markers",
    name="DS18B20 #2 (média hora)"
))

fig2.update_layout(
    title="Temperatura média por hora",
    height=450
)

st.plotly_chart(fig2, use_container_width=True, key="hour_chart")

# Diferença entre sensores
fig_diff = go.Figure()
df["diff"] = df["ds18b201"] - df["ds18b202"]
fig_diff.add_trace(go.Scatter(
    x=df["timestamp"],
    y=df["diff"],
    mode="lines",
    name="S1 - S2"
))
fig_diff.update_layout(
    title="Diferença entre sensores",
    height=300
)
st.plotly_chart(fig_diff, use_container_width=True)

# Variação
df["var_s1"] = df["ds18b201"].diff()
df["var_s2"] = df["ds18b202"].diff()

fig_var = go.Figure()

fig_var.add_trace(go.Scatter(
    x=df["timestamp"],
    y=df["var_s1"],
    mode="lines",
    name="Variação S1"
))

fig_var.add_trace(go.Scatter(
    x=df["timestamp"],
    y=df["var_s2"],
    mode="lines",
    name="Variação S2"
))

fig_var.update_layout(
    title="Variação de temperatura",
    height=350
)

st.plotly_chart(fig_var, use_container_width=True, key="var_chart")

# picos de variação
threshold = 1.5  # ajuste conforme seu sensor

df["spike_s1"] = df["var_s1"].abs() > threshold
fig_var.add_trace(go.Scatter(
    x=df[df["spike_s1"]]["timestamp"],
    y=df[df["spike_s1"]]["var_s1"],
    mode="markers",
    name="Picos S1",
    marker=dict(size=8)
))

# -------------------------
# TABELA DESCRESCENTE
# -------------------------
st.subheader("Últimos registros")

st.dataframe(
    df.sort_values("timestamp", ascending=False).head(5),
    use_container_width=True
)

st.caption(f"Última atualização: {ultimo['timestamp']}")

# -------------------------
# AUTO REFRESH
# -------------------------
st_autorefresh(interval=5000, key="refresh")