import io
import json
import re
from datetime import datetime

import google.generativeai as genai
import streamlit as st
from PyPDF2 import PdfReader
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

st.set_page_config(
    page_title="AI Resume & ATS Analyzer",
    page_icon="📄",
    layout="wide",
)

# High Quota Stable Model
PRIMARY_MODEL = "gemini-3.5-flash"
FALLBACK_MODEL = "gemini-2.0-flash"

ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "ats_match_percentage": {
            "type": "number",
            "description": "Overall ATS match score from 0 to 100.",
        },
        "missing_keywords": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Important job keywords or skills missing from the resume.",
        },
        "strengths": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Key profile strengths relative to the job.",
        },
        "weaknesses": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Key profile weaknesses or gaps relative to the job.",
        },
        "recommendations": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Specific, actionable resume improvement suggestions.",
        },
    },
    "required": [
        "ats_match_percentage",
        "missing_keywords",
        "strengths",
        "weaknesses",
        "recommendations",
    ],
}

BULLET_SCHEMA = {
    "type": "object",
    "properties": {
        "optimized_bullet": {
            "type": "string",
            "description": "The rewritten, ATS-optimized resume bullet point.",
        },
        "keywords_integrated": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Missing keywords successfully woven into the bullet.",
        },
    },
    "required": ["optimized_bullet", "keywords_integrated"],
}

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None
if "stored_job_description" not in st.session_state:
    st.session_state.stored_job_description = ""


def escape_pdf_text(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def extract_text_from_pdf(uploaded_file) -> str:
    """Extract plain text from an uploaded PDF resume."""
    reader = PdfReader(uploaded_file)
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n".join(pages).strip()


def parse_json_response(raw_text: str) -> dict:
    """Parse Gemini JSON output, with a fallback for fenced code blocks."""
    text = raw_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def configure_gemini(api_key: str) -> None:
    genai.configure(api_key=api_key)


def build_analysis_prompt(resume_text: str, job_description: str) -> str:
    return f"""You are an expert ATS (Applicant Tracking System) analyst and career coach.

Compare the candidate's resume against the job description below. Be specific, practical, and honest.

Return your analysis as JSON matching the required schema.

Guidelines:
- ats_match_percentage: integer or decimal from 0 to 100 based on skills, experience, keywords, and role fit.
- missing_keywords: list important skills, tools, certifications, or terms from the job description that are absent or weak in the resume.
- strengths: 3-6 concise bullet-style points about what aligns well.
- weaknesses: 3-6 concise bullet-style points about gaps or risks.
- recommendations: 4-8 concrete edits the candidate should make to improve ATS match and recruiter appeal.

JOB DESCRIPTION:
{job_description}

RESUME:
{resume_text}
"""


def analyze_with_gemini(api_key: str, resume_text: str, job_description: str) -> dict:
    configure_gemini(api_key)
    prompt = build_analysis_prompt(resume_text, job_description)
    
    try:
        model = genai.GenerativeModel(
            model_name=PRIMARY_MODEL,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=ANALYSIS_SCHEMA,
                temperature=0.3,
            ),
        )
        response = model.generate_content(prompt)
        return parse_json_response(response.text)
    except Exception as e:
        # Fallback if primary model runs out of quota or fails
        if "429" in str(e) or "ResourceExhausted" in str(e):
            st.warning(f"⚠️ Primary model quota reached. Switching to fallback model ({FALLBACK_MODEL})...")
            model = genai.GenerativeModel(
                model_name=FALLBACK_MODEL,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=ANALYSIS_SCHEMA,
                    temperature=0.3,
                ),
            )
            response = model.generate_content(prompt)
            return parse_json_response(response.text)
        else:
            raise e


def build_bullet_prompt(
    bullet: str,
    missing_keywords: list[str],
    job_description: str,
) -> str:
    keywords_str = ", ".join(missing_keywords) if missing_keywords else "relevant job keywords"
    return f"""You are an expert resume writer specializing in ATS optimization.

Rewrite the following resume bullet point to be stronger, more impactful, and naturally integrate these missing job keywords where truthful and relevant: {keywords_str}

Rules:
- Keep it to one concise bullet point (1-2 lines max)
- Use strong action verbs and quantifiable impact where possible
- Do NOT invent experience or skills the candidate does not imply
- Integrate keywords naturally, not as a keyword dump
- Return JSON with optimized_bullet (string) and keywords_integrated (array of keywords you successfully wove in)

JOB DESCRIPTION (for context):
{job_description}

ORIGINAL BULLET:
{bullet}
"""


def optimize_bullet_with_gemini(
    api_key: str,
    bullet: str,
    missing_keywords: list[str],
    job_description: str,
) -> dict:
    configure_gemini(api_key)
    prompt = build_bullet_prompt(bullet, missing_keywords, job_description)
    
    try:
        model = genai.GenerativeModel(
            model_name=PRIMARY_MODEL,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=BULLET_SCHEMA,
                temperature=0.5,
            ),
        )
        response = model.generate_content(prompt)
        return parse_json_response(response.text)
    except Exception as e:
        if "429" in str(e) or "ResourceExhausted" in str(e):
            model = genai.GenerativeModel(
                model_name=FALLBACK_MODEL,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=BULLET_SCHEMA,
                    temperature=0.5,
                ),
            )
            response = model.generate_content(prompt)
            return parse_json_response(response.text)
        else:
            raise e


def generate_pdf_report(result: dict) -> bytes:
    """Build a clean PDF report from analysis results."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontSize=20,
        spaceAfter=12,
        textColor=colors.HexColor("#1a1a2e"),
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#666666"),
        spaceAfter=16,
    )
    heading_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontSize=14,
        spaceBefore=14,
        spaceAfter=8,
        textColor=colors.HexColor("#16213e"),
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=11,
        leading=15,
        spaceAfter=4,
    )
    bullet_style = ParagraphStyle(
        "Bullet",
        parent=body_style,
        leftIndent=18,
        bulletIndent=8,
        spaceAfter=6,
    )

    story = []
    story.append(Paragraph("AI Resume &amp; ATS Analysis Report", title_style))
    story.append(
        Paragraph(
            f"Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
            subtitle_style,
        )
    )
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e0e0e0")))
    story.append(Spacer(1, 0.2 * inch))

    score = max(0, min(100, float(result.get("ats_match_percentage", 0))))
    story.append(Paragraph("ATS Match Score", heading_style))
    story.append(Paragraph(f"<b>{score:.1f}%</b>", body_style))
    story.append(Spacer(1, 0.15 * inch))

    sections = [
        ("Missing Keywords", result.get("missing_keywords", [])),
        ("Key Strengths", result.get("strengths", [])),
        ("Key Weaknesses", result.get("weaknesses", [])),
        ("Recommendations", result.get("recommendations", [])),
    ]

    for title, items in sections:
        story.append(Paragraph(title, heading_style))
        if items:
            for item in items:
                story.append(Paragraph(f"&bull; {escape_pdf_text(item)}", bullet_style))
        else:
            story.append(Paragraph("None identified.", body_style))
        story.append(Spacer(1, 0.08 * inch))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def render_match_score(score: float) -> None:
    score = max(0, min(100, float(score)))
    st.metric(label="ATS Match Score", value=f"{score:.1f}%")
    st.progress(score / 100)


def render_bullet_list(title: str, items: list[str], icon: str) -> None:
    st.subheader(f"{icon} {title}")
    if items:
        for item in items:
            st.markdown(f"- {item}")
    else:
        st.info("No items returned.")


def render_analysis_results(result: dict) -> None:
    st.success("Analysis complete!")
    st.divider()

    render_match_score(result.get("ats_match_percentage", 0))

    st.divider()
    left, right = st.columns(2)
    with left:
        render_bullet_list("Key Strengths", result.get("strengths", []), "✅")
    with right:
        render_bullet_list("Key Weaknesses", result.get("weaknesses", []), "⚠️")

    st.divider()
    render_bullet_list("Missing Keywords", result.get("missing_keywords", []), "🔍")

    st.divider()
    render_bullet_list(
        "Recommendations to Improve Your Resume",
        result.get("recommendations", []),
        "💡",
    )

    st.divider()
    pdf_bytes = generate_pdf_report(result)
    st.download_button(
        label="📥 Download PDF Report",
        data=pdf_bytes,
        file_name=f"ATS_Analysis_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
        mime="application/pdf",
        use_container_width=True,
    )


def render_bullet_optimizer(
    api_key: str,
    result: dict,
    job_description: str,
) -> None:
    st.subheader("✨ AI Resume Bullet Optimizer")
    st.markdown(
        "Paste an existing bullet from your resume and Gemini will rewrite it, "
        "naturally weaving in missing job keywords."
    )

    missing_keywords = result.get("missing_keywords", [])
    if missing_keywords:
        st.caption("Missing keywords to integrate: " + ", ".join(missing_keywords))

    original_bullet = st.text_area(
        "Original Resume Bullet",
        height=100,
        placeholder="e.g. Led a team project that improved efficiency and reduced costs.",
        key="bullet_optimizer_input",
    )

    if st.button("Optimize Bullet", type="secondary", use_container_width=True):
        if not api_key:
            st.error("Please enter your Gemini API key in the sidebar.")
        elif not original_bullet.strip():
            st.error("Please paste a resume bullet point to optimize.")
        else:
            with st.spinner("Optimizing your bullet point with Gemini AI..."):
                try:
                    optimized = optimize_bullet_with_gemini(
                        api_key,
                        original_bullet.strip(),
                        missing_keywords,
                        job_description,
                    )
                    st.markdown("**Optimized Bullet:**")
                    st.info(optimized.get("optimized_bullet", ""))

                    integrated = optimized.get("keywords_integrated", [])
                    if integrated:
                        st.markdown("**Keywords integrated:** " + ", ".join(integrated))
                except json.JSONDecodeError:
                    st.error("Failed to parse the AI response. Please try again.")
                except Exception as exc:
                    st.error(f"Bullet optimization failed: {exc}")


st.title("📄 AI Resume & ATS Analyzer")
st.markdown(
    "Upload your resume and paste a job description to get an ATS compatibility "
    "score, keyword gaps, and actionable improvement tips powered by Gemini AI."
)

with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input(
        "Gemini API Key",
        type="password",
        help="Get your key from Google AI Studio: [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey)",
    )
    st.markdown("---")
    st.markdown(
        "**How to use**\n\n"
        "1. Enter your Gemini API key\n"
        "2. Upload a PDF resume\n"
        "3. Paste the job description\n"
        "4. Click **Analyze**\n"
        "5. Download the PDF report or optimize a bullet point"
    )

col_upload, col_jd = st.columns(2)

with col_upload:
    uploaded_resume = st.file_uploader(
        "Upload Resume (PDF)",
        type=["pdf"],
        help="Only PDF files are supported.",
    )

with col_jd:
    job_description = st.text_area(
        "Job Description",
        height=280,
        placeholder="Paste the full job description here...",
    )

analyze_clicked = st.button("Analyze", type="primary", use_container_width=True)

if analyze_clicked:
    if not api_key:
        st.error("Please enter your Gemini API key in the sidebar.")
    elif not uploaded_resume:
        st.error("Please upload a PDF resume.")
    elif not job_description.strip():
        st.error("Please paste a job description.")
    else:
        with st.spinner("Reading resume and analyzing with Gemini AI..."):
            try:
                resume_text = extract_text_from_pdf(uploaded_resume)
                if not resume_text:
                    st.error(
                        "Could not extract text from the PDF. "
                        "The file may be scanned/image-based or empty."
                    )
                else:
                    result = analyze_with_gemini(api_key, resume_text, job_description.strip())
                    st.session_state.analysis_result = result
                    st.session_state.stored_job_description = job_description.strip()
            except json.JSONDecodeError:
                st.error("Failed to parse the AI response. Please try again.")
            except Exception as exc:
                st.error(f"Analysis failed: {exc}")

if st.session_state.analysis_result:
    render_analysis_results(st.session_state.analysis_result)
    st.divider()
    render_bullet_optimizer(
        api_key,
        st.session_state.analysis_result,
        st.session_state.stored_job_description,
    )