import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime, timedelta

# --- KONFIGURACJA ---
st.set_page_config(page_title="Magazyn AI Pro", layout="wide", page_icon="🤖")

@st.cache_resource
def init_connection():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except:
        st.error("Błąd połączenia."); st.stop()

supabase = init_connection()

# --- DANE ---
@st.cache_data(ttl=600)
def get_data():
    p = supabase.table("Produkty").select("*").execute()
    k = supabase.table("Kategorie").select("*").execute()
    return pd.DataFrame(p.data), pd.DataFrame(k.data)

df, cat_df = get_data()

# --- LOGIKA ANALITYCZNA (PROGNOZOWANIE) ---
def get_prediction(row):
    # Symulacja średniego zużycia (w realnym systemie bralibyśmy to z historii transakcji)
    # Tutaj: zakładamy, że produkty z małą ilością schodzą w tempie ok. 1.5 szt./dzień
    daily_usage = 1.5 
    if row['Liczba'] < 10:
        days_left = int(row['Liczba'] / daily_usage)
        return days_left
    return None

# --- INTERFEJS ---
st.title("🤖 Magazyn Pro + Estymacja AI")

tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "📦 Magazyn", "📥 Wiadomości Tomasza", "🔧 Administracja"])

if not df.empty:
    # --- TAB 1: ANALIZA ---
    with tab1:
        st.subheader("Prognoza zapasów")
        df['dni_do_zera'] = df.apply(get_prediction, axis=1)
        critical = df[df['dni_do_zera'].notnull()].sort_values('dni_do_zera')
        
        if not critical.empty:
            st.warning("Produkty wymagające uwagi w najbliższym tygodniu:")
            st.dataframe(critical[['Nazwa', 'Liczba', 'dni_do_zera']].rename(
                columns={'dni_do_zera': 'Dni do wyczerpania'}), use_container_width=True)

    # --- TAB 2: MAGAZYN ---
    with tab2:
        for _, row in df.iterrows():
            color = "red" if row['Liczba'] < 5 else "orange" if row['Liczba'] < 10 else "green"
            with st.expander(f"**{row['Nazwa']}**"):
                st.markdown(f"Aktualny stan: :{color}[{row['Liczba']} szt.]")
                if st.button("➕ Dostawa (+1)", key=f"up_{row['id']}"):
                    supabase.table("Produkty").update({"Liczba": row['Liczba']+1}).eq("id", row['id']).execute()
                    st.cache_data.clear(); st.rerun()
                if st.button("➖ Wydanie (-1)", key=f"down_{row['id']}"):
                    supabase.table("Produkty").update({"Liczba": max(0, row['Liczba']-1)}).eq("id", row['id']).execute()
                    st.cache_data.clear(); st.rerun()

    # --- TAB 3: WIADOMOŚCI DLA TOMASZA ---
    with tab3:
        st.header("📥 Skrzynka Zaopatrzeniowca")
        alerts = df[df['Liczba'] < 10]
        
        if alerts.empty:
            st.success("Wszystko pod kontrolą, Tomaszu!")
        else:
            for _, alert in alerts.iterrows():
                days = get_prediction(alert)
                termin = (datetime.now() + timedelta(days=days)).strftime("%d.%m.%Y")
                
                with st.chat_message("assistant"):
                    st.write(f"**Cześć Tomasz!**")
                    st.write(f"Produkt **{alert['Nazwa']}** skończy się za około **{days} dni** ({termin}).")
                    st.write(f"Sugerowane zamówienie: **{int(20 - alert['Liczba'])} szt.**")
                    st.button("✅ Oznacz jako zamówione", key=f"msg_{alert['id']}")

    # --- TAB 4: ADMIN ---
    with tab4:
        st.subheader("Nowy produkt")
        with st.form("add"):
            name = st.text_input("Nazwa")
            qty = st.number_input("Ilość", 0)
            price = st.number_input("Cena", 0.0)
            cat = st.selectbox("Kategoria", cat_df['Nazwa'].tolist())
            if st.form_submit_button("Dodaj"):
                cat_id = cat_df[cat_df['Nazwa'] == cat]['id'].values[0]
                supabase.table("Produkty").insert({"Nazwa":name, "Liczba":qty, "Cena":price, "Kategoria_id":cat_id}).execute()
                st.cache_data.clear(); st.rerun()
