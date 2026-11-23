import streamlit as st

from config.settings import APP_NAME, APP_VERSION, APP_MODE


st.set_page_config(
    page_title=APP_NAME,
    page_icon="📊",
    layout="wide",
)

st.title("📊 India Arbitrage Lab")

st.caption(
    f"Version {APP_VERSION} | Mode: {APP_MODE}"
)

st.markdown("---")

st.subheader("Research & Paper Trading Platform")

st.info(
    "இந்த project தற்போது research, historical analysis "
    "மற்றும் paper trading பயன்பாட்டிற்காக உருவாக்கப்படுகிறது. "
    "Real orders செயல்படுத்தப்படாது."
)

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label="Strategy Engines",
        value="0 / 10",
        help="Strategy modules test செய்யப்பட்ட பிறகு எண்ணிக்கை update செய்யப்படும்."
    )

with col2:
    st.metric(
        label="Qualified Opportunities",
        value=0,
    )

with col3:
    st.metric(
        label="Paper Trading",
        value="Inactive",
    )

st.markdown("### Project Modules")

modules = [
    "Data Engine",
    "Contract Master",
    "Charges Calculator",
    "Fair Value Engine",
    "Opportunity Scanner",
    "Validation Engine",
    "Opportunity Ranking",
    "Risk & Margin Manager",
    "Paper Trading Engine",
    "Backtesting Engine",
    "Portfolio & P&L",
    "Analytics & AI Research",
]

for module in modules:
    st.write(f"🔹 {module}")

st.markdown("---")

st.warning(
    "Market data இணைக்கப்படவில்லை. "
    "இந்த dashboard தற்போது foundation stage-ல் உள்ளது."
)

st.caption(
    "India Arbitrage Lab | Research & Simulation Only"
)
