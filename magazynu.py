import streamlit as st
import pandas as pd
from supabase import create_client, Client

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Magazyn Pro v6", layout="wide", page_icon="📦")

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
    # Pobieramy dane z złączeniem (jeśli Supabase pozwala) lub czyste dane
    res = supabase.table("Produkty").select("*").execute()
    return res.data

# --- FUNKCJE OPERACYJNE ---
def update_stock(product_id, current_stock, change):
    new_stock = max(0, current_stock + change)
    try:
        supabase.table("Produkty").update({"Liczba": new_stock}).eq("id", product_id).execute()
        st.cache_data.clear()
        st.rerun()
    except Exception as e:
        st.error(f"Błąd aktualizacji: {e}")

# --- PRZYGOTOWANIE DANYCH ---
products = get_products()
categories = get_categories()
df = pd.DataFrame(products) if products else pd.DataFrame()
cat_df = pd.DataFrame(categories) if categories else pd.DataFrame()

# --- INTERFEJS ---
st.title("🚀 System Zarządzania Magazynem")

tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "📦 Magazyn", "🔧 Administracja", "📄 Raporty"])

if not df.empty:
    # --- TAB 1: DASHBOARD ---
    with tab1:
        low_stock_limit = 10
        low_stock_items = df[df['Liczba'] < low_stock_limit]
        
        if not low_stock_items.empty:
            st.error(f"🚨 ALERM: {len(low_stock_items)} produktów wymaga zamówienia!")
        
        col1, col2, col3, col4 = st.columns(4)
        total_val = (df['Liczba'] * df['Cena']).sum()
        col1.metric("Wartość towaru", f"{total_val:,.2f} zł")
        col2.metric("Suma sztuk", f"{int(df['Liczba'].sum())}")
        col3.metric("Liczba SKU", len(df))
        col4.metric("Kategorie", len(cat_df))

        st.divider()
        c_left, c_right = st.columns(2)
        
        with c_left:
            st.subheader("Stan ilościowy")
            st.bar_chart(df.set_index('Nazwa')['Liczba'])
        
        with c_right:
            st.subheader("Wartość wg kategorii")
            if not cat_df.empty:
                m_df = df.merge(cat_df.rename(columns={'id': 'Kategoria_id', 'Nazwa': 'Kat_Nazwa'}), on='Kategoria_id')
                m_df['Suma'] = m_df['Liczba'] * m_df['Cena']
                cat_chart = m_df.groupby('Kat_Nazwa')['Suma'].sum()
                st.bar_chart(cat_chart)

    # --- TAB 2: MAGAZYN & KONTROLA ---
    with tab2:
        st.header("Kontrola towaru")
        
        f_col1, f_col2 = st.columns([1, 2])
        with f_col1:
            cat_filter = ["Wszystkie"] + cat_df['Nazwa'].tolist() if not cat_df.empty else ["Wszystkie"]
            sel_cat = st.selectbox("Filtruj kategorię", cat_filter)
        with f_col2:
            search = st.text_input("Szukaj nazwy...", placeholder="Wpisz min. 3 znaki")

        # Filtrowanie
        display_df = df.copy()
        if sel_cat != "Wszystkie":
            target_id = cat_df[cat_df['Nazwa'] == sel_cat]['id'].values[0]
            display_df = display_df[display_df['Kategoria_id'] == target_id]
        if search:
            display_df = display_df[display_df['Nazwa'].str.contains(search, case=False)]

        for _, row in display_df.iterrows():
            with st.expander(f"📦 {row['Nazwa']} (Obecnie: {row['Liczba']} szt.)", expanded=True):
                c1, c2, c3 = st.columns([3, 2, 2])
                c1.write(f"**Cena jedn:** {row['Cena']:.2f} zł | **Wartość:** {row['Cena']*row['Liczba']:.2f} zł")
                
                # Szybka zmiana stanu
                amt = c2.number_input("Ilość", min_value=1, value=1, key=f"amt_{row['id']}")
                btn_col1, btn_col2 = c3.columns(2)
                if btn_col1.button("➕", key=f"add_{row['id']}", use_container_width=True):
                    update_stock(row['id'], row['Liczba'], amt)
                if btn_col2.button("➖", key=f"sub_{row['id']}", use_container_width=True):
                    update_stock(row['id'], row['Liczba'], -amt)

    # --- TAB 3: ADMINISTRACJA ---
    with tab3:
        st.subheader("Zarządzanie bazą danych")
        
        col_add, col_del = st.columns(2)
        with col_add:
            st.info("Dodaj nowy produkt")
            with st.form("add_form", clear_on_submit=True):
                new_n = st.text_input("Nazwa produktu")
                new_l = st.number_input("Stan początkowy", min_value=0)
                new_c = st.number_input("Cena netto", min_value=0.0)
                new_k = st.selectbox("Kategoria", cat_df['Nazwa'].tolist() if not cat_df.empty else [])
                
                if st.form_submit_button("Zapisz w bazie"):
                    k_id = cat_df[cat_df['Nazwa'] == new_k]['id'].values[0]
                    supabase.table("Produkty").insert({
                        "Nazwa": new_n, "Liczba": new_l, "Cena": new_c, "Kategoria_id": k_id
                    }).execute()
                    st.cache_data.clear()
                    st.rerun()

        with col_del:
            st.warning("Usuwanie produktów")
            del_prod = st.selectbox("Wybierz produkt do usunięcia", df['Nazwa'].tolist())
            if st.button("Usuń bezpowrotnie", type="primary"):
                target_id = df[df['Nazwa'] == del_prod]['id'].values[0]
                supabase.table("Produkty").delete().eq("id", target_id).execute()
                st.cache_data.clear()
                st.rerun()
        
        st.divider()
        st.caption(f"Wykorzystanie limitu darmowej bazy (Supabase): {len(df)} wierszy.")

    # --- TAB 4: RAPORTY ---
    with tab4:
        st.subheader("Eksport danych")
        st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Pobierz plik CSV", csv, "magazyn_eksport.csv", "text/csv")

else:
    st.warning("Magazyn jest pusty. Przejdź do zakładki Administracja, aby dodać pierwsze produkty.")
