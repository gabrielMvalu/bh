import streamlit as st
from firebase_admin import firestore
import pandas as pd
from datetime import datetime, timedelta
import json

if 'user' not in st.session_state or st.session_state.user is None:
    st.warning("⚠️ Vă rugăm să vă autentificați")
    st.stop()

db = firestore.client()

st.title("📜 Jurnalul de Audit")
st.markdown("Istoric complet al modificărilor din sistem")

# Filtre
col1, col2, col3, col4 = st.columns(4)

with col1:
    filter_entity = st.selectbox("Entitate", 
                                 ["Toate", "Employee", "Site", "Assignment", "Timesheet"])

with col2:
    filter_action = st.selectbox("Acțiune", 
                                 ["Toate", "create", "update", "delete"])

with col3:
    date_from = st.date_input("De la data", 
                              value=datetime.now() - timedelta(days=30))

with col4:
    filter_actor = st.text_input("🔍 Actor (email)", placeholder="user@email.com")

# Obținere înregistrări audit
audit_ref = db.collection('audit_log')

date_from_dt = datetime.combine(date_from, datetime.min.time())
audit_ref = audit_ref.where('timestamp', '>=', date_from_dt)

if filter_entity != "Toate":
    audit_ref = audit_ref.where('entity', '==', filter_entity)

if filter_action != "Toate":
    audit_ref = audit_ref.where('action', '==', filter_action)

audit_logs = list(audit_ref.order_by('timestamp', direction=firestore.Query.DESCENDING).limit(200).stream())

# Filtrare client-side pentru actor (Firestore nu suportă query pe text parțial)
if filter_actor:
    audit_logs = [log for log in audit_logs if filter_actor.lower() in log.to_dict().get('actor', '').lower()]

if audit_logs:
    st.success(f"✅ Găsite {len(audit_logs)} înregistrări")
    
    # Statistici
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        create_count = len([log for log in audit_logs if log.to_dict().get('action') == 'create'])
        st.metric("➕ Create", create_count)
    
    with col2:
        update_count = len([log for log in audit_logs if log.to_dict().get('action') == 'update'])
        st.metric("✏️ Update", update_count)
    
    with col3:
        delete_count = len([log for log in audit_logs if log.to_dict().get('action') == 'delete'])
        st.metric("🗑️ Delete", delete_count)
    
    with col4:
        unique_actors = len(set(log.to_dict().get('actor') for log in audit_logs))
        st.metric("👥 Utilizatori Activi", unique_actors)
    
    st.markdown("---")
    
    # Afișare timeline
    st.subheader("📋 Istoric Modificări")
    
    for log in audit_logs:
        data = log.to_dict()
        
        # Determinare culoare și icon în funcție de acțiune
        action = data.get('action', 'unknown')
        if action == 'create':
            icon = "➕"
            color = "#10b981"
        elif action == 'update':
            icon = "✏️"
            color = "#3b82f6"
        elif action == 'delete':
            icon = "🗑️"
            color = "#ef4444"
        else:
            icon = "❓"
            color = "#6b7280"
        
        entity = data.get('entity', 'N/A')
        entity_id = data.get('entity_id', 'N/A')
        actor = data.get('actor', 'Unknown')
        timestamp = data.get('timestamp', datetime.now())
        
        if isinstance(timestamp, datetime):
            timestamp_str = timestamp.strftime('%d.%m.%Y %H:%M:%S')
        else:
            timestamp_str = 'N/A'
        
        # Card pentru fiecare înregistrare
        with st.expander(f"{icon} {action.upper()} - {entity} - {timestamp_str}", expanded=False):
            col1, col2 = st.columns([1, 3])
            
            with col1:
                st.markdown(f"""
                <div style='background: {color}; color: white; padding: 15px; 
                           border-radius: 8px; text-align: center;'>
                    <div style='font-size: 32px;'>{icon}</div>
                    <div style='font-weight: bold; margin-top: 5px;'>{action.upper()}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                **Entitate:** {entity}  
                **ID Entitate:** `{entity_id}`  
                **Actor:** {actor}  
                **Timestamp:** {timestamp_str}
                """)
            
            # Detalii modificări
            details = data.get('details', {})
            if details:
                st.markdown("**Detalii modificări:**")
                
                if action == 'create':
                    st.json(details)
                elif action == 'update':
                    if 'old' in details and 'new' in details:
                        col_old, col_new = st.columns(2)
                        
                        with col_old:
                            st.markdown("**Valori Vechi:**")
                            st.json(details['old'])
                        
                        with col_new:
                            st.markdown("**Valori Noi:**")
                            st.json(details['new'])
                    elif 'active' in details:
                        # Cazul pentru toggle active
                        old_val = details['active'].get('old', 'N/A')
                        new_val = details['active'].get('new', 'N/A')
                        st.markdown(f"**Status schimbat:** `{old_val}` → `{new_val}`")
                    else:
                        st.json(details)
                elif action == 'delete':
                    st.json(details)
    
    # Export audit log
    st.markdown("---")
    st.subheader("📥 Export Audit Log")
    
    # Pregătire date pentru export
    export_data = []
    for log in audit_logs:
        data = log.to_dict()
        timestamp = data.get('timestamp', datetime.now())
        
        export_data.append({
            'Timestamp': timestamp.strftime('%d.%m.%Y %H:%M:%S') if isinstance(timestamp, datetime) else 'N/A',
            'Actor': data.get('actor', 'Unknown'),
            'Acțiune': data.get('action', 'N/A'),
            'Entitate': data.get('entity', 'N/A'),
            'ID Entitate': data.get('entity_id', 'N/A'),
            'Detalii': json.dumps(data.get('details', {}), ensure_ascii=False)
        })
    
    df = pd.DataFrame(export_data)
    
    # Export CSV
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📊 Descarcă CSV",
        data=csv,
        file_name=f"audit_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True
    )
    
    # Vizualizare ca tabel
    st.markdown("---")
    st.subheader("📊 Vedere Tabelară")
    st.dataframe(df, use_container_width=True, hide_index=True)

else:
    st.warning("⚠️ Nu s-au găsit înregistrări conform filtrelor")

# Statistici generale
st.markdown("---")
st.subheader("📊 Statistici Generale Audit")

# Activitate pe utilizatori
all_logs = list(db.collection('audit_log').stream())

user_activity = {}
for log in all_logs:
    actor = log.to_dict().get('actor', 'Unknown')
    user_activity[actor] = user_activity.get(actor, 0) + 1

if user_activity:
    st.markdown("**🏆 Top Utilizatori Activi**")
    
    sorted_users = sorted(user_activity.items(), key=lambda x: x[1], reverse=True)[:10]
    
    import plotly.graph_objects as go
    
    fig = go.Figure(data=[
        go.Bar(
            x=[count for _, count in sorted_users],
            y=[user for user, _ in sorted_users],
            orientation='h',
            marker=dict(
                color=[count for _, count in sorted_users],
                colorscale='Blues'
            ),
            text=[f'{count} acțiuni' for _, count in sorted_users],
            textposition='auto'
        )
    ])
    
    fig.update_layout(
        title="Top 10 Utilizatori după Număr de Acțiuni",
        xaxis_title="Număr Acțiuni",
        yaxis_title="Utilizator",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)

# Activitate pe tipuri de acțiuni
action_counts = {'create': 0, 'update': 0, 'delete': 0}
for log in all_logs:
    action = log.to_dict().get('action', 'unknown')
    if action in action_counts:
        action_counts[action] += 1

st.markdown("**📈 Distribuție Acțiuni**")

import plotly.express as px

fig2 = px.pie(
    names=['Create', 'Update', 'Delete'],
    values=[action_counts['create'], action_counts['update'], action_counts['delete']],
    title='Distribuția Acțiunilor în Sistem',
    color_discrete_sequence=['#10b981', '#3b82f6', '#ef4444']
)

st.plotly_chart(fig2, use_container_width=True)

# Footer
st.markdown("---")
total_logs = len(all_logs)
last_7_days = len([log for log in all_logs 
                  if (datetime.now() - log.to_dict().get('timestamp', datetime.now())).days <= 7])
last_30_days = len([log for log in all_logs 
                   if (datetime.now() - log.to_dict().get('timestamp', datetime.now())).days <= 30])

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("📊 Total Înregistrări", total_logs)
with col2:
    st.metric("📅 Ultimele 7 Zile", last_7_days)
with col3:
    st.metric("📆 Ultimele 30 Zile", last_30_days)
