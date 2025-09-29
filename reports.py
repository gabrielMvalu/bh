import streamlit as st
from firebase_admin import firestore
import pandas as pd
from datetime import datetime, timedelta
from io import BytesIO
import xlsxwriter
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

if 'user' not in st.session_state or st.session_state.user is None:
    st.warning("⚠️ Vă rugăm să vă autentificați")
    st.stop()

db = firestore.client()

st.title("📊 Rapoarte și Export")

tab1, tab2, tab3 = st.tabs(["📅 Raport Săptămânal", "📆 Raport Lunar", "📈 Rapoarte Personalizate"])

def generate_excel(timesheets_data, aggregates_data, absences_data, title):
    """Generează fișier Excel cu multiple sheet-uri"""
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    
    # Formatare
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#4F46E5',
        'font_color': 'white',
        'border': 1
    })
    
    cell_format = workbook.add_format({
        'border': 1
    })
    
    # Sheet 1: Pontaje Detaliate
    worksheet1 = workbook.add_worksheet('Pontaje Detaliate')
    
    headers1 = ['Data', 'Angajat', 'Șantier', 'Ore', 'Status', 'Observații']
    for col, header in enumerate(headers1):
        worksheet1.write(0, col, header, header_format)
    
    for row, ts in enumerate(timesheets_data, start=1):
        worksheet1.write(row, 0, ts.get('date', ''), cell_format)
        worksheet1.write(row, 1, ts.get('employee_name', ''), cell_format)
        worksheet1.write(row, 2, ts.get('site_name', ''), cell_format)
        worksheet1.write(row, 3, ts.get('hours', 0), cell_format)
        worksheet1.write(row, 4, ts.get('status', ''), cell_format)
        worksheet1.write(row, 5, ts.get('note', ''), cell_format)
    
    # Sheet 2: Agregare
    worksheet2 = workbook.add_worksheet('Agregare')
    
    headers2 = ['Angajat', 'Șantier', 'Status', 'Total Ore']
    for col, header in enumerate(headers2):
        worksheet2.write(0, col, header, header_format)
    
    for row, agg in enumerate(aggregates_data, start=1):
        worksheet2.write(row, 0, agg.get('employee', ''), cell_format)
        worksheet2.write(row, 1, agg.get('site', ''), cell_format)
        worksheet2.write(row, 2, agg.get('status', ''), cell_format)
        worksheet2.write(row, 3, agg.get('hours', 0), cell_format)
    
    # Sheet 3: Absențe
    worksheet3 = workbook.add_worksheet('Absențe')
    
    headers3 = ['Angajat', 'Tip Absență', 'Număr Zile']
    for col, header in enumerate(headers3):
        worksheet3.write(0, col, header, header_format)
    
    for row, abs_data in enumerate(absences_data, start=1):
        worksheet3.write(row, 0, abs_data.get('employee', ''), cell_format)
        worksheet3.write(row, 1, abs_data.get('type', ''), cell_format)
        worksheet3.write(row, 2, abs_data.get('count', 0), cell_format)
    
    workbook.close()
    output.seek(0)
    return output

def generate_pdf(timesheets_data, title):
    """Generează fișier PDF"""
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=landscape(A4))
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Titlu
    title_para = Paragraph(f"<b>{title}</b>", styles['Title'])
    elements.append(title_para)
    elements.append(Spacer(1, 12))
    
    # Tabel
    table_data = [['Data', 'Angajat', 'Șantier', 'Ore', 'Status']]
    
    for ts in timesheets_data[:100]:  # Limitare la 100 rânduri pentru PDF
        table_data.append([
            ts.get('date', ''),
            ts.get('employee_name', ''),
            ts.get('site_name', ''),
            str(ts.get('hours', 0)),
            ts.get('status', '')
        ])
    
    table = Table(table_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4F46E5')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(table)
    doc.build(elements)
    
    output.seek(0)
    return output

with tab1:
    st.subheader("📅 Raport Săptămânal")
    
    # Selectare săptămână
    selected_date = st.date_input("Selectează o dată din săptămână", value=datetime.now())
    
    # Calculare început și sfârșit săptămână (Luni-Duminică)
    week_day = selected_date.weekday()
    week_start = selected_date - timedelta(days=week_day)
    week_end = week_start + timedelta(days=6)
    
    st.info(f"📅 Săptămâna selectată: {week_start.strftime('%d.%m.%Y')} - {week_end.strftime('%d.%m.%Y')}")
    
    week_start_dt = datetime.combine(week_start, datetime.min.time())
    week_end_dt = datetime.combine(week_end, datetime.max.time())
    
    # Obținere pontaje
    timesheets = list(db.collection('timesheets')\
                     .where('date', '>=', week_start_dt)\
                     .where('date', '<=', week_end_dt)\
                     .stream())
    
    if timesheets:
        st.success(f"✅ Găsite {len(timesheets)} pontaje")
        
        # Statistici
        col1, col2, col3, col4 = st.columns(4)
        
        total_hours = sum(ts.to_dict().get('hours', 0) for ts in timesheets)
        present_count = len([ts for ts in timesheets if ts.to_dict().get('status') == 'present'])
        absent_count = len([ts for ts in timesheets if ts.to_dict().get('status') in ['absent', 'medical', 'leave']])
        unique_employees = len(set(ts.to_dict().get('employee_id') for ts in timesheets))
        
        with col1:
            st.metric("Ore Totale", f"{total_hours:.0f}h")
        with col2:
            st.metric("Zile Prezent", present_count)
        with col3:
            st.metric("Absențe", absent_count)
        with col4:
            st.metric("Angajați", unique_employees)
        
        # Pregătire date pentru tabel
        timesheets_data = []
        for ts in timesheets:
            data = ts.to_dict()
            timesheets_data.append({
                'date': data['date'].strftime('%d.%m.%Y') if isinstance(data['date'], datetime) else 'N/A',
                'employee_name': data.get('employee_name', 'N/A'),
                'site_name': data.get('site_name', 'N/A'),
                'hours': data.get('hours', 0),
                'status': data.get('status', 'N/A'),
                'note': data.get('note', '')
            })
        
        df = pd.DataFrame(timesheets_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Agregare
        st.markdown("---")
        st.subheader("📊 Agregare (Angajat × Șantier × Status)")
        
        aggregates = {}
        for ts in timesheets:
            data = ts.to_dict()
            key = (data.get('employee_name'), data.get('site_name'), data.get('status'))
            if key not in aggregates:
                aggregates[key] = 0
            aggregates[key] += data.get('hours', 0)
        
        aggregates_data = []
        for (emp, site, status), hours in aggregates.items():
            aggregates_data.append({
                'employee': emp,
                'site': site,
                'status': status,
                'hours': hours
            })
        
        df_agg = pd.DataFrame(aggregates_data)
        st.dataframe(df_agg, use_container_width=True, hide_index=True)
        
        # Absențe
        st.markdown("---")
        st.subheader("🏥 Absențe și Concedii")
        
        absences = {}
        for ts in timesheets:
            data = ts.to_dict()
            if data.get('status') in ['absent', 'medical', 'leave']:
                key = (data.get('employee_name'), data.get('status'))
                absences[key] = absences.get(key, 0) + 1
        
        absences_data = []
        for (emp, abs_type), count in absences.items():
            absences_data.append({
                'employee': emp,
                'type': {'absent': 'Absent', 'medical': 'Concediu Medical', 'leave': 'Concediu'}[abs_type],
                'count': count
            })
        
        if absences_data:
            df_abs = pd.DataFrame(absences_data)
            st.dataframe(df_abs, use_container_width=True, hide_index=True)
        else:
            st.info("✅ Nu există absențe în această săptămână")
        
        # Export buttons
        st.markdown("---")
        st.subheader("📥 Export Raport")
        
        col1, col2 = st.columns(2)
        
        with col1:
            excel_file = generate_excel(timesheets_data, aggregates_data, absences_data, 
                                       f"Raport Săptămânal {week_start.strftime('%d.%m.%Y')}-{week_end.strftime('%d.%m.%Y')}")
            st.download_button(
                label="📊 Descarcă Excel (.xlsx)",
                data=excel_file,
                file_name=f"raport_saptamanal_{week_start.strftime('%Y%m%d')}_{week_end.strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        
        with col2:
            pdf_file = generate_pdf(timesheets_data, 
                                   f"Raport Săptămânal {week_start.strftime('%d.%m.%Y')}-{week_end.strftime('%d.%m.%Y')}")
            st.download_button(
                label="📄 Descarcă PDF",
                data=pdf_file,
                file_name=f"raport_saptamanal_{week_start.strftime('%Y%m%d')}_{week_end.strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
    else:
        st.warning("⚠️ Nu există pontaje pentru această săptămână")

with tab2:
    st.subheader("📆 Raport Lunar")
    
    col1, col2 = st.columns(2)
    with col1:
        selected_year = st.number_input("An", min_value=2020, max_value=2030, value=datetime.now().year)
    with col2:
        selected_month = st.selectbox("Lună", range(1, 13), 
                                     format_func=lambda x: ['Ianuarie', 'Februarie', 'Martie', 'Aprilie', 'Mai', 'Iunie',
                                                           'Iulie', 'August', 'Septembrie', 'Octombrie', 'Noiembrie', 'Decembrie'][x-1],
                                     index=datetime.now().month - 1)
    
    # Calculare interval
    month_start = datetime(selected_year, selected_month, 1)
    if selected_month == 12:
        month_end = datetime(selected_year + 1, 1, 1) - timedelta(seconds=1)
    else:
        month_end = datetime(selected_year, selected_month + 1, 1) - timedelta(seconds=1)
    
    st.info(f"📅 Luna selectată: {month_start.strftime('%B %Y')}")
    
    # Obținere pontaje lunare
    timesheets = list(db.collection('timesheets')\
                     .where('date', '>=', month_start)\
                     .where('date', '<=', month_end)\
                     .stream())
    
    if timesheets:
        st.success(f"✅ Găsite {len(timesheets)} pontaje")
        
        # Statistici lunare
        col1, col2, col3, col4 = st.columns(4)
        
        total_hours = sum(ts.to_dict().get('hours', 0) for ts in timesheets)
        working_days = len(set(ts.to_dict()['date'].date() for ts in timesheets if isinstance(ts.to_dict()['date'], datetime)))
        unique_employees = len(set(ts.to_dict().get('employee_id') for ts in timesheets))
        absent_count = len([ts for ts in timesheets if ts.to_dict().get('status') in ['absent', 'medical', 'leave']])
        
        with col1:
            st.metric("Ore Totale", f"{total_hours:.0f}h")
        with col2:
            st.metric("Zile Lucrate", working_days)
        with col3:
            st.metric("Angajați Activi", unique_employees)
        with col4:
            st.metric("Total Absențe", absent_count)
        
        # Grafic evoluție zilnică
        import plotly.express as px
        
        daily_hours = {}
        for ts in timesheets:
            data = ts.to_dict()
            date_str = data['date'].strftime('%Y-%m-%d') if isinstance(data['date'], datetime) else 'N/A'
            daily_hours[date_str] = daily_hours.get(date_str, 0) + data.get('hours', 0)
        
        df_daily = pd.DataFrame(list(daily_hours.items()), columns=['Data', 'Ore'])
        df_daily = df_daily.sort_values('Data')
        
        fig = px.line(df_daily, x='Data', y='Ore', title='Evoluție Ore Lucrate (zilnic)',
                     markers=True)
        fig.update_layout(xaxis_title='Data', yaxis_title='Ore Totale')
        st.plotly_chart(fig, use_container_width=True)
        
        # Pregătire date pentru export
        timesheets_data = []
        for ts in timesheets:
            data = ts.to_dict()
            timesheets_data.append({
                'date': data['date'].strftime('%d.%m.%Y') if isinstance(data['date'], datetime) else 'N/A',
                'employee_name': data.get('employee_name', 'N/A'),
                'site_name': data.get('site_name', 'N/A'),
                'hours': data.get('hours', 0),
                'status': data.get('status', 'N/A'),
                'note': data.get('note', '')
            })
        
        # Agregare lunară
        aggregates = {}
        for ts in timesheets:
            data = ts.to_dict()
            key = (data.get('employee_name'), data.get('site_name'), data.get('status'))
            if key not in aggregates:
                aggregates[key] = 0
            aggregates[key] += data.get('hours', 0)
        
        aggregates_data = [{'employee': emp, 'site': site, 'status': status, 'hours': hours}
                          for (emp, site, status), hours in aggregates.items()]
        
        # Absențe
        absences = {}
        for ts in timesheets:
            data = ts.to_dict()
            if data.get('status') in ['absent', 'medical', 'leave']:
                key = (data.get('employee_name'), data.get('status'))
                absences[key] = absences.get(key, 0) + 1
        
        absences_data = [{'employee': emp, 'type': abs_type, 'count': count}
                        for (emp, abs_type), count in absences.items()]
        
        # Export
        st.markdown("---")
        st.subheader("📥 Export Raport Lunar")
        
        col1, col2 = st.columns(2)
        
        with col1:
            excel_file = generate_excel(timesheets_data, aggregates_data, absences_data,
                                       f"Raport Lunar {month_start.strftime('%B %Y')}")
            st.download_button(
                label="📊 Descarcă Excel (.xlsx)",
                data=excel_file,
                file_name=f"raport_lunar_{selected_year}_{selected_month:02d}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        
        with col2:
            pdf_file = generate_pdf(timesheets_data, f"Raport Lunar {month_start.strftime('%B %Y')}")
            st.download_button(
                label="📄 Descarcă PDF",
                data=pdf_file,
                file_name=f"raport_lunar_{selected_year}_{selected_month:02d}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
    else:
        st.warning("⚠️ Nu există pontaje pentru această lună")

with tab3:
    st.subheader("📈 Rapoarte Personalizate")
    
    st.info("💡 Personalizați intervalul și filtrele pentru rapoarte custom")
    
    col1, col2 = st.columns(2)
    with col1:
        date_from = st.date_input("De la data", value=datetime.now() - timedelta(days=30))
    with col2:
        date_to = st.date_input("Până la data", value=datetime.now())
    
    # Filtre suplimentare
    employees = {emp.id: emp.to_dict()['full_name'] 
                for emp in db.collection('employees').where('active', '==', True).stream()}
    sites = {site.id: site.to_dict()['name'] 
            for site in db.collection('sites').where('active', '==', True).stream()}
    
    filter_employee = st.multiselect("Filtrează după angajați", options=list(employees.values()))
    filter_site = st.multiselect("Filtrează după șantiere", options=list(sites.values()))
    
    if st.button("🔍 Generează Raport", use_container_width=True, type="primary"):
        date_from_dt = datetime.combine(date_from, datetime.min.time())
        date_to_dt = datetime.combine(date_to, datetime.max.time())
        
        timesheets = list(db.collection('timesheets')\
                         .where('date', '>=', date_from_dt)\
                         .where('date', '<=', date_to_dt)\
                         .stream())
        
        # Aplicare filtre
        filtered = []
        for ts in timesheets:
            data = ts.to_dict()
            if filter_employee and data.get('employee_name') not in filter_employee:
                continue
            if filter_site and data.get('site_name') not in filter_site:
                continue
            filtered.append(data)
        
        if filtered:
            st.success(f"✅ Găsite {len(filtered)} pontaje")
            
            # Statistici
            total_hours = sum(ts.get('hours', 0) for ts in filtered)
            st.metric("Ore Totale", f"{total_hours:.0f}h")
            
            # Tabel
            timesheets_data = [{
                'date': ts['date'].strftime('%d.%m.%Y') if isinstance(ts['date'], datetime) else 'N/A',
                'employee_name': ts.get('employee_name', 'N/A'),
                'site_name': ts.get('site_name', 'N/A'),
                'hours': ts.get('hours', 0),
                'status': ts.get('status', 'N/A'),
                'note': ts.get('note', '')
            } for ts in filtered]
            
            df = pd.DataFrame(timesheets_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Export
            excel_file = generate_excel(timesheets_data, [], [],
                                       f"Raport Personalizat {date_from.strftime('%d.%m.%Y')}-{date_to.strftime('%d.%m.%Y')}")
            st.download_button(
                label="📊 Descarcă Excel (.xlsx)",
                data=excel_file,
                file_name=f"raport_custom_{date_from.strftime('%Y%m%d')}_{date_to.strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("⚠️ Nu s-au găsit pontaje conform criteriilor")
