import streamlit as st
from firebase_admin import firestore
import pandas as pd
from datetime import datetime, timedelta

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

def check_overlap(employee_id, site_id, start_date, end_date, exclude_id=None):
    """Verifică dacă există suprapuneri de asignări"""
    assignments = db.collection('assignments')\
        .where('employee_id', '==', employee_id)\
        .where('site_id', '==', site_id)\
        .stream()
    
    for assignment in assignments:
        if exclude_id and assignment.id == exclude_id:
            continue
        
        data = assignment.to_dict()
        existing_start = data['start_date']
        existing_end = data.get('end_date')
        
        # Convertire la datetime dacă e necesar
        if not isinstance(existing_start, datetime):
            continue
        
        # Dacă asignarea existentă nu are end_date, e activă
        if existing_end is None:
            if end_date is None or start_date <= datetime.now():
                return True, assignment.id
        else:
            # Verificare suprapunere intervale
            if not isinstance(existing_end, datetime):
                continue
            
            # Suprapunere dacă:
            # start_date este între existing_start și existing_end
            # sau end_date este între existing_start și existing_end
            # sau intervalul nou cuprinde intervalul existent
            if (existing_start <= start_date <= existing_end or
                (end_date and existing_start <= end_date <= existing_end) or
                (start_date <= existing_start and (end_date is None or end_date >= existing_end))):
                return True, assignment.id
    
    return False, None

st.title("📋 Gestionare Asignări")
st.markdown("Gestionează asignările angajaților la șantiere")

tab1, tab2, tab3 = st.tabs(["📋 Lista Asignări", "➕ Asignare Nouă", "📊 Vizualizare"])

# Helper functions
def get_employees():
    employees = list(db.collection('employees').where('active', '==', True).stream())
    return {emp.id: emp.to_dict()['full_name'] for emp in employees}

def get_sites():
    sites = list(db.collection('sites').where('active', '==', True).stream())
    return {site.id: site.to_dict()['name'] for site in sites}

with tab1:
    st.subheader("📋 Asignări Active și Istoric")
    
    # Filtre
    col1, col2, col3 = st.columns(3)
    
    employees = get_employees()
    sites = get_sites()
    
    with col1:
        filter_employee = st.selectbox("Angajat", ["Toți"] + list(employees.values()))
    with col2:
        filter_site = st.selectbox("Șantier", ["Toate"] + list(sites.values()))
    with col3:
        filter_status = st.selectbox("Status", ["Toate", "Active", "Încheiate"])
    
    # Obținere asignări
    assignments = list(db.collection('assignments').stream())
    
    # Filtrare
    filtered = []
    for assignment in assignments:
        data = assignment.to_dict()
        data['id'] = assignment.id
        
        if filter_employee != "Toți" and data.get('employee_name') != filter_employee:
            continue
        if filter_site != "Toate" and data.get('site_name') != filter_site:
            continue
        
        is_active = data.get('end_date') is None
        if filter_status == "Active" and not is_active:
            continue
        if filter_status == "Încheiate" and is_active:
            continue
        
        filtered.append(data)
    
    if filtered:
        st.success(f"✅ Găsite {len(filtered)} asignări")
        
        # Sortare după start_date
        filtered.sort(key=lambda x: x.get('start_date', datetime.min), reverse=True)
        
        # Afișare cards
        for assignment in filtered:
            is_active = assignment.get('end_date') is None
            status_color = "#10b981" if is_active else "#6b7280"
            status_text = "🟢 Activ" if is_active else "⚫ Încheiat"
            
            start_date = assignment.get('start_date')
            end_date = assignment.get('end_date')
            
            start_str = start_date.strftime('%d.%m.%Y') if isinstance(start_date, datetime) else 'N/A'
            end_str = end_date.strftime('%d.%m.%Y') if isinstance(end_date, datetime) else 'În curs'
            
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.markdown(f"""
                    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                               padding: 20px; border-radius: 10px; color: white; margin-bottom: 10px;'>
                        <h4 style='margin: 0; color: white;'>👤 {assignment.get('employee_name', 'N/A')}</h4>
                        <p style='margin: 5px 0; opacity: 0.9;'>🏗️ {assignment.get('site_name', 'N/A')}</p>
                        <p style='margin: 5px 0; font-size: 14px;'>📅 {start_str} → {end_str}</p>
                        <p style='margin: 5px 0;'><span style='background: {status_color}; padding: 5px 10px; 
                           border-radius: 5px; font-size: 12px;'>{status_text}</span></p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    if is_active:
                        if st.button("🔚 Încheie", key=f"end_{assignment['id']}", use_container_width=True):
                            st.session_state.end_assignment_id = assignment['id']
                            st.rerun()
                
                with col3:
                    if st.button("🗑️ Șterge", key=f"del_{assignment['id']}", use_container_width=True):
                        # Verificare dependențe
                        timesheets_count = len(list(db.collection('timesheets')\
                            .where('employee_id', '==', assignment.get('employee_id'))\
                            .where('site_id', '==', assignment.get('site_id'))\
                            .limit(1).stream()))
                        
                        if timesheets_count > 0:
                            st.error("❌ Nu se poate șterge! Există pontaje asociate acestei asignări.")
                        else:
                            db.collection('assignments').document(assignment['id']).delete()
                            log_audit(
                                st.session_state.user_email,
                                'delete',
                                'Assignment',
                                assignment['id'],
                                assignment
                            )
                            st.success("✅ Asignare ștearsă!")
                            st.rerun()
        
        # Modal pentru încheierea asignării
        if 'end_assignment_id' in st.session_state:
            st.markdown("---")
            st.subheader("🔚 Încheiere Asignare")
            
            assignment_doc = db.collection('assignments').document(st.session_state.end_assignment_id).get()
            assignment_data = assignment_doc.to_dict()
            
            st.info(f"Încheiere asignare pentru: **{assignment_data.get('employee_name')}** la **{assignment_data.get('site_name')}**")
            
            end_date = st.date_input("Data încheierii", value=datetime.now())
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 Confirmă Încheierea", use_container_width=True, type="primary"):
                    end_date_dt = datetime.combine(end_date, datetime.min.time())
                    
                    # Verificare ca end_date să fie după start_date
                    start_date = assignment_data.get('start_date')
                    if isinstance(start_date, datetime) and end_date_dt < start_date:
                        st.error("❌ Data încheierii nu poate fi înainte de data începerii!")
                    else:
                        db.collection('assignments').document(st.session_state.end_assignment_id).update({
                            'end_date': end_date_dt,
                            'updated_at': datetime.now(),
                            'updated_by': st.session_state.user_email
                        })
                        
                        log_audit(
                            st.session_state.user_email,
                            'update',
                            'Assignment',
                            st.session_state.end_assignment_id,
                            {'end_date': {'old': None, 'new': end_date_dt}}
                        )
                        
                        del st.session_state.end_assignment_id
                        st.success("✅ Asignare încheiată!")
                        st.rerun()
            
            with col2:
                if st.button("❌ Anulează", use_container_width=True):
                    del st.session_state.end_assignment_id
                    st.rerun()
    else:
        st.info("📭 Nu există asignări care să corespundă filtrelor")

with tab2:
    st.subheader("➕ Creare Asignare Nouă")
    
    employees = get_employees()
    sites = get_sites()
    
    if not employees:
        st.error("❌ Nu există angajați activi. Adăugați angajați mai întâi.")
    elif not sites:
        st.error("❌ Nu există șantiere active. Adăugați șantiere mai întâi.")
    else:
        with st.form("new_assignment_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                selected_employee = st.selectbox("Angajat *", 
                                                options=list(employees.keys()),
                                                format_func=lambda x: employees[x])
            
            with col2:
                selected_site = st.selectbox("Șantier *",
                                            options=list(sites.keys()),
                                            format_func=lambda x: sites[x])
            
            col3, col4 = st.columns(2)
            
            with col3:
                start_date = st.date_input("Data început *", value=datetime.now())
            
            with col4:
                has_end_date = st.checkbox("Are dată de sfârșit?")
                if has_end_date:
                    end_date = st.date_input("Data sfârșit", value=datetime.now() + timedelta(days=30))
                else:
                    end_date = None
            
            submit = st.form_submit_button("💾 Creează Asignare", use_container_width=True, type="primary")
            
            if submit:
                start_date_dt = datetime.combine(start_date, datetime.min.time())
                end_date_dt = datetime.combine(end_date, datetime.min.time()) if end_date else None
                
                # Validare date
                if end_date_dt and end_date_dt < start_date_dt:
                    st.error("❌ Data de sfârșit nu poate fi înainte de data de început!")
                else:
                    # Verificare suprapuneri
                    has_overlap, overlap_id = check_overlap(selected_employee, selected_site, 
                                                           start_date_dt, end_date_dt)
                    
                    if has_overlap:
                        st.error(f"""
                        ❌ **Conflict detectat!** 
                        
                        Există deja o asignare pentru **{employees[selected_employee]}** 
                        la **{sites[selected_site]}** care se suprapune cu intervalul selectat.
                        
                        **Soluții:**
                        - Încheiați asignarea existentă mai întâi
                        - Modificați datele acestei asignări
                        - Alegeți un alt șantier
                        """)
                    else:
                        assignment_data = {
                            'employee_id': selected_employee,
                            'employee_name': employees[selected_employee],
                            'site_id': selected_site,
                            'site_name': sites[selected_site],
                            'start_date': start_date_dt,
                            'end_date': end_date_dt,
                            'created_at': datetime.now(),
                            'created_by': st.session_state.user_email
                        }
                        
                        doc_ref = db.collection('assignments').add(assignment_data)
                        
                        log_audit(
                            st.session_state.user_email,
                            'create',
                            'Assignment',
                            doc_ref[1].id,
                            assignment_data
                        )
                        
                        st.success(f"✅ Asignare creată: {employees[selected_employee]} → {sites[selected_site]}!")
                        st.balloons()

with tab3:
    st.subheader("📊 Vizualizare Asignări")
    
    # Vizualizare pe angajat
    st.markdown("### 👤 Asignări pe Angajat")
    
    all_assignments = list(db.collection('assignments').stream())
    
    employee_assignments = {}
    for assignment in all_assignments:
        data = assignment.to_dict()
        emp_name = data.get('employee_name', 'Unknown')
        
        if emp_name not in employee_assignments:
            employee_assignments[emp_name] = {'active': 0, 'completed': 0, 'sites': set()}
        
        if data.get('end_date') is None:
            employee_assignments[emp_name]['active'] += 1
        else:
            employee_assignments[emp_name]['completed'] += 1
        
        employee_assignments[emp_name]['sites'].add(data.get('site_name', 'Unknown'))
    
    if employee_assignments:
        # Tabel sumar
        summary_data = []
        for emp, stats in employee_assignments.items():
            summary_data.append({
                'Angajat': emp,
                'Asignări Active': stats['active'],
                'Asignări Încheiate': stats['completed'],
                'Total Asignări': stats['active'] + stats['completed'],
                'Șantiere Unice': len(stats['sites'])
            })
        
        df_summary = pd.DataFrame(summary_data)
        df_summary = df_summary.sort_values('Asignări Active', ascending=False)
        st.dataframe(df_summary, use_container_width=True, hide_index=True)
        
        # Grafic
        st.markdown("---")
        st.markdown("### 📈 Top Angajați după Număr de Asignări")
        
        import plotly.graph_objects as go
        
        top_employees = df_summary.head(10)
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            name='Active',
            x=top_employees['Angajat'],
            y=top_employees['Asignări Active'],
            marker_color='#10b981'
        ))
        
        fig.add_trace(go.Bar(
            name='Încheiate',
            x=top_employees['Angajat'],
            y=top_employees['Asignări Încheiate'],
            marker_color='#6b7280'
        ))
        
        fig.update_layout(
            barmode='stack',
            title='Top 10 Angajați - Asignări Active vs Încheiate',
            xaxis_title='Angajat',
            yaxis_title='Număr Asignări',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📭 Nu există asignări în sistem")
    
    # Vizualizare pe șantier
    st.markdown("---")
    st.markdown("### 🏗️ Asignări pe Șantier")
    
    site_assignments = {}
    for assignment in all_assignments:
        data = assignment.to_dict()
        site_name = data.get('site_name', 'Unknown')
        
        if site_name not in site_assignments:
            site_assignments[site_name] = {'active': 0, 'completed': 0, 'employees': set()}
        
        if data.get('end_date') is None:
            site_assignments[site_name]['active'] += 1
        else:
            site_assignments[site_name]['completed'] += 1
        
        site_assignments[site_name]['employees'].add(data.get('employee_name', 'Unknown'))
    
    if site_assignments:
        summary_sites = []
        for site, stats in site_assignments.items():
            summary_sites.append({
                'Șantier': site,
                'Asignări Active': stats['active'],
                'Asignări Încheiate': stats['completed'],
                'Total Asignări': stats['active'] + stats['completed'],
                'Angajați Unici': len(stats['employees'])
            })
        
        df_sites = pd.DataFrame(summary_sites)
        df_sites = df_sites.sort_values('Asignări Active', ascending=False)
        st.dataframe(df_sites, use_container_width=True, hide_index=True)
        
        # Grafic pie pentru distribuție
        import plotly.express as px
        
        fig2 = px.pie(
            df_sites,
            values='Total Asignări',
            names='Șantier',
            title='Distribuția Asignărilor pe Șantiere'
        )
        
        st.plotly_chart(fig2, use_container_width=True)

# Footer statistici
st.markdown("---")
total_assignments = len(list(db.collection('assignments').stream()))
active_assignments = len(list(db.collection('assignments').where('end_date', '==', None).stream()))

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("📊 Total Asignări", total_assignments)
with col2:
    st.metric("🟢 Asignări Active", active_assignments)
with col3:
    st.metric("⚫ Asignări Încheiate", total_assignments - active_assignments)
