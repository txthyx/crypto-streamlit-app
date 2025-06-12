# crypto-price-app.py

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from pycoingecko import CoinGeckoAPI
import base64

#---------------------------------#
# Page setup
st.set_page_config(layout="wide", page_title="Crypto Price Tracker")

with st.sidebar:
    st.image("logo.png")

#---------------------------------#
# Title
st.title('📈 Crypto Price Tracker using CoinGecko')
st.markdown("""
This app retrieves cryptocurrency data using **CoinGecko API** and displays:
- Top 25 cryptocurrencies
- Live prices in USD or INR
- 1h, 24h, and 7d percentage changes
- Visual bar plot of percentage change
""")

#---------------------------------#
# Highlights Section
cg = CoinGeckoAPI()
@st.cache_data(ttl=300)
def get_global_data():
    return cg.get_global()
global_data = get_global_data()

currency = 'usd'  # Default for highlights before sidebar
market_cap = global_data['total_market_cap'][currency.lower()]
market_cap_change = global_data['market_cap_change_percentage_24h_usd']
volume_24h = global_data['total_volume'][currency.lower()]

@st.cache_data(ttl=300)
def get_trending():
    return cg.get_search_trending()
trending = get_trending()['coins']

trending_ids = [coin['item']['id'] for coin in trending[:3]]
if trending_ids:
    trending_prices = cg.get_price(ids=trending_ids, vs_currencies=currency.lower())
else:
    trending_prices = {}

st.markdown('---')
hcol1, hcol2 = st.columns([2,2])

with hcol1:
    st.metric(
        label='Global Market Cap',
        value=f"${market_cap:,}",
        delta=f"{market_cap_change:.2f}% (24h)",
        delta_color='normal' if market_cap_change >= 0 else 'inverse'
    )
    st.metric(
        label='24h Trading Volume',
        value=f"${volume_24h:,.0f}"
    )

    # --- Search Bar for Top 100 Cryptos ---
    @st.cache_data(ttl=300)
    def get_top100():
        cg = CoinGeckoAPI()
        data = cg.get_coins_markets(
            vs_currency=currency,
            per_page=100,
            page=1,
            price_change_percentage="24h"
        )
        return pd.DataFrame(data)

    top100_df = get_top100()
    search_query = st.text_input('🔍 Search Top 100 Cryptos (by name or symbol)')
    if search_query:
        results = top100_df[
            top100_df['name'].str.contains(search_query, case=False) |
            top100_df['symbol'].str.contains(search_query, case=False)
        ]
        if not results.empty:
            for _, row in results.iterrows():
                st.write(f"**{row['name']} ({row['symbol'].upper()})**")
                st.write(f"Price: {row['current_price']}")
                pct = row.get('price_change_percentage_24h_in_currency', None)
                if pct is not None:
                    st.write(f"24h %: {pct:.2f}%")
                st.markdown('---')
        else:
            st.info('No matching cryptocurrency found.')

with hcol2:
    st.markdown('**🔥 Trending Coins**')
    for coin in trending[:3]:
        c = coin['item']
        price = trending_prices.get(c['id'], {}).get(currency.lower(), 'N/A')
        st.write(f"{c['name']} ({c['symbol'].upper()})")
        st.write(f"Rank: {c['market_cap_rank']}")
        st.write(f"Price: {price}")
        st.markdown('---')

#---------------------------------#
# Sidebar Inputs
currency = st.sidebar.selectbox('Currency', ['USD', 'INR'])
percent_timeframe = st.sidebar.selectbox('Change Time Frame', ['1h', '24h', '7d'])
sort_values = st.sidebar.selectbox('Sort values?', ['Yes', 'No'])

#---------------------------------#
# Load Data
@st.cache_data
def load_data(currency):
    cg = CoinGeckoAPI()
    data = cg.get_coins_markets(
        vs_currency=currency,
        per_page=250,
        page=1,
        price_change_percentage="1h,24h,7d"
    )
    
    df = pd.DataFrame(data)[[
        'name', 'symbol', 'current_price', 'market_cap', 'total_volume',
        'price_change_percentage_1h_in_currency',
        'price_change_percentage_24h_in_currency',
        'price_change_percentage_7d_in_currency'
    ]]

    df.rename(columns={
        'name': 'Coin Name',
        'symbol': 'Symbol',
        'current_price': f'Price ({currency.upper()})',
        'market_cap': 'Market Cap',
        'total_volume': '24h Volume',
        'price_change_percentage_1h_in_currency': '1h %',
        'price_change_percentage_24h_in_currency': '24h %',
        'price_change_percentage_7d_in_currency': '7d %'
    }, inplace=True)
    
    return df

df = load_data(currency)

#---------------------------------#
# Multiselect Filter
coins = sorted(df['Symbol'])
selected_coins = st.sidebar.multiselect('Filter by Coins (optional)', coins, default=coins)

if selected_coins:
    df = df[df['Symbol'].isin(selected_coins)]

# Limit to top N coins
max_n = min(len(df), 25)
top_n = st.sidebar.slider("Top N Coins to Display", 1, max_n, max_n)
df = df.head(top_n)

#---------------------------------#
# Display Data Table
st.subheader(f"📊 Top {top_n} Cryptocurrencies in {currency.upper()}")
st.write(f"Data for {len(df)} coins.")
st.dataframe(df)

#---------------------------------#
# CSV Download
def download_link(df):
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    return f'<a href="data:file/csv;base64,{b64}" download="crypto_data.csv">📥 Download CSV</a>'

st.markdown(download_link(df), unsafe_allow_html=True)

#---------------------------------#
# % Change Plot
st.subheader(f"📉 {percent_timeframe} % Change - Bar Plot")

change_column = {
    '1h': '1h %',
    '24h': '24h %',
    '7d': '7d %'
}[percent_timeframe]

df_plot = df[['Symbol', change_column]].copy()
df_plot.set_index('Symbol', inplace=True)
df_plot['positive'] = df_plot[change_column] > 0

if sort_values == "Yes":
    df_plot.sort_values(by=change_column, inplace=True)

# Horizontal bar chart
fig, ax = plt.subplots(figsize=(10, max(4, 0.4 * len(df_plot))))
bars = ax.barh(
    df_plot.index,
    df_plot[change_column],
    color=df_plot['positive'].map({True: 'green', False: 'red'})
)

ax.set_xlabel(f'{percent_timeframe} % Change')
ax.set_title(f'Change in Price ({percent_timeframe})')

st.pyplot(fig)
