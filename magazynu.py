import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Magazyn Pro v6", layout="wide", page_icon="🏢")

# --- POŁĄCZENIE Z BAZĄ ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Błąd konfiguracji: {e}")
        st.stop()

supabase = init_connection()

# --- FUNKCJE DANYCH ---
@st.cache_data(ttl=60)
def get_data(table_name):
    return supabase.table(table_name).select("*").execute().data

def log_sale(product_id, product_name, quantity, total_price):
    """Rejestruje sprzedaż i aktualizuje magazyn."""
    # 1. Dodaj do tabeli Sprzedaz
    supabase.table("Sprzedaz").insert({
        "produkt_id": product_id,
        "nazwa_produktu": product_name,
        "ilosc": quantity,
        "cena_calkowita": total_price
    }).execute()
    
    # 2. Pobierz aktualny stan
    res = supabase.table("Produkty").select("Liczba").eq("id", product_id).execute()
    current_stock = res.data[0]['Liczba']
    
    # 3. Aktualizuj stan
    supabase.table("Produkty").update({"Liczba": current_stock - quantity}).eq("id", product_id).execute()
    st.cache_data.clear()

# --- UI ---
st.title("🏢 Magazyn & Sprzedaż Enterprise")

products = get_data("Produkty")
categories = get_data("Kategorie")
sales = get_data("Sprzedaz")

if products:
    df_prod = pd.DataFrame(products)
    df_sales = pd.DataFrame(sales) if sales else pd.DataFrame()

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Dashboard", "🛒 Sprzedaż (Kasa)", "📦 Magazyn", "📜 Historia", "⚙️ Admin"
    ])

    # --- TAB 1: DASHBOARD (Analityka) ---
    with tab1:
        col1, col2, col3 = st.columns(3)
        total_val = (df_prod['Liczba'] * df_prod['Cena']).sum()
        
        col1.metric("Wartość towaru", f"{total_val:,.2f} zł")
        if not df_sales.empty:
            total_revenue = df_sales['cena_calkowita'].sum()
            col2.metric("Przychód całkowity", f"{total_revenue:,.2f} zł", delta=f"{len(df_sales)} transakcji")
        
        st.subheader("Popularność produktów (sprzedaż)")
        if not df_sales.empty:
            sales_chart = df_sales.groupby('nazwa_produktu')['ilosc'].sum().sort_values(ascending=False)
            st.bar_chart(sales_chart)

    # --- TAB 2: SPRZEDAŻ (Nowość) ---
    with tab2:
        st.header("🛒 Panel Kasjera")
        col_s1, col_s2 = st.columns([2, 1])
        
        with col_s1:
            selected_p_name = st.selectbox("Wybierz produkt do sprzedaży", df_prod['Nazwa'].tolist())
            product_row = df_prod[df_prod['Nazwa'] == selected_p_name].iloc[0]
            
            max_qty = int(product_row['Liczba'])
            st.info(f"Dostępność: {max_qty} szt. | Cena jedn.: {product_row['Cena']:.2f} zł")
            
            sale_qty = st.number_input("Ilość", min_value=1, max_value=max_qty if max_qty > 0 else 1, step=1)
            total_p = sale_qty * product_row['Cena']
            
        with col_s2:
            st.write("### Podsumowanie")
            st.write(f"Do zapłaty: **{total_p:.2f} zł**")
            if max_qty <= 0:
                st.error("Brak towaru na stanie!")
            elif st.button("Potwierdź Sprzedaż", type="primary", use_container_width=True):
                log_sale(product_row['id'], selected_p_name, sale_qty, total_p)
                st.success("Sprzedano!")
                st.rerun()

    # --- TAB 3: MAGAZYN ---
    with tab3:
        st.header("📦 Zarządzanie stanami")
        st.dataframe(df_prod[['Nazwa', 'Liczba', 'Cena']], use_container_width=True)
        # Tu można zostawić Twoją poprzednią logikę kart z pętlą for

    # --- TAB 4: HISTORIA (Archiwizacja) ---
    with tab4:
        st.header("📜 Historia Operacji")
        if not df_sales.empty:
            df_sales['created_at'] = pd.to_datetime(df_sales['created_at'])
            st.dataframe(df_sales.sort_values('created_at', ascending=False), use_container_width=True)
            
            # Eksport do CSV
            csv = df_sales.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Pobierz raport sprzedaży (CSV)", csv, "raport_sprzedazy.csv", "text/csv")
        else:
            st.info("Brak zarejestrowanych sprzedaży.")

    # --- TAB 5: ADMIN ---
    with tab5:
        # Przenieś tutaj formularze dodawania i usuwania produktów
        st.subheader("Zarządzanie bazą danych")
        if st.button("Wyczyść pamięć podręczną (Cache)"):
            st.cache_data.clear()
            st.rerun()
