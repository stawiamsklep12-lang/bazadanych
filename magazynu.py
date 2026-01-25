import streamlit as st
import pandas as pd
from supabase import create_client, Client
from postgrest.exceptions import APIError

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Magazyn Pro v5", layout="wide", page_icon="🚀")

# --- POŁĄCZENIE Z BAZĄ ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Błąd konfiguracji połączenia: {e}")
        st.stop()

supabase = init_connection()

# --- FUNKCJE POBIERANIA DANYCH ---
@st.cache_data(ttl=600)
def get_categories():
    res = supabase.table("Kategorie").select("id, Nazwa").execute()
    return res.data

@st.cache_data(ttl=600)
def get_products():
    res = supabase.table("Produkty").select("id, Nazwa, Liczba, Cena, Kategoria_id").execute()
    return res.data

# --- FUNKCJE OPERACYJNE ---
def update_stock(product_id, current_stock, change):
    new_stock = max(0, current_stock + change)
    try:
        supabase.table("Produkty").update({"Liczba": new_stock}).eq("id", product_id).execute()
        st.cache_data.clear()
        st.rerun()
    except Exception as e:
        st.error(f"Błąd podczas aktualizacji: {e}")

# --- GŁÓWNA LOGIKA ---
st.title("🚀 Inteligentny Magazyn Pro")

# Pobranie danych
products = get_products()
categories = get_categories()

# Zakładki
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "📦 Magazyn & Kontrola", "🔧 Administracja", "📄 Raporty"])

if products:
    df = pd.DataFrame(products)
    
    # --- TAB 1: DASHBOARD ---
    with tab1:
        # Alerty o niskim stanie na samej górze
        low_stock_items = df[df['Liczba'] < 10]
        if not low_stock_items.empty:
            st.warning(f"⚠️ Uwaga! Masz {len(low_stock_items)} produkty z niskim stanem zapasów!")
            with st.expander("Zobacz listę braków"):
                st.write(", ".join(low_stock_items['Nazwa'].tolist()))

        total_value = (df['Liczba'] * df['Cena']).sum()
        total_items = df['Liczba'].sum()
        
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Wycena magazynu", f"{total_value:,.2f} zł", help="Suma (Cena * Liczba)")
        col_b.metric("Suma jednostek", f"{int(total_items)} szt.")
        col_c.metric("Asortyment", len(df), help="Liczba unikalnych produktów")
        
        st.divider()
        st.subheader("Struktura zapasów")
        st.bar_chart(df.set_index('Nazwa')['Liczba'])

    # --- TAB 2: MAGZYN & KONTROLA (UX UPGRADE) ---
    with tab2:
        st.header("Zarządzanie zapasami")
        search = st.text_input("🔍 Wyszukaj produkt lub kategorię...", placeholder="Zacznij pisać...")
        
        df_filtered = df[df['Nazwa'].str.contains(search, case=False)] if search else df

        # Wyświetlanie jako karty/wiersze z paskami postępu
        for _, row in df_filtered.iterrows():
            with st.status(f"📦 {row['Nazwa']} | Stan: {row['Liczba']} szt.", expanded=True):
                c1, c2, c3 = st.columns([2, 2, 2])
                
                with c1:
                    st.write(f"**Cena:** {row['Cena']:.2f} zł")
                    st.write(f"**Wartość pozycji:** {row['Cena']*row['Liczba']:.2f} zł")
                
                with c2:
                    # Pasek postępu (przyjmujemy 100 jako 'pełny magazyn' dla wizualizacji)
                    progress = min(row['Liczba'] / 100, 1.0)
                    st.write("Poziom zapasów:")
                    st.progress(progress)
                
                with c3:
                    st.write("Szybka korekta:")
                    cc1, cc2, cc3 = st.columns([2, 1, 1])
                    amt = cc1.number_input("Ilość", min_value=1, value=1, key=f"n_{row['id']}", label_visibility="collapsed")
                    if cc2.button("➕", key=f"p_{row['id']}", use_container_width=True):
                        update_stock(row['id'], row['Liczba'], amt)
                    if cc3.button("➖", key=f"m_{row['id']}", use_container_width=True):
                        update_stock(row['id'], row['Liczba'], -amt)

    # --- TAB 3: ADMINISTRACJA ---
    with tab3:
        col_add, col_del = st.columns(2)
        with col_add:
            st.subheader("✨ Nowy produkt")
            if categories:
                cat_map = {c['Nazwa']: c['id'] for c in categories}
                with st.form("new_prod"):
                    n = st.text_input("Nazwa")
                    l = st.number_input("Ilość", min_value=0)
                    c = st.number_input("Cena", min_value=0.0)
                    k = st.selectbox("Kategoria", list(cat_map.keys()))
                    if st.form_submit_button("Dodaj produkt"):
                        supabase.table("Produkty").insert({"Nazwa":n, "Liczba":l, "Cena":c, "Kategoria_id":cat_map[k]}).execute()
                        st.cache_data.clear()
                        st.rerun()
        
        with col_del:
            st.subheader("🗑️ Usuwanie")
            to_del = st.selectbox("Produkt", df['Nazwa'].tolist())
            if st.button("Usuń trwale", type="primary"):
                tid = df[df['Nazwa'] == to_del]['id'].values[0]
                supabase.table("Produkty").delete().eq("id", tid).execute()
                st.cache_data.clear()
                st.rerun()

    # --- TAB 4: RAPORTY ---
    with tab4:
        st.header("Archiwizacja i dane")
        st.dataframe(df, use_container_width=True)
        st.download_button("Pobierz Arkusz Excel (CSV)", df.to_csv().encode('utf-8'), "magazyn.csv", "text/csv")

else:
    st.info("Brak towaru. Dodaj coś w administracji!")
