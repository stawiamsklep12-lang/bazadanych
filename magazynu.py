import streamlit as st
import pandas as pd
from supabase import create_client, Client
from postgrest.exceptions import APIError

# --- KONFIGURACJA ---
st.set_page_config(page_title="Magazyn Pro", layout="wide", page_icon="📦")

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

# --- FUNKCJE POBIERANIA DANYCH (Z CACHE) ---
@st.cache_data(ttl=600)  # Dane ważne przez 10 minut lub do ręcznego czyszczenia
def get_categories():
    res = supabase.table("Kategorie").select("id, Nazwa").execute()
    return res.data

@st.cache_data(ttl=600)
def get_products():
    res = supabase.table("Produkty").select("id, Nazwa, Liczba, Cena, Kategoria_id").execute()
    return res.data

# --- LOGIKA APLIKACJI ---
st.title("📦 System Zarządzania Magazynem")

# UI: DODAWANIE PRODUKTU
with st.expander("➕ Dodaj nowy produkt"):
    categories = get_categories()
    if categories:
        cat_mapping = {cat['Nazwa']: cat['id'] for cat in categories}
        
        with st.form("add_form", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            nazwa = col1.text_input("Nazwa produktu")
            liczba = col2.number_input("Ilość (szt.)", min_value=0, step=1)
            cena = col3.number_input("Cena (zł)", min_value=0.0, format="%.2f")
            kat = st.selectbox("Kategoria", options=list(cat_mapping.keys()))
            
            if st.form_submit_button("Zatwierdź i dodaj"):
                if nazwa:
                    try:
                        supabase.table("Produkty").insert({
                            "Nazwa": nazwa,
                            "Liczba": liczba,
                            "Cena": round(float(cena), 2),
                            "Kategoria_id": cat_mapping[kat]
                        }).execute()
                        
                        st.success(f"Produkt {nazwa} dodany!")
                        st.cache_data.clear() # Czyścimy cache, by pobrać nowe dane
                        st.rerun()
                    except APIError as e:
                        st.error(f"Błąd bazy danych: {e}")
                else:
                    st.warning("Podaj nazwę produktu.")
    else:
        st.error("Brak kategorii w bazie.")

st.divider()

# POBIERANIE DANYCH
products = get_products()

if products:
    df = pd.DataFrame(products)
    
    # SEKCJA: WYKRESY
    st.header("📊 Wizualizacja stanów")
    # Ulepszony wykres - sortowanie po liczbie
    chart_data = df[['Nazwa', 'Liczba']].sort_values(by='Liczba', ascending=False)
    st.bar_chart(chart_data, x='Nazwa', y='Liczba', color="#FF4B4B")

    st.divider()

    # SEKCJA: TABELA
    st.header("📋 Lista produktów")
    
    def highlight_low_stock(s):
        return ['background-color: rgba(255, 75, 75, 0.3)' if s.Liczba < 10 else '' for _ in s]

    # Używamy st.column_config dla lepszego UX
    st.dataframe(
        df[['id', 'Nazwa', 'Liczba', 'Cena']].style.apply(highlight_low_stock, axis=1),
        column_config={
            "Cena": st.column_config.NumberColumn("Cena", format="%.2f zł"),
            "Liczba": st.column_config.NumberColumn("Stan", help="Liczba sztuk w magazynie"),
            "id": None # Ukrywamy ID w widoku
        },
        use_container_width=True,
        hide_index=True
    )

    # USUWANIE (W SIDEBARZE)
    with st.sidebar:
        st.header("⚙️ Zarządzanie")
        prod_to_del = st.selectbox("Produkt do usunięcia", options=df['Nazwa'].tolist(), key="del_box")
        
        if st.button("🗑️ Usuń trwale", type="primary"):
            target_id = df[df['Nazwa'] == prod_to_del]['id'].values[0]
            try:
                supabase.table("Produkty").delete().eq("id", target_id).execute()
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Błąd podczas usuwania: {e}")
else:
    st.info("Brak produktów w bazie danych.")
