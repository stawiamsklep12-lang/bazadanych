import streamlit as st
import pandas as pd
from supabase import create_client, Client
from postgrest.exceptions import APIError

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Magazyn Pro v2", layout="wide", page_icon="📦")

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
    # Pobieramy dane wraz z nazwą kategorii (join)
    res = supabase.table("Produkty").select("id, Nazwa, Liczba, Cena, Kategoria_id").execute()
    return res.data

# --- GŁÓWNA LOGIKA ---
st.title("📦 System Zarządzania Magazynem")

# Zakładki dla lepszej organizacji
tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "📋 Stan Magazynowy", "⚙️ Operacje"])

# Pobranie danych na początku
products = get_products()
categories = get_categories()

if products:
    df = pd.DataFrame(products)
    
    # --- TAB 1: DASHBOARD ---
    with tab1:
        st.header("Podsumowanie")
        
        # Obliczenia KPI
        total_value = (df['Liczba'] * df['Cena']).sum()
        total_items = df['Liczba'].sum()
        low_stock_count = len(df[df['Liczba'] < 10])
        
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Wartość magazynu", f"{total_value:,.2f} zł")
        col_b.metric("Suma produktów", f"{int(total_items)} szt.")
        col_c.metric("Niski stan (<10)", low_stock_count, delta_color="inverse", delta=f"-{low_stock_count}" if low_stock_count > 0 else 0)
        
        st.divider()
        st.subheader("Wizualizacja stanów")
        chart_data = df[['Nazwa', 'Liczba']].sort_values(by='Liczba', ascending=False)
        st.bar_chart(chart_data, x='Nazwa', y='Liczba', color="#0072B2")

    # --- TAB 2: STAN MAGAZYNOWY ---
    with tab2:
        st.header("Lista produktów")
        
        # Wyszukiwarka
        search = st.text_input("🔍 Szukaj produktu po nazwie...")
        if search:
            df_view = df[df['Nazwa'].str.contains(search, case=False)]
        else:
            df_view = df

        # Funkcja kolorowania
        def highlight_low_stock(s):
            return ['background-color: rgba(255, 75, 75, 0.2)' if s.Liczba < 10 else '' for _ in s]

        st.dataframe(
            df_view[['id', 'Nazwa', 'Liczba', 'Cena']].style.apply(highlight_low_stock, axis=1),
            column_config={
                "Cena": st.column_config.NumberColumn("Cena", format="%.2f zł"),
                "Liczba": st.column_config.NumberColumn("Stan"),
                "id": None
            },
            use_container_width=True,
            hide_index=True
        )

    # --- TAB 3: OPERACJE (DODAWANIE I USUWANIE) ---
    with tab3:
        col_add, col_del = st.columns(2)
        
        with col_add:
            st.subheader("➕ Dodaj produkt")
            if categories:
                cat_mapping = {cat['Nazwa']: cat['id'] for cat in categories}
                with st.form("add_form", clear_on_submit=True):
                    nazwa = st.text_input("Nazwa produktu")
                    c1, c2 = st.columns(2)
                    liczba = c1.number_input("Ilość", min_value=0, step=1)
                    cena = c2.number_input("Cena (zł)", min_value=0.0, format="%.2f")
                    kat = st.selectbox("Kategoria", options=list(cat_mapping.keys()))
                    
                    if st.form_submit_button("Zapisz w bazie"):
                        if nazwa:
                            try:
                                supabase.table("Produkty").insert({
                                    "Nazwa": nazwa, "Liczba": liczba,
                                    "Cena": round(float(cena), 2),
                                    "Kategoria_id": cat_mapping[kat]
                                }).execute()
                                st.success("Dodano!")
                                st.cache_data.clear()
                                st.rerun()
                            except APIError as e:
                                st.error(f"Błąd: {e}")
                        else:
                            st.warning("Podaj nazwę.")
            else:
                st.error("Brak kategorii.")

        with col_del:
            st.subheader("🗑️ Usuń produkt")
            prod_to_del = st.selectbox("Wybierz do usunięcia", options=df['Nazwa'].tolist())
            if st.button("Usuń bezpowrotnie", type="primary"):
                target_id = df[df['Nazwa'] == prod_to_del]['id'].values[0]
                supabase.table("Produkty").delete().eq("id", target_id).execute()
                st.cache_data.clear()
                st.rerun()

else:
    st.info("Baza jest pusta. Dodaj pierwszy produkt w zakładce 'Operacje'.")
    with tab3:
        # Pozwalamy dodać produkt nawet gdy baza jest pusta
        st.subheader("➕ Dodaj pierwszy produkt")
        # (Tutaj musiałby być powtórzony kod formularza lub funkcja)
