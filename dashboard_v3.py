import streamlit as st
import json
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import logging

# ---------------------------
# Setup Logging
# ---------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------
# Data Loading Functions
# ---------------------------
@st.cache_data
def load_daily_summary(date_str):
    file_path = Path("daily_summaries") / f"{date_str}.json"
    if file_path.exists():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data
        except Exception as e:
            logger.error(f"Error loading daily summary for {date_str}: {e}")
            return None
    return None

def load_aggregated_data(start_date, end_date):
    """Aggregate events over the selected date range (up to 7 days)."""
    aggregated_events = []
    current_date = start_date
    while current_date <= end_date:
        date_key = current_date.strftime("%Y-%m-%d")
        daily_data = load_daily_summary(date_key)
        if daily_data and 'events' in daily_data:
            for event in daily_data['events']:
                event['date'] = date_key  # tag with date for later analysis
                aggregated_events.append(event)
        current_date += timedelta(days=1)
    return aggregated_events

# ---------------------------
# Sidebar: Universal Filters
# ---------------------------
st.sidebar.header("Filtrer par Période")
date_range = st.sidebar.date_input(
    "Plage de dates (max 7 jours)",
    value=(datetime.now() - timedelta(days=6), datetime.now())
)
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
    if (end_date - start_date).days > 6:
        st.sidebar.error("Veuillez sélectionner une plage de dates maximum de 7 jours.")
else:
    start_date = end_date = datetime.now()

# ---------------------------
# Main Dashboard: Tabbed Layout
# ---------------------------
tabs = st.tabs(["Overview", "Minister Details", "Event Trends", "Comparison & Insights", "Location"])

# --- Tab 1: Overview ---
with tabs[0]:
    st.header("Vue d'ensemble")
    st.markdown("### Synthèse Globale")
    aggregated_events = load_aggregated_data(start_date, end_date)
    if not aggregated_events:
        st.write("Aucun événement trouvé pour la période sélectionnée.")
    else:
        df = pd.DataFrame(aggregated_events)
        total_events = len(df)
        unique_locations = df['location'].nunique()
        meeting_count = df['description'].apply(lambda d: 1 if ("meeting" in d.lower() or "réunion" in d.lower()) else 0).sum()
        st.metric("Total d'événements", total_events)
        st.metric("Lieux uniques", unique_locations)
        st.metric("Réunions", meeting_count)
        st.markdown(f"Pendant la période du **{start_date.strftime('%Y-%m-%d')}** au **{end_date.strftime('%Y-%m-%d')}**, "
                    f"il y a eu **{total_events}** événements, couvrant **{unique_locations}** lieux et "
                    f"comprenant **{meeting_count}** réunions.")

# --- Tab 2: Minister Details ---
with tabs[1]:
    st.header("Détails par Ministre")
    aggregated_events = load_aggregated_data(start_date, end_date)
    if not aggregated_events:
        st.write("Aucun événement trouvé pour la période sélectionnée.")
    else:
        df = pd.DataFrame(aggregated_events)
        ministers = sorted(df['minister'].unique())
        minister_choice = st.selectbox("Sélectionnez un ministre", ["Tous"] + ministers)
        if minister_choice != "Tous":
            df = df[df['minister'] == minister_choice]
        st.dataframe(df)
        st.markdown("#### Chronologie des événements")
        df_sorted = df.sort_values(by=["date", "time"])
        st.table(df_sorted[['date', 'time', 'minister', 'description', 'location', 'minister_status']])

# --- Tab 3: Event Trends ---
with tabs[2]:
    st.header("Tendances des Événements")
    aggregated_events = load_aggregated_data(start_date, end_date)
    if not aggregated_events:
        st.write("Aucun événement trouvé pour la période sélectionnée.")
    else:
        df = pd.DataFrame(aggregated_events)
        df['date'] = pd.to_datetime(df['date'])
        daily_counts = df.groupby('date').size().reset_index(name="Nombre d'événements")
        st.line_chart(daily_counts.rename(columns={'date': 'index'}).set_index('index')["Nombre d'événements"])
        st.markdown("**Nombre d'événements par jour**")

# --- Tab 4: Comparison & Insights ---
with tabs[3]:
    st.header("Comparaison & Insights des Ministres")
    aggregated_events = load_aggregated_data(start_date, end_date)
    if not aggregated_events:
        st.write("Aucun événement trouvé pour la période sélectionnée.")
    else:
        df = pd.DataFrame(aggregated_events)
        # Flag events as meetings based on keywords
        df['meeting_flag'] = df['description'].apply(lambda d: 1 if ("meeting" in d.lower() or "réunion" in d.lower()) else 0)
        summary = df.groupby('minister').agg(
            total_events=('minister', 'count'),
            unique_locations=('location', lambda x: x.nunique()),
            meeting_count=('meeting_flag', 'sum')
        ).reset_index()

        # Identify top performers in each category
        top_total = summary.loc[summary['total_events'].idxmax()]
        top_locations = summary.loc[summary['unique_locations'].idxmax()]
        top_meetings = summary.loc[summary['meeting_count'].idxmax()]

        st.subheader("Synthèse des Performances")
        st.markdown(f"- **Événements totaux:** {top_total['minister']} avec **{int(top_total['total_events'])}** événements.")
        st.markdown(f"- **Couverture géographique:** {top_locations['minister']} avec **{int(top_locations['unique_locations'])}** lieux uniques.")
        st.markdown(f"- **Réunions:** {top_meetings['minister']} avec **{int(top_meetings['meeting_count'])}** réunions.")
        st.subheader("Comparaison Détailée par Ministre")
        st.dataframe(summary)
        st.markdown("#### Visualisations")
        st.bar_chart(summary.set_index('minister')['total_events'])
        st.bar_chart(summary.set_index('minister')['unique_locations'])
        st.bar_chart(summary.set_index('minister')['meeting_count'])

# --- Tab 5: Location ---
with tabs[4]:
    st.header("Rapport par Lieu")
    aggregated_events = load_aggregated_data(start_date, end_date)
    if not aggregated_events:
        st.write("Aucun événement trouvé pour la période sélectionnée.")
    else:
        df = pd.DataFrame(aggregated_events)
        # Group events by location and aggregate minister info
        location_summary = df.groupby('location').agg(
            total_events=('location', 'count'),
            ministers=('minister', lambda x: ', '.join(sorted(set(x)))),
            unique_ministers=('minister', lambda x: x.nunique())
        ).reset_index()
        st.subheader("Synthèse par Lieu")
        st.dataframe(location_summary)
        st.markdown("#### Visualisation: Nombre d'événements par lieu")
        st.bar_chart(location_summary.set_index('location')['total_events'])
        st.markdown("#### Détails par Lieu")
        selected_location = st.selectbox("Sélectionnez un lieu pour voir les événements", location_summary['location'].tolist())
        detailed_df = df[df['location'] == selected_location].sort_values(by=['date', 'time'])
        st.table(detailed_df[['date', 'time', 'minister', 'description', 'minister_status']])
