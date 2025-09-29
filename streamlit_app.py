import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore, auth
import pandas as pd
from datetime import datetime, timedelta
import json
from io import BytesIO
import plotly.express as px
import plotly.graph_objects as go

# Configurare pagină
st.set_page_config(
    page_title="WorkForce Pro - Pontaj",
    page_icon="⏰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inițializare Firebase
@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        # IMPORTANT: Înlocuiește cu credențialele tale Firebase
        cred_dict = {
            "type": "service_account",
            "project_id": "your-project-id",
            "private_key_id": "your-key-id",
            "private_key": "-----BEGIN PRIVATE KEY-----\nYOUR_PRIVATE_KEY\n-----END PRIVATE KEY-----\n",
            "client_email": "your-service-account@your-project.iam.gserviceaccount.com",
            "client_id": "your-client-id",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs"
        }
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = init_firebase()

# CSS Modern
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    .main {
        background: white;
        border-radius: 15px;
        padding: 20px;
        margin: 20px;
    }
    .stat-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .stat-number {
        font-size: 48px;
        font-weight: bold;
        margin: 10px 0;
    }
    .stat-label {
        font-size: 16px;
        opacity: 0.9;
    }
    .action-button {
        background: #667eea;
        color: white;
        padding: 10px 20px;
        border-radius: 8px;
        border: none;
        cursor: pointer;
        font-weight: 600;
    }
    div[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e3a8a 0%, #1e40af 100%);
    }
    div[data-testid="stSidebar"] * {
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# Funcții helper
def log_audit(actor, action, entity, entity_id, details):
    """Înregistrare în log audit"""
    db.collection('audit_log').add({
        'timestamp': datetime.now(),
        'actor': actor,
        'action': action,
        'entity': entity,
        'entity_id': entity_id,
        'details': details
    })

def get_current_week_hours():
    """Calculează orele totale pentru săptămâna curentă"""
    today = datetime.now()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    
    timesheets = db.collection('timesheets').where('date', '>=', week_start).where('date', '<=', week_end).stream()
    total = sum(ts.to_dict().get('hours', 0) for ts in timesheets)
    return total

def get_active_counts():
    """Număr angajați și șantiere active"""
    employees = len([e for e in db.collection('employees').where('active', '==', True).stream()])
    sites = len([s for s in db.collection('sites').where('active', '==', True).stream()])
    return employees, sites

def get_week_absences():
    """Absențe săptămâna curentă"""
    today = datetime.now()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    
    timesheets = db.collection('timesheets').where('date', '>=', week_start).where('date', '<=', week_end).stream()
    absences = len([ts for ts in timesheets if ts.to_dict().get('status') in ['absent', 'medical', 'leave']])
    return absences

# Session state pentru autentificare
if 'user' not in st.session_state:
    st.session_state.user = None
if 'user_email' not in st.session_state:
    st.session_state.user_email = None

# Login/Logout
def login_page():
    st.markdown("<h1 style='text-align: center; color: white;'>🏗️ WorkForce Pro</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: white;'>Sistem de Pontaj și Gestionare Personal</h3>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<div style='background: white; padding: 40px; border-radius: 15px; box-shadow: 0 8px 16px rgba(0,0,0,0.2);'>", unsafe_allow_html=True)
        
        email = st.text_input("📧 Email", placeholder="introduceti@email.com")
        password = st.text_input("🔒 Parolă", type="password", placeholder="••••••••")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("🔐 Autentificare", use_container_width=True):
                try:
                    # Simulare autentificare (în producție, folosește Firebase Auth)
                    if email and password:
                        st.session_state.user = email.split('@')[0]
                        st.session_state.user_email = email
                        st.rerun()
                    else:
                        st.error("❌ Email și parolă sunt necesare")
                except Exception as e:
                    st.error(f"❌ Eroare autentificare: {str(e)}")
        
        with col_btn2:
            if st.button("📝 Înregistrare", use_container_width=True):
                st.info("💡 Contactați administratorul pentru cont nou")
        
        st.markdown("</div>", unsafe_allow_html=True)

# Sidebar
def show_sidebar():
    with st.sidebar:
        st.markdown(f"""
        <div style='text-align: center; padding: 20px;'>
            <h2>⏰ WorkForce Pro</h2>
            <p style='opacity: 0.8;'>Utilizator: <b>{st.session_state.user}</b></p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Meniu navigare
        menu_items = {
            "🏠 Dashboard": "dashboard",
            "👥 Angajați": "employees",
            "🏗️ Șantiere": "sites",
            "📋 Asignări": "assignments",
            "⏰ Pontaje": "timesheets",
            "📊 Rapoarte": "reports",
            "📜 Audit Log": "audit"
        }
        
        if 'current_page' not in st.session_state:
            st.session_state.current_page = 'dashboard'
        
        for label, page in menu_items.items():
            if st.button(label, use_container_width=True, key=page):
                st.session_state.current_page = page
                st.rerun()
        
        st.markdown("---")
        if st.button("🚪 Deconectare", use_container_width=True):
            st.session_state.user = None
            st.session_state.user_email = None
            st.rerun()

# Dashboard
def show_dashboard():
    st.title("📊 Dashboard - Prezentare Generală")
    
    # Cards statistici
    col1, col2, col3, col4 = st.columns(4)
    
    total_hours = get_current_week_hours()
    employees, sites = get_active_counts()
    absences = get_week_absences()
    
    with col1:
        st.markdown(f"""
        <div class='stat-card'>
            <div class='stat-label'>Ore Totale</div>
            <div class='stat-label'>Săptămâna Aceasta</div>
            <div class='stat-number'>{total_hours:.0f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class='stat-card'>
            <div class='stat-label'>Angajați Activi</div>
            <div class='stat-number'>{employees}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class='stat-card'>
            <div class='stat-label'>Șantiere Active</div>
            <div class='stat-number'>{sites}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class='stat-card'>
            <div class='stat-label'>Absențe</div>
            <div class='stat-label'>Săptămâna Aceasta</div>
            <div class='stat-number'>{absences}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Două coloane pentru Recent Timesheets și Top Sites
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("📋 Pontaje Recente")
        timesheets = list(db.collection('timesheets').order_by('date', direction=firestore.Query.DESCENDING).limit(5).stream())
        
        if timesheets:
            for ts in timesheets:
                data = ts.to_dict()
                emp_name = data.get('employee_name', 'N/A')
                site_name = data.get('site_name', 'N/A')
                hours = data.get('hours', 0)
                status = data.get('status', 'present')
                date = data.get('date', datetime.now())
                
                status_color = "green" if status == "present" else "red"
                st.markdown(f"""
                <div style='background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 10px;'>
                    <b>{emp_name}</b> - {site_name}<br>
                    <span style='color: {status_color};'>{hours}h - {status}</span>
                    <span style='float: right; opacity: 0.7;'>{date.strftime('%d.%m.%Y') if isinstance(date, datetime) else 'N/A'}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Nu există pontaje înregistrate")
    
    with col_right:
        st.subheader("🏗️ Top Șantiere (Ore)")
        
        # Calculare top șantiere
        timesheets_all = db.collection('timesheets').stream()
        site_hours = {}
        for ts in timesheets_all:
            data = ts.to_dict()
            site = data.get('site_name', 'Unknown')
            hours = data.get('hours', 0)
            site_hours[site] = site_hours.get(site, 0) + hours
        
        sorted_sites = sorted(site_hours.items(), key=lambda x: x[1], reverse=True)[:5]
        
        if sorted_sites:
            for site, hours in sorted_sites:
                progress = min(hours / max(site_hours.values()) * 100, 100)
                st.markdown(f"""
                <div style='margin-bottom: 15px;'>
                    <div style='display: flex; justify-content: space-between;'>
                        <b>{site}</b>
                        <span>{hours:.0f}h</span>
                    </div>
                    <div style='background: #e0e0e0; border-radius: 10px; height: 8px; margin-top: 5px;'>
                        <div style='background: linear-gradient(90deg, #667eea, #764ba2); width: {progress}%; height: 100%; border-radius: 10px;'></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Nu există date disponibile")
    
    # Quick Actions
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("⚡ Acțiuni Rapide")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("➕ Pontaj Nou", use_container_width=True):
            st.session_state.current_page = 'timesheets'
            st.rerun()
    with col2:
        if st.button("📋 Duplică Ieri", use_container_width=True):
            st.info("Funcție în dezvoltare")
    with col3:
        if st.button("📥 Export Săptămânal", use_container_width=True):
            st.session_state.current_page = 'reports'
            st.rerun()

# Main
if st.session_state.user is None:
    login_page()
else:
    show_sidebar()
    
    # Routing către pagini
    if st.session_state.current_page == 'dashboard':
        show_dashboard()
    elif st.session_state.current_page == 'employees':
        st.title("👥 Angajați")
        st.info("Pagina se încarcă din pages/1_👥_Angajați.py")
    elif st.session_state.current_page == 'sites':
        st.title("🏗️ Șantiere")
        st.info("Pagina se încarcă din pages/2_🏗️_Șantiere.py")
    elif st.session_state.current_page == 'assignments':
        st.title("📋 Asignări")
        st.info("Pagina se încarcă din pages/3_📋_Asignări.py")
    elif st.session_state.current_page == 'timesheets':
        st.title("⏰ Pontaje")
        st.info("Pagina se încarcă din pages/4_⏰_Pontaje.py")
    elif st.session_state.current_page == 'reports':
        st.title("📊 Rapoarte")
        st.info("Pagina se încarcă din pages/5_📊_Rapoarte.py")
    elif st.session_state.current_page == 'audit':
        st.title("📜 Audit Log")
        st.info("Pagina se încarcă din pages/6_📜_Audit.py")
