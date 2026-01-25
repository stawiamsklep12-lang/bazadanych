import streamlit as st
import pandas as pd
from supabase import create_client, Client
from postgrest.exceptions import APIError

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Magazyn Pro v3", layout="wide", page_icon="📦")

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
    supabase.table("Produkty").update({"Liczba": new_stock}).eq("id", product_id).execute()
    st.cache_data.clear()
    st.rerun()

# --- GŁÓWNA LOGIKA ---
st.title("📦 System Zarządzania Magazynem")

# Pobranie danych
products = get_products()
categories = get_categories()

# Zakładki
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "📋 Stan Magazynowy", "➕ Dodaj/Usuń", "📥 Raporty"])

if products:
    df = pd.DataFrame(products)
    
    # --- TAB 1: DASHBOARD ---
    with tab1:
        st.header("Podsumowanie")
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

    # --- TAB 2: STAN MAGAZYNOWY (Z EDYCJĄ) ---
    with tab2:
        st.header("Zarządzanie ilością")
        
        # Wyszukiwarka
        search = st.text_input("🔍 Szukaj produktu...")
        df_display = df[df['Nazwa'].str.contains(search, case=False)] if search else df

        # Wyświetlanie produktów z przyciskami edycji w kolumnach
        for _, row in df_display.iterrows():
            with st.container():
                c1, c2, c3, c4 = st.columns([3, 2, 2, 3])
                c1.write(f"**{row['Nazwa']}**")
                
                # Kolorowanie stanu
                stock_color = ":red[" if row['Liczba'] < 10 else ":green["
                c2.write(f"Stan: {stock_color}{row['Liczba']} szt.]")
                
                c3.write(f"Cena: {row['Cena']:.2f} zł")
                
                # Przyciski szybkiej zmiany
                btn_col1, btn_col2 = c4.columns(2)
                if btn_col1.button("➕", key=f"add_{row['id']}"):
                    update_stock(row['id'], row['Liczba'], 1)
                if btn_col2.button("➖", key=f"sub_{row['id']}"):
                    update_stock(row['id'], row['Liczba'], -1)
                st.divider()

    # --- TAB 3: DODAWANIE I USUWANIE ---
    with tab3:
        col_add, col_del = st.columns(2)
        
        with col_add:
            st.subheader("Dodaj nowy produkt")
            if categories:
                cat_mapping = {cat['Nazwa']: cat['id'] for cat in categories}
                with st.form("add_form", clear_on_submit=True):
                    nazwa = st.text_input("Nazwa produktu")
                    c1, c2 = st.columns(2)
                    liczba = c1.number_input("Ilość", min_value=0, step=1)
                    cena = c2.number_input("Cena (zł)", min_value=0.0, format="%.2f")
                    kat = st.selectbox("Kategoria", options=list(cat_mapping.keys()))
                    
                    if st.form_submit_button("Dodaj do bazy"):
                        if nazwa:
                            try:
                                supabase.table("Produkty").insert({
                                    "Nazwa": nazwa, "Liczba": liczba,
                                    "Cena": round(float(cena), 2),
                                    "Kategoria_id": cat_mapping[kat]
                                }).execute()
                                st.cache_data.clear()
                                st.success("Dodano produkt!")
                                st.rerun()
                            except APIError as e:
                                st.error(f"Błąd: {e}")
            else:
                st.error("Brak kategorii.")

        with col_del:
            st.subheader("Usuń produkt")
            prod_to_del = st.selectbox("Wybierz do usunięcia", options=df['Nazwa'].tolist())
            if st.button("Usuń trwale", type="primary"):
                target_id = df[df['Nazwa'] == prod_to_del]['id'].values[0]
                supabase.table("Produkty").delete().eq("id", target_id).execute()
                st.cache_data.clear()
                st.rerun()

    # --- TAB 4: RAPORTY ---
    with tab4:
        st.header("Eksport danych")
        st.write("Pobierz aktualny stan magazynowy w formacie CSV, który otworzysz w Excelu.")
        
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Pobierz raport CSV",
            data=csv,
            file_name='stan_magazynu.csv',
            mime='text/csv',
        )
else:
    st.info("Baza jest pusta. Dodaj pierwszy produkt w zakładce 'Dodaj/Usuń'.")
