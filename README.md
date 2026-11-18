<div align="center">

# � BillBrain AI

### *Your smart finance assistant that reads, understands, and organizes your bills instantly.*

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35%2B-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)](https://streamlit.io)
[![Gemini](https://img.shields.io/badge/Gemini-2.5%20Flash-4285F4?style=flat-square&logo=google&logoColor=white)](https://aistudio.google.com)
[![License](https://img.shields.io/badge/License-MIT-22C55E?style=flat-square)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-45%20passing-22C55E?style=flat-square&logo=pytest&logoColor=white)](tests/)

<br/>

**BillBrain AI** is a full-featured, AI-powered invoice processing assistant built on [Streamlit](https://streamlit.io) and [Google Gemini 2.5 Flash](https://aistudio.google.com). It transforms raw invoice images and PDFs into structured, searchable, exportable financial data — with confidence scoring, duplicate detection, multi-language support, persistent history, and smart spending dashboards.

[**Live Demo**](#) · [**Setup Guide**](setup.md) · [**Report a Bug**](https://github.com/deepakprajapati/billbrain-ai/issues) · [**Request a Feature**](https://github.com/deepakprajapati/billbrain-ai/issues)

</div>

---

## ✨ Highlights

| Capability | Details |
|---|---|
| 📤 **Batch Upload** | Process up to 20 invoices (JPG, PNG, PDF) in a single session |
| 🤖 **AI Extraction** | Gemini 2.5 Flash extracts vendor, date, items, amounts, tax, due date |
| 🌐 **Multi-Language** | Supports English, Hindi, Tamil, Marathi and more |
| 🎯 **Confidence Scoring** | Per-field High / Medium / Low confidence on every extraction |
| 🔁 **Duplicate Detection** | Flags duplicate invoices by vendor + amount + date |
| 📊 **Smart Dashboard** | Monthly spend, top vendor, overdue invoices at a glance |
| 📥 **Export** | Download results as CSV or Excel with one click |
| 🕐 **History** | Persistent invoice history per authenticated user |
| 🔐 **Authentication** | Dev mock login included; Google OAuth-ready for production |
| 📧 **Email Alerts** | Due-date reminders via SMTP or SendGrid |
| 🧪 **45 Tests** | Full property-based test suite covering 18 correctness properties |

---

## 📸 Screenshots

```
┌─────────────────────────────────────────────────────────┐
│  🧠 BillBrain AI                          [Login] button │
├──────────┬──────────┬──────────┬──────────────────────── │
│ 📤 Upload│ 📊 Results│ 🕐 History│ 📈 Dashboard           │
├──────────┴──────────┴──────────┴──────────────────────── │
│                                                          │
│  Drag & drop up to 20 invoices (jpg / png / pdf)         │
│  [🔎 Extract All Invoices]                               │
│                                                          │
│  Vendor | Date | Items | Amount | Tax | Due | Confidence │
│  ⚠️ Duplicate rows highlighted in yellow                 │
│  [📥 Download CSV]  [📥 Download Excel]                  │
│                                                          │
│  💰 Total Spent  |  🏆 Top Vendor  |  ⚠️ Overdue         │
└─────────────────────────────────────────────────────────┘
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Streamlit Frontend                       │
│         Upload · Results · History · Dashboard               │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────▼───────────────┐
         │       Core Processing Engine   │
         │                               │
         │  File Handler → Gemini Client │
         │       ↓                       │
         │  Structured Extractor         │
         │  ├── Confidence Scorer        │
         │  ├── Language Detector        │
         │  └── Duplicate Checker        │
         └───────────────┬───────────────┘
                         │
         ┌───────────────▼───────────────┐
         │       Storage Layer           │
         │   SQLite (local) · Supabase   │
         └───────────────┬───────────────┘
                         │
         ┌───────────────▼───────────────┐
         │       Alert System            │
         │   smtplib · SendGrid          │
         └───────────────────────────────┘
```

The system is rolled out across three independently deployable phases:

- **Phase 1 — Core**: Batch upload, structured extraction, tabbed UI, CSV/Excel export
- **Phase 2 — Intelligence**: Multi-language support, confidence scoring, duplicate detection, dashboard
- **Phase 3 — Production**: Google OAuth, SQLite/Supabase persistence, email due-date alerts

---

## 📁 Project Structure

```
billbrain-ai/
├── app.py                  # Main Streamlit application
├── models.py               # Dataclasses — InvoiceRecord, ConfidenceReport, etc.
├── file_handler.py         # Multi-file upload, validation, normalization
├── gemini_client.py        # Gemini 2.5 Flash API client with retry logic
├── extractor.py            # JSON parsing, confidence scoring, language detection
├── duplicate_checker.py    # Vendor + amount + date duplicate detection
├── export_engine.py        # CSV and Excel export engine
├── dashboard_engine.py     # Spending analytics and overdue detection
├── storage.py              # SQLite / Supabase persistence layer
├── auth.py                 # Authentication (mock dev + Google OAuth-ready)
├── email_alerts.py         # Due-date reminder email system
├── requirement.txt         # Python dependencies
├── setup.md                # Full setup and deployment guide
├── tests/
│   ├── test_file_handler.py      # Properties 1–5
│   ├── test_extractor.py         # Properties 6–10
│   ├── test_duplicate_checker.py # Properties 11–12
│   ├── test_gemini_client.py     # Property 13
│   ├── test_export_engine.py     # Properties 14–15
│   ├── test_dashboard_engine.py  # Properties 16–18
│   └── test_examples.py          # Example-based unit tests
└── .streamlit/
    └── secrets.toml        # Local secrets (never commit)
```

---

## ⚡ Quick Start

### 1. Clone & install

```bash
git clone https://github.com/deepakprajapati/billbrain-ai.git
cd billbrain-ai
python -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirement.txt
```

### 2. Add your Gemini API key

Create `.streamlit/secrets.toml`:

```toml
GOOGLE_API_KEY = "your-gemini-api-key"
```

Get a free key at [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey).

### 3. Run

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

> For full configuration options (Supabase, OAuth, email alerts) see [setup.md](setup.md).

---

## 🧪 Testing

```bash
# Run all 45 tests
pytest tests/ -v

# Short output
pytest tests/ --tb=short
```

The test suite uses [`hypothesis`](https://hypothesis.readthedocs.io/) for property-based testing, covering 18 formal correctness properties across all core components.

| Test File | Properties Covered |
|---|---|
| `test_file_handler.py` | Batch size invariant, file limit rejection, MIME acceptance, field completeness, error records |
| `test_extractor.py` | Never raises, low-confidence fallback, unique IDs, overall = minimum, field assignment rules |
| `test_duplicate_checker.py` | Duplicate consistency, vendor normalization idempotence |
| `test_gemini_client.py` | Retry on failure, exactly 3 API calls, returns None |
| `test_export_engine.py` | CSV round-trip, column completeness (CSV + Excel) |
| `test_dashboard_engine.py` | Total correctness, overdue filtering, top vendor |
| `test_examples.py` | Unsupported file type, malformed JSON, empty export, empty dashboard |

---

## 🚀 Deployment

| Platform | Free | Persistent DB | Recommended For |
|---|---|---|---|
| [Streamlit Community Cloud](https://share.streamlit.io) | ✅ Always free | ❌ Ephemeral | Quickest deploy |
| [Railway](https://railway.app) | ✅ 500 hrs/mo | ✅ 1GB disk | Persistent SQLite |
| [Render](https://render.com) | ✅ Limited | ❌ Ephemeral | Simple deploys |
| [Supabase](https://supabase.com) | ✅ 500MB DB | ✅ Cloud | Cloud DB backend |

See [setup.md](setup.md) for step-by-step instructions for each platform.

> **Vercel note**: Streamlit apps are long-running processes and are not natively supported on Vercel's serverless runtime. Use Streamlit Community Cloud for the full UI.

---

## 🔐 Security

- API keys and credentials are stored exclusively in `st.secrets` — never in code or committed files
- OAuth tokens are stored only in `st.session_state` and never persisted to the database
- All database queries use parameterized statements to prevent SQL injection
- User data is fully isolated by `user_id` — no cross-user data access is possible
- File validation (MIME type + 10MB size limit) runs before any processing begins

---

## 📦 Dependencies

| Package | Purpose |
|---|---|
| `streamlit >= 1.35` | UI framework |
| `google-generativeai >= 0.8` | Gemini 2.5 Flash API |
| `PyPDF2` | PDF text extraction |
| `Pillow` | Image handling |
| `pandas` | DataFrame and CSV export |
| `openpyxl` | Excel export |
| `langdetect` | Fallback language detection |
| `python-dotenv` | Local `.env` loading |
| `pytest` + `hypothesis` | Testing framework |

Optional: `supabase-py`, `streamlit-google-auth`, `sendgrid`

---

## �️ Roadmap

- [ ] Real Google OAuth integration (production-ready)
- [ ] Full Supabase backend implementation
- [ ] Invoice chart visualizations (spend over time, category breakdown)
- [ ] Scheduled email reminders via APScheduler
- [ ] Multi-user admin panel
- [ ] Mobile-responsive UI improvements
- [ ] Support for scanned PDFs via Gemini Vision

---

## 🤝 Contributing

Contributions are welcome. Please open an issue first to discuss what you'd like to change.

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m 'Add your feature'`
4. Push to the branch: `git push origin feature/your-feature`
5. Open a Pull Request

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

## 👨‍💻 Author

**Deepak Prajapati** — Lead Developer & Architect

- GitHub: [@deepakprajapati8938](https://github.com/deepakprajapati8938-del)
- Email: deepakprajapati@gmail.com

---

<div align="center">

Made with ❤️ by [Deepak Prajapati](https://github.com/deepakprajapati8938-del)

*If this project helped you, consider giving it a ⭐ on GitHub.*

</div>
