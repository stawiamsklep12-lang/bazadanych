import streamlit as st
from supabase import create_client, Client

# 1. Połączenie z bazą danych
# Upewnij się, że w Streamlit Cloud w sekcji Secrets masz dodane:
# SUPABASE_URL = "..."
# SUPABASE_KEY = "..."

try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("Błąd konfiguracji kluczy API. Sprawdź plik .streamlit/secrets.toml")
    st.stop()

st.set_page_config(page_title="Magazyn Produktów", layout="centered")
st.title("📦 System Zarządzania Produktami")

# --- FUNKCJE POMOCNICZE ---

def fetch_categories():
    res = supabase.table("Kategorie").select("id, Nazwa").execute()
    return res.data

def fetch_products():
    # Pobieramy produkty wraz z nazwą kategorii (join)
    res = supabase.table("Produkty").select("id, Nazwa, Liczba, Cena, Kategoria_id").execute()
    return res.data

# --- UI: DODAWANIE PRODUKTU ---
st.header("➕ Dodaj nowy produkt")

categories = fetch_categories()
if not categories:
    st.warning("Najpierw dodaj kategorie w bazie danych!")
else:
    cat_mapping = {cat['Nazwa']: cat['id'] for cat in categories}
    
    with st.form("form_dodawania", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nazwa = st.text_input("Nazwa produktu")
            liczba = st.number_input("Ilość (Liczba)", min_value=0, step=1)
        with col2:
            # UWAGA: Sprawdź czy w bazie masz "Cena" czy "Ce..." 
            cena = st.number_input("Cena (numeric)", min_value=0.0, format="%.2f")
            kategoria_nazwa = st.selectbox("Wybierz kategorię", options=list(cat_mapping.keys()))
        
        submit = st.form_submit_button("Zapisz w bazie")

        if submit:
            if nazwa:
                data_to_insert = {
                    "Nazwa": nazwa,
                    "Liczba": liczba,
                    "Cena": cena, # Jeśli na obrazku ucięło nazwę, zmień tutaj na poprawną
                    "Kategoria_id": cat_mapping[kategoria_nazwa]
                }
                response = supabase.table("Produkty").insert(data_to_insert).execute()
                if response.data:
                    st.success(f"Dodano produkt: {nazwa}")
                    st.rerun()
                else:
                    st.error("Wystąpił błąd podczas zapisywania.")
            else:
                st.warning("Nazwa produktu nie może być pusta.")

st.divider()

# --- UI: LISTA I USUWANIE ---
st.header("📋 Lista produktów i usuwanie")

products = fetch_products()

if products:
    for p in products:
        with st.expander(f"{p['Nazwa']} (ID: {p['id']})"):
            st.write(f"Ilość: {p['Liczba']} | Cena: {p['Cena']} zł")
            
            # Przycisk usuwania z unikalnym kluczem
            if st.button(f"Usuń {p['Nazwa']}", key=f"del_{p['id']}", type="primary"):
                supabase.table("Produkty").delete().eq("id", p['id']).execute()
                st.toast(f"Usunięto {p['Nazwa']}")
                st.rerun()
else:
    st.info("Brak produktów do wyświetlenia.")
