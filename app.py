import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler

st.set_page_config(page_title="B3 IA Analyzer", page_icon="📈", layout="wide")

st.title("📈 B3 IA Analyzer")
st.caption("Análise estatística de ações da B3 — não é recomendação de investimento.")

DEFAULTS = ["PETR4", "VALE3", "ITUB4", "BBAS3", "WEGE3", "B3SA3", "ABEV3"]

def ticker_b3(symbol):
    symbol = symbol.strip().upper()
    return symbol if symbol.endswith(".SA") else symbol + ".SA"

@st.cache_data(ttl=300)
def load_data(symbol, period):
    df = yf.download(ticker_b3(symbol), period=period, interval="1d",
                     auto_adjust=False, progress=False)
    if df.empty:
        return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df.dropna(subset=["Close"])

def features(df):
    x = df.copy()
    close = x["Close"]
    volume = x["Volume"]

    x["ret_1"] = close.pct_change()
    x["ret_5"] = close.pct_change(5)
    x["ret_20"] = close.pct_change(20)
    x["sma_10"] = close.rolling(10).mean()
    x["sma_20"] = close.rolling(20).mean()
    x["sma_50"] = close.rolling(50).mean()
    x["ema_12"] = close.ewm(span=12, adjust=False).mean()
    x["ema_26"] = close.ewm(span=26, adjust=False).mean()

    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    x["rsi"] = 100 - (100 / (1 + rs))

    x["macd"] = x["ema_12"] - x["ema_26"]
    x["macd_signal"] = x["macd"].ewm(span=9, adjust=False).mean()
    x["volatility_20"] = x["ret_1"].rolling(20).std()
    x["volume_ratio"] = volume / volume.rolling(20).mean()

    x["dist_sma20"] = close / x["sma_20"] - 1
    x["dist_sma50"] = close / x["sma_50"] - 1

    # Target: next trading day's close is higher than today's close.
    x["target"] = (close.shift(-1) > close).astype(int)
    return x

FEATURES = [
    "ret_1","ret_5","ret_20","rsi","macd","macd_signal",
    "volatility_20","volume_ratio","dist_sma20","dist_sma50"
]

def train_and_predict(df):
    x = features(df).dropna(subset=FEATURES)
    if len(x) < 150:
        raise ValueError("Poucos dados para treinar o modelo. Use um período maior.")

    train = x.iloc[:-1].copy()
    last = x.iloc[[-1]].copy()

    # Walk-forward-like split: the most recent 20% is held out for a simple validation.
    split = max(100, int(len(train) * 0.8))
    X_train, y_train = train[FEATURES].iloc[:split], train["target"].iloc[:split]
    X_val, y_val = train[FEATURES].iloc[split:], train["target"].iloc[split:]

    model = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("rf", RandomForestClassifier(
            n_estimators=350, max_depth=6, min_samples_leaf=5,
            random_state=42, class_weight="balanced_subsample"
        ))
    ])
    model.fit(X_train, y_train)

    val_acc = float(model.score(X_val, y_val)) if len(X_val) else np.nan
    prob_up = float(model.predict_proba(last[FEATURES])[0][1])
    direction = "ALTA" if prob_up >= 0.5 else "QUEDA"

    # Simple technical context
    row = last.iloc[0]
    trend = "Alta" if row["sma_20"] > row["sma_50"] else "Baixa"
    rsi = float(row["rsi"])
    if rsi >= 70:
        rsi_state = "sobrecomprada"
    elif rsi <= 30:
        rsi_state = "sobrevendida"
    else:
        rsi_state = "neutra"

    return {
        "model": model,
        "prob_up": prob_up,
        "direction": direction,
        "validation_accuracy": val_acc,
        "last_price": float(row["Close"]),
        "trend": trend,
        "rsi": rsi,
        "rsi_state": rsi_state,
        "data": x
    }

with st.sidebar:
    st.header("Configuração")
    symbol = st.selectbox("Ação", DEFAULTS, index=0)
    custom = st.text_input("Ou informe outro ticker", placeholder="Ex.: PETR4")
    if custom.strip():
        symbol = custom.strip().upper()
    period = st.selectbox("Histórico", ["2y", "5y", "10y"], index=1)
    analyze = st.button("🔎 Analisar", use_container_width=True)

if analyze or "result" not in st.session_state:
    with st.spinner("Baixando dados e treinando o modelo..."):
        try:
            df = load_data(symbol, period)
            if df.empty:
                st.error("Não foi possível encontrar dados para esse ticker.")
                st.stop()
            st.session_state.result = train_and_predict(df)
            st.session_state.symbol = symbol.upper()
        except Exception as e:
            st.error(f"Erro na análise: {e}")
            st.stop()

r = st.session_state.result
symbol = st.session_state.symbol

c1, c2, c3, c4 = st.columns(4)
c1.metric("Preço", f"R$ {r['last_price']:.2f}")
c2.metric("Cenário do modelo", r["direction"])
c3.metric("Prob. estimada de alta", f"{r['prob_up']*100:.1f}%")
c4.metric("Validação histórica", f"{r['validation_accuracy']*100:.1f}%")

st.divider()

left, right = st.columns([2, 1])
with left:
    st.subheader(f"{symbol} — preço e médias")
    chart = r["data"][["Close", "sma_20", "sma_50"]].rename(
        columns={"Close":"Preço", "sma_20":"MM20", "sma_50":"MM50"}
    )
    st.line_chart(chart)

with right:
    st.subheader("Indicadores")
    st.write(f"**Tendência:** {r['trend']}")
    st.write(f"**RSI(14):** {r['rsi']:.1f} — {r['rsi_state']}")
    st.write(f"**Probabilidade de queda:** {(1-r['prob_up'])*100:.1f}%")
    st.info(
        "A probabilidade é uma estimativa estatística do modelo para a direção "
        "do próximo pregão. Não representa certeza nem retorno esperado."
    )

st.subheader("Como o modelo decide")
st.write(
    "O protótipo combina retornos de 1/5/20 dias, RSI, MACD, volatilidade, "
    "volume relativo e distância das médias móveis. Um Random Forest é treinado "
    "com o histórico disponível e calcula a probabilidade de alta no próximo pregão."
)

st.warning(
    "⚠️ Protótipo educacional. Não use o resultado isoladamente para comprar ou vender. "
    "Mercados podem sofrer eventos inesperados e dados históricos não garantem resultados futuros."
)
