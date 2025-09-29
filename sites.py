import streamlit as st
from firebase_admin import firestore
import pandas as pd
from datetime import datetime

if 'user' not in st.session_state or st.session_state.user is None:
    st.warning("⚠️ Vă rugăm să vă autentificați")
    st.stop()

db = firestore.client()

def log_audit(actor, action, entity, entity_id, details):
    db.collection('audit_log').add({
        'timestamp': datetime.now(),
        'actor': actor,
        'action': action,
        'entity': entity,
        'entity_id': entity_id,
        'details': details
    })

st.title("🏗️ Gestionare Șantiere")

tab1, tab2, tab3 = st.tabs(["📋 Lista Șantiere", "➕ Adaugă Șantier", "📊 Statistici"])

with tab1:
    st.subheader("Lista Șantiere")
    
    # Filtre
    col1, col2 = st.columns(2)
    with col1:
        filter_status = st.selectbox("Status", ["Toate", "Activ", "Inactiv"])
    with col2:
        search_name = st.text_input("🔍 Caută după nume", "")
    
    sites_ref = db.collection('sites')
    
    if filter_status == "Activ":
        sites_ref = sites_ref.where('active', '==', True)
    elif filter_status == "Inactiv":
        sites_ref = sites_ref.where('active', '==', False)
    
    sites = list(sites_ref.stream())
    
    filtered_sites = []
    for site in sites:
        data = site.to_dict()
        data['id'] = site.id
        
        if search_name and search_name.lower() not in data.get('name', '').lower():
            continue
        
        filtered_sites.append(data)
    
    if filtered_sites:
        # Afișare cards
        for site_data in filtered_sites:
            status_color = "#4CAF50" if site_data.get('active') else "#f44336"
            status_text = "Activ" if site_data.get('active') else "Inactiv"
            
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.markdown(f"""
                    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                padding: 20px; border-radius: 10px; color: white; margin-bottom: 10px;'>
                        <h3 style='margin: 0; color: white;'>🏗️ {site_data.get('name', 'N/A')}</h3>
                        <p style='margin: 5px 0; opacity: 0.9;'>📍 {site_data.get('location', 'N/A')}</p>
                        <p style='margin: 5px 0;'><span style='background: {status_color}; padding: 5px 10px; 
                           border-radius: 5px; font-size: 12px;'>{status_text}</span></p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    if st.button("✏️ Editează", key=f"edit_{site_data['id']}", use_container_width=True):
                        st.session_state.edit_site_id = site_data['id']
                        st.rerun()
                
                with col3:
                    action = "Activează" if not site_data.get('active') else "Dezactivează"
                    if st.button(f"🔄 {action}", key=f"toggle_{site_data['id']}", use_container_width=True):
                        current_status = site_data.get('active', True)
                        db.collection('sites').document(site_data['id']).update({
                            'active': not current_status
                        })
                        log_audit(
                            st.session_state.user_email,
                            'update',
                            'Site',
                            site_data['id'],
                            {'active': {'old': current_status, 'new': not current_status}}
                        )
                        st.success(f"✅ Șantier {action.lower()}!")
                        st.rerun()
        
        st.markdown(f"**Total: {len(filtered_sites)} șantiere**")
        
        # Editare inline
        if 'edit_site_id' in st.session_state:
            st.markdown("---")
            st.subheader("✏️ Editare Șantier")
            
            site_doc = db.collection('sites').document(st.session_state.edit_site_id).get()
            site_data = site_doc.to_dict()
            
            with st.form("edit_site_form"):
                edit_name = st.text_input("Nume Șantier", value=site_data.get('name', ''))
                edit_location = st.text_input("Locație", value=site_data.get('location', ''))
                edit_active = st.checkbox("Activ", value=site_data.get('active', True))
                
                col_save, col_cancel = st.columns(2)
                with col_save:
                    submit_edit = st.form_submit_button("💾 Salvează", use_container_width=True, type="primary")
                with col_cancel:
                    cancel_edit = st.form_submit_button("❌ Anulează", use_container_width=True)
                
                if submit_edit:
                    updated_data = {
                        'name': edit_name,
                        'location': edit_location,
                        'active': edit_active,
                        'updated_at': datetime.now()
                    }
                    
                    db.collection('sites').document(st.session_state.edit_site_id).update(updated_data)
                    log_audit(
                        st.session_state.user_email,
                        'update',
                        'Site',
                        st.session_state.edit_site_id,
                        {'old': site_data, 'new': updated_data}
                    )
                    
                    del st.session_state.edit_site_id
                    st.success("✅ Șantier actualizat!")
                    st.rerun()
                
                if cancel_edit:
                    del st.session_state.edit_site_id
                    st.rerun()
    else:
        st.info("📭 Nu există șantiere care să corespundă filtrelor")

with tab2:
    st.subheader("➕ Adaugă Șantier Nou")
    
    with st.form("add_site_form"):
        new_name = st.text_input("Nume Șantier *", placeholder="Ex: Complex Rezidențial Nord")
        new_location = st.text_input("Locație *", placeholder="Ex: București, Sector 1")
        new_active = st.checkbox("Activ", value=True)
        
        submit = st.form_submit_button("💾 Adaugă Șantier", use_container_width=True, type="primary")
        
        if submit:
            if not new_name or not new_location:
                st.error("❌ Numele și locația sunt obligatorii!")
            else:
                existing = list(db.collection('sites').where('name', '==', new_name).limit(1).stream())
                
                if existing:
                    st.error(f"❌ Un șantier cu numele '{new_name}' există deja!")
                else:
                    site_data = {
                        'name': new_name,
                        'location': new_location,
                        'active': new_active,
                        'created_at': datetime.now(),
                        'created_by': st.session_state.user_email
                    }
                    
                    doc_ref = db.collection('sites').add(site_data)
                    
                    log_audit(
                        st.session_state.user_email,
                        'create',
                        'Site',
                        doc_ref[1].id,
                        site_data
                    )
                    
                    st.success(f"✅ Șantier '{new_name}' adăugat cu succes!")
                    st.balloons()

with tab3:
    st.subheader("📊 Statistici Șantiere")
    
    all_sites = list(db.collection('sites').stream())
    total_sites = len(all_sites)
    active_sites = len([s for s in all_sites if s.to_dict().get('active', True)])
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Șantiere", total_sites)
    with col2:
        st.metric("Șantiere Active", active_sites, delta=f"+{active_sites}")
    with col3:
        st.metric("Șantiere Inactive", total_sites - active_sites)
    
    st.markdown("---")
    
    # Top șantiere după ore lucrate
    st.subheader("🏆 Top Șantiere (Total Ore Lucrate)")
    
    timesheets = list(db.collection('timesheets').stream())
    site_hours = {}
    
    for ts in timesheets:
        data = ts.to_dict()
        site_name = data.get('site_name', 'Unknown')
        hours = data.get('hours', 0)
        site_hours[site_name] = site_hours.get(site_name, 0) + hours
    
    if site_hours:
        sorted_sites = sorted(site_hours.items(), key=lambda x: x[1], reverse=True)[:10]
        
        import plotly.graph_objects as go
        
        fig = go.Figure(data=[
            go.Bar(
                x=[hours for _, hours in sorted_sites],
                y=[name for name, _ in sorted_sites],
                orientation='h',
                marker=dict(
                    color=[hours for _, hours in sorted_sites],
                    colorscale='Viridis'
                ),
                text=[f'{hours:.0f}h' for _, hours in sorted_sites],
                textposition='auto'
            )
        ])
        
        fig.update_layout(
            title="Top 10 Șantiere după Ore Lucrate",
            xaxis_title="Ore Totale",
            yaxis_title="Șantier",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📭 Nu există date despre ore lucrate")
    
    # Activitate lunară
    st.markdown("---")
    st.subheader("📅 Activitate Lunară pe Șantiere")
    
    # Grupare după lună
    from collections import defaultdict
    monthly_data = defaultdict(lambda: defaultdict(float))
    
    for ts in timesheets:
        data = ts.to_dict()
        date = data.get('date')
        if isinstance(date, datetime):
            month_key = date.strftime('%Y-%m')
            site_name = data.get('site_name', 'Unknown')
            hours = data.get('hours', 0)
            monthly_data[month_key][site_name] += hours
    
    if monthly_data:
        import plotly.express as px
        
        # Pregătire date pentru grafic
        chart_data = []
        for month, sites in sorted(monthly_data.items()):
            for site, hours in sites.items():
                chart_data.append({
                    'Luna': month,
                    'Șantier': site,
                    'Ore': hours
                })
        
        df_chart = pd.DataFrame(chart_data)
        
        fig2 = px.bar(df_chart, x='Luna', y='Ore', color='Șantier',
                     title='Ore Lucrate pe Șantiere - Evoluție Lunară',
                     barmode='stack')
        
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("📭 Nu există suficiente date pentru graficul lunar")

st.markdown("---")
total = len(list(db.collection('sites').stream()))
active = len(list(db.collection('sites').where('active', '==', True).stream()))

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("📊 Total Șantiere", total)
with col2:
    st.metric("✅ Șantiere Active", active)
with col3:
    st.metric("❌ Șantiere Inactive", total - active)
