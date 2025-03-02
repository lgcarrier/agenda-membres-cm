import streamlit as st
import json
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import logging

# ---------------------------
# Setup logging
# ---------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ---------------------------
# Data Loading Functions
# ---------------------------
@st.cache_data
def load_daily_summary(date_str):
    """
    Load the JSON file for a specific date, if it exists.
    """
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
    """
    Aggregate events for each day in the [start_date, end_date] range.
    Returns a list of event dicts, each tagged with its date.
    """
    aggregated_events = []
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        daily_data = load_daily_summary(date_str)
        if daily_data and 'events' in daily_data:
            for event in daily_data['events']:
                # Tag the event with its date
                event['date'] = date_str
                aggregated_events.append(event)
        current_date += timedelta(days=1)
    return aggregated_events


# ---------------------------
# Streamlit Page Setup
# ---------------------------
st.set_page_config(page_title="Optimized Minister Agendas Dashboard", layout="wide")
st.title("Dashboard des Agendas des Ministres")

# ---------------------------
# Sidebar: Date Range Filter
# ---------------------------
st.sidebar.header("Filtrer par Période")
date_range = st.sidebar.date_input(
    "Plage de dates (max 7 jours)",
    value=(datetime.now(), datetime.now())  # default = single day
)

# Validate date range
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
    # Enforce max 7 days
    if (end_date - start_date).days > 6:
        st.sidebar.error("Veuillez sélectionner une plage de dates maximum de 7 jours.")
        st.stop()
else:
    start_date = end_date = datetime.now()

# Load data for the chosen range
events = load_aggregated_data(start_date, end_date)
df = pd.DataFrame(events)

if df.empty:
    st.warning("Aucun événement trouvé pour la période sélectionnée.")
    st.stop()  # no need to show the rest of the interface


# ---------------------------
# Helper transformations
# ---------------------------

# Convert 'date' to an actual datetime (for sorting, charts, etc.)
df['date'] = pd.to_datetime(df['date'])

# Quick helper to flag "meetings" by keywords
def is_meeting(description):
    desc_lower = description.lower()
    return ("meeting" in desc_lower or "réunion" in desc_lower)

df['meeting_flag'] = df['description'].apply(lambda d: 1 if is_meeting(d) else 0)


# ---------------------------
# Tabs for Different Views
# ---------------------------
tab_overview, tab_details, tab_grouping, tab_minister, tab_location = st.tabs([
    "Vue d'ensemble",
    "Événements en détail",
    "Regroupement",
    "Analyse Ministres",
    "Analyse Lieux"
])

# ===================
# 1) Overview
# ===================
with tab_overview:
    st.subheader("Vue d'ensemble")
    
    # Compute simple metrics
    total_events = len(df)
    unique_locations = df['location'].nunique()
    meeting_count = df['meeting_flag'].sum()

    col1, col2, col3 = st.columns(3)
    col1.metric("Total d'événements", total_events)
    col2.metric("Lieux uniques", unique_locations)
    col3.metric("Nombre de réunions", meeting_count)

    st.markdown(
        f"Sur la période du **{start_date.strftime('%Y-%m-%d')}** au **{end_date.strftime('%Y-%m-%d')}**:"
        f"\n- **{total_events}** événements au total"
        f"\n- **{unique_locations}** lieux couverts"
        f"\n- **{meeting_count}** réunions identifiées"
    )

    # Show a line chart of # of events by day
    daily_counts = df.groupby('date').size().reset_index(name="Nombre d'événements")
    st.markdown("#### Nombre d'événements par jour")
    st.line_chart(daily_counts.set_index('date')["Nombre d'événements"])


# ===================
# 2) Detailed Events
# ===================
with tab_details:
    st.subheader("Liste détaillée des événements")

    # Let user filter by minister or choose "Tous"
    ministers = sorted(df['minister'].dropna().unique())
    chosen_minister = st.selectbox("Filtrer par Ministre", ["Tous"] + ministers)

    filtered_df = df.copy()
    if chosen_minister != "Tous":
        filtered_df = filtered_df[filtered_df['minister'] == chosen_minister]
    
    # Sort by date/time
    # (time might be something like "HH:MM" or "HHhMM", so we parse or just sort lexicographically if consistent)
    filtered_df = filtered_df.sort_values(by=["date", "time"])

    st.dataframe(filtered_df[[
        'date', 'time', 'minister', 'minister_status',
        'description', 'location', 'participants'
    ]])

    st.markdown(
        "Affiche les événements chronologiquement pour la période sélectionnée. "
        "Utilisez le filtre ci-dessus pour cibler un ministre particulier."
    )


# ===================
# 3) Grouping
# ===================
with tab_grouping:
    st.subheader("Regroupement par Lieu et Description")

    if filtered_df.empty:
        st.write("Aucun événement disponible pour regroupement.")
    else:
        # Group events by location & description
        grouped = filtered_df.groupby(['location', 'description'], dropna=False).agg({
            'minister': lambda x: ', '.join(sorted(set(x.dropna()))),
            'time': lambda x: ', '.join(sorted(set(x.dropna()))),
            'minister_status': lambda x: ', '.join(sorted(set(x.dropna()))),
        }).reset_index()

        st.write("### Tableau de regroupement")
        st.dataframe(grouped)

        st.markdown(
            "Chaque ligne rassemble les événements qui partagent le même **lieu** et la même **description**."
        )


# ===================
# 4) Minister Analysis
# ===================
with tab_minister:
    st.subheader("Analyse et Comparaison des Ministres")

    # Summaries: total_events, unique_locations, meeting_count
    summary_df = (
        df.groupby('minister')
          .agg(total_events=('minister', 'count'),
               unique_locations=('location', 'nunique'),
               meeting_count=('meeting_flag', 'sum'))
          .reset_index()
    )

    # Identify top ministers in each category
    top_total = summary_df.loc[summary_df['total_events'].idxmax()]
    top_locs = summary_df.loc[summary_df['unique_locations'].idxmax()]
    top_meetings = summary_df.loc[summary_df['meeting_count'].idxmax()]

    st.markdown("#### Faits marquants")
    st.markdown(f"- **Événements totaux**: {top_total['minister']} avec **{top_total['total_events']}** événements.")
    st.markdown(f"- **Couverture géographique**: {top_locs['minister']} avec **{top_locs['unique_locations']}** lieux uniques.")
    st.markdown(f"- **Réunions**: {top_meetings['minister']} avec **{top_meetings['meeting_count']}** réunions.")

    # Show a table
    st.markdown("#### Tableau récapitulatif")
    st.dataframe(summary_df)

    # Visualizations
    st.markdown("#### Visualisations")
    st.bar_chart(summary_df.set_index('minister')['total_events'])
    st.bar_chart(summary_df.set_index('minister')['unique_locations'])
    st.bar_chart(summary_df.set_index('minister')['meeting_count'])


# ===================
# 5) Location Analysis
# ===================
with tab_location:
    st.subheader("Analyse par Lieu")
    
    loc_summary = (
        df.groupby('location')
          .agg(total_events=('location', 'count'),
               ministers=('minister', lambda x: ', '.join(sorted(set(x.dropna())))),
               unique_ministers=('minister', 'nunique'))
          .reset_index()
    ).sort_values(by="total_events", ascending=False)

    st.markdown("#### Tableau des Lieux")
    st.dataframe(loc_summary)

    st.markdown("#### Nombre d'événements par Lieu")
    st.bar_chart(loc_summary.set_index('location')['total_events'])

    # Let user drill down into one location
    all_locations = loc_summary['location'].dropna().unique().tolist()
    if all_locations:
        chosen_location = st.selectbox("Sélectionnez un lieu pour voir le détail", all_locations)
        loc_filtered = df[df['location'] == chosen_location].copy()
        loc_filtered.sort_values(by=["date", "time"], inplace=True)
        st.table(loc_filtered[[
            'date', 'time', 'minister', 'description', 'minister_status', 'participants'
        ]])

