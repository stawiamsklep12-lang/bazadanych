import streamlit as st
import pandas as pd
from supabase import create_client, Client

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Magazyn Pro v9", layout="wide", page_icon="📦")

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

# --- SŁOWNIK JEDNOSTEK ---
# Definiujemy jednostki dostępne w systemie
UNITS = ["szt.", "kg", "g", "ml", "l", "m", "m2", "opak."]

# --- FUNKCJE ---
@st.cache_data(ttl=600)
def get_data(table):
    res = supabase.table(table).select("*").execute()
    return res.data

def update_stock(product_id, current_stock, change):
    new_stock = max(0.0, float(current_stock) + float(change))
    supabase.table("Produkty").update({"Liczba": new_stock}).eq("id", product_id).execute()
    st.cache_data.clear()
    st.rerun()

# --- PRZYGOTOWANIE DANYCH ---
prods = get_data("Produkty")
cats = get_data("Kategorie")
df = pd.DataFrame(prods) if prods else pd.DataFrame()
cat_df = pd.DataFrame(cats) if cats else pd.DataFrame()

# Trik: Wyciągamy jednostkę z nazwy, jeśli jest zapisana w formacie "Nazwa [jedn]"
def parse_unit(name):
    for u in UNITS:
        if f"[{u}]" in name:
            return u
    return "szt."

# --- INTERFEJS ---
st.title("📦 Magazyn z Obsługą Jednostek Miary")

tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "📦 Zapasy", "🔧 Administracja", "📄 Raporty"])

if not df.empty:
    with tab1:
        c1, c2, c3 = st.columns(3)
        c1.metric("Wartość całkowita", f"{(df['Liczba'] * df['Cena']).sum():,.2f} zł")
        c2.metric("Liczba pozycji", len(df))
        c3.metric("Niskie stany", len(df[df['Liczba'] < 5]))

    with tab2:
        search = st.text_input("Szukaj towaru...")
        filtered = df[df['Nazwa'].str.contains(search, case=False)] if search else df
        
        for _, row in filtered.iterrows():
            unit = parse_unit(row['Nazwa'])
            clean_name = row['Nazwa'].split(" [")[0] # Wyświetlamy ładną nazwę bez nawiasów
            
            with st.expander(f"{clean_name} — Stan: {row['Liczba']} {unit}"):
                col1, col2, col3 = st.columns([2,2,1])
                # Dla kg/l pozwalamy na wartości dziesiętne (step=0.1)
                step_val = 0.1 if unit in ["kg", "l", "m", "m2"] else 1.0
                
                change = col1.number_input(f"Ilość ({unit})", min_value=0.1 if step_val == 0.1 else 1, step=step_val, key=f"n_{row['id']}")
                if col2.button("➕ Dodaj", key=f"add_{row['id']}"):
                    update_stock(row['id'], row['Liczba'], change)
                if col3.button("➖ Odejmij", key=f"sub_{row['id']}"):
                    update_stock(row['id'], row['Liczba'], -change)

    with tab3:
        st.subheader("Dodaj nowy produkt")
        with st.form("new_product"):
            col_n, col_u = st.columns([3, 1])
            base_name = col_n.text_input("Nazwa produktu")
            unit_choice = col_u.selectbox("Jednostka", UNITS)
            
            c_l, c_c, c_k = st.columns(3)
            start_qty = c_l.number_input("Ilość początkowa", min_value=0.0, step=0.1)
            price = c_c.number_input("Cena za jednostkę", min_value=0.0)
            category = c_k.selectbox("Kategoria", cat_df['Nazwa'].tolist() if not cat_df.empty else ["Brak"])
            
            if st.form_submit_button("Zapisz produkt"):
                # Łączymy nazwę z jednostką w jeden ciąg, aby baza to przyjęła
                full_name = f"{base_name} [{unit_choice}]"
                cat_id = cat_df[cat_df['Nazwa'] == category]['id'].values[0]
                
                supabase.table("Produkty").insert({
                    "Nazwa": full_name,
                    "Liczba": start_qty,
                    "Cena": price,
                    "Kategoria_id": cat_id
                }).execute()
                st.cache_data.clear()
                st.success(f"Dodano: {full_name}")
                st.rerun()

    with tab4:
        # Prezentacja w tabeli z wyczyszczonymi nazwami
        report_df = df.copy()
        report_df['Jednostka'] = report_df['Nazwa'].apply(parse_unit)
        report_df['Nazwa'] = report_df['Nazwa'].apply(lambda x: x.split(" [")[0])
        st.dataframe(report_df[['id', 'Nazwa', 'Liczba', 'Jednostka', 'Cena']], use_container_width=True)

else:
    st.warning("Baza jest pusta.")
