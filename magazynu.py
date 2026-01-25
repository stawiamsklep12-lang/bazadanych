import streamlit as st
import pandas as pd
from supabase import create_client, Client
import plotly.express as px  # Nowa biblioteka do niezawodnych wykresów

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Magazyn Pro Ultra", layout="wide", page_icon="💎")

# --- POŁĄCZENIE Z BAZĄ ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Błąd połączenia: {e}")
        st.stop()

supabase = init_connection()

# --- FUNKCJE DANYCH ---
@st.cache_data(ttl=600)
def get_categories():
    res = supabase.table("Kategorie").select("id, Nazwa").execute()
    return res.data

@st.cache_data(ttl=600)
def get_products():
    res = supabase.table("Produkty").select("id, Nazwa, Liczba, Cena, Kategoria_id").execute()
    return res.data

def update_stock(product_id, current_stock, change):
    new_stock = max(0, current_stock + change)
    supabase.table("Produkty").update({"Liczba": new_stock}).eq("id", product_id).execute()
    st.cache_data.clear()
    st.rerun()

# --- INTERFEJS ---
st.title("💎 Magazyn Pro Ultra")

products = get_products()
categories = get_categories()

if products:
    df = pd.DataFrame(products)
    # Dodajemy kolumnę z obliczoną wartością dla łatwiejszej analityki
    df['Wartość_Łączna'] = df['Liczba'] * df['Cena']
    
    # --- BOCZNY PANEL ---
    with st.sidebar:
        st.header("📊 Finanse")
        total_val = df['Wartość_Łączna'].sum()
        st.metric("Suma Majątku", f"{total_val:,.2f} zł")
        st.divider()
        st.subheader("Najcenniejsze pozycje")
        top_val = df.nlargest(3, 'Wartość_Łączna')
        for _, r in top_val.iterrows():
            st.caption(f"{r['Nazwa']}: {r['Wartość_Łączna']:.2f} zł")

    tab1, tab2, tab3, tab4 = st.tabs(["🚀 Dashboard", "📦 Magazyn", "🛠️ Edycja", "📈 Wykresy"])

    # --- TAB 1: DASHBOARD ---
    with tab1:
        c1, c2, c3 = st.columns(3)
        low_stock = df[df['Liczba'] < 10]
        c1.metric("Liczba SKU", len(df))
        c2.metric("Niskie stany", len(low_stock))
        c3.metric("Łączna ilość sztuk", int(df['Liczba'].sum()))

        if not low_stock.empty:
            st.warning("⚠️ Produkty wymagające uzupełnienia:")
            st.dataframe(low_stock[['Nazwa', 'Liczba']], use_container_width=True, hide_index=True)

    # --- TAB 2: MAGAZYN ---
    with tab2:
        search = st.text_input("🔍 Szukaj produktu...", placeholder="Wpisz nazwę...")
        df_f = df[df['Nazwa'].str.contains(search, case=False)] if search else df

        for _, row in df_f.iterrows():
            with st.container(border=True):
                col1, col2, col3, col4 = st.columns([2, 1, 1, 2])
                col1.write(f"**{row['Nazwa']}**")
                col2.write(f"{row['Cena']:.2f} zł/szt")
                
                status_color = "🔴" if row['Liczba'] < 10 else "🟢"
                col3.write(f"{status_color} {int(row['Liczba'])} szt.")
                
                with col4:
                    cc1, cc2, cc3 = st.columns([2, 1, 1])
                    amt = cc1.number_input("Ilość", min_value=1, value=1, key=f"v_{row['id']}", label_visibility="collapsed")
                    if cc2.button("➕", key=f"p_{row['id']}"): update_stock(row['id'], row['Liczba'], amt)
                    if cc3.button("➖", key=f"m_{row['id']}"): update_stock(row['id'], row['Liczba'], -amt)

    # --- TAB 3: EDYCJA ---
    with tab3:
        with st.expander("➕ Nowy produkt"):
            if categories:
                cat_map = {c['Nazwa']: c['id'] for c in categories}
                with st.form("new_prod"):
                    n = st.text_input("Nazwa")
                    l = st.number_input("Ilość", min_value=0)
                    p = st.number_input("Cena", min_value=0.0)
                    k = st.selectbox("Kategoria", list(cat_map.keys()))
                    if st.form_submit_button("Dodaj"):
                        supabase.table("Produkty").insert({"Nazwa":n, "Liczba":l, "Cena":p, "Kategoria_id":cat_map[k]}).execute()
                        st.cache_data.clear()
                        st.rerun()

        with st.expander("🗑️ Usuń produkt"):
            to_del = st.selectbox("Wybierz", df['Nazwa'].tolist())
            if st.button("Usuń", type="primary"):
                tid = df[df['Nazwa'] == to_del]['id'].values[0]
                supabase.table("Produkty").delete().eq("id", tid).execute()
                st.cache_data.clear()
                st.rerun()

    # --- TAB 4: WYKRESY (NAPRAWIONE) ---
    with tab4:
        st.header("Analityka Wizualna")
        
        c_left, c_right = st.columns(2)
        
        with c_left:
            st.subheader("Udział ilościowy produktów")
            # Używamy Plotly - jest 100% pewny
            fig_pie = px.pie(df, values='Liczba', names='Nazwa', hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with c_right:
            st.subheader("Wartość towaru (Top 10)")
            fig_bar = px.bar(df.nlargest(10, 'Wartość_Łączna'), x='Nazwa', y='Wartość_Łączna', color='Nazwa')
            st.plotly_chart(fig_bar, use_container_width=True)

else:
    st.info("Baza danych jest pusta.")
