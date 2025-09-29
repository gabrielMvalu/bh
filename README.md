# 🏗️ WorkForce Pro - Sistem de Pontaj și Gestionare Personal

Aplicație modernă pentru gestionarea pontajelor, angajaților, șantierelor și asignărilor pentru companii de construcții.

## 🌟 Caracteristici Principale

### 📊 Dashboard Interactiv
- Vizualizare ore totale săptămână curentă
- Număr angajați și șantiere active
- Statistici absențe
- Top șantiere după ore lucrate
- Pontaje recente

### 👥 Gestionare Angajați
- CRUD complet (Create, Read, Update, Delete)
- Activare/Dezactivare angajați
- Căutare și filtrare avansată
- Validare date duplicate
- Protecție împotriva ștergerii cu dependențe

### 🏗️ Gestionare Șantiere
- CRUD complet pentru șantiere
- Statistici detaliate per șantier
- Grafice evoluție ore lucrate
- Filtrare și căutare

### 📋 Asignări Angajați-Șantiere
- Asignare angajați la șantiere cu interval de date
- Detectare automată suprapuneri
- Încheierea asignărilor active
- Istoric complet asignări
- Vizualizări și statistici

### ⏰ Pontaje
- **Pontaj Zilnic**: Înregistrare rapidă pontaje zilnice
- **Pontaj Săptămânal**: Vizualizare grid săptămânal
- **Istoric Complet**: Toate pontajele cu filtre avansate
- Status: Prezent, Absent, Concediu Medical, Concediu, Lucru Remote
- Validare duplicate (un pontaj/angajat/zi)
- Observații pentru fiecare pontaj

### 📊 Rapoarte Avansate
- **Raport Săptămânal**: Detalii complete + agregări + absențe
- **Raport Lunar**: Statistici lunare + grafice evoluție
- **Rapoarte Personalizate**: Filtre custom + intervale de date
- Export Excel (.xlsx) cu multiple sheet-uri
- Export PDF pentru rapoarte

### 📜 Audit Log
- Înregistrare completă toate modificările
- Filtrare după entitate, acțiune, actor, dată
- Vizualizare before/after pentru update-uri
- Export CSV
- Statistici utilizatori activi
- Grafice distribuție acțiuni

## 🚀 Instalare și Configurare

### Cerințe
- Python 3.8+
- Cont Firebase (Firestore Database)
- Git

### Pași Instalare

1. **Clonare repository**
```bash
git clone https://github.com/gabrielMvalu/bh.git
cd pontaj-brenado
```

2. **Creare mediu virtual**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# SAU
venv\Scripts\activate  # Windows
```

3. **Instalare dependențe**
```bash
pip install -r requirements.txt
```

4. **Configurare Firebase**

   a. Accesează [Firebase Console](https://console.firebase.google.com/)
   
   b. Creează un proiect nou sau folosește unul existent
   
   c. Activează **Firestore Database**
   
   d. Generează credențiale service account:
      - Project Settings → Service Accounts
      - Generate New Private Key
   
   e. Deschide `app.py` și înlocuiește în funcția `init_firebase()`:
   ```python
   cred_dict = {
       "type": "service_account",
       "project_id": "your-project-id",
       "private_key_id": "your-key-id",
       "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
       "client_email": "your-service-account@your-project.iam.gserviceaccount.com",
       # ... rest of credentials
   }
   ```

5. **Rulare aplicație local**
```bash
streamlit run app.py
```

Aplicația va porni la `http://localhost:8501`

## 🌐 Deploy pe Streamlit Cloud

1. **Push repository pe GitHub**
```bash
git add .
git commit -m "Initial commit"
git push origin main
```

2. **Configurare Streamlit Cloud**
   - Accesează [share.streamlit.io](https://share.streamlit.io)
   - Conectează-te cu GitHub
   - Selectează repository-ul
   - Click pe "Deploy"

3. **Configurare Secrets (Firebase)**
   - În Streamlit Cloud → App Settings → Secrets
   - Adaugă credențialele Firebase în format TOML:
   ```toml
   [firebase]
   type = "service_account"
   project_id = "your-project-id"
   private_key_id = "your-key-id"
   private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
   client_email = "your-service-account@your-project.iam.gserviceaccount.com"
   client_id = "your-client-id"
   auth_uri = "https://accounts.google.com/o/oauth2/auth"
   token_uri = "https://oauth2.googleapis.com/token"
   auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
   ```

4. **Modificare cod pentru secrets**
   În `app.py`, modifică funcția `init_firebase()`:
   ```python
   @st.cache_resource
   def init_firebase():
       if not firebase_admin._apps:
           # Verifică dacă rulează pe Streamlit Cloud
           if 'firebase' in st.secrets:
               cred_dict = dict(st.secrets['firebase'])
           else:
               # Credențiale hardcodate pentru local
               cred_dict = {...}
           
           cred = credentials.Certificate(cred_dict)
           firebase_admin.initialize_app(cred)
       return firestore.client()
   ```

## 📁 Structura Proiectului

```
pontaj-brenado/
├── app.py                          # Aplicația principală + Dashboard
├── requirements.txt                # Dependențe Python
├── README.md                       # Documentație
├── .streamlit/
│   └── config.toml                # Configurare UI Streamlit
├── pages/
│   ├── 1_👥_Angajați.py          # Gestionare angajați
│   ├── 2_🏗️_Șantiere.py         # Gestionare șantiere
│   ├── 3_📋_Asignări.py          # Asignări angajați-șantiere
│   ├── 4_⏰_Pontaje.py           # Pontaje zilnice/săptămânale
│   ├── 5_📊_Rapoarte.py          # Rapoarte și export
│   └── 6_📜_Audit.py             # Jurnal audit
└── .gitignore                      # Fișiere ignorate de Git
```

## 🗄️ Structura Baza de Date (Firebase Firestore)

### Collections

#### 1. `employees`
```javascript
{
  full_name: string,
  role: string,           // "Muncitor", "Șef Șantier", "Inginer", "Manager"
  email: string,
  phone: string,
  active: boolean,
  created_at: timestamp,
  created_by: string,
  updated_at: timestamp
}
```

#### 2. `sites`
```javascript
{
  name: string,
  location: string,
  active: boolean,
  created_at: timestamp,
  created_by: string,
  updated_at: timestamp
}
```

#### 3. `assignments`
```javascript
{
  employee_id: string,
  employee_name: string,
  site_id: string,
  site_name: string,
  start_date: timestamp,
  end_date: timestamp | null,
  created_at: timestamp,
  created_by: string,
  updated_at: timestamp,
  updated_by: string
}
```

#### 4. `timesheets`
```javascript
{
  date: timestamp,
  employee_id: string,
  employee_name: string,
  site_id: string,
  site_name: string,
  hours: number,
  status: string,         // "present", "absent", "medical", "leave", "remote"
  note: string,
  created_at: timestamp,
  created_by: string
}
```

#### 5. `audit_log`
```javascript
{
  timestamp: timestamp,
  actor: string,          // email utilizator
  action: string,         // "create", "update", "delete"
  entity: string,         // "Employee", "Site", "Assignment", "Timesheet"
  entity_id: string,
  details: object         // before/after pentru update
}
```

## 🔐 Securitate

- Autentificare utilizatori prin email/parolă
- Audit log complet pentru toate modificările
- Validare date pe server-side
- Protecție împotriva ștergerii cu dependențe
- Firebase Security Rules (recomandare):

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Necesită autentificare pentru orice acces
    match /{document=**} {
      allow read, write: if request.auth != null;
    }
  }
}
```

## 📊 Funcționalități Avansate

### Validări
- ✅ Duplicate: un pontaj/angajat/zi
- ✅ Ore maxime: alertă dacă >12h/zi
- ✅ Suprapuneri asignări: detectare automată
- ✅ Date logice: end_date > start_date

### Export
- 📊 Excel (.xlsx) cu multiple sheet-uri
- 📄 PDF pentru rapoarte printabile
- 📋 CSV pentru audit log

### Statistici și Grafice
- 📈 Evoluție ore lucrate (zilnic/lunar)
- 📊 Top angajați și șantiere
- 🥧 Distribuții (pie charts)
- 📉 Trend-uri absențe

## 🎨 Personalizare

### Culori Tema
Editează `.streamlit/config.toml`:
```toml
[theme]
primaryColor = "#667eea"          # Culoare principală
backgroundColor = "#ffffff"        # Fundal
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"
```

### Roluri și Permisiuni
În `app.py`, adaugă logică pentru roluri:
```python
if st.session_state.user_role == 'Admin':
    # Acces complet
elif st.session_state.user_role == 'Manager':
    # Acces limitat
else:
    # View-only
```

## 🐛 Troubleshooting

### Eroare Firebase Credentials
- Verifică că toate câmpurile din `cred_dict` sunt corecte
- Asigură-te că `private_key` conține `\n` pentru newlines
- Verifică că Firestore este activat în Firebase Console

### Aplicația nu pornește
```bash
# Verifică versiunea Python
python --version  # Trebuie 3.8+

# Reinstalează dependențele
pip install -r requirements.txt --upgrade

# Verifică erorile
streamlit run app.py --logger.level=debug
```

### Probleme pe Streamlit Cloud
- Verifică că `requirements.txt` este corect
- Verifică secrets în App Settings
- Verifică logs în Streamlit Cloud Console

## 📝 TODO / Viitoare Îmbunătățiri

- [ ] Notificări email pentru absențe
- [ ] Autentificare Firebase Auth reală
- [ ] Management permisiuni (RBAC)
- [ ] Import bulk angajați din Excel
- [ ] Rapoarte programate automate
- [ ] API REST pentru integrări externe
- [ ] Aplicație mobilă (PWA)
- [ ] Dashboard manager cu insights AI
- [ ] Predicții ore lucrate (ML)

## 🤝 Contribuții

Contribuțiile sunt binevenite! Pentru modificări majore:
1. Fork repository-ul
2. Creează un branch pentru feature (`git checkout -b feature/AmazingFeature`)
3. Commit modificările (`git commit -m 'Add AmazingFeature'`)
4. Push pe branch (`git push origin feature/AmazingFeature`)
5. Deschide un Pull Request

## 📄 Licență

Acest proiect este licențiat sub MIT License.

## 👨‍💻 Autor

Creat cu ❤️ pentru gestionarea eficientă a pontajelor în construcții

## 📞 Support

Pentru probleme sau întrebări:
- 🐛 Issues: [GitHub Issues](https://github.com/gabrielMvalu/bh/issues)
- 📧 Email: mariang-gabriel.valu@castemill.com
- 💬 Discussions: [GitHub Discussions](https://github.com/gabrielMvalu/bh/discussions)

---

**Nota**: Înlocuiește `yourusername` cu username-ul tău GitHub în toate link-urile de mai sus.
