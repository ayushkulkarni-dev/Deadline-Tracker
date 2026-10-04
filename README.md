# 📅 Deadline Tracker

An AI-powered academic deadline management application built with **Python and Streamlit**. Upload a syllabus, timetable, or assignment sheet and use **Gemini AI** to extract important deadlines into a structured, easy-to-manage dashboard.

## 🚀 Features

- 📸 Upload academic documents/images
- 🤖 Gemini-powered deadline extraction
- 📋 Structured deadline information
- ✏️ Review and edit extracted deadlines
- 🗄️ SQLite database for storing deadlines
- 📊 Upcoming and overdue deadline tracking
- ⏳ Days-remaining calculation
- 🔔 Reminder system
- 🔐 Secure API key management using environment variables

## ⚙️ How It Works

```text
Academic Document
       ↓
   Gemini AI
       ↓
Deadline Extraction
       ↓
User Review & Editing
       ↓
     SQLite
       ↓
Deadline Dashboard
       ↓
    Reminders
```

## 🛠️ Tech Stack

- **Python**
- **Streamlit**
- **Google Gemini API**
- **SQLite**
- **Pillow**
- **python-dotenv**

## 📂 Project Structure

```text
deadline-tracker/
│
├── app.py
├── gemini.py
├── database.py
├── reminders.py
├── scheduler.py
│
├── data/
│   └── deadlines.db
│
├── .env
├── .gitignore
├── requirements.txt
└── README.md
```

## 🔧 Installation

Clone the repository:

```bash
git clone <your-repository-url>
cd deadline-tracker
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate it:

**Windows:**
```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## 🔑 Environment Variables

Create a `.env` file:

```env
GEMINI_API_KEY=your_api_key_here
```

Never commit your `.env` file to GitHub.

## ▶️ Run Locally

```bash
streamlit run app.py
```

Then open the Streamlit URL shown in your terminal.

## 📖 Usage

1. Upload a syllabus, timetable, or assignment image.
2. Let Gemini analyze the document.
3. Review the extracted deadlines.
4. Edit or remove incorrect information.
5. Save the deadlines.
6. Track upcoming and overdue tasks from the dashboard.

## 📸 Screenshots

_Add screenshots of the application interface here._

## 🔮 Future Improvements

- Telegram and WhatsApp notifications
- Calendar integration
- Multiple document processing
- Natural-language deadline queries
- Cloud database support
- Advanced reminder scheduling

## 💡 Key Implementation Highlights

The project combines **multimodal AI, structured data extraction, database management, and automation** into a single academic productivity application.

## 📄 License

This project is licensed under the **MIT License**.