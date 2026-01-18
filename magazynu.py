import streamlit as st
import pandas as pd
from supabase import create_client, Client

# --- KONFIGURACJA POŁĄCZENIA ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception:
    st.error("Błąd konfiguracji kluczy API w Secrets.")
    st.stop()

st.set_page_config(page_title="Magazyn Pro", layout="wide")

# --- FUNKCJE POBIERANIA DANYCH ---
def get_categories():
    res = supabase.table("Kategorie").select("id, Nazwa").execute()
    return res.data

def get_products():
    res = supabase.table("Produkty").select("id, Nazwa, Liczba, Cena, Kategoria_id").execute()
    return res.data

# --- UI: DODAWANIE ---
st.title("📦 Zarządzanie Magazynem")

with st.expander("➕ Dodaj nowy produkt"):
    categories = get_categories()
    cat_mapping = {cat['Nazwa']: cat['id'] for cat in categories}
    
    with st.form("add_form"):
        col1, col2, col3 = st.columns(3)
        nazwa = col1.text_input("Nazwa")
        liczba = col2.number_input("Ilość", min_value=0, step=1)
        cena = col3.number_input("Cena", min_value=0.0)
        kat = st.selectbox("Kategoria", options=list(cat_mapping.keys()))
        
        if st.form_submit_button("Zatwierdź"):
            supabase.table("Produkty").insert({
                "Nazwa": nazwa,
                "Liczba": liczba,
                "Cena": cena,
                "Kategoria_id": cat_mapping[kat]
            }).execute()
            st.success("Produkt dodany!")
            st.rerun()

st.divider()

# --- UI: LISTA Z OSTRZEŻENIEM O NISKIM STANIE ---
st.header("📋 Aktualny stan magazynowy")
st.info("Produkty podświetlone na **czerwono** mają stan poniżej 10 sztuk.")

products = get_products()

if products:
    df = pd.DataFrame(products)
    
    # Reorganizacja kolumn dla czytelności
    df = df[['id', 'Nazwa', 'Liczba', 'Cena']]

    # Funkcja do kolorowania wierszy
    def highlight_low_stock(row):
        color = 'background-color: rgba(255, 0, 0, 0.3)' if row['Liczba'] < 10 else ''
        return [color] * len(row)

    # Wyświetlanie sformatowanej tabeli
    st.dataframe(
        df.style.apply(highlight_low_stock, axis=1),
        use_container_width=True,
        hide_index=True
    )

    # --- USUWANIE ---
    st.subheader("🗑️ Usuwanie produktów")
    prod_to_del = st.selectbox("Wybierz produkt do usunięcia", options=df['Nazwa'].tolist())
    if st.button("Usuń produkt", type="primary"):
        target_id = df[df['Nazwa'] == prod_to_del]['id'].values[0]
        supabase.table("Produkty").delete().eq("id", target_id).execute()
        st.warning(f"Usunięto: {prod_to_del}")
        st.rerun()
else:
    st.write("Magazyn jest pusty.")
