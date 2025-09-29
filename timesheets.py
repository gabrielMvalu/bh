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

st.title("⏰ Gestionare Pontaje")

tab1, tab2, tab3 = st.tabs(["📅 Pontaj Zilnic", "📊 Pontaj Săptămânal", "📋 Toate Pontajele"])

# Helper functions
def get_employees():
    employees = list(db.collection('employees').where('active', '==', True).stream())
    return {emp.id: emp.to_dict()['full_name'] for emp in employees}

def get_sites():
    sites = list(db.collection('sites').where('active', '==', True).stream())
    return {site.id: site.to_dict()['name'] for site in sites}

with tab1:
    st.subheader("📅 Înregistrare Pontaj Zilnic")
    
    employees = get_employees()
    sites = get_sites()
    
    if not employees:
        st.error("❌ Nu există angajați activi. Adăugați angajați mai întâi.")
        st.stop()
    
    if not sites:
        st.error("❌ Nu există șantiere active. Adăugați șantiere mai întâi.")
        st.stop()
    
    with st.form("daily_timesheet"):
        col1, col2 = st.columns(2)
        
        with col1:
            selected_date = st.date_input("Data *", value=datetime.now())
            selected_employee = st.selectbox("Angajat *", options=list(employees.keys()), 
                                            format_func=lambda x: employees[x])
        
        with col2:
            selected_site = st.selectbox("Șantier *", options=list(sites.keys()),
                                        format_func=lambda x: sites[x])
            hours = st.number_input("Ore Lucrate", min_value=0.0, max_value=24.0, 
                                   value=8.0, step=0.5)
        
        status = st.selectbox("Status", 
                             ["present", "absent", "medical", "leave", "remote"],
                             format_func=lambda x: {
                                 "present": "Prezent",
                                 "absent": "Absent",
                                 "medical": "Concediu Medical",
                                 "leave": "Concediu",
                                 "remote": "Lucru Remote"
                             }[x])
        
        note = st.text_area("Observații (opțional)", placeholder="Adăugați observații...")
        
        submit = st.form_submit_button("💾 Salvează Pontaj", use_container_width=True, type="primary")
        
        if submit:
            # Verificare duplicat
            existing = list(db.collection('timesheets')\
                          .where('date', '==', selected_date)\
                          .where('employee_id', '==', selected_employee)\
                          .limit(1).stream())
            
            if existing:
                st.error(f"❌ Există deja un pontaj pentru {employees[selected_employee]} la data {selected_date}!")
            else:
                timesheet_data = {
                    'date': datetime.combine(selected_date, datetime.min.time()),
                    'employee_id': selected_employee,
                    'employee_name': employees[selected_employee],
                    'site_id': selected_site,
                    'site_name': sites[selected_site],
                    'hours': hours if status == "present" else 0,
                    'status': status,
                    'note': note,
                    'created_at': datetime.now(),
                    'created_by': st.session_state.user_email
                }
                
                doc_ref = db.collection('timesheets').add(timesheet_data)
                
                log_audit(
                    st.session_state.user_email,
                    'create',
                    'Timesheet',
                    doc_ref[1].id,
                    timesheet_data
                )
                
                st.success(f"✅ Pontaj salvat pentru {employees[selected_employee]}!")
                st.balloons()

with tab2:
    st.subheader("📊 Vizualizare Săptămânală")
    
    # Selectare săptămână
    selected_week_start = st.date_input("Selectează prima zi (Luni)", value=datetime.now() - timedelta(days=datetime.now().weekday()))
    
    week_start = datetime.combine(selected_week_start, datetime.min.time())
    week_end = week_start + timedelta(days=6)
    
    st.info(f"📅 Săptămâna: {week_start.strftime('%d.%m.%Y')} - {week_end.strftime('%d.%m.%Y')}")
    
    # Obținere pontaje pentru săptămână
    timesheets = list(db.collection('timesheets')\
                     .where('date', '>=', week_start)\
                     .where('date', '<=', week_end)\
                     .stream())
    
    if timesheets:
        # Grupare pe angajat și zi
        employees = get_employees()
        
        # Creare grid săptămânal
        days = ['Luni', 'Marți', 'Miercuri', 'Joi', 'Vineri', 'Sâmbătă', 'Duminică']
        
        for emp_id, emp_name in employees.items():
            st.markdown(f"### 👤 {emp_name}")
            
            cols = st.columns(7)
            
            for i, day in enumerate(days):
                day_date = week_start + timedelta(days=i)
                
                # Caută pontaj pentru ziua respectivă
                day_timesheet = next((ts.to_dict() for ts in timesheets 
                                    if ts.to_dict()['employee_id'] == emp_id and 
                                    ts.to_dict()['date'].date() == day_date.date()), None)
                
                with cols[i]:
                    st.markdown(f"**{day}**<br>{day_date.strftime('%d.%m')}", unsafe_allow_html=True)
                    
                    if day_timesheet:
                        hours = day_timesheet['hours']
                        status = day_timesheet['status']
                        site = day_timesheet.get('site_name', 'N/A')
                        
                        status_emoji = {
                            'present': '✅',
                            'absent': '❌',
                            'medical': '🏥',
                            'leave': '🏖️',
                            'remote': '💻'
                        }.get(status, '❓')
                        
                        st.markdown(f"""
                        <div style='background: #f0f0f0; padding: 10px; border-radius: 5px; text-align: center;'>
                            <div style='font-size: 24px;'>{status_emoji}</div>
                            <div style='font-weight: bold;'>{hours}h</div>
                            <div style='font-size: 10px; opacity: 0.7;'>{site[:15]}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown("""
                        <div style='background: #fff3cd; padding: 10px; border-radius: 5px; text-align: center;'>
                            <div style='font-size: 16px; opacity: 0.5;'>-</div>
                        </div>
                        """, unsafe_allow_html=True)
            
            st.markdown("---")
    else:
        st.warning("⚠️ Nu există pontaje pentru această săptămână")
    
    # Butoane acțiuni rapide
    st.subheader("⚡ Acțiuni Rapide")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📋 Completează Săptămână", use_container_width=True):
            st.info("Funcție în dezvoltare - va completa automat 8h/zi prezent")
    
    with col2:
        if st.button("📥 Export Săptămână Excel", use_container_width=True):
            st.info("Navigați la secțiunea Rapoarte pentru export")
    
    with col3:
        if st.button("🔄 Duplică Săptămâna Anterioară", use_container_width=True):
            st.info("Funcție în dezvoltare")

with tab3:
    st.subheader("📋 Toate Pontajele")
    
    # Filtre
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        filter_employee = st.selectbox("Angajat", ["Toți"] + list(get_employees().values()))
    with col2:
        filter_site = st.selectbox("Șantier", ["Toate"] + list(get_sites().values()))
    with col3:
        filter_status = st.selectbox("Status", ["Toate", "Prezent", "Absent", "Medical", "Concediu", "Remote"])
    with col4:
        date_from = st.date_input("De la data", value=datetime.now() - timedelta(days=30))
    
    # Obținere pontaje
    timesheets_ref = db.collection('timesheets')
    
    date_from_dt = datetime.combine(date_from, datetime.min.time())
    timesheets_ref = timesheets_ref.where('date', '>=', date_from_dt)
    
    all_timesheets = list(timesheets_ref.order_by('date', direction=firestore.Query.DESCENDING).stream())
    
    # Filtrare
    filtered_timesheets = []
    for ts in all_timesheets:
        data = ts.to_dict()
        data['id'] = ts.id
        
        if filter_employee != "Toți" and data.get('employee_name') != filter_employee:
            continue
        if filter_site != "Toate" and data.get('site_name') != filter_site:
            continue
        
        status_map = {
            "Prezent": "present",
            "Absent": "absent",
            "Medical": "medical",
            "Concediu": "leave",
            "Remote": "remote"
        }
        if filter_status != "Toate" and data.get('status') != status_map.get(filter_status):
            continue
        
        filtered_timesheets.append(data)
    
    if filtered_timesheets:
        st.success(f"✅ Găsite {len(filtered_timesheets)} pontaje")
        
        # Afișare ca tabel
        df_data = []
        for ts in filtered_timesheets:
            df_data.append({
                'Data': ts['date'].strftime('%d.%m.%Y') if isinstance(ts['date'], datetime) else 'N/A',
                'Angajat': ts.get('employee_name', 'N/A'),
                'Șantier': ts.get('site_name', 'N/A'),
                'Ore': ts.get('hours', 0),
                'Status': {
                    'present': 'Prezent ✅',
                    'absent': 'Absent ❌',
                    'medical': 'Medical 🏥',
                    'leave': 'Concediu 🏖️',
                    'remote': 'Remote 💻'
                }.get(ts.get('status'), 'N/A'),
                'Observații': ts.get('note', '-')
            })
        
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Statistici
        st.markdown("---")
        st.subheader("📊 Statistici")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            total_hours = sum(ts.get('hours', 0) for ts in filtered_timesheets)
            st.metric("Ore Totale", f"{total_hours:.0f}h")
        with col2:
            present_count = len([ts for ts in filtered_timesheets if ts.get('status') == 'present'])
            st.metric("Zile Prezent", present_count)
        with col3:
            absent_count = len([ts for ts in filtered_timesheets if ts.get('status') in ['absent', 'medical', 'leave']])
            st.metric("Absențe", absent_count)
        with col4:
            avg_hours = total_hours / len(filtered_timesheets) if filtered_timesheets else 0
            st.metric("Medie Ore/Zi", f"{avg_hours:.1f}h")
    else:
        st.warning("⚠️ Nu s-au găsit pontaje conform filtrelor")

# Footer statistici generale
st.markdown("---")
total_timesheets = len(list(db.collection('timesheets').stream()))
this_week_start = datetime.now() - timedelta(days=datetime.now().weekday())
this_week_timesheets = len(list(db.collection('timesheets').where('date', '>=', this_week_start).stream()))

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("📊 Total Pontaje", total_timesheets)
with col2:
    st.metric("📅 Pontaje Săptămâna Curentă", this_week_timesheets)
with col3:
    total_hours_all = sum(ts.to_dict().get('hours', 0) for ts in db.collection('timesheets').stream())
    st.metric("⏰ Total Ore Lucrate", f"{total_hours_all:.0f}h")
