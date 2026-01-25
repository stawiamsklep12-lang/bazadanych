import streamlit as st
import pandas as pd
from supabase import create_client, Client

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Magazyn Pro v7", layout="wide", page_icon="📦")

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

# --- LOGIKA POWIADOMIEŃ DLA TOMASZA ---
low_stock_threshold = 10
notifications = []
if not df.empty:
    low_stock_df = df[df['Liczba'] < low_stock_threshold]
    for _, row in low_stock_df.iterrows():
        notifications.append({
            "Odbiorca": "Zaopatrzeniowiec Tomasz",
            "Produkt": row['Nazwa'],
            "Stan": row['Liczba'],
            "Priorytet": "Wysoki" if row['Liczba'] <= 3 else "Normalny"
        })

# --- INTERFEJS ---
st.title("🚀 System Zarządzania Magazynem")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Dashboard", 
    "📦 Magazyn", 
    "📥 Wiadomości", 
    "🔧 Administracja", 
    "📄 Raporty"
])

if not df.empty:
    # --- TAB 1: DASHBOARD ---
    with tab1:
        col1, col2, col3 = st.columns(3)
        total_val = (df['Liczba'] * df['Cena']).sum()
        col1.metric("Wartość towaru", f"{total_val:,.2f} zł")
        col2.metric("Suma sztuk", f"{int(df['Liczba'].sum())}")
        col3.metric("Alerty", len(notifications))

        st.divider()
        st.subheader("Analiza struktury")
        st.bar_chart(df.set_index('Nazwa')['Liczba'])

    # --- TAB 2: MAGAZYN & KONTROLA ---
    with tab2:
        search = st.text_input("Szukaj produktu...", placeholder="Wpisz nazwę...")
        display_df = df[df['Nazwa'].str.contains(search, case=False)] if search else df

        for _, row in display_df.iterrows():
            with st.expander(f"📦 {row['Nazwa']} (Stan: {row['Liczba']})"):
                c1, c2, c3 = st.columns([3, 2, 2])
                c1.write(f"**Cena:** {row['Cena']:.2f} zł")
                amt = c2.number_input("Ilość", min_value=1, value=1, key=f"amt_{row['id']}")
                if c3.button("Dodaj", key=f"add_{row['id']}"): update_stock(row['id'], row['Liczba'], amt)
                if c3.button("Odejmij", key=f"sub_{row['id']}"): update_stock(row['id'], row['Liczba'], -amt)

    # --- TAB 3: SKRZYNKA WIADOMOŚCI (NOWOŚĆ) ---
    with tab5: # Przesunięte dla Tomasza
        pass 

    with tab3:
        st.header("📥 Skrzynka odbiorcza: Zaopatrzeniowiec Tomasz")
        if not notifications:
            st.success("Wszystkie stany magazynowe w normie. Brak nowych wiadomości.")
        else:
            st.info(f"Masz {len(notifications)} nowych powiadomień o niskim stanie zapasów.")
            for msg in notifications:
                with st.chat_message("user"):
                    st.write(f"**DO:** {msg['Odbiorca']}")
                    st.write(f"**TREŚĆ:** Produkt **{msg['Produkt']}** jest na wyczerpaniu. Obecny stan: **{msg['Stan']} szt.**")
                    st.caption(f"Priorytet: {msg['Priorytet']}")
                    if st.button(f"Potwierdź odbiór dla {msg['Produkt']}", key=f"msg_{msg['Produkt']}"):
                        st.toast(f"Powiadomienie dla {msg['Produkt']} zostało zarchiwizowane.")

    # --- TAB 4: ADMINISTRACJA ---
    with tab4:
        st.subheader("Zarządzanie produktami")
        with st.form("add_form"):
            n = st.text_input("Nazwa")
            l = st.number_input("Ilość", min_value=0)
            c = st.number_input("Cena", min_value=0.0)
            k = st.selectbox("Kategoria", cat_df['Nazwa'].tolist() if not cat_df.empty else [])
            if st.form_submit_button("Dodaj produkt"):
                k_id = cat_df[cat_df['Nazwa'] == k]['id'].values[0]
                supabase.table("Produkty").insert({"Nazwa": n, "Liczba": l, "Cena": c, "Kategoria_id": k_id}).execute()
                st.cache_data.clear()
                st.rerun()

    # --- TAB 5: RAPORTY ---
    with tab5:
        st.dataframe(df, use_container_width=True)
        st.download_button("Eksportuj do CSV", df.to_csv(index=False).encode('utf-8'), "raport.csv")

else:
    st.info("Brak produktów w bazie.")
