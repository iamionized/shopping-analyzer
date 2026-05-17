import streamlit as st
import pandas as pd
import json
import os
import glob

# --- Data Loading and Preparation ---

def load_all_data():
    df_list = []
    
    # Find all json files matching the pattern lidl_receipts_COUNTRY_ACCOUNT.json
    receipt_files = glob.glob("lidl_receipts_*.json")
    
    if not receipt_files:
        st.error("Fehler: Keine Kassenbon-Dateien gefunden. Bitte Daten abrufen.")
        return None
        
    for file in receipt_files:
        try:
            clean_name = file.replace("lidl_receipts_", "").replace(".json", "")
            parts = clean_name.split("_")
            
            country = parts[0].upper() if len(parts) >= 1 else "DE"
            account = parts[1].capitalize() if len(parts) >= 2 else "Main"
            
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if data:
                    df_temp = pd.DataFrame(data)
                    if not df_temp.empty:
                        df_temp['Land'] = country
                        df_temp['Konto'] = account
                        df_list.append(df_temp)
        except Exception as e:
            st.error(f"Fehler beim Laden von {file}: {e}")
            
    if not df_list:
        return None
        
    return pd.concat(df_list, ignore_index=True)

# Load the data
df = load_all_data()

# --- Main Application Logic ---
if df is not None:

    # --- Data Cleaning and Transformation ---
    def to_float(x):
        if x is None or x == '' or str(x).strip() == '':
            return 0.0
        return float(str(x).replace(',', '.'))

    # Apply conversions
    df['purchase_date'] = pd.to_datetime(df['purchase_date'], format='%Y.%m.%d')
    df['total_price'] = df['total_price'].apply(to_float)
    df['saved_amount'] = df['saved_amount'].apply(to_float)
    df['lidlplus_saved_amount'] = df['lidlplus_saved_amount'].apply(to_float) if 'lidlplus_saved_amount' in df.columns else 0.0
    
    # Handle sticker discounts (RABATT X%) if present
    if 'sticker_discount_amount' in df.columns:
        df['sticker_discount_amount'] = df['sticker_discount_amount'].apply(to_float)
    else:
        df['sticker_discount_amount'] = 0.0

    # --- Data Filtering ---
    initial_count = len(df)
    
    df = df[df['items'].notna()]  # Remove null items
    df = df[df['items'].apply(lambda x: isinstance(x, list) and len(x) > 0)]  # Remove empty arrays
    
    filtered_count = len(df)
    filtered_out = initial_count - filtered_count
    
    if filtered_out > 0:
        st.info(f"Info: Kassenbons ({filtered_out}) wurden herausgefiltert. Entweder hatten sie keinen Gesamtpreis oder keine Artikel. Kassenbons vor Februar 2023 sind möglicherweise betroffen.")

    # --- Streamlit Dashboard ---
    st.set_page_config(layout="wide", page_title="Lidl Kassenbons Dashboard", page_icon="🛒")

    st.title("Lidl+ Dashboard")

    # --- Sidebar for Filters ---
    st.sidebar.header("Nach Konto filtern")
    accounts = ["Alle"] + sorted(df['Konto'].unique().tolist())
    account_filter = st.sidebar.radio("Konto:", accounts)
    
    if account_filter != "Alle":
        df = df[df['Konto'] == account_filter]

    st.sidebar.header("Nach Land filtern")
    countries = ["Alle"] + sorted(df['Land'].unique().tolist())
    country_filter = st.sidebar.radio("Land:", countries)
    
    if country_filter != "Alle":
        df = df[df['Land'] == country_filter]

    st.sidebar.header("Nach Datum filtern")
    min_date = df['purchase_date'].min().date()
    max_date = df['purchase_date'].max().date()

    start_date = st.sidebar.date_input("Startdatum", min_date, min_value=min_date, max_value=max_date)
    end_date = st.sidebar.date_input("Enddatum", max_date, min_value=min_date, max_value=max_date)

    start_datetime = pd.to_datetime(start_date)
    end_datetime = pd.to_datetime(end_date) + pd.Timedelta(days=1)

    filtered_df = df[(df['purchase_date'] >= start_datetime) & (df['purchase_date'] < end_datetime)]

    # --- Main Page ---
    st.header("Kennzahlen")

    total_receipts = len(filtered_df)
    total_spent = filtered_df['total_price'].sum()
    total_saved = filtered_df['saved_amount'].sum()
    sticker_saved = filtered_df['sticker_discount_amount'].sum() if 'sticker_discount_amount' in filtered_df.columns else 0.0
    
    if 'lidlplus_saved_amount' in filtered_df.columns:
        lidlplus_saved = filtered_df['lidlplus_saved_amount'].sum()
    else:
        lidlplus_saved = 0

    st.markdown("##### Grunddaten")
    col1, col2 = st.columns(2)
    col1.metric("Ausgaben gesamt", f"€{total_spent:,.2f}")
    col2.metric("Kassenbons gesamt", f"{total_receipts}")
    
    st.markdown("##### Lidl Plus Ersparnisse")
    col1, col2 = st.columns(2)
    lidlplus_percentage = (lidlplus_saved / total_spent * 100) if total_spent > 0 else 0
    col1.metric("Lidl Plus gespart", f"€{lidlplus_saved:,.2f}")
    col2.metric("Lidl Plus Sparquote", f"{lidlplus_percentage:.1f}%")
    
    st.markdown("##### Reguläre Rabatte")
    col1, col2 = st.columns(2)
    regular_percentage = (total_saved / total_spent * 100) if total_spent > 0 else 0
    col1.metric("Reguläre Rabatte gespart", f"€{total_saved:,.2f}")
    col2.metric("Reguläre Sparquote", f"{regular_percentage:.1f}%")

    st.markdown("##### Sticker Rabatte (RABATT X%)")
    col1, col2 = st.columns(2)
    sticker_percentage = (sticker_saved / total_spent * 100) if total_spent > 0 else 0
    col1.metric("Sticker Rabatte gespart", f"€{sticker_saved:,.2f}")
    col2.metric("Sticker Sparquote", f"{sticker_percentage:.1f}%")

    st.markdown("---")

    # --- Spending Over Time ---
    st.header("Ausgaben über Zeit")
    
    if not filtered_df.empty:
        color_by = st.radio("Graph einfärben nach:", ["Konto", "Land"], horizontal=True)
        
        spending_over_time = filtered_df.copy()
        spending_over_time['date'] = spending_over_time['purchase_date'].dt.date
        
        daily_spending = spending_over_time.groupby(['date', color_by])['total_price'].sum().reset_index()
        daily_chart_data = daily_spending.pivot(index='date', columns=color_by, values='total_price').fillna(0)
        
        daily_spending_sorted = daily_spending.sort_values('date')
        daily_spending_sorted['Kumulative Ausgaben'] = daily_spending_sorted.groupby(color_by)['total_price'].cumsum()
        
        cum_chart_data = daily_spending_sorted.pivot(index='date', columns=color_by, values='Kumulative Ausgaben')
        cum_chart_data = cum_chart_data.ffill().fillna(0)
        
        spending_view = st.radio("Ausgabenansicht:", ["Täglich", "Kumulativ"], horizontal=True, key="spending_view")
        
        if spending_view == "Täglich":
            st.bar_chart(daily_chart_data)
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Durchschnittlicher Einkaufswert", f"€{filtered_df['total_price'].mean():.2f}")
            col2.metric("Höchster Einkaufswert", f"€{filtered_df['total_price'].max():.2f}")
            col3.metric("Niedrigster Einkaufswert", f"€{filtered_df['total_price'].min():.2f}")
            
        else:  # Cumulative view
            st.bar_chart(cum_chart_data)
            
            total_days = len(spending_over_time['date'].unique())
            total_spent_all = filtered_df['total_price'].sum()
            avg_daily_growth = total_spent_all / total_days if total_days > 0 else 0
            
            col1, col2 = st.columns(2)
            col1.metric("Tage mit Einkäufen", total_days)
            col2.metric("Durchschn. Ausgaben pro Einkaufstag", f"€{avg_daily_growth:.2f}")
    else:
        st.write("Keine Ausgabendaten für den ausgewählten Datumsbereich verfügbar.")

    st.markdown("---")

    # --- Top 10 Most Purchased Items ---
    st.header("Top 10 der meistgekauften Artikel")
    
    if not filtered_df.empty:
        view_mode = st.radio("Anzeigen nach:", ["Menge", "Gesamtpreis"], horizontal=True)
        
        items_data = []
        for _, row in filtered_df.iterrows():
            if row.get('items') and isinstance(row['items'], list):
                for item in row['items']:
                    try:
                        quantity_str = str(item.get('quantity', 1))
                        quantity = float(quantity_str.replace(',', '.'))
                        price = to_float(item.get('price', 0))
                        unit = item.get('unit', 'stk')
                    except (ValueError, TypeError):
                        quantity = 1.0
                        price = 0
                        unit = 'stk'
                    
                    items_data.append({
                        'name': item['name'],
                        'quantity': quantity,
                        'price': price,
                        'unit': unit,
                        'total_value': quantity * price
                    })

        if items_data:
            items_df = pd.DataFrame(items_data)
            items_df = items_df[~items_df['name'].str.contains('Pfand', case=False, na=False)]
            
            if view_mode == "Menge":
                grouped = items_df.groupby('name').agg({'quantity': 'sum', 'unit': 'first'}).reset_index()
                grouped = grouped.sort_values('quantity', ascending=False).head(10)
                
                grouped['Gesamtmenge'] = grouped.apply(lambda row: 
                    f"{row['quantity']:.3f} {row['unit']}" if row['unit'] == 'kg' 
                    else f"{int(row['quantity'])} {row['unit']}", axis=1)
                
                display_df = grouped[['name', 'Gesamtmenge']].copy()
                display_df.columns = ['Artikel', 'Gesamtmenge']
                st.dataframe(display_df, width='stretch', hide_index=True)
                
            else:  # Total Price view
                grouped = items_df.groupby('name')['total_value'].sum().reset_index()
                grouped = grouped.sort_values('total_value', ascending=False).head(10)
                grouped.columns = ['Artikel', 'Ausgaben gesamt (€)']
                grouped['Ausgaben gesamt (€)'] = grouped['Ausgaben gesamt (€)'].round(2)
                st.dataframe(grouped, width='stretch', hide_index=True)
        else:
            st.write("Keine Artikel im ausgewählten Datumsbereich gefunden.")
    else:
        st.write("Keine Daten für den ausgewählten Datumsbereich verfügbar.")
