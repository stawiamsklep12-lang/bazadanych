import streamlit as st
import pandas as pd
from supabase import create_client, Client

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Magazyn Pro v8", layout="wide", page_icon="🚀")

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
    try:
        res = supabase.table("Kategorie").select("id, Nazwa").execute()
        return res.data
    except:
        return []

@st.cache_data(ttl=600)
def get_products():
    try:
        res = supabase.table("Produkty").select("*").execute()
        return res.data
    except:
        return []

# --- FUNKCJE OPERACYJNE ---
def update_stock(product_id, current_stock, change):
    # Rzutowanie na natywne typy Pythona (int), aby uniknąć błędów JSON
    new_stock = int(max(0, current_stock + change))
    try:
        supabase.table("Produkty").update({"Liczba": new_stock}).eq("id", int(product_id)).execute()
        st.cache_data.clear()
        st.rerun()
    except Exception as e:
        st.error(f"Błąd aktualizacji stanu: {e}")

def update_price(product_id, new_price):
    try:
        # Rzutowanie na float dla typu numeric w bazie
        supabase.table("Produkty").update({"Cena": float(new_price)}).eq("id", int(product_id)).execute()
        st.cache_data.clear()
        st.rerun()
    except Exception as e:
        st.error(f"Błąd aktualizacji ceny: {e}")

# --- PRZYGOTOWANIE DANYCH ---
products = get_products()
categories = get_categories()
df = pd.DataFrame(products) if products else pd.DataFrame()
cat_df = pd.DataFrame(categories) if categories else pd.DataFrame()

# Łączenie danych dla czytelności (Join Kategorii)
if not df.empty and not cat_df.empty:
    df_full = df.merge(cat_df, left_on='Kategoria_id', right_on='id', suffixes=('', '_kat'))
else:
    df_full = df

# --- LOGIKA ALERTÓW ---
low_stock_threshold = 10
notifications = []
if not df.empty:
    low_stock_df = df[df['Liczba'] < low_stock_threshold]
    for _, row in low_stock_df.iterrows():
        notifications.append({
            "Produkt": row['Nazwa'],
            "Stan": row['Liczba'],
            "Priorytet": "🔴 WYSOKI" if row['Liczba'] <= 3 else "🟡 ŚREDNI"
        })

# --- INTERFEJS ---
st.title("🚀 System Magazynowy Pro v8")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Analizy", 
    "📦 Magazyn", 
    "📥 Zaopatrzenie", 
    "🔧 Administracja", 
    "📄 Raporty"
])

# --- TAB 1: DASHBOARD (ANALIZY) ---
with tab1:
    if not df.empty:
        col1, col2, col3, col4 = st.columns(4)
        total_val = (df['Liczba'] * df['Cena']).sum()
        out_of_stock = len(df[df['Liczba'] == 0])
        
        col1.metric("Wartość towaru", f"{total_val:,.2f} zł")
        col2.metric("Suma sztuk", f"{int(df['Liczba'].sum())}")
        col3.metric("Alerty", len(notifications), delta=out_of_stock, delta_color="inverse")
        col4.metric("Średnia cena", f"{df['Cena'].mean():.2f} zł")

        st.divider()
        c1, c2 = st.columns([2, 1])
        with c1:
            st.subheader("Stan ilościowy produktów")
            st.bar_chart(df.set_index('Nazwa')['Liczba'])
        with c2:
            st.subheader("Podział wg kategorii")
            if not cat_df.empty and 'Nazwa_kat' in df_full.columns:
                cat_counts = df_full.groupby('Nazwa_kat')['Liczba'].sum()
                st.info("Udział sztuk w kategoriach")
                st.bar_chart(cat_counts)
    else:
        st.info("Brak danych do wyświetlenia analiz.")

# --- TAB 2: MAGAZYN & KONTROLA ---
with tab2:
    if not df.empty:
        search = st.text_input("Szukaj produktu...", placeholder="Wpisz nazwę produktu...")
        display_df = df[df['Nazwa'].str.contains(search, case=False)] if search else df

        for _, row in display_df.iterrows():
            if row['Liczba'] == 0: status_icon = "🔴 BRAK"
            elif row['Liczba'] < low_stock_threshold: status_icon = "🟡 NISKI"
            else: status_icon = "🟢 OK"
            
            with st.expander(f"{status_icon} | {row['Nazwa']} (Stan: {row['Liczba']})"):
                c1, c2, c3 = st.columns([3, 2, 2])
                c1.write(f"**Cena:** {row['Cena']:.2f} zł")
                amt = c2.number_input("Ilość", min_value=1, value=1, key=f"amt_{row['id']}")
                if c3.button("Dodaj", key=f"add_{row['id']}", use_container_width=True): 
                    update_stock(row['id'], row['Liczba'], amt)
                if c3.button("Odejmij", key=f"sub_{row['id']}", use_container_width=True): 
                    update_stock(row['id'], row['Liczba'], -amt)
    else:
        st.info("Magazyn jest pusty.")

# --- TAB 3: ZAOPATRZENIE ---
with tab3:
    st.header("📥 Panel Zaopatrzeniowca")
    if not notifications:
        st.success("Wszystkie stany magazynowe w normie.")
    else:
        st.warning(f"Masz {len(notifications)} pozycji do uzupełnienia.")
        shop_list_text = "LISTA ZAKUPÓW:\n" + "\n".join([f"- {m['Produkt']}: {m['Stan']} szt. (Priorytet: {m['Priorytet']})" for m in notifications])
        st.download_button("Pobierz listę zakupów", shop_list_text, "zakupy.txt")
        
        for msg in notifications:
            with st.chat_message("user"):
                st.write(f"Produkt: **{msg['Produkt']}** | Stan: `{msg['Stan']} szt.`")
                st.caption(f"Status: {msg['Priorytet']}")

# --- TAB 4: ADMINISTRACJA ---
with tab4:
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Nowy produkt")
        with st.form("add_form", clear_on_submit=True):
            n = st.text_input("Nazwa produktu")
            l = st.number_input("Ilość początkowa", min_value=0, step=1)
            c = st.number_input("Cena jednostkowa", min_value=0.0, step=0.01)
            opcje_kat = cat_df['Nazwa'].tolist() if not cat_df.empty else []
            k = st.selectbox("Wybierz kategorię", opcje_kat)
            
            if st.form_submit_button("Dodaj do bazy"):
                if n and k:
                    try:
                        k_id = int(cat_df[cat_df['Nazwa'] == k]['id'].values[0])
                        payload = {
                            "Nazwa": str(n),
                            "Liczba": int(l),
                            "Cena": float(c),
                            "Kategoria_id": k_id
                        }
                        supabase.table("Produkty").insert(payload).execute()
                        st.cache_data.clear()
                        st.success(f"Dodano produkt: {n}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Błąd zapisu: {e}")
                else:
                    st.warning("Uzupełnij nazwę i wybierz kategorię.")
    
    with col_b:
        st.subheader("Edytuj cenę")
        if not df.empty:
            with st.form("price_form"):
                p_name = st.selectbox("Wybierz produkt do zmiany ceny", df['Nazwa'].tolist())
                new_p = st.number_input("Nowa cena (zł)", min_value=0.0, step=0.01)
                if st.form_submit_button("Zastosuj nową cenę"):
                    p_id = df[df['Nazwa'] == p_name]['id'].values[0]
                    update_price(p_id, new_p)
        else:
            st.info("Brak produktów do edycji.")

# --- TAB 5: RAPORTY ---
with tab5:
    st.subheader("Pełna ewidencja")
    if not df_full.empty:
        if not cat_df.empty:
            f_kat = st.multiselect("Filtruj wg kategorii", cat_df['Nazwa'].unique())
            df_to_show = df_full[df_full['Nazwa_kat'].isin(f_kat)] if f_kat else df_full
        else:
            df_to_show = df_full

        st.dataframe(df_to_show, use_container_width=True)
        csv = df_to_show.to_csv(index=False).encode('utf-8')
        st.download_button("Eksportuj do CSV", csv, "magazyn_raport.csv", "text/csv")
    else:
        st.info("Brak danych do wygenerowania raportu.")
