import streamlit as st
from supabase import create_client, Client

# Konfiguracja połączenia z Supabase
# Dane te znajdziesz w Settings -> API w panelu Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.title("📦 Zarządzanie Produktami")

# --- SEKCJA 1: DODAWANIE PRODUKTU ---
st.header("Dodaj nowy produkt")

# Pobieranie kategorii do listy rozwijanej
def get_categories():
    response = supabase.table("Kategorie").select("id, Nazwa").execute()
    return response.data

categories = get_categories()
cat_options = {cat['Nazwa']: cat['id'] for cat in categories}

with st.form("add_product_form"):
    nazwa = st.text_input("Nazwa produktu")
    liczba = st.number_input("Liczba (sztuki)", min_value=0, step=1)
    cena = st.number_input("Cena", min_value=0.0, format="%.2f")
    kategoria_nazwa = st.selectbox("Kategoria", options=list(cat_options.keys()))
    
    submit_button = st.form_submit_button("Dodaj produkt")

if submit_button:
    new_product = {
        "Nazwa": nazwa,
        "Liczba": liczba,
        "Ce...": cena, # Nazwa kolumny ucięta na obrazku, dostosuj jeśli trzeba
        "Kategoria_id": cat_options[kategoria_nazwa]
    }
    
    try:
        supabase.table("Produkty").insert(new_product).execute()
        st.success(f"Produkt '{nazwa}' został dodany!")
    except Exception as e:
        st.error(f"Błąd podczas dodawania: {e}")

---

# --- SEKCJA 2: USUWANIE PRODUKTU ---
st.header("Usuń produkt")

def get_products():
    response = supabase.table("Produkty").select("id, Nazwa").execute()
    return response.data

products = get_products()
if products:
    prod_options = {prod['Nazwa']: prod['id'] for prod in products}
    selected_prod = st.selectbox("Wybierz produkt do usunięcia", options=list(prod_options.keys()))
    
    if st.button("Usuń wybrany produkt", type="primary"):
        supabase.table("Produkty").delete().eq("id", prod_options[selected_prod]).execute()
        st.warning(f"Produkt '{selected_prod}' został usunięty.")
        st.rerun()
else:
    st.info("Brak produktów w bazie.")
