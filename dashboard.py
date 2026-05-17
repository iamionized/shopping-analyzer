import streamlit as st
import pandas as pd
import json
import os
import glob

# --- Translations ---
LANGUAGES = {
    "de": {
        "page_title": "Lidl Kassenbons Dashboard",
        "title": "Lidl+ Dashboard",
        "language_selector": "🌐 Sprache",
        "filter_header": "Nach Datum filtern",
        "start_date": "Startdatum",
        "end_date": "Enddatum",
        "kpi_header": "Kennzahlen",
        "basic_data": "Grunddaten",
        "total_spent": "Ausgaben gesamt",
        "total_receipts": "Kassenbons gesamt",
        "lidl_plus_savings_header": "Lidl Plus Ersparnisse",
        "lidl_plus_saved": "Lidl Plus gespart",
        "lidl_plus_rate": "Lidl Plus Sparquote",
        "regular_savings_header": "Reguläre Rabatte",
        "regular_saved": "Reguläre Rabatte gespart",
        "regular_rate": "Reguläre Sparquote",
        "spending_over_time": "Ausgaben über Zeit",
        "spending_view": "Ausgabenansicht:",
        "daily": "Täglich",
        "cumulative": "Kumulativ",
        "avg_daily_spending": "Durchschnittliche tägliche Ausgaben",
        "highest_daily_spending": "Höchste tägliche Ausgaben",
        "lowest_daily_spending": "Niedrigste tägliche Ausgaben",
        "total_days": "Tage gesamt",
        "avg_daily_growth": "Durchschnittliches tägliches Wachstum",
        "no_spending_data": "Keine Ausgabendaten für den ausgewählten Datumsbereich verfügbar.",
        "top_10_items": "Top 10 der meistgekauften Artikel",
        "view_by": "Anzeigen nach:",
        "quantity": "Menge",
        "total_price_view": "Gesamtpreis",
        "item_col": "Artikel",
        "total_quantity_col": "Gesamtmenge",
        "total_spent_col": "Ausgaben gesamt (€)",
        "no_items_found": "Keine Artikel im ausgewählten Datumsbereich gefunden.",
        "no_data_for_range": "Keine Daten für den ausgewählten Datumsbereich verfügbar.",
        "error_file_not_found": "Fehler: Keine Kassenbon-Dateien gefunden. Bitte Daten abrufen.",
        "error_invalid_json": "Fehler: Eine der JSON-Dateien ist ungültig. Bitte überprüfen Sie das Format.",
        "error_unexpected": "Ein unerwarteter Fehler ist aufgetreten: {e}",
        "account_filter_header": "Nach Konto filtern",
        "account": "Konto:",
        "all": "Alle",
        "country_filter_header": "Nach Land filtern",
        "country": "Land:",
        "sticker_savings_header": "Sticker Rabatte (RABATT X%)",
        "sticker_saved": "Sticker Rabatte gespart",
        "sticker_rate": "Sticker Sparquote",
        "color_by": "Graph einfärben nach:",
        "avg_purchase_value": "Durchschnittlicher Einkaufswert",
        "highest_purchase_value": "Höchster Einkaufswert",
        "lowest_purchase_value": "Niedrigster Einkaufswert",
        "days_with_purchases": "Tage mit Einkäufen",
        "avg_spent_per_purchase_day": "Durchschn. Ausgaben pro Einkaufstag"
    },
    "nl": {
        "page_title": "Lidl Kassabonnen Dashboard",
        "title": "Lidl+ Dashboard",
        "language_selector": "🌐 Taal",
        "filter_header": "Filter op datum",
        "start_date": "Startdatum",
        "end_date": "Einddatum",
        "kpi_header": "Kerncijfers",
        "basic_data": "Basisgegevens",
        "total_spent": "Totaal uitgegeven",
        "total_receipts": "Totaal kassabonnen",
        "lidl_plus_savings_header": "Lidl Plus Besparingen",
        "lidl_plus_saved": "Lidl Plus bespaard",
        "lidl_plus_rate": "Lidl Plus besparingspercentage",
        "regular_savings_header": "Reguliere Kortingen",
        "regular_saved": "Reguliere kortingen bespaard",
        "regular_rate": "Regulier besparingspercentage",
        "spending_over_time": "Uitgaven in de tijd",
        "spending_view": "Uitgavenweergave:",
        "daily": "Dagelijks",
        "cumulative": "Cumulatief",
        "avg_daily_spending": "Gemiddelde dagelijkse uitgaven",
        "highest_daily_spending": "Hoogste dagelijkse uitgaven",
        "lowest_daily_spending": "Laagste dagelijkse uitgaven",
        "total_days": "Totaal aantal dagen",
        "avg_daily_growth": "Gemiddelde dagelijkse groei",
        "no_spending_data": "Geen uitgavengegevens beschikbaar voor de geselecteerde periode.",
        "top_10_items": "Top 10 meest gekochte artikelen",
        "view_by": "Weergeven op:",
        "quantity": "Hoeveelheid",
        "total_price_view": "Totale prijs",
        "item_col": "Artikel",
        "total_quantity_col": "Totale hoeveelheid",
        "total_spent_col": "Totaal uitgegeven (€)",
        "no_items_found": "Geen artikelen gevonden in de geselecteerde periode.",
        "no_data_for_range": "Geen gegevens beschikbaar voor de geselecteerde periode.",
        "error_file_not_found": "Fout: Geen kassabonbestanden gevonden. Haal eerst de gegevens op.",
        "error_invalid_json": "Fout: Een van de JSON-bestanden is ongeldig. Controleer het formaat.",
        "error_unexpected": "Er is een onverwachte fout opgetreden: {e}",
        "account_filter_header": "Filter op account",
        "account": "Account:",
        "all": "Alle",
        "country_filter_header": "Filter op land",
        "country": "Land:",
        "sticker_savings_header": "Sticker Kortingen (KORTING X%)",
        "sticker_saved": "Sticker korting bespaard",
        "sticker_rate": "Sticker besparingspercentage",
        "color_by": "Grafiek kleuren op:",
        "avg_purchase_value": "Gemiddelde aankoopwaarde",
        "highest_purchase_value": "Hoogste aankoopwaarde",
        "lowest_purchase_value": "Laagste aankoopwaarde",
        "days_with_purchases": "Dagen met aankopen",
        "avg_spent_per_purchase_day": "Gem. uitgaven per aankoopdag"
    }
}

# --- Language Selection & State Management ---
# 1. Check if language is in the URL query parameters
if "lang" in st.query_params:
    if st.query_params["lang"] in ["de", "nl"]:
        st.session_state.language = st.query_params["lang"]

# 2. Set default language if nothing is set
if "language" not in st.session_state:
    st.session_state.language = "de"

LANG = st.session_state.language
T = LANGUAGES[LANG]

# --- Streamlit Dashboard Layout Setup ---
# Hardcoded to always say "Lidl+ Dashboard" in the browser tab
st.set_page_config(layout="wide", page_title="Lidl+ Dashboard", page_icon="🛒")

# Custom CSS for better styling and fixing sidebar whitespace
st.markdown("""
<style>
.main .block-container {padding-top: 2rem;}
[data-testid="stSidebarUserContent"] {padding-top: 0rem;}
.metric-card {background-color: #f0f2f6; padding: 1rem; border-radius: 0.5rem; border-left: 4px solid #1f77b4;}
</style>
""", unsafe_allow_html=True)

# --- Language Toggle in Sidebar ---
st.sidebar.markdown(f"### {T['language_selector']}")
new_lang_choice = st.sidebar.radio(
    label="Language",
    options=["Deutsch", "Nederlands"],
    index=0 if LANG == "de" else 1,
    horizontal=True,
    label_visibility="collapsed"
)

new_lang_code = "de" if new_lang_choice == "Deutsch" else "nl"

# If the user changed the toggle, update state, URL, and reload
if new_lang_code != LANG:
    st.session_state.language = new_lang_code
    st.query_params["lang"] = new_lang_code
    st.rerun()

st.sidebar.markdown("---")

st.title(T["title"])

# --- Data Loading and Preparation ---

def load_all_data(lang):
    df_list = []
    # Find all json files matching the pattern lidl_receipts_COUNTRY_ACCOUNT.json
    receipt_files = glob.glob("lidl_receipts_*.json")

    if not receipt_files:
        st.error(LANGUAGES[lang]["error_file_not_found"])
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

df = load_all_data(LANG)

# --- Main Application Logic ---
if df is not None:

    # --- Data Cleaning and Transformation ---
    def to_float(x):
        if x is None or x == '' or str(x).strip() == '':
            return 0.0
        return float(str(x).replace(',', '.'))

    # Apply conversions (Handles both the new Y.m.d and old d.m.Y formats automatically)
    df['purchase_date'] = pd.to_datetime(df['purchase_date'], errors='coerce')
    df.dropna(subset=['purchase_date'], inplace=True) # Drop rows where date conversion failed

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

    # --- Sidebar for Filters ---
    st.sidebar.header(T["account_filter_header"])
    accounts = [T["all"]] + sorted(df['Konto'].unique().tolist())
    account_filter = st.sidebar.radio(T["account"], accounts)

    if account_filter != T["all"]:
        df = df[df['Konto'] == account_filter]

    st.sidebar.header(T["country_filter_header"])
    countries = [T["all"]] + sorted(df['Land'].unique().tolist())
    country_filter = st.sidebar.radio(T["country"], countries)

    if country_filter != T["all"]:
        df = df[df['Land'] == country_filter]

    st.sidebar.header(T["filter_header"])
    min_date = df['purchase_date'].min().date()
    max_date = df['purchase_date'].max().date()

    start_date = st.sidebar.date_input(T["start_date"], min_date, min_value=min_date, max_value=max_date)
    end_date = st.sidebar.date_input(T["end_date"], max_date, min_value=min_date, max_value=max_date)

    start_datetime = pd.to_datetime(start_date)
    end_datetime = pd.to_datetime(end_date) + pd.Timedelta(days=1)

    filtered_df = df[(df['purchase_date'] >= start_datetime) & (df['purchase_date'] < end_datetime)]

    # --- Main Page ---
    st.header(T["kpi_header"])

    total_receipts = len(filtered_df)
    total_spent = filtered_df['total_price'].sum()
    total_saved = filtered_df['saved_amount'].sum()
    sticker_saved = filtered_df['sticker_discount_amount'].sum() if 'sticker_discount_amount' in filtered_df.columns else 0.0
    lidlplus_saved = filtered_df['lidlplus_saved_amount'].sum() if 'lidlplus_saved_amount' in filtered_df.columns else 0

    # First row: Basic metrics
    st.markdown(f"##### {T['basic_data']}")
    col1, col2 = st.columns(2)
    col1.metric(T["total_spent"], f"€{total_spent:,.2f}")
    col2.metric(T["total_receipts"], f"{total_receipts}")

    # Second row: Lidl Plus savings
    st.markdown(f"##### {T['lidl_plus_savings_header']}")
    col1, col2 = st.columns(2)
    lidlplus_percentage = (lidlplus_saved / total_spent * 100) if total_spent > 0 else 0
    col1.metric(T["lidl_plus_saved"], f"€{lidlplus_saved:,.2f}")
    col2.metric(T["lidl_plus_rate"], f"{lidlplus_percentage:.1f}%")

    # Third row: Regular savings
    st.markdown(f"##### {T['regular_savings_header']}")
    col1, col2 = st.columns(2)
    regular_percentage = (total_saved / total_spent * 100) if total_spent > 0 else 0
    col1.metric(T["regular_saved"], f"€{total_saved:,.2f}")
    col2.metric(T["regular_rate"], f"{regular_percentage:.1f}%")

    st.markdown(f"##### {T['sticker_savings_header']}")
    col1, col2 = st.columns(2)
    sticker_percentage = (sticker_saved / total_spent * 100) if total_spent > 0 else 0
    col1.metric(T["sticker_saved"], f"€{sticker_saved:,.2f}")
    col2.metric(T["sticker_rate"], f"{sticker_percentage:.1f}%")

    st.markdown("---")
    # --- Spending Over Time ---
    st.header(T["spending_over_time"])
    if not filtered_df.empty:
        color_by = st.radio(T["color_by"], ["Konto", "Land"], horizontal=True)

        spending_over_time = filtered_df.copy()
        spending_over_time['date'] = spending_over_time['purchase_date'].dt.date

        daily_spending = spending_over_time.groupby(['date', color_by])['total_price'].sum().reset_index()
        daily_chart_data = daily_spending.pivot(index='date', columns=color_by, values='total_price').fillna(0)

        daily_spending_sorted = daily_spending.sort_values('date')
        daily_spending_sorted['Kumulative Ausgaben'] = daily_spending_sorted.groupby(color_by)['total_price'].cumsum()

        cum_chart_data = daily_spending_sorted.pivot(index='date', columns=color_by, values='Kumulative Ausgaben')
        cum_chart_data = cum_chart_data.ffill().fillna(0)

        spending_view = st.radio(T["spending_view"], [T["daily"], T["cumulative"]], horizontal=True, key="spending_view")

        if spending_view == T["daily"]:
            st.bar_chart(daily_chart_data)

            col1, col2, col3 = st.columns(3)
            col1.metric(T["avg_purchase_value"], f"€{filtered_df['total_price'].mean():.2f}")
            col2.metric(T["highest_purchase_value"], f"€{filtered_df['total_price'].max():.2f}")
            col3.metric(T["lowest_purchase_value"], f"€{filtered_df['total_price'].min():.2f}")

        else:  # Cumulative view
            st.bar_chart(cum_chart_data)

            total_days = len(spending_over_time['date'].unique())
            total_spent_all = filtered_df['total_price'].sum()
            avg_daily_growth = total_spent_all / total_days if total_days > 0 else 0

            col1, col2 = st.columns(2)
            col1.metric(T["days_with_purchases"], total_days)
            col2.metric(T["avg_spent_per_purchase_day"], f"€{avg_daily_growth:.2f}")

    else:
        st.write(T["no_spending_data"])

    st.markdown("---")
    # --- Top 10 Most Purchased Items ---
    st.header(T["top_10_items"])

    if not filtered_df.empty:
        view_mode = st.radio(T["view_by"], [T["quantity"], T["total_price_view"]], horizontal=True)

        items_data = []
        for _, row in filtered_df.iterrows():
            if row.get('items') and isinstance(row['items'], list):
                for item in row['items']:
                    try:
                        quantity_str = str(item.get('quantity', 1))
                        quantity = float(quantity_str.replace(',', '.'))
                        price = to_float(item.get('price', 0))
                        unit = item.get('unit', 'stk')
                        items_data.append({'name': item['name'], 'quantity': quantity, 'price': price, 'unit': unit, 'total_value': quantity * price})
                    except (ValueError, TypeError):
                        continue
        if items_data:
            items_df = pd.DataFrame(items_data)
            items_df = items_df[~items_df['name'].str.contains('Pfand', case=False, na=False)]

            if view_mode == T["quantity"]:
                grouped = items_df.groupby('name').agg({'quantity': 'sum', 'unit': 'first'}).reset_index()
                grouped = grouped.sort_values('quantity', ascending=False).head(10)

                grouped[T['total_quantity_col']] = grouped.apply(lambda row:
                    f"{row['quantity']:.3f} {row['unit']}" if row['unit'] == 'kg'
                    else f"{int(row['quantity'])} {row['unit']}", axis=1)

                display_df = grouped[['name', T['total_quantity_col']]].copy()
                display_df.columns = [T['item_col'], T['total_quantity_col']]
                st.dataframe(display_df, width='stretch', hide_index=True)

            else:  # Total Price view
                grouped = items_df.groupby('name')['total_value'].sum().reset_index()
                grouped = grouped.sort_values('total_value', ascending=False).head(10)
                grouped.columns = [T['item_col'], T['total_spent_col']]
                grouped[T['total_spent_col']] = grouped[T['total_spent_col']].round(2)
                st.dataframe(grouped, width='stretch', hide_index=True)
        else:
            st.write(T["no_items_found"])
    else:
        st.write(T["no_data_for_range"])
