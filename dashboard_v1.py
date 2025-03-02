import streamlit as st
import json
import pandas as pd
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dashboard.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_daily_summary(date_str):
    file_path = Path("daily_summaries") / f"{date_str}.json"
    logger.debug(f"Attempting to load daily summary for date: {date_str}")
    if file_path.exists():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"Successfully loaded daily summary for {date_str}")
                return data
        except Exception as e:
            logger.error(f"Error loading daily summary for {date_str}: {str(e)}")
            return None
    logger.debug(f"No daily summary found for date: {date_str}")
    return None

def load_weekly_summary():
    file_path = Path("weekly_summary.json")
    logger.debug("Attempting to load weekly summary")
    if file_path.exists():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info("Successfully loaded weekly summary")
                return data
        except Exception as e:
            logger.error(f"Error loading weekly summary: {str(e)}")
            return None
    logger.debug("No weekly summary file found")
    return None

st.title("Dashboard des Agendas des Ministres")
st.sidebar.title("Navigation")
view_option = st.sidebar.selectbox("Sélectionnez la vue", 
                                   ["Daily", "Weekly", "Grouped", "Minister Report", "Minister Comparison"])
logger.info(f"Selected view option: {view_option}")

if view_option == "Daily":
    st.header("Agenda Quotidien")
    selected_date = st.date_input("Sélectionnez une date", datetime.now(), key="daily_date")
    date_key = selected_date.strftime("%Y-%m-%d")
    daily_data = load_daily_summary(date_key)
    if daily_data:
        st.subheader(f"Agenda du {daily_data['date']}")
        for event in daily_data['events']:
            st.markdown(f"**{event['time']} - {event['minister']}**")
            if 'minister_status' in event:
                st.markdown(f"Statut: {event['minister_status']}")
            st.markdown(f"*{event['description']}*")
            st.markdown(f"Lieu: {event['location']}")
            if event.get('participants'):
                st.markdown(f"Participants: {event['participants']}")
            st.markdown("---")
    else:
        st.write("Aucun événement trouvé pour cette date.")

elif view_option == "Weekly":
    st.header("Agenda Hebdomadaire")
    weekly_data = load_weekly_summary()
    if weekly_data and 'week' in weekly_data:
        for daily in weekly_data['week']:
            st.subheader(f"Date: {daily['date']}")
            for event in daily['events']:
                st.markdown(f"**{event['time']} - {event['minister']}**")
                if 'minister_status' in event:
                    st.markdown(f"Statut: {event['minister_status']}")
                st.markdown(f"*{event['description']}*")
                st.markdown(f"Lieu: {event['location']}")
                if event.get('participants'):
                    st.markdown(f"Participants: {event['participants']}")
                st.markdown("---")
    else:
        st.write("Résumé hebdomadaire non disponible.")

elif view_option == "Grouped":
    st.header("Regroupement par Lieu et Description")
    selected_date = st.date_input("Sélectionnez une date pour regrouper", datetime.now(), key="grouped_date")
    date_key = selected_date.strftime("%Y-%m-%d")
    daily_data = load_daily_summary(date_key)
    if daily_data:
        df = pd.DataFrame(daily_data['events'])
        if df.empty:
            st.write("Aucun événement trouvé pour cette date.")
        else:
            # Group events by location and description, also aggregating minister and status info
            grouped = df.groupby(['location', 'description']).agg({
                'minister': lambda x: ', '.join(sorted(set(x))),
                'time': lambda x: ', '.join(sorted(set(x))),
                'minister_status': lambda x: ', '.join(sorted(set(x)))
            }).reset_index()
            st.write("### Regroupement des événements")
            st.dataframe(grouped)
            for _, row in grouped.iterrows():
                st.subheader(f"Lieu: {row['location']} — Description: {row['description']}")
                st.write(f"Ministres: {row['minister']}")
                st.write(f"Heures: {row['time']}")
                st.write(f"Statuts: {row['minister_status']}")
                st.markdown("---")
    else:
        st.write("Aucun événement trouvé pour cette date.")

elif view_option == "Minister Report":
    logger.info("Entering Minister Report view")
    st.header("Rapport par Ministre sur une Période")
    date_range = st.date_input("Sélectionnez une plage de dates (max 7 jours)", 
                               value=(datetime.now(), datetime.now()), key="minister_range")
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
        logger.info(f"Selected date range: {start_date} to {end_date}")
        
        if (end_date - start_date).days > 6:
            logger.warning(f"Invalid date range selected: {(end_date - start_date).days} days")
            st.error("Veuillez sélectionner une plage de dates maximum de 7 jours.")
        else:
            logger.debug("Starting event aggregation for date range")
            aggregated_events = []
            current_date = start_date
            while current_date <= end_date:
                date_key = current_date.strftime("%Y-%m-%d")
                logger.debug(f"Processing date: {date_key}")
                daily_data = load_daily_summary(date_key)
                if daily_data and 'events' in daily_data:
                    logger.debug(f"Found {len(daily_data['events'])} events for {date_key}")
                    for event in daily_data['events']:
                        event['date'] = date_key
                        aggregated_events.append(event)
                current_date += timedelta(days=1)
            
            if not aggregated_events:
                logger.info("No events found for the selected period")
                st.write("Aucun événement trouvé pour la période sélectionnée.")
            else:
                logger.info(f"Total events aggregated: {len(aggregated_events)}")
                ministers = sorted(set(event['minister'] for event in aggregated_events))
                logger.debug(f"Available ministers: {ministers}")
                
                minister_choice = st.selectbox("Sélectionnez un ministre", ["All"] + ministers)
                logger.info(f"Selected minister: {minister_choice}")
                
                if minister_choice != "All":
                    filtered_events = [event for event in aggregated_events if event['minister'] == minister_choice]
                    logger.debug(f"Filtered {len(filtered_events)} events for minister {minister_choice}")
                else:
                    filtered_events = aggregated_events
                    logger.debug("Showing all events (no minister filter)")
                
                filtered_events.sort(key=lambda x: (x.get('date'), x.get('time')))
                logger.debug("Events sorted by date and time")
                
                st.subheader(f"Rapport pour {minister_choice} du {start_date.strftime('%Y-%m-%d')} au {end_date.strftime('%Y-%m-%d')}")
                for event in filtered_events:
                    logger.debug(f"Displaying event: {event.get('date')} - {event['minister']} - {event['description'][:30]}...")
                    st.markdown(f"**{event.get('date')} {event['time']} - {event['minister']}**")
                    if 'minister_status' in event:
                        st.markdown(f"Statut: {event['minister_status']}")
                    st.markdown(f"*{event['description']}*")
                    st.markdown(f"Lieu: {event['location']}")
                    if event.get('participants'):
                        st.markdown(f"Participants: {event['participants']}")
                    st.markdown("---")
    else:
        logger.warning("No valid date range selected")
        st.error("Veuillez sélectionner une plage de dates.")

elif view_option == "Minister Comparison":
    st.header("Comparaison & Insights des Ministres")
    # Date range picker with maximum range of 7 days
    date_range = st.date_input("Sélectionnez une plage de dates (max 7 jours)", 
                               value=(datetime.now(), datetime.now()), key="comparison_range")
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
        if (end_date - start_date).days > 6:
            st.error("Veuillez sélectionner une plage de dates maximum de 7 jours.")
        else:
            aggregated_events = []
            current_date = start_date
            while current_date <= end_date:
                date_key = current_date.strftime("%Y-%m-%d")
                daily_data = load_daily_summary(date_key)
                if daily_data and 'events' in daily_data:
                    for event in daily_data['events']:
                        # Tag each event with its date for later analysis
                        event['date'] = date_key
                        aggregated_events.append(event)
                current_date += timedelta(days=1)
            
            if not aggregated_events:
                st.write("Aucun événement trouvé pour la période sélectionnée.")
            else:
                # Convert aggregated events into a DataFrame for analysis
                df = pd.DataFrame(aggregated_events)

                # Define a flag for meetings based on keywords (case-insensitive)
                def meeting_flag(desc):
                    return 1 if ("meeting" in desc.lower() or "réunion" in desc.lower()) else 0

                df['meeting_flag'] = df['description'].apply(meeting_flag)
                summary = df.groupby('minister').agg(
                    total_events=('minister', 'count'),
                    unique_locations=('location', lambda x: x.nunique()),
                    meeting_count=('meeting_flag', 'sum')
                ).reset_index()

                # Compute rankings (1 = highest)
                summary['rank_total'] = summary['total_events'].rank(method='min', ascending=False)
                summary['rank_locations'] = summary['unique_locations'].rank(method='min', ascending=False)
                summary['rank_meetings'] = summary['meeting_count'].rank(method='min', ascending=False)

                # Identify top ministers in each category
                top_total = summary.loc[summary['total_events'].idxmax()]
                top_locations = summary.loc[summary['unique_locations'].idxmax()]
                top_meetings = summary.loc[summary['meeting_count'].idxmax()]

                # Display narrative insights
                st.subheader("Synthèse des Performances")
                st.markdown(f"- **Nombre total d'événements:** {top_total['minister']} mène la course avec {int(top_total['total_events'])} événements.")
                st.markdown(f"- **Couverture géographique (lieux uniques):** {top_locations['minister']} couvre {int(top_locations['unique_locations'])} lieux distincts.")
                st.markdown(f"- **Réunions enregistrées:** {top_meetings['minister']} a participé à {int(top_meetings['meeting_count'])} réunions.")

                st.subheader("Comparaison Détailée par Ministre")
                st.dataframe(summary)

                # Visualize each metric
                st.markdown("#### Total d'événements par ministre")
                st.bar_chart(summary.set_index('minister')['total_events'])

                st.markdown("#### Nombre de lieux uniques par ministre")
                st.bar_chart(summary.set_index('minister')['unique_locations'])

                st.markdown("#### Nombre de réunions par ministre")
                st.bar_chart(summary.set_index('minister')['meeting_count'])
    else:
        st.error("Veuillez sélectionner une plage de dates.")

