from datetime import datetime
from pathlib import Path
import re

import requests
import streamlit as st


BACKEND_URL = "http://127.0.0.1:8000"
DEFAULT_SOURCE_COUNT = 3
DOCUMENTS_DIRECTORY = Path("documents")

EXAMPLE_QUESTIONS = {
    "Application period": "When can I apply?",
    "Version conflict": (
        "The older exchange guide says I can request course "
        "approval after returning, but the current policy "
        "requires pre-approval. Which procedure applies?"
    ),
    "Role-aware guidance": (
        "A student changed a host course during mobility. "
        "What should the Academic Advisor do, and what remains "
        "the student's responsibility?"
    ),
    "Missing information": (
        "Exactly how many working days will a course-recognition "
        "request take?"
    ),
    "Submission conflict": (
        "Is an unsigned Learning Agreement sent by email a "
        "completed submission under the current procedure?"
    ),
    "Partner institutions": (
        "Which universities have an exchange agreement with us?"
    ),
}

DOCUMENT_HEADINGS = (
    "General rule",
    "Disclosure",
    "Unclear instructions",
    "Decision authority",
    "Scope",
    "Student responsibility",
    "Academic review",
    "Limitations",
    "Purpose",
    "Recurring application windows",
    "Student submission",
    "Responsibilities",
    "Exceptions and gaps",
    "Legacy procedure",
    "Approval",
    "Document status",
    "Before mobility",
    "During mobility",
    "After mobility",
    "Processing time",
    "Legacy submission method",
    "Initial submission",
    "Changes during mobility",
    "Final submission",
    "Historical answers",
    "Warning",
    "Starting an appeal",
    "Role boundaries",
    "Missing information",
    "Recognized partner institutions",
    "Confirming a current agreement",
)

ANSWER_SECTIONS = (
    "Applicable guidance",
    "Actions for the selected role",
    "Responsibilities of other roles",
    "Version and conflict check",
    "Information gaps",
)


LANGUAGE_OPTIONS = ("English", "Türkçe")

# The local model, the prompt contract and the synthetic policy documents
# are all English-only. Translating this dictionary changes interface
# chrome (labels, headings, status messages); it never changes the
# retrieved policy text or the generated answer, so evidence and citations
# stay exactly what the model produced.
TEXT = {
    "English": {
        "kicker": "GLOBAL MOBILITY INTELLIGENCE",
        "subtitle": (
            "Learn the current procedure and get guidance suited to "
            "your role. Every answer is backed by its source document, "
            "entirely on this device."
        ),
        "status_header": "Status",
        "engine_ready_label": "Local policy engine connected",
        "engine_ready_detail": "Private on-device inference",
        "technical_details_expander": "Technical system details",
        "chat_model_label": "Chat model",
        "embedding_model_label": "Embedding model",
        "retrieval_label": "Retrieval",
        "indexed_sections_metric": "Indexed policy sections",
        "engine_busy_label": "Local policy engine busy",
        "engine_busy_detail": "A local operation is still running",
        "busy_caption": (
            "The service was available moments ago. Its last known "
            "model and index details are shown below."
        ),
        "last_known_details_expander": "Last known system details",
        "engine_offline_label": "Local policy engine unavailable",
        "offline_info": "Start the app with .\\serve_globalmobility.ps1.",
        "privacy_header": "Privacy",
        "privacy_note_html": (
            "Policy documents, questions and model responses remain "
            "on this device. No cloud inference API is used."
        ),
        "prototype_caption": (
            "Prototype developed with Microsoft Foundry Local."
        ),
        "ask_question_title": "Ask a policy question",
        "ask_question_description": (
            "Choose your role, try an example or write your own question."
        ),
        "try_example_label": "Try an example",
        "your_role_label": "Your role",
        "your_question_label": "Your question",
        "submit_button_label": "Check applicable policies",
        "backend_offline_error": (
            "The local backend is not running. Start backend.py first."
        ),
        "engine_starting_warning": (
            "The local policy engine is still starting. Try again in "
            "a moment."
        ),
        "empty_question_warning": "Please enter a policy question.",
        "spinner_text": (
            "Reviewing current and historical policies on this device..."
        ),
        "timeout_error": (
            "The local model exceeded the response timeout."
        ),
        "connection_error": "The connection to the backend was lost.",
        "quality_gate_failed_error": (
            "The system could not produce a confidently grounded answer "
            "for this question and role. Try the matching role for this "
            "example, or rephrase your question."
        ),
        "backend_interrupted_error": (
            "The local model connection was interrupted before it "
            "finished responding. This is usually temporary — please "
            "wait a moment and try again."
        ),
        "policy_guidance_title": "Policy guidance",
        "bottom_line_kicker": "Bottom line",
        "what_next_heading": "What to do next",
        "actions_heading": "What you should do as {role}",
        "other_roles_heading": "Who else is involved",
        "information_gap_heading": "What the policy does not specify",
        "documents_checked_heading": "Documents checked",
        "sources_used_heading": "Sources used",
        "source_effective_owner": "{status} · Effective {date} · Owner: {owner}",
        "audit_details_expander": "Audit details (optional)",
        "audit_details_caption": (
            "Version comparison, role boundaries and information-gap "
            "checks for reviewers."
        ),
        "completed_locally_caption": "Completed locally in {duration}.",
        "sources_verification_title": "Sources and verification",
        "sources_verification_description": (
            "Open a source to check its status, date and owner. "
            "Technical ranking details and the original policy text "
            "are available inside each source."
        ),
        "source_title_version_date": "{title} · Version {version} · Effective {date}",
        "source_caption": (
            "{status} · Owner: {owner} · Audience: {audience} · "
            "File: {source_name}"
        ),
        "version_link_info": (
            "Version link: shown next to the current version for "
            "comparison, regardless of its ranking score below, because "
            "it is explicitly marked as a previous or replacement "
            "version in the policy metadata."
        ),
        "score_question_match": "Question match",
        "score_policy_authority": "Policy authority",
        "score_recency": "Recency",
        "score_role_relevance": "Role relevance",
        "score_legend_caption": (
            "Question match = topic similarity · Policy authority = "
            "approval status · Recency = how current the document is · "
            "Role relevance = fit for the selected role."
        ),
        "overall_ranking_caption": (
            "Overall ranking: {score}. This retrieval score orders "
            "evidence; it is not a confidence score or an official "
            "policy rating."
        ),
        "view_original_popover": "View original policy text",
        "original_text_caption": (
            "Original text from this synthetic demonstration document."
        ),
        "raw_source_popover": "View raw source file (unedited)",
        "raw_source_caption": (
            "Exact, unformatted file contents, read directly from disk. "
            "Nothing has been added, removed or reformatted by the app "
            "— use this to check the answer against the source yourself."
        ),
        "footer_caption": (
            "GlobalMobility EDU is a research prototype using synthetic "
            "policy documents. Responses must be verified against "
            "official university sources and do not replace authorized "
            "academic decisions."
        ),
        "untitled_policy": "Untitled policy",
        "unknown_policy": "Unknown policy",
        "not_specified": "Not specified",
        "the_policy_owner": "the policy owner",
        "backend_invalid_response": (
            "The local backend returned an invalid response."
        ),
        "backend_unknown_error": "Unknown backend error.",
        "timing_bottom_line": (
            "The available current policies do not give a guaranteed "
            "number of working days or completion time {citations}."
        ),
        "timing_next_step": (
            "Ask {policy_owners} for the current expected timeline "
            "before relying on a deadline."
        ),
        "explain_current": (
            "Current approved evidence. Use this document for the "
            "present request."
        ),
        "explain_historical_linked": (
            "Included to show the documented version conflict. It is "
            "linked to the current policy and must not govern a new "
            "request."
        ),
        "explain_historical_plain": (
            "Historical comparison only. It must not govern a new "
            "request."
        ),
        "explain_draft": "Draft evidence only. It is not an approved policy.",
        "explain_default": (
            "Supporting evidence retrieved for comparison."
        ),
        "note_answer_english": (
            "The generated policy answer and source documents are "
            "shown in English, the language of the local model and "
            "the demonstration policies."
        ),
    },
    "Türkçe": {
        "kicker": "GLOBAL MOBILITY INTELLIGENCE",
        "subtitle": (
            "Geçerli süreci öğrenin ve rolünüze uygun rehberlik alın. "
            "Her cevap kaynak belgeyle desteklenir, tamamı bu cihazda "
            "çalışır."
        ),
        "status_header": "Durum",
        "engine_ready_label": "Yerel politika motoru bağlı",
        "engine_ready_detail": "Cihaz üzerinde özel çıkarım",
        "technical_details_expander": "Teknik sistem ayrıntıları",
        "chat_model_label": "Sohbet modeli",
        "embedding_model_label": "Gömme (embedding) modeli",
        "retrieval_label": "Getirim (retrieval)",
        "indexed_sections_metric": "İndekslenmiş politika bölümü",
        "engine_busy_label": "Yerel politika motoru meşgul",
        "engine_busy_detail": "Bir yerel işlem hâlâ çalışıyor",
        "busy_caption": (
            "Servis az önce kullanılabilirdi. Son bilinen model ve "
            "indeks bilgileri aşağıda gösteriliyor."
        ),
        "last_known_details_expander": "Son bilinen sistem ayrıntıları",
        "engine_offline_label": "Yerel politika motoru kullanılamıyor",
        "offline_info": "Uygulamayı .\\serve_globalmobility.ps1 ile başlatın.",
        "privacy_header": "Gizlilik",
        "privacy_note_html": (
            "Politika belgeleri, sorular ve model cevapları bu cihazda "
            "kalır. Bulut tabanlı bir çıkarım API'si kullanılmaz."
        ),
        "prototype_caption": (
            "Microsoft Foundry Local ile geliştirilen prototip."
        ),
        "ask_question_title": "Bir soru sor",
        "ask_question_description": (
            "Rolünüzü seçin, bir örnek deneyin veya kendi sorunuzu yazın."
        ),
        "try_example_label": "Bir örnek deneyin",
        "your_role_label": "Rolünüz",
        "your_question_label": "Sorunuz",
        "submit_button_label": "Geçerli politikaları kontrol et",
        "backend_offline_error": (
            "Yerel backend çalışmıyor. Önce backend.py dosyasını "
            "başlatın."
        ),
        "engine_starting_warning": (
            "Yerel politika motoru hâlâ başlatılıyor. Bir süre sonra "
            "tekrar deneyin."
        ),
        "empty_question_warning": "Lütfen bir politika sorusu girin.",
        "spinner_text": (
            "Güncel ve geçmiş politikalar bu cihaz üzerinde "
            "inceleniyor..."
        ),
        "timeout_error": (
            "Yerel model, yanıt zaman aşımı süresini aştı."
        ),
        "connection_error": "Backend ile bağlantı kesildi.",
        "quality_gate_failed_error": (
            "Sistem bu soru ve rol için güvenilir, kanıta dayalı bir "
            "cevap üretemedi. Örnekteki eşleşen rolü deneyin veya "
            "sorunuzu farklı ifade edin."
        ),
        "backend_interrupted_error": (
            "Yerel model bağlantısı, cevabını tamamlamadan kesildi. "
            "Bu genellikle geçicidir — birazdan tekrar deneyin."
        ),
        "policy_guidance_title": "Politika rehberliği",
        "bottom_line_kicker": "Özet",
        "what_next_heading": "Şimdi ne yapmalısınız",
        "actions_heading": "{role} olarak yapmanız gerekenler",
        "other_roles_heading": "Sürece dahil olan diğer roller",
        "information_gap_heading": "Politikanın belirtmediği noktalar",
        "documents_checked_heading": "Kontrol edilen belgeler",
        "sources_used_heading": "Kullanılan kaynaklar",
        "source_effective_owner": (
            "{status} · Yürürlük {date} · Sahip: {owner}"
        ),
        "audit_details_expander": "Denetim ayrıntıları (opsiyonel)",
        "audit_details_caption": (
            "İncelemeciler için sürüm karşılaştırması, rol sınırları ve "
            "eksik-bilgi kontrolleri."
        ),
        "completed_locally_caption": "Cihazda {duration} içinde tamamlandı.",
        "sources_verification_title": "Kaynaklar ve doğrulama",
        "sources_verification_description": (
            "Durumunu, tarihini ve sahibini kontrol etmek için bir "
            "kaynağı açın. Teknik sıralama ayrıntıları ve orijinal "
            "politika metni her kaynağın içinde bulunur."
        ),
        "source_title_version_date": (
            "{title} · Sürüm {version} · Yürürlük {date}"
        ),
        "source_caption": (
            "{status} · Sahip: {owner} · Hedef kitle: {audience} · "
            "Dosya: {source_name}"
        ),
        "version_link_info": (
            "Sürüm bağlantısı: bu belge, aşağıdaki sıralama puanından "
            "bağımsız olarak, güncel sürümle karşılaştırma amacıyla "
            "yanına eklenmiştir — çünkü politika metadata'sında önceki "
            "veya yerini alan bir sürüm olarak açıkça işaretlenmiştir."
        ),
        "score_question_match": "Soru eşleşmesi",
        "score_policy_authority": "Politika yetkisi",
        "score_recency": "Güncellik",
        "score_role_relevance": "Rol uygunluğu",
        "score_legend_caption": (
            "Soru eşleşmesi = konu benzerliği · Politika yetkisi = "
            "onay durumu · Güncellik = belgenin ne kadar güncel olduğu "
            "· Rol uygunluğu = seçili role uygunluk."
        ),
        "overall_ranking_caption": (
            "Genel sıralama: {score}. Bu getirim skoru kanıtları "
            "sıralar; bir güven skoru veya resmi bir politika "
            "değerlendirmesi değildir."
        ),
        "view_original_popover": "Orijinal politika metnini görüntüle",
        "original_text_caption": (
            "Bu sentetik demo belgesinin orijinal metni."
        ),
        "raw_source_popover": "Ham kaynak dosyasını görüntüle (düzenlenmemiş)",
        "raw_source_caption": (
            "Diskten doğrudan okunan, tam ve biçimlendirilmemiş dosya "
            "içeriği. Uygulama hiçbir şey eklemedi, çıkarmadı veya "
            "yeniden düzenlemedi — cevabı kaynakla kendiniz "
            "karşılaştırmak için kullanın."
        ),
        "footer_caption": (
            "GlobalMobility EDU, sentetik politika belgeleri kullanan bir "
            "araştırma prototipidir. Cevaplar resmi üniversite "
            "kaynaklarıyla doğrulanmalı ve yetkili akademik kararların "
            "yerini tutmaz."
        ),
        "untitled_policy": "Başlıksız politika",
        "unknown_policy": "Bilinmeyen politika",
        "not_specified": "Belirtilmemiş",
        "the_policy_owner": "politika sahibini",
        "backend_invalid_response": (
            "Yerel backend geçersiz bir yanıt döndürdü."
        ),
        "backend_unknown_error": "Bilinmeyen backend hatası.",
        "timing_bottom_line": (
            "Mevcut güncel politikalar garantili bir işlem günü sayısı "
            "veya tamamlanma süresi vermiyor {citations}."
        ),
        "timing_next_step": (
            "Bir teslim tarihine güvenmeden önce güncel zaman "
            "çizelgesini {policy_owners} birimine sorun."
        ),
        "explain_current": (
            "Güncel onaylı kanıt. Bu belgeyi mevcut talep için kullanın."
        ),
        "explain_historical_linked": (
            "Belgelenmiş sürüm çakışmasını göstermek için eklendi. "
            "Güncel politikayla bağlantılıdır ve yeni bir talebi "
            "yönetmemelidir."
        ),
        "explain_historical_plain": (
            "Yalnızca tarihsel karşılaştırma amaçlıdır. Yeni bir talebi "
            "yönetmemelidir."
        ),
        "explain_draft": (
            "Yalnızca taslak kanıt. Onaylanmış bir politika değildir."
        ),
        "explain_default": (
            "Karşılaştırma için getirilen destekleyici kanıt."
        ),
        "note_answer_english": (
            "Üretilen politika cevabı ve kaynak belgeler, yerel modelin "
            "ve demo politikalarının dili olan İngilizce olarak "
            "gösterilir."
        ),
    },
}


def t(key, **kwargs):
    """Return the interface string for the active language."""

    language = st.session_state.get("language", LANGUAGE_OPTIONS[0])
    catalog = TEXT.get(language, TEXT["English"])
    template = catalog.get(key, TEXT["English"].get(key, key))
    return template.format(**kwargs) if kwargs else template


STATUS_LABELS = {
    "English": {
        "current_approved": "Current approved",
        "legacy": "Historical — do not use",
        "legacy_unverified": "Historical — unverified",
        "superseded": "Replaced — do not use",
        "draft": "Draft — not approved",
        "unclassified": "Unclassified",
    },
    "Türkçe": {
        "current_approved": "Onaylı ve güncel",
        "legacy": "Tarihsel — kullanılmamalı",
        "legacy_unverified": "Tarihsel — doğrulanmamış",
        "superseded": "Yerini almış — kullanılmamalı",
        "draft": "Taslak — onaylanmamış",
        "unclassified": "Sınıflandırılmamış",
    },
}

ROLE_DISPLAY_NAMES = {
    "English": {
        "Student": "Student",
        "Academic Advisor": "Academic Advisor",
        "Department Administrator": "Department Administrator",
    },
    "Türkçe": {
        "Student": "Öğrenci",
        "Academic Advisor": "Akademik Danışman",
        "Department Administrator": "Bölüm Sekreterliği",
    },
}

SCENARIO_DISPLAY_NAMES = {
    "English": {name: name for name in EXAMPLE_QUESTIONS},
    "Türkçe": {
        "Application period": "Başvuru dönemi",
        "Version conflict": "Sürüm çakışması",
        "Role-aware guidance": "Role özel rehberlik",
        "Missing information": "Eksik bilgi",
        "Submission conflict": "Teslim çakışması",
        "Partner institutions": "Anlaşmalı üniversiteler",
    },
}

MONTH_ABBREVIATIONS_TR = {
    "Jan": "Oca", "Feb": "Şub", "Mar": "Mar", "Apr": "Nis",
    "May": "May", "Jun": "Haz", "Jul": "Tem", "Aug": "Ağu",
    "Sep": "Eyl", "Oct": "Eki", "Nov": "Kas", "Dec": "Ara",
}


st.set_page_config(
    page_title="GlobalMobility EDU",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="auto",
)

st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Inter:wght@400;500;600;700&display=swap');

        :root {
            --navy: #173b63;
            --navy-deep: #0f2a48;
            --gold: #9a7438;
            --gold-light: #c9a15c;
            --bg: #f7f6f2;
            --surface: #ffffff;
            --border: #dde3ec;
            --text: #172b4d;
            --muted: #64748b;
            --font-serif: 'Fraunces', Georgia, 'Times New Roman', serif;
            --font-sans: 'Inter', -apple-system, BlinkMacSystemFont,
                'Segoe UI', sans-serif;
        }

        /* Keep the header in the layout (it still hosts the sidebar
           reopen control) but strip its background/shadow so the empty
           toolbar (toolbarMode=minimal) does not read as a colored bar. */
        [data-testid="stHeader"] {
            background: transparent;
            box-shadow: none;
        }
        [data-testid="stMainBlockContainer"] { padding-top: 1.4rem; }

        .stApp {
            font-family: var(--font-sans);
            background:
                radial-gradient(circle at 88% 6%, rgba(154, 116, 56, .11) 0%, transparent 46%),
                radial-gradient(circle at 6% 96%, rgba(23, 59, 99, .09) 0%, transparent 42%),
                repeating-linear-gradient(
                    135deg,
                    rgba(23, 59, 99, .025) 0px,
                    rgba(23, 59, 99, .025) 1px,
                    transparent 1px,
                    transparent 26px
                ),
                linear-gradient(180deg, var(--bg) 0%, #ffffff 46%);
        }
        .hero-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 2.5rem;
        }
        .hero-copy { flex: 1 1 auto; min-width: 0; }
        .hero-seal {
            flex: 0 0 auto;
            opacity: .9;
        }
        .doc-rule {
            width: 84px;
            margin-top: 1.1rem;
            border-top: 3px solid var(--navy);
        }
        .doc-rule::after {
            content: "";
            display: block;
            width: 38px;
            margin-top: 3px;
            border-top: 1px solid var(--gold);
        }
        @media (max-width: 900px) {
            .hero-seal { display: none; }
        }
        [data-testid="stMarkdownContainer"],
        [data-testid="stMarkdownContainer"] p,
        [data-testid="stCaptionContainer"],
        [data-testid="stWidgetLabel"] p,
        [data-testid="stTextArea"] textarea,
        [data-testid="stSelectbox"] input {
            font-family: var(--font-sans) !important;
        }
        .block-container {
            max-width: 1120px;
            padding-bottom: 4rem;
        }
        .academic-label {
            color: var(--gold);
            font-size: .74rem;
            font-weight: 700;
            letter-spacing: .2rem;
            margin-bottom: .6rem;
        }
        .academic-title, .section-title {
            font-family: var(--font-serif) !important;
        }
        .academic-title {
            color: var(--navy);
            font-size: 3.4rem;
            font-weight: 600;
            line-height: 1.05;
            letter-spacing: -.01em;
        }
        .academic-title span { color: var(--gold); font-style: italic; }
        .subtitle {
            color: var(--muted);
            font-size: 1.06rem;
            line-height: 1.7;
            max-width: 780px;
            margin: .9rem 0 2.2rem 0;
        }
        .answer-kicker {
            color: var(--gold);
            font-size: .76rem;
            font-weight: 700;
            letter-spacing: .08rem;
            text-transform: uppercase;
            margin-bottom: .35rem;
        }
        .section-title {
            color: var(--navy);
            font-size: 1.65rem;
            font-weight: 600;
            margin-bottom: .3rem;
        }
        .section-description {
            color: var(--muted);
            font-size: .94rem;
            margin-bottom: 1.15rem;
        }
        .status-dot {
            display: inline-block;
            width: .55rem;
            height: .55rem;
            border-radius: 50%;
            margin-right: .4rem;
            vertical-align: middle;
        }
        .status-dot--ready {
            background: #2f9e6e;
            box-shadow: 0 0 0 3px rgba(47, 158, 110, .18);
        }
        .status-dot--busy {
            background: #c99a3a;
            box-shadow: 0 0 0 3px rgba(201, 154, 58, .18);
        }
        .status-dot--offline {
            background: #c15a5a;
            box-shadow: 0 0 0 3px rgba(193, 90, 90, .18);
        }
        .status-line {
            display: flex;
            align-items: center;
            font-size: .88rem;
            font-weight: 600;
            color: var(--text);
        }
        .status-sub {
            font-size: .8rem;
            color: var(--muted);
            margin: .15rem 0 0 1rem;
        }
        .privacy-note {
            padding: .85rem 1rem;
            border-left: 3px solid var(--gold);
            background: #f8f4ea;
            color: #5f5544;
            font-size: .87rem;
            line-height: 1.55;
        }
        div[data-testid="stForm"] {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: .9rem;
            padding: 1.35rem;
            box-shadow: 0 8px 25px rgba(23, 59, 99, .06);
        }
        [data-testid="stSidebar"] {
            background: #fbfbfa !important;
            border-right: 1px solid var(--border);
        }
        [data-testid="stSidebar"] [data-testid="stHeading"] h2,
        [data-testid="stSidebar"] [data-testid="stHeading"] h3 {
            font-family: var(--font-sans) !important;
            font-size: .68rem !important;
            font-weight: 700 !important;
            letter-spacing: .09rem !important;
            text-transform: uppercase !important;
            color: var(--muted) !important;
            margin: 1.5rem 0 .7rem 0 !important;
            padding: 0 !important;
        }
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"]
            > div:first-child [data-testid="stHeading"] h2 {
            margin-top: 0 !important;
        }
        div[data-testid="stMetric"] {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: .75rem;
            padding: .75rem .85rem;
        }
        [data-testid="stMetricLabel"] {
            font-size: .7rem;
            text-transform: uppercase;
            letter-spacing: .05rem;
            color: var(--muted);
        }
        [data-testid="stMetricValue"] {
            color: var(--navy);
            font-weight: 700;
        }
        [data-testid="stWidgetLabel"] p {
            font-weight: 600;
            color: var(--text);
            font-size: .92rem;
        }
        [data-testid="stSelectbox"] [role="group"],
        [data-testid="stTextArea"] textarea {
            border: 1px solid var(--border) !important;
            border-radius: .65rem !important;
            background: var(--surface) !important;
            transition: border-color .15s ease, box-shadow .15s ease;
        }
        [data-testid="stSelectbox"] [role="group"]:focus-within,
        [data-testid="stTextArea"] textarea:focus {
            border-color: var(--navy) !important;
            box-shadow: 0 0 0 3px rgba(23, 59, 99, .12) !important;
        }
        [data-testid="stSelectbox"] input[role="combobox"] {
            color: var(--text) !important;
        }
        .stFormSubmitButton > button,
        [data-testid="stBaseButton-primaryFormSubmit"] {
            background: var(--navy);
            border-color: var(--navy);
            color: #ffffff;
            font-weight: 650;
            letter-spacing: .01em;
            border-radius: .65rem;
            transition: background .15s ease;
        }
        .stFormSubmitButton > button:hover,
        [data-testid="stBaseButton-primaryFormSubmit"]:hover {
            background: var(--navy-deep);
            border-color: var(--navy-deep);
            color: #ffffff;
        }
        div[data-testid="stExpander"] {
            border: 1px solid var(--border);
            border-radius: .7rem;
            background: var(--surface);
            overflow: hidden;
        }
        hr {
            border-color: var(--border) !important;
        }
        @media (max-width: 760px) {
            [data-testid="stMainBlockContainer"] {
                padding: 1.35rem 1rem 3rem 1rem;
            }
            .academic-title {
                font-size: 2.35rem;
            }
            .subtitle {
                font-size: .96rem;
                margin-bottom: 1.55rem;
            }
            .section-title {
                font-size: 1.45rem;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def get_backend_health():
    try:
        response = requests.get(
            f"{BACKEND_URL}/health",
            timeout=5,
        )
        if response.ok:
            return response.json()
    except requests.RequestException:
        return None

    return None


class QualityGateFailure(RuntimeError):
    """Raised when the backend's fail-closed answer-quality gate rejects a draft."""


def request_analysis(question, role, top_k):
    response = requests.post(
        f"{BACKEND_URL}/analyze",
        json={
            "question": question,
            "role": role,
            "top_k": top_k,
        },
        timeout=900,
    )

    try:
        data = response.json()
    except ValueError as error:
        raise RuntimeError(t("backend_invalid_response")) from error

    if not response.ok:
        message = data.get("error", t("backend_unknown_error"))
        if response.status_code == 422:
            raise QualityGateFailure(message)
        raise RuntimeError(message)

    return data


def sync_example_question():
    selected_scenario = st.session_state["demonstration_scenario"]
    st.session_state["policy_question"] = EXAMPLE_QUESTIONS[
        selected_scenario
    ]


def humanize_status(status):
    language = st.session_state.get("language", LANGUAGE_OPTIONS[0])
    labels = STATUS_LABELS.get(language, STATUS_LABELS["English"])
    return labels.get(
        status,
        str(status).replace("_", " ").strip().title(),
    )


def format_duration(seconds):
    language = st.session_state.get("language", LANGUAGE_OPTIONS[0])
    rounded_seconds = max(0, round(float(seconds)))

    if language == "Türkçe":
        unit_min, unit_sec = "dk", "sn"
    else:
        unit_min, unit_sec = "min", "sec"

    if rounded_seconds < 60:
        return f"{rounded_seconds} {unit_sec}"

    minutes, remaining_seconds = divmod(rounded_seconds, 60)
    if remaining_seconds == 0:
        return f"{minutes} {unit_min}"
    return f"{minutes} {unit_min} {remaining_seconds} {unit_sec}"


def format_date(date_value):
    try:
        parsed_date = datetime.strptime(date_value, "%Y-%m-%d")
    except (TypeError, ValueError):
        return date_value or t("not_specified")

    language = st.session_state.get("language", LANGUAGE_OPTIONS[0])
    month_abbreviation = parsed_date.strftime("%b")

    if language == "Türkçe":
        month_abbreviation = MONTH_ABBREVIATIONS_TR.get(
            month_abbreviation,
            month_abbreviation,
        )

    return f"{parsed_date.day} {month_abbreviation} {parsed_date.year}"


def read_raw_source_text(source_name):
    """Return the exact on-disk contents of a source file, or None."""

    path = DOCUMENTS_DIRECTORY / source_name

    if not path.is_file():
        return None

    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def format_evidence_content(content):
    if not content:
        return "No policy text available."

    formatted = content.strip()
    notice = (
        "SYNTHETIC DEMONSTRATION DOCUMENT — "
        "NOT AN OFFICIAL UNIVERSITY POLICY"
    )
    notice_match = re.match(rf"{re.escape(notice)}\.?\s*", formatted)

    if notice_match:
        formatted = (
            f"*{notice.title()}*\n\n" + formatted[notice_match.end():]
        )

    for heading in DOCUMENT_HEADINGS:
        formatted = re.sub(
            rf"(?<!\w){re.escape(heading)}\.?(?=\s|$)",
            f"\n\n**{heading}**\n\n",
            formatted,
        )

    return formatted.strip()


def build_source_reference_map(sources):
    references = {}
    for source in sources:
        source_name = source.get("source", t("unknown_policy"))
        if source_name not in references:
            references[source_name] = len(references) + 1
    return references


def format_answer_for_display(answer, source_references):
    formatted = answer
    for source_name, reference_number in source_references.items():
        formatted = formatted.replace(
            f"[{source_name}]",
            f"[**Source {reference_number}**](#source-{reference_number})",
        )

    status_terms = {
        "current_approved": "current approved",
        "legacy_unverified": "historical unverified",
    }
    for raw_status, readable_status in status_terms.items():
        formatted = formatted.replace(raw_status, readable_status)

    return formatted


def explain_source_role(source):
    status = source.get("status", "unclassified")
    linked_version = source.get("relationship_included")

    if status == "current_approved":
        return t("explain_current")
    if status in {"legacy", "legacy_unverified", "superseded"}:
        if linked_version:
            return t("explain_historical_linked")
        return t("explain_historical_plain")
    if status == "draft":
        return t("explain_draft")
    return t("explain_default")


def split_answer_sections(answer):
    heading_pattern = re.compile(
        r"^#{2,3}\s+("
        + "|".join(re.escape(heading) for heading in ANSWER_SECTIONS)
        + r")\s*$",
        flags=re.MULTILINE,
    )
    matches = list(heading_pattern.finditer(answer))
    sections = {}

    for index, match in enumerate(matches):
        body_start = match.end()
        body_end = (
            matches[index + 1].start()
            if index + 1 < len(matches)
            else len(answer)
        )
        sections[match.group(1)] = answer[body_start:body_end].strip()

    return sections


def is_empty_user_section(text):
    if not text:
        return True

    normalized = re.sub(r"\[[^\]]+\]", "", text).lower()
    empty_phrases = (
        "no selected-role action is specified",
        "no other-role responsibility specifies",
        "no material information gap was identified",
    )
    return any(phrase in normalized for phrase in empty_phrases)


def is_timing_question(question):
    return bool(
        re.search(
            r"(?:how many|exactly|processing time).{0,40}"
            r"(?:working )?days?|(?:working )?days?.{0,40}"
            r"(?:take|processing)",
            question,
            flags=re.IGNORECASE,
        )
    )


def build_user_answer(answer, question, sources):
    sections = split_answer_sections(answer)
    current_sources = [
        source
        for source in sources
        if source.get("status") == "current_approved"
    ]

    if is_timing_question(question) and current_sources:
        citations = " ".join(
            f"[{source['source']}]" for source in current_sources
        )
        policy_owners = ", ".join(
            dict.fromkeys(
                source.get("owner", t("the_policy_owner"))
                for source in current_sources
            )
        )
        bottom_line = t("timing_bottom_line", citations=citations)
        next_step = t("timing_next_step", policy_owners=policy_owners)
    else:
        bottom_line = sections.get("Applicable guidance", "").strip()
        if not bottom_line:
            bottom_line = sections.get(
                "Version and conflict check",
                "",
            ).strip()
        if not bottom_line:
            bottom_line = sections.get("Information gaps", "").strip()
        if not bottom_line:
            bottom_line = answer.strip()
        next_step = ""

    actions = sections.get("Actions for the selected role", "")
    other_roles = sections.get("Responsibilities of other roles", "")
    information_gap = (
        ""
        if is_timing_question(question)
        else sections.get("Information gaps", "")
    )

    return {
        "bottom_line": bottom_line,
        "next_step": next_step,
        "actions": "" if is_empty_user_section(actions) else actions,
        "other_roles": (
            "" if is_empty_user_section(other_roles) else other_roles
        ),
        "information_gap": (
            ""
            if is_empty_user_section(information_gap)
            else information_gap
        ),
    }


if "language" not in st.session_state:
    st.session_state["language"] = LANGUAGE_OPTIONS[0]

with st.sidebar:
    st.selectbox(
        "Language / Dil",
        LANGUAGE_OPTIONS,
        key="language",
    )

current_health = get_backend_health()
if current_health and current_health.get("status") == "ready":
    st.session_state["last_backend_health"] = current_health
    st.session_state["health_check_failures"] = 0
    health = current_health
    engine_state = "ready"
elif current_health:
    health = current_health
    engine_state = "busy"
elif (
    st.session_state.get("last_backend_health")
    and st.session_state.get("health_check_failures", 0) < 2
):
    st.session_state["health_check_failures"] = (
        st.session_state.get("health_check_failures", 0) + 1
    )
    health = st.session_state["last_backend_health"]
    engine_state = "busy"
else:
    st.session_state["health_check_failures"] = (
        st.session_state.get("health_check_failures", 0) + 1
    )
    health = None
    engine_state = "offline"

HERO_SEAL_SVG = (
    '<img src="data:image/png;base64,' + "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" + '" '
    'alt="GlobalMobility EDU logo" width="129" height="190" '
    'style="display:block;" />'
)

st.markdown(
    f"""
    <div class="hero-row">
        <div class="hero-copy">
            <div class="academic-label">{t('kicker')}</div>
            <div class="academic-title">GlobalMobility <span>EDU</span></div>
            <div class="doc-rule"></div>
            <div class="subtitle">
                {t('subtitle')}
            </div>
        </div>
        <div class="hero-seal">{HERO_SEAL_SVG}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header(t("status_header"))

    if engine_state == "ready":
        st.markdown(
            f"""
            <div class="status-line">
                <span class="status-dot status-dot--ready"></span>
                {t('engine_ready_label')}
            </div>
            <div class="status-sub">{t('engine_ready_detail')}</div>
            """,
            unsafe_allow_html=True,
        )
        with st.expander(t("technical_details_expander")):
            st.write(
                f"**{t('chat_model_label')}**  \n"
                f"{health.get('chat_model', 'Phi-4 Mini')}"
            )
            st.write(
                f"**{t('embedding_model_label')}**  \n"
                f"{health.get('embedding_model', 'Qwen3 Embedding')}"
            )
            st.write(
                f"**{t('retrieval_label')}**  \n"
                f"{health.get('ranking', 'Policy-aware ranking')}"
            )
            st.metric(
                t("indexed_sections_metric"),
                health.get("indexed_chunks", 0),
            )
    elif engine_state == "busy":
        st.markdown(
            f"""
            <div class="status-line">
                <span class="status-dot status-dot--busy"></span>
                {t('engine_busy_label')}
            </div>
            <div class="status-sub">{t('engine_busy_detail')}</div>
            """,
            unsafe_allow_html=True,
        )
        st.caption(t("busy_caption"))
        with st.expander(t("last_known_details_expander")):
            st.write(
                f"**{t('chat_model_label')}**  \n"
                f"{health.get('chat_model', 'Phi-4 Mini')}"
            )
            st.write(
                f"**{t('embedding_model_label')}**  \n"
                f"{health.get('embedding_model', 'Qwen3 Embedding')}"
            )
            st.metric(
                t("indexed_sections_metric"),
                health.get("indexed_chunks", 0),
            )
    else:
        st.markdown(
            f"""
            <div class="status-line">
                <span class="status-dot status-dot--offline"></span>
                {t('engine_offline_label')}
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.info(t("offline_info"))

    st.subheader(t("privacy_header"))
    st.markdown(
        f"""
        <div class="privacy-note">
            {t('privacy_note_html')}
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(t("prototype_caption"))
    if st.session_state.get("language") == "Türkçe":
        st.caption(t("note_answer_english"))

st.markdown(
    f"""
    <div class="section-title">{t('ask_question_title')}</div>
    <div class="section-description">
        {t('ask_question_description')}
    </div>
    """,
    unsafe_allow_html=True,
)

if "demonstration_scenario" not in st.session_state:
    st.session_state["demonstration_scenario"] = next(
        iter(EXAMPLE_QUESTIONS)
    )
if "policy_question" not in st.session_state:
    sync_example_question()

active_language = st.session_state.get("language", LANGUAGE_OPTIONS[0])
scenario_labels = SCENARIO_DISPLAY_NAMES.get(
    active_language,
    SCENARIO_DISPLAY_NAMES["English"],
)
role_labels = ROLE_DISPLAY_NAMES.get(
    active_language,
    ROLE_DISPLAY_NAMES["English"],
)

example_name = st.selectbox(
    t("try_example_label"),
    list(EXAMPLE_QUESTIONS),
    key="demonstration_scenario",
    format_func=lambda name: scenario_labels.get(name, name),
    on_change=sync_example_question,
)

with st.form("policy_analysis_form"):
    role = st.selectbox(
        t("your_role_label"),
        [
            "Student",
            "Academic Advisor",
            "Department Administrator",
        ],
        format_func=lambda value: role_labels.get(value, value),
    )

    question = st.text_area(
        t("your_question_label"),
        key="policy_question",
        height=130,
    )
    analyze_button = st.form_submit_button(
        t("submit_button_label"),
        type="primary",
        width="stretch",
    )

if analyze_button:
    if engine_state == "offline":
        st.error(t("backend_offline_error"))
    elif current_health and current_health.get("status") != "ready":
        st.warning(t("engine_starting_warning"))
    elif not question.strip():
        st.warning(t("empty_question_warning"))
    else:
        with st.spinner(t("spinner_text")):
            try:
                result = request_analysis(
                    question=question,
                    role=role,
                    top_k=DEFAULT_SOURCE_COUNT,
                )
            except requests.Timeout:
                st.error(t("timeout_error"))
                st.stop()
            except requests.ConnectionError:
                st.error(t("connection_error"))
                st.stop()
            except QualityGateFailure:
                st.error(t("quality_gate_failed_error"))
                st.stop()
            except Exception:
                st.error(t("backend_interrupted_error"))
                st.stop()

        st.divider()
        st.markdown(
            f'<div class="section-title">{t("policy_guidance_title")}</div>',
            unsafe_allow_html=True,
        )
        sources = result.get("sources", [])
        source_references = build_source_reference_map(sources)
        user_answer = build_user_answer(
            result["answer"],
            question,
            sources,
        )
        if result.get("next_step"):
            user_answer["next_step"] = result["next_step"]
        with st.container(border=True):
            st.markdown(
                f'<div class="answer-kicker">{t("bottom_line_kicker")}</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                format_answer_for_display(
                    user_answer["bottom_line"],
                    source_references,
                )
            )

            if user_answer["next_step"]:
                st.markdown(f"### {t('what_next_heading')}")
                st.markdown(user_answer["next_step"])

            if user_answer["actions"]:
                st.markdown(
                    "### "
                    + t(
                        "actions_heading",
                        role=role_labels.get(role, role),
                    )
                )
                st.markdown(
                    format_answer_for_display(
                        user_answer["actions"],
                        source_references,
                    )
                )

            if user_answer["other_roles"]:
                st.markdown(f"### {t('other_roles_heading')}")
                st.markdown(
                    format_answer_for_display(
                        user_answer["other_roles"],
                        source_references,
                    )
                )

            if user_answer["information_gap"]:
                st.markdown(f"### {t('information_gap_heading')}")
                st.markdown(
                    format_answer_for_display(
                        user_answer["information_gap"],
                        source_references,
                    )
                )

            if source_references:
                source_heading = (
                    t("documents_checked_heading")
                    if result.get("answerability") == "not_covered"
                    else t("sources_used_heading")
                )
                st.markdown(f"### {source_heading}")
                listed_sources = set()
                for source in sources:
                    source_name = source.get(
                        "source",
                        t("unknown_policy"),
                    )
                    if source_name in listed_sources:
                        continue
                    listed_sources.add(source_name)
                    reference_number = source_references[source_name]
                    st.markdown(
                        f"[**Source {reference_number} — "
                        f"{source.get('title', t('untitled_policy'))} "
                        f"v{source.get('version', 'unknown')}**]"
                        f"(#source-{reference_number})  \n"
                        + t(
                            "source_effective_owner",
                            status=humanize_status(
                                source.get("status", "unclassified")
                            ),
                            date=format_date(source.get("effective_date")),
                            owner=source.get("owner", t("not_specified")),
                        )
                    )

        with st.expander(t("audit_details_expander")):
            st.caption(t("audit_details_caption"))
            st.markdown(
                format_answer_for_display(
                    result["answer"],
                    source_references,
                )
            )

        response_time = result.get("response_time_seconds")
        if response_time is not None:
            st.caption(
                t(
                    "completed_locally_caption",
                    duration=format_duration(response_time),
                )
            )

        st.divider()
        st.markdown(
            f"""
            <div class="section-title">{t('sources_verification_title')}</div>
            <div class="section-description">
                {t('sources_verification_description')}
            </div>
            """,
            unsafe_allow_html=True,
        )

        for index, source in enumerate(
            result.get("sources", []),
            start=1,
        ):
            source_name = source.get("source", t("unknown_policy"))
            status = source.get("status", "unclassified")
            score = source.get("score", 0.0)
            reference_number = source_references[source_name]
            label = (
                f":blue[Source {reference_number}] · "
                f":orange[{source.get('title', t('untitled_policy'))} "
                f"v{source.get('version', 'unknown')}] · "
                f"{humanize_status(status)}"
            )

            st.markdown(
                f'<span id="source-{reference_number}"></span>',
                unsafe_allow_html=True,
            )
            with st.expander(label):
                st.markdown(
                    t(
                        "source_title_version_date",
                        title=(
                            f":orange[**"
                            f"{source.get('title', t('untitled_policy'))}"
                            f"**]"
                        ),
                        version=source.get("version", "unknown"),
                        date=format_date(source.get("effective_date")),
                    )
                )
                st.caption(
                    t(
                        "source_caption",
                        status=humanize_status(status),
                        owner=source.get("owner", t("not_specified")),
                        audience=source.get(
                            "audience", t("not_specified")
                        ),
                        source_name=source_name,
                    )
                )

                if status == "current_approved":
                    st.success(explain_source_role(source))
                elif status in {
                    "legacy",
                    "legacy_unverified",
                    "superseded",
                    "draft",
                }:
                    st.warning(explain_source_role(source))
                else:
                    st.info(explain_source_role(source))

                if source.get("relationship_included"):
                    st.info(t("version_link_info"))

                score_columns = st.columns(4)
                score_columns[0].metric(
                    t("score_question_match"),
                    f"{source.get('semantic_score', 0):.0%}",
                )
                score_columns[1].metric(
                    t("score_policy_authority"),
                    f"{source.get('status_score', 0):.0%}",
                )
                score_columns[2].metric(
                    t("score_recency"),
                    f"{source.get('recency_score', 0):.0%}",
                )
                score_columns[3].metric(
                    t("score_role_relevance"),
                    f"{source.get('role_score', 0):.0%}",
                )
                st.caption(t("score_legend_caption"))
                st.caption(
                    t("overall_ranking_caption", score=f"{score:.0%}")
                )
                with st.popover(
                    t("view_original_popover"),
                    width="stretch",
                ):
                    st.caption(t("original_text_caption"))
                    st.markdown(
                        format_evidence_content(source.get("content"))
                    )

                raw_source_text = read_raw_source_text(source_name)
                if raw_source_text is not None:
                    with st.popover(
                        t("raw_source_popover"),
                        width="stretch",
                    ):
                        st.caption(t("raw_source_caption"))
                        st.code(raw_source_text, language=None)

st.divider()
st.caption(t("footer_caption"))
