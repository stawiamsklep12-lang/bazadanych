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

st.title("📦 System Zarządzania Magazynem")

# --- UI: DODAWANIE PRODUKTU ---
with st.expander("➕ Dodaj nowy produkt"):
    categories = get_categories()
    if categories:
        cat_mapping = {cat['Nazwa']: cat['id'] for cat in categories}
        
        with st.form("add_form", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            nazwa = col1.text_input("Nazwa produktu")
            liczba = col2.number_input("Ilość (szt.)", min_value=0, step=1)
            # Ustawienie formatu w input na 2 miejsca po przecinku
            cena = col3.number_input("Cena (zł)", min_value=0.0, format="%.2f")
            kat = st.selectbox("Kategoria", options=list(cat_mapping.keys()))
            
            if st.form_submit_button("Zatwierdź i dodaj"):
                if nazwa:
                    supabase.table("Produkty").insert({
                        "Nazwa": nazwa,
                        "Liczba": liczba,
                        "Cena": round(float(cena), 2), # Zaokrąglanie przed wysyłką
                        "Kategoria_id": cat_mapping[kat]
                    }).execute()
                    st.success(f"Produkt {nazwa} dodany!")
                    st.rerun()
                else:
                    st.warning("Podaj nazwę produktu.")
    else:
        st.error("Brak kategorii w bazie. Dodaj je najpierw w panelu Supabase.")

st.divider()

# --- POBIERANIE DANYCH DO TABELI I WYKRESU ---
products = get_products()

if products:
    df = pd.DataFrame(products)
    
    # --- SEKCJA: WYKRESY ---
    st.header("📊 Wizualizacja stanów")
    # Tworzymy wykres: oś X to Nazwa, oś Y to Liczba
    chart_data = df[['Nazwa', 'Liczba']].set_index('Nazwa')
    st.bar_chart(chart_data)

    st.divider()

    # --- SEKCJA: TABELA Z OSTRZEŻENIAMI ---
    st.header("📋 Lista produktów")
    st.info("Produkty na czerwono: stan poniżej 10 sztuk.")

    # Formatowanie wyświetlania ceny w dataframe
    df_display = df[['id', 'Nazwa', 'Liczba', 'Cena']].copy()

    # Funkcja do kolorowania niskiego stanu
    def highlight_low_stock(row):
        color = 'background-color: rgba(255, 75, 75, 0.4)' if row['Liczba'] < 10 else ''
        return [color] * len(row)

    # Wyświetlanie tabeli ze stylami i formatowaniem ceny
    st.dataframe(
        df_display.style.apply(highlight_low_stock, axis=1)
                        .format({"Cena": "{:.2f} zł"}), # Zaokrąglanie widoku do 2 miejsc
        use_container_width=True,
        hide_index=True
    )

    # --- USUWANIE ---
    with st.sidebar:
        st.header("Usuwanie")
        prod_to_del = st.selectbox("Produkt do usunięcia", options=df['Nazwa'].tolist())
        if st.button("Usuń trwale", type="primary"):
            target_id = df[df['Nazwa'] == prod_to_del]['id'].values[0]
            supabase.table("Produkty").delete().eq("id", target_id).execute()
            st.rerun()
else:
    st.info("Brak produktów w bazie danych.")
