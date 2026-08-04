# 📄 AI Resume & ATS Analyzer

An end-to-end, AI-powered Applicant Tracking System (ATS) and Resume Analyzer built using **Streamlit** and **Gemini AI**. This application enables job seekers to benchmark their resumes against specific job descriptions, calculate ATS match scores, highlight key strengths & weaknesses, identify missing keywords, and export detailed PDF analysis reports.

---

## 🌐 Live Demo & Video Showcase

* 🚀 **Live Streamlit App:** [View Live Application](https://giridhar-ai-resume-ats-analyzer.streamlit.app/)
* 📹 **Video Walkthrough:** [Watch Project Demo](https://drive.google.com/file/d/15dzRUZqUhZp-6JmahPQmKeVgiL8zXxLm/view?usp=drive_link)

---


## ✨ Key Features

* **📊 ATS Match Score:** Calculates real-time compatibility percentages between uploaded PDF resumes and job descriptions.
* **🔍 In-Depth Feedback:** Detailed extraction of technical strengths, critical skill gaps/weaknesses, and missing keywords (e.g., RAG, LangChain, Vector DBs).
* **💡 Actionable Insights:** Provides actionable recommendations to optimize resume bullet points for better ATS parsing.
* **📄 PDF Export:** Generates downloadable, formatted PDF analysis reports for offline review.
* **✨ AI Bullet Optimizer:** Rewrites existing resume bullet points dynamically to seamlessly integrate target keywords.

---

## 🛠️ Tech Stack & Tools

* **Frontend / UI:** Streamlit
* **AI Engine:** Google Gemini API (`gemini-1.5-flash` / `gemini-pro`)
* **Document Processing:** PyPDF2 / pdfplumber
* **Language & PDF Generation:** Python, ReportLab / FPDF

---

## 🚀 Getting Started

### 1. Prerequisites
Ensure Python 3.9 or higher is installed.

### 2. Installation
```bash
# Clone repository
git clone [https://github.com/your-username/ai-resume-ats-analyzer.git](https://github.com/your-username/ai-resume-ats-analyzer.git)
cd ai-resume-ats-analyzer

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Run Application
```bash
streamlit run app.py
```

---

## 📸 Demo & Workflow

1. **Enter API Key:** Provide your Google Gemini API key in the sidebar.
2. **Upload & Paste:** Upload your resume PDF and paste the target Job Description.
3. **Analyze:** Click **Analyze** to generate match scores, missing keywords, and recommendations.
4. **Download Report:** Export the complete feedback into a clean PDF summary report.
