import streamlit as st
import firebase_admin
from firebase_admin import firestore
import pandas as pd
from datetime import datetime

# Verificare autentificare
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

st.title("👥 Gestionare Angajați")

# Tabs pentru diferite acțiuni
tab1, tab2, tab3 = st.tabs(["📋 Lista Angajați", "➕ Adaugă Angajat", "🔍 Căutare"])

with tab1:
    st.subheader("Lista Angajați")
    
    # Filtre
    col1, col2, col3 = st.columns(3)
    with col1:
        filter_status = st.selectbox("Status", ["Toți", "Activ", "Inactiv"])
    with col2:
        filter_role = st.selectbox("Rol", ["Toate", "Muncitor", "Șef Șantier", "Inginer", "Manager"])
    with col3:
        search_name = st.text_input("🔍 Caută după nume", "")
    
    # Obținere angajați
    employees_ref = db.collection('employees')
    
    if filter_status == "Activ":
        employees_ref = employees_ref.where('active', '==', True)
    elif filter_status == "Inactiv":
        employees_ref = employees_ref.where('active', '==', False)
    
    employees = list(employees_ref.stream())
    
    # Filtrare după nume și rol
    filtered_employees = []
    for emp in employees:
        data = emp.to_dict()
        data['id'] = emp.id
        
        if search_name and search_name.lower() not in data.get('full_name', '').lower():
            continue
        if filter_role != "Toate" and data.get('role') != filter_role:
            continue
        
        filtered_employees.append(data)
    
    if filtered_employees:
        # Afișare ca tabel
        df = pd.DataFrame(filtered_employees)
        df = df[['full_name', 'role', 'email', 'phone', 'active']]
        df.columns = ['Nume Complet', 'Rol', 'Email', 'Telefon', 'Activ']
        
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        st.markdown(f"**Total: {len(filtered_employees)} angajați**")
        
        # Acțiuni pe angajați
        st.markdown("---")
        st.subheader("Acțiuni Rapide")
        
        selected_employee = st.selectbox(
            "Selectează angajat pentru editare/dezactivare",
            options=[emp['id'] for emp in filtered_employees],
            format_func=lambda x: next(e['full_name'] for e in filtered_employees if e['id'] == x)
        )
        
        col_edit, col_deactivate, col_delete = st.columns(3)
        
        with col_edit:
            if st.button("✏️ Editează", use_container_width=True):
                st.session_state.edit_employee_id = selected_employee
                st.rerun()
        
        with col_deactivate:
            emp_data = next(e for e in filtered_employees if e['id'] == selected_employee)
            current_status = emp_data.get('active', True)
            action = "Activează" if not current_status else "Dezactivează"
            
            if st.button(f"🔄 {action}", use_container_width=True):
                db.collection('employees').document(selected_employee).update({
                    'active': not current_status
                })
                log_audit(
                    st.session_state.user_email,
                    'update',
                    'Employee',
                    selected_employee,
                    {'active': {'old': current_status, 'new': not current_status}}
                )
                st.success(f"✅ Angajat {action.lower()}!")
                st.rerun()
        
        with col_delete:
            if st.button("🗑️ Șterge", use_container_width=True, type="secondary"):
                # Verificare dependențe
                timesheets_count = len(list(db.collection('timesheets').where('employee_id', '==', selected_employee).limit(1).stream()))
                
                if timesheets_count > 0:
                    st.error("❌ Nu se poate șterge! Angajatul are pontaje înregistrate. Dezactivați-l în loc.")
                else:
                    if st.button("⚠️ Confirmare Ștergere", type="primary"):
                        db.collection('employees').document(selected_employee).delete()
                        log_audit(
                            st.session_state.user_email,
                            'delete',
                            'Employee',
                            selected_employee,
                            emp_data
                        )
                        st.success("✅ Angajat șters!")
                        st.rerun()
        
        # Editare inline
        if 'edit_employee_id' in st.session_state:
            st.markdown("---")
            st.subheader("✏️ Editare Angajat")
            
            emp_doc = db.collection('employees').document(st.session_state.edit_employee_id).get()
            emp_data = emp_doc.to_dict()
            
            with st.form("edit_employee_form"):
                edit_name = st.text_input("Nume Complet", value=emp_data.get('full_name', ''))
                edit_role = st.selectbox("Rol", ["Muncitor", "Șef Șantier", "Inginer", "Manager"], 
                                        index=["Muncitor", "Șef Șantier", "Inginer", "Manager"].index(emp_data.get('role', 'Muncitor')))
                edit_email = st.text_input("Email", value=emp_data.get('email', ''))
                edit_phone = st.text_input("Telefon", value=emp_data.get('phone', ''))
                edit_active = st.checkbox("Activ", value=emp_data.get('active', True))
                
                col_save, col_cancel = st.columns(2)
                with col_save:
                    submit_edit = st.form_submit_button("💾 Salvează", use_container_width=True, type="primary")
                with col_cancel:
                    cancel_edit = st.form_submit_button("❌ Anulează", use_container_width=True)
                
                if submit_edit:
                    updated_data = {
                        'full_name': edit_name,
                        'role': edit_role,
                        'email': edit_email,
                        'phone': edit_phone,
                        'active': edit_active,
                        'updated_at': datetime.now()
                    }
                    
                    db.collection('employees').document(st.session_state.edit_employee_id).update(updated_data)
                    log_audit(
                        st.session_state.user_email,
                        'update',
                        'Employee',
                        st.session_state.edit_employee_id,
                        {'old': emp_data, 'new': updated_data}
                    )
                    
                    del st.session_state.edit_employee_id
                    st.success("✅ Angajat actualizat!")
                    st.rerun()
                
                if cancel_edit:
                    del st.session_state.edit_employee_id
                    st.rerun()
    else:
        st.info("📭 Nu există angajați care să corespundă filtrelor")

with tab2:
    st.subheader("➕ Adaugă Angajat Nou")
    
    with st.form("add_employee_form"):
        new_name = st.text_input("Nume Complet *", placeholder="Ex: Ion Popescu")
        new_role = st.selectbox("Rol *", ["Muncitor", "Șef Șantier", "Inginer", "Manager"])
        new_email = st.text_input("Email", placeholder="ion.popescu@email.com")
        new_phone = st.text_input("Telefon", placeholder="+40 712 345 678")
        new_active = st.checkbox("Activ", value=True)
        
        submit = st.form_submit_button("💾 Adaugă Angajat", use_container_width=True, type="primary")
        
        if submit:
            if not new_name:
                st.error("❌ Numele este obligatoriu!")
            else:
                # Verificare duplicat
                existing = list(db.collection('employees').where('full_name', '==', new_name).limit(1).stream())
                
                if existing:
                    st.error(f"❌ Un angajat cu numele '{new_name}' există deja!")
                else:
                    employee_data = {
                        'full_name': new_name,
                        'role': new_role,
                        'email': new_email,
                        'phone': new_phone,
                        'active': new_active,
                        'created_at': datetime.now(),
                        'created_by': st.session_state.user_email
                    }
                    
                    doc_ref = db.collection('employees').add(employee_data)
                    
                    log_audit(
                        st.session_state.user_email,
                        'create',
                        'Employee',
                        doc_ref[1].id,
                        employee_data
                    )
                    
                    st.success(f"✅ Angajat '{new_name}' adăugat cu succes!")
                    st.balloons()

with tab3:
    st.subheader("🔍 Căutare Avansată")
    
    search_query = st.text_input("Caută după nume, email sau telefon", "")
    
    if search_query:
        all_employees = list(db.collection('employees').stream())
        results = []
        
        for emp in all_employees:
            data = emp.to_dict()
            data['id'] = emp.id
            
            search_lower = search_query.lower()
            if (search_lower in data.get('full_name', '').lower() or
                search_lower in data.get('email', '').lower() or
                search_lower in data.get('phone', '').lower()):
                results.append(data)
        
        if results:
            st.success(f"✅ Găsite {len(results)} rezultate")
            
            for emp in results:
                status_icon = "✅" if emp.get('active') else "❌"
                st.markdown(f"""
                <div style='background: #f8f9fa; padding: 20px; border-radius: 10px; margin-bottom: 15px;'>
                    <h4>{status_icon} {emp.get('full_name')}</h4>
                    <p><b>Rol:</b> {emp.get('role', 'N/A')}</p>
                    <p><b>Email:</b> {emp.get('email', 'N/A')}</p>
                    <p><b>Telefon:</b> {emp.get('phone', 'N/A')}</p>
                    <p><b>Status:</b> {'Activ' if emp.get('active') else 'Inactiv'}</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("⚠️ Nu s-au găsit rezultate")
    else:
        st.info("💡 Introduceți termeni de căutare")

# Footer cu statistici
st.markdown("---")
total_employees = len(list(db.collection('employees').stream()))
active_employees = len(list(db.collection('employees').where('active', '==', True).stream()))

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Angajați", total_employees)
with col2:
    st.metric("Angajați Activi", active_employees)
with col3:
    st.metric("Angajați Inactivi", total_employees - active_employees)
