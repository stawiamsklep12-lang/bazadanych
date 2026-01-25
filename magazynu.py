import streamlit as st
import pandas as pd
from supabase import create_client, Client
from postgrest.exceptions import APIError

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Magazyn Pro Ultra", layout="wide", page_icon="💎")

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

# --- FUNKCJE DANYCH ---
@st.cache_data(ttl=600)
def get_categories():
    return supabase.table("Kategorie").select("id, Nazwa").execute().data

@st.cache_data(ttl=600)
def get_products():
    return supabase.table("Produkty").select("id, Nazwa, Liczba, Cena, Kategoria_id").execute().data

def update_stock(product_id, current_stock, change):
    new_stock = max(0, current_stock + change)
    supabase.table("Produkty").update({"Liczba": new_stock}).eq("id", product_id).execute()
    st.cache_data.clear()
    st.rerun()

# --- INTERFEJS ---
st.title("💎 Magazyn Pro Ultra")

products = get_products()
categories = get_categories()

if products:
    df = pd.DataFrame(products)
    
    # --- BOCZNY PANEL STATYSTYK ---
    with st.sidebar:
        st.header("📊 Statystyki Szybkie")
        val = (df['Liczba'] * df['Cena']).sum()
        st.metric("Wartość Całkowita", f"{val:,.2f} zł")
        st.write("---")
        st.subheader("Bestsellery (Top 3)")
        top_3 = df.nlargest(3, 'Liczba')
        for _, r in top_3.iterrows():
            st.caption(f"{r['Nazwa']}: {int(r['Liczba'])} szt.")

    tab1, tab2, tab3, tab4 = st.tabs(["🚀 Centrum Dowodzenia", "📦 Zarządzanie Zapasami", "🛠️ Ustawienia Produktów", "📈 Raporty Analityczne"])

    # --- TAB 1: DASHBOARD ---
    with tab1:
        c1, c2, c3 = st.columns(3)
        low_stock = df[df['Liczba'] < 10]
        out_of_stock = df[df['Liczba'] == 0]
        
        c1.metric("Wszystkie SKU", len(df))
        c2.metric("Niskie stany", len(low_stock), delta="- Braki!", delta_color="inverse" if len(low_stock) > 0 else "normal")
        c3.metric("Brak na stanie", len(out_of_stock))

        if not low_stock.empty:
            st.error("🚨 Krytyczne braki! Należy niezwłocznie zamówić poniższe produkty.")
            st.table(low_stock[['Nazwa', 'Liczba']])

    # --- TAB 2: ZARZĄDZANIE ZAPASAMI (UX PREMIUM) ---
    with tab2:
        col_search, col_sort = st.columns([3, 1])
        search = col_search.text_input("🔍 Szybkie szukanie...", placeholder="Wpisz nazwę produktu...")
        sort_order = col_sort.selectbox("Sortuj według", ["Nazwa", "Liczba (Rosnąco)", "Liczba (Malejąco)", "Cena"])

        # Logika filtrowania i sortowania
        df_f = df[df['Nazwa'].str.contains(search, case=False)]
        if "Rosnąco" in sort_order: df_f = df_f.sort_values("Liczba")
        elif "Malejąco" in sort_order: df_f = df_f.sort_values("Liczba", ascending=False)
        elif "Cena" in sort_order: df_f = df_f.sort_values("Cena", ascending=False)

        for _, row in df_f.iterrows():
            with st.container(border=True):
                cols = st.columns([1, 2, 2, 2, 2])
                
                # 1. Status wizualny
                if row['Liczba'] == 0: status = "🔴 Brak"
                elif row['Liczba'] < 10: status = "🟡 Niski"
                else: status = "🟢 OK"
                cols[0].write(status)
                
                # 2. Informacje o produkcie
                cols[1].write(f"**{row['Nazwa']}**")
                cols[1].caption(f"ID: {row['id']}")
                
                # 3. Dane finansowe
                cols[2].write(f"Cena: {row['Cena']:.2f} zł")
                cols[2].write(f"Wartość: {row['Cena']*row['Liczba']:.2f} zł")
                
                # 4. Pasek postępu
                prog = min(row['Liczba'] / 50, 1.0) # Zakładamy 50 jako optymalny stan
                cols[3].write(f"Stan: {int(row['Liczba'])} szt.")
                cols[3].progress(prog)
                
                # 5. Kontrola
                with cols[4]:
                    cc1, cc2, cc3 = st.columns([1.5, 1, 1])
                    change = cc1.number_input("Ile", min_value=1, value=1, key=f"v_{row['id']}", label_visibility="collapsed")
                    if cc2.button("➕", key=f"p_{row['id']}"): update_stock(row['id'], row['Liczba'], change)
                    if cc3.button("➖", key=f"m_{row['id']}"): update_stock(row['id'], row['Liczba'], -change)

    # --- TAB 3: USTAWIENIA (DODAWANIE / USUWANIE) ---
    with tab3:
        with st.expander("➕ Dodaj nowy produkt do systemu", expanded=False):
            if categories:
                cat_map = {c['Nazwa']: c['id'] for c in categories}
                with st.form("new_form"):
                    n = st.text_input("Pełna nazwa produktu")
                    c1, c2 = st.columns(2)
                    l = c1.number_input("Stan początkowy", min_value=0)
                    p = c2.number_input("Cena sprzedaży (netto)", min_value=0.0)
                    k = st.selectbox("Kategoria", list(cat_map.keys()))
                    if st.form_submit_button("Zatwierdź i wprowadź na stan"):
                        supabase.table("Produkty").insert({"Nazwa":n, "Liczba":l, "Cena":p, "Kategoria_id":cat_map[k]}).execute()
                        st.cache_data.clear()
                        st.rerun()

        with st.expander("🗑️ Usuwanie i czyszczenie bazy"):
            to_del = st.selectbox("Wybierz produkt do usunięcia", df['Nazwa'].tolist())
            if st.button("USUŃ TRWALE", type="primary"):
                tid = df[df['Nazwa'] == to_del]['id'].values[0]
                supabase.table("Produkty").delete().eq("id", tid).execute()
                st.cache_data.clear()
                st.rerun()

    # --- TAB 4: RAPORTY ---
    with tab4:
        st.header("Analityka Magazynowa")
        col_r1, col_r2 = st.columns(2)
        
        with col_r1:
            st.subheader("Udział wartościowy kategorii")
            # Tutaj można by dodać join z kategoriami dla lepszego wykresu
            st.pie_chart(df, values='Cena', names='Nazwa')
        
        with col_r2:
            st.subheader("Eksport danych")
            st.write("Wygeneruj raport w formacie CSV gotowy do otwarcia w Excelu.")
            st.download_button("📥 Pobierz Pełny Raport CSV", df.to_csv(index=False).encode('utf-8'), "raport_magazyn.csv", "text/csv")

else:
    st.warning("Baza danych jest pusta. Użyj zakładki 'Ustawienia', aby dodać produkty.")
