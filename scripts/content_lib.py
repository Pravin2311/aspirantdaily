"""Shared configuration and state for the content pipeline.

The master plan is built from the topic lists in content/plan/topics/*.tsv plus
the existing pages recorded in content_inventory.json. Pipeline state (which
pages are drafted, reviewed, approved, published, and the hashes that make
publishing idempotent) lives in content/state.json.
"""
import csv
import hashlib
import json
import os
import re
from datetime import date

from seo_lib import HOST, ROOT

CONTENT = os.path.join(ROOT, "content")
TOPICS_DIR = os.path.join(CONTENT, "plan", "topics")
DRAFTS_DIR = os.path.join(CONTENT, "drafts")
PREVIEW_DIR = os.path.join(CONTENT, "preview")
BATCHES_DIR = os.path.join(CONTENT, "batches")
STATE_PATH = os.path.join(CONTENT, "state.json")
PLAN_CSV = os.path.join(ROOT, "CONTENT_MASTER_PLAN.csv")
INVENTORY = os.path.join(ROOT, "content_inventory.json")

STATUSES = ["planned", "drafted", "fact-checked", "approved", "published"]
PAGE_TYPES = {
    "guide": "A. Comprehensive topic guide",
    "mcq": "B. Topic-wise MCQ set",
    "method": "C. Quant/reasoning method page",
    "revision": "D. Revision resource",
    "exam": "E. Exam-specific resource",
    "ca": "F. Current affairs",
}
EXAMS = {"U": "UPSC", "S": "SSC", "B": "Banking", "R": "Railway", "P": "State PSC", "D": "Defence (CDS/NDA/AFCAT)"}

# Category -> (topic file, planning target incl. existing pages). Targets sum to 1,000.
CATEGORIES = {
    "Indian Polity and Constitution": ("polity.tsv", 180),
    "History and Culture": ("history.tsv", 130),
    "Geography and Environment": ("geography-environment.tsv", 120),
    "Quantitative Aptitude": ("quant.tsv", 150),
    "Reasoning and Computer Awareness": ("reasoning-computer.tsv", 120),
    "Economy and General Science": ("economy-science.tsv", 120),
    "Current Affairs and Static GK": ("current-affairs-gk.tsv", 70),
    "Exam-Specific Guides": ("exam-guides.tsv", 80),
    "English Language": ("english.tsv", 30),
}

ENV_SUBTOPICS = {"ecology", "biodiversity", "environment-laws", "pollution", "climate", "disasters"}
COMPUTER_SUBTOPICS = {"computer-basics", "software", "networking", "internet", "security", "office"}
ECONOMY_SUBTOPICS = {"national-income", "inflation", "banking", "financial-markets", "public-finance",
                     "external-sector", "planning", "development", "agriculture", "industry"}


def folder_for(category, subtopic):
    """Site folder for a planned page."""
    if category == "Indian Polity and Constitution":
        return "study/polity"
    if category == "History and Culture":
        return "study/gk" if subtopic == "static-gk" else "study/history"
    if category == "Geography and Environment":
        return "study/environment" if subtopic in ENV_SUBTOPICS else "study/geography"
    if category == "Quantitative Aptitude":
        return "study/quant"
    if category == "Reasoning and Computer Awareness":
        return "study/computer" if subtopic in COMPUTER_SUBTOPICS else "study/reasoning"
    if category == "Economy and General Science":
        return "study/economy" if subtopic in ECONOMY_SUBTOPICS else "study/science-tech"
    if category == "Current Affairs and Static GK":
        return "study/gk" if subtopic in ("static-gk", "awards") else "study/current-affairs"
    if category == "Exam-Specific Guides":
        return "exams"
    if category == "English Language":
        return "study/english"
    raise ValueError(category)


# Hubs that the pipeline creates when the first page in the folder is published.
NEW_HUBS = {
    "study/quant": ("Quantitative Aptitude", "Methods, worked examples and practice for SSC, bank and railway Quant."),
    "study/reasoning": ("Reasoning", "Methods and practice for verbal, logical and non-verbal reasoning."),
    "study/computer": ("Computer Awareness", "Hardware, software, networking and security for SSC and bank exams."),
    "study/english": ("English Language", "Grammar rules, vocabulary and comprehension methods for SSC and bank exams."),
    "study/gk": ("Static GK", "Verified static general knowledge lists with sources."),
    "exams": ("Exam Guides", "Syllabus, pattern and eligibility guides, each tied to its official notification."),
}

# Subtopic -> existing pages that cover it broadly (parents). Paths are site-relative.
PARENTS = {
    "constitution-basics": ["study/polity/constitution-making-and-salient-features.html"],
    "citizenship": ["study/polity/constitution-making-and-salient-features.html"],
    "amendments": ["study/polity/constitution-making-and-salient-features.html"],
    "official-language": ["study/polity/constitution-making-and-salient-features.html"],
    "fundamental-rights": ["study/polity/fundamental-rights-dpsp-duties.html"],
    "dpsp": ["study/polity/fundamental-rights-dpsp-duties.html"],
    "parliament": ["study/polity/parliament-of-india.html"],
    "union-executive": ["study/polity/union-and-state-executive.html"],
    "state-executive": ["study/polity/union-and-state-executive.html"],
    "state-legislature": ["study/polity/union-and-state-executive.html"],
    "services": ["study/polity/union-and-state-executive.html"],
    "judiciary": ["study/polity/judiciary-and-landmark-cases.html"],
    "landmark-cases": ["study/polity/judiciary-and-landmark-cases.html"],
    "federalism": ["study/polity/federalism-and-centre-state-relations.html"],
    "emergency": ["study/polity/federalism-and-centre-state-relations.html"],
    "local-government": ["study/polity/panchayati-raj-and-municipalities.html"],
    "constitutional-bodies": ["study/polity/constitutional-and-statutory-bodies.html"],
    "statutory-bodies": ["study/polity/constitutional-and-statutory-bodies.html"],
    "elections": ["study/polity/constitutional-and-statutory-bodies.html"],
    "governance": ["study/polity/constitutional-and-statutory-bodies.html"],
    "ancient": ["study/history/indus-valley-and-vedic-age.html", "study/history/buddhism-jainism-mauryas-guptas.html",
                "study/history/south-indian-dynasties.html"],
    "medieval": ["study/history/delhi-sultanate-and-mughals.html"],
    "modern": ["study/history/modern-india-freedom-struggle.html", "study/history/social-reform-and-british-administration.html"],
    "art-culture": ["study/history/indian-architecture-and-sculpture.html", "study/history/indian-dance-music-and-painting.html"],
    "static-gk": ["repeated-questions/static-gk-cheat-code.html"],
    "climatology": ["study/geography/atmosphere-and-oceans.html"],
    "oceanography": ["study/geography/atmosphere-and-oceans.html"],
    "geomorphology": ["study/geography/geomorphology-earth-interior-and-landforms.html"],
    "world-geography": ["repeated-questions/geography-cheat-code.html"],
    "india-physiography": ["study/geography/physiography-of-india.html"],
    "drainage": ["study/geography/rivers-and-drainage-of-india.html"],
    "india-climate": ["study/geography/climate-and-monsoon-of-india.html"],
    "india-resources": ["study/geography/agriculture-minerals-industries-and-transport.html"],
    "protected-areas": ["study/geography/soils-vegetation-and-protected-areas.html"],
    "india-human": ["study/geography/agriculture-minerals-industries-and-transport.html"],
    "ecology": ["study/environment/ecology-and-ecosystem-basics.html"],
    "biodiversity": ["study/environment/biodiversity-and-conservation.html"],
    "environment-laws": ["study/environment/wildlife-and-forest-laws-of-india.html", "study/environment/pollution-and-environmental-laws.html"],
    "pollution": ["study/environment/pollution-and-environmental-laws.html"],
    "climate": ["study/environment/climate-change-and-india.html", "study/environment/environmental-conventions-and-organisations.html"],
    "disasters": ["study/environment/disaster-management-in-india.html"],
    "computer-basics": ["study/science-tech/computer-and-it-fundamentals.html", "repeated-questions/computer-awareness-cheat-code.html"],
    "software": ["study/science-tech/computer-and-it-fundamentals.html"],
    "networking": ["study/science-tech/computer-and-it-fundamentals.html"],
    "internet": ["study/science-tech/computer-and-it-fundamentals.html"],
    "security": ["study/science-tech/computer-and-it-fundamentals.html", "study/current-affairs/cybersecurity-policy-india.html"],
    "office": ["repeated-questions/computer-awareness-cheat-code.html"],
    "puzzles": ["blog/bank-exam-puzzles-5-types.html"],
    "arrangement": ["blog/bank-exam-puzzles-5-types.html"],
    "national-income": ["study/economy/national-income-and-inflation.html"],
    "inflation": ["study/economy/national-income-and-inflation.html"],
    "development": ["study/economy/national-income-and-inflation.html"],
    "banking": ["study/economy/money-banking-and-rbi.html", "repeated-questions/banking-awareness-cheat-code.html"],
    "financial-markets": ["study/economy/money-banking-and-rbi.html"],
    "public-finance": ["study/economy/budget-and-fiscal-policy.html", "study/economy/taxation-and-gst.html"],
    "external-sector": ["study/economy/external-sector-and-trade.html"],
    "planning": ["study/economy/planning-reforms-and-agriculture.html"],
    "agriculture": ["study/economy/planning-reforms-and-agriculture.html"],
    "industry": ["study/economy/planning-reforms-and-agriculture.html"],
    "physics": ["study/science-tech/physics-in-everyday-life.html"],
    "chemistry": ["study/science-tech/chemistry-in-everyday-life.html"],
    "biology": ["study/science-tech/human-body-and-health.html", "study/science-tech/cell-genetics-and-plant-biology.html"],
    "space": ["study/science-tech/space-and-defence-technology.html"],
    "defence": ["study/science-tech/space-and-defence-technology.html"],
    "energy": ["study/science-tech/biotechnology-nuclear-and-emerging-tech.html"],
    "monthly": ["blog/top-25-current-affairs-mcqs-december-2025.html"],
    "economy-ca": ["study/current-affairs/union-budget-2026-27.html"],
    "governance-ca": ["study/current-affairs/index.html"],
    "ir-ca": ["study/ir/india-foreign-policy-and-neighbours.html"],
    "environment-ca": ["study/current-affairs/climate-summit-outcomes.html"],
    "science-ca": ["study/current-affairs/gaganyaan-chandrayaan4-progress-2026.html"],
    "awards": ["repeated-questions/static-gk-cheat-code.html"],
    "ssc": ["blog/ssc-cgl-syllabus-2025.html"],
    "banking-exams": ["blog/bank-exam-syllabus-2025.html"],
    "railway": ["blog/rrb-syllabus-2025.html"],
    "upsc": ["blog/upsc-prelims-syllabus-2025.html"],
    "state-psc": ["blog/psc-syllabus-2025.html"],
    "defence-exams": ["exam-calendar.html"],
    "general": ["exam-calendar.html"],
    "grammar": ["repeated-questions/english-cheat-code.html"],
    "vocabulary": ["repeated-questions/english-cheat-code.html"],
    "comprehension": ["repeated-questions/english-cheat-code.html"],
}
QUANT_PARENT = ["repeated-questions/quant-cheat-code.html"]

# Source keys used in the topic lists -> what the drafter must cite. Domains are the bodies' own sites.
SOURCES = {
    "COI": "Constitution of India, current consolidated text (Legislative Department, legislative.gov.in)",
    "AMD": "Text of the relevant Constitution (Amendment) Act (legislative.gov.in or egazette.gov.in)",
    "SCJ": "The Supreme Court judgment itself, cited by case name and year (sci.gov.in or the official law report)",
    "ACT": "The statute as amended, from India Code (indiacode.nic.in)",
    "GAZ": "Gazette of India notification (egazette.gov.in)",
    "RULES": "Rules of Procedure and Conduct of Business of the Lok Sabha / Rajya Sabha (sansad.in)",
    "ECI": "Election Commission of India (eci.gov.in)",
    "MHA": "Ministry of Home Affairs (mha.gov.in)",
    "MOPR": "Ministry of Panchayati Raj (panchayat.gov.in)",
    "FINCOM": "Finance Commission of India (fincomindia.nic.in)",
    "CABRES": "Cabinet resolution constituting NITI Aayog (niti.gov.in)",
    "NCERT": "NCERT textbook chapter, cited by class and chapter (ncert.nic.in/textbook.php)",
    "ASI": "Archaeological Survey of India (asi.nic.in)",
    "UNESCO": "UNESCO World Heritage List entry (whc.unesco.org)",
    "SNA": "Sangeet Natak Akademi (sangeetnatak.gov.in)",
    "GI": "Geographical Indications Registry (ipindia.gov.in)",
    "IMD": "India Meteorological Department (mausam.imd.gov.in)",
    "NOAA": "NOAA Climate Prediction Center ENSO pages (noaa.gov)",
    "NASA": "NASA (nasa.gov)",
    "MEA": "Ministry of External Affairs (mea.gov.in)",
    "CWC": "Central Water Commission (cwc.gov.in)",
    "ICAR": "Indian Council of Agricultural Research (icar.org.in)",
    "MOEFCC": "Ministry of Environment, Forest and Climate Change (moef.gov.in)",
    "NTCA": "National Tiger Conservation Authority (ntca.gov.in)",
    "RAMSAR": "Ramsar Sites Information Service (rsis.ramsar.org)",
    "MOA": "Ministry of Agriculture & Farmers Welfare (agriwelfare.gov.in)",
    "IBM": "Indian Bureau of Mines (ibm.gov.in)",
    "NPCIL": "Nuclear Power Corporation of India (npcil.nic.in)",
    "MOPSW": "Ministry of Ports, Shipping and Waterways (shipmin.gov.in)",
    "CENSUS": "Office of the Registrar General & Census Commissioner (censusindia.gov.in)",
    "CI": "Critical Ecosystem Partnership Fund hotspot profiles (cepf.net)",
    "IUCN": "IUCN Red List (iucnredlist.org)",
    "CPCB": "Central Pollution Control Board (cpcb.nic.in)",
    "UNEP": "UN Environment Programme / Ozone Secretariat (unep.org)",
    "IPCC": "IPCC assessment reports (ipcc.ch)",
    "UNFCCC": "UNFCCC decisions and texts (unfccc.int)",
    "PIB": "Press Information Bureau release, cited by date (pib.gov.in)",
    "FSI": "Forest Survey of India (fsi.nic.in)",
    "BIS": "Bureau of Indian Standards (bis.gov.in)",
    "NDMA": "National Disaster Management Authority (ndma.gov.in)",
    "BMTPC": "Vulnerability Atlas of India (bmtpc.org)",
    "IWAI": "Inland Waterways Authority of India (iwai.nic.in)",
    "RAIL": "Ministry of Railways (indianrailways.gov.in)",
    "MOS": "Ministry of Steel (steel.gov.in)",
    "ORIG": "Original problems and solutions; every numeric answer is verified by an automated computation check",
    "IEC": "IEC 80000-13 / NIST guidance on binary prefixes (nist.gov)",
    "ISO": "ISO/IEC 7498-1 (OSI reference model)",
    "IETF": "IETF RFCs for the protocols named (ietf.org)",
    "CERTIN": "CERT-In advisories and glossary (cert-in.org.in)",
    "MSDOC": "Microsoft Support documentation (support.microsoft.com)",
    "NIST": "NIST SP 800-145 cloud definition (nist.gov)",
    "MEITY": "Ministry of Electronics and IT (meity.gov.in)",
    "CCA": "Controller of Certifying Authorities (cca.gov.in)",
    "RBI": "Reserve Bank of India publications and master directions (rbi.org.in)",
    "NPCI": "National Payments Corporation of India (npci.org.in)",
    "MOSPI": "Ministry of Statistics and Programme Implementation / NSO (mospi.gov.in)",
    "DPIIT": "Office of the Economic Adviser, DPIIT (eaindustry.nic.in)",
    "BASEL": "Bank for International Settlements, Basel Committee (bis.org)",
    "IBBI": "Insolvency and Bankruptcy Board of India (ibbi.gov.in)",
    "SEBI": "Securities and Exchange Board of India (sebi.gov.in)",
    "MOF": "Union Budget and Economic Survey documents (indiabudget.gov.in)",
    "WTO": "World Trade Organization (wto.org)",
    "NITI": "NITI Aayog (niti.gov.in)",
    "UNDP": "UNDP Human Development Report (hdr.undp.org)",
    "CACP": "Commission for Agricultural Costs and Prices (cacp.da.gov.in)",
    "MSME": "Ministry of MSME (msme.gov.in)",
    "DICGC": "Deposit Insurance and Credit Guarantee Corporation (dicgc.org.in)",
    "NABARD": "NABARD (nabard.org)",
    "GSTC": "GST Council (gstcouncil.gov.in)",
    "CBDT": "Income Tax Department / CBDT (incometaxindia.gov.in)",
    "BIPM": "SI Brochure, BIPM (bipm.org)",
    "WHO": "World Health Organization fact sheets (who.int)",
    "ICMR": "ICMR-NIN dietary guidelines (icmr.gov.in)",
    "DBT": "Department of Biotechnology (dbtindia.gov.in)",
    "ISRO": "Indian Space Research Organisation (isro.gov.in)",
    "DRDO": "Defence Research and Development Organisation (drdo.gov.in)",
    "DAE": "Department of Atomic Energy (dae.gov.in)",
    "MNRE": "Ministry of New and Renewable Energy (mnre.gov.in)",
    "MOD": "Ministry of Defence (mod.gov.in)",
    "MORD": "Ministry of Rural Development (rural.gov.in)",
    "MOC": "Department of Commerce (commerce.gov.in)",
    "NOBEL": "The Nobel Prize official site (nobelprize.org)",
    "NOTICE": "The current official notification of the exam body (upsc.gov.in, ssc.gov.in, ibps.in, sbi.bank.in, opportunities.rbi.org.in, rrbapply.gov.in, or the state PSC's site), cited by notice number and date",
    "PYQ": "Official question papers (e.g. upsc.gov.in/examinations/previous-question-papers), cited by paper year and question number",
    "DOPT": "Department of Personnel and Training orders (dopt.gov.in)",
    "DOEPWD": "Department of Empowerment of Persons with Disabilities guidelines (depwd.gov.in)",
    "GRAM": "Standard grammar references (e.g. Cambridge or Oxford learner's grammar); all example sentences original",
    "DICT": "Learner's dictionaries (Oxford, Cambridge) for meanings; all example sentences original",
    "SOI": "Survey of India (surveyofindia.gov.in)",
    "MTA": "Ministry of Tribal Affairs (tribal.nic.in)",
    "MOPNG": "Ministry of Petroleum and Natural Gas (mopng.gov.in)",
    "NMCG": "National Mission for Clean Ganga (nmcg.nic.in)",
}

# Primary/official domains a draft may cite without a warning.
PRIMARY_DOMAINS = re.compile(
    r"(\.gov\.in|\.nic\.in|rbi\.org\.in|ibps\.in|sbi\.bank\.in|sbi\.co\.in|npci\.org\.in|dicgc\.org\.in|nabard\.org|"
    r"unfccc\.int|unep\.org|ipcc\.ch|ramsar\.org|unesco\.org|iucnredlist\.org|cepf\.net|who\.int|wto\.org|bis\.org|"
    r"undp\.org|un\.org|bipm\.org|nist\.gov|nasa\.gov|noaa\.gov|ietf\.org|rfc-editor\.org|iso\.org|nobelprize\.org|"
    r"support\.microsoft\.com|icar\.org\.in|bmtpc\.org|cert-in\.org\.in|isro\.gov\.in|sansad\.in|niti\.gov\.in)$")


def today():
    return date.today().isoformat()


def slug_url(folder, slug):
    return f"{folder}/{slug}.html"


def read_topics():
    """Yield planned-topic dicts from every TSV, in file order."""
    for category, (fname, _target) in CATEGORIES.items():
        path = os.path.join(TOPICS_DIR, fname)
        with open(path, encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, 1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = [p.strip() for p in line.split("|")]
                if len(parts) != 9:
                    raise ValueError(f"{fname}:{lineno}: expected 9 fields, got {len(parts)}")
                slug, title, subtopic, ptype, exams, query, outcome, src, prio = parts
                if ptype not in PAGE_TYPES:
                    raise ValueError(f"{fname}:{lineno}: unknown page type {ptype!r}")
                for key in src.split("+"):
                    if key not in SOURCES:
                        raise ValueError(f"{fname}:{lineno}: unknown source key {key!r}")
                for code in exams.split():
                    if code not in EXAMS:
                        raise ValueError(f"{fname}:{lineno}: unknown exam code {code!r}")
                folder = folder_for(category, subtopic)
                yield {
                    "id": slug, "category": category, "subtopic": subtopic, "page_type": ptype,
                    "title": title, "exams": [EXAMS[c] for c in exams.split()], "primary_query": query,
                    "learning_outcome": outcome, "source_keys": src.split("+"), "priority": prio,
                    "path": slug_url(folder, slug), "folder": folder, "topic_file": f"{fname}:{lineno}",
                }


def parents_for(topic):
    if topic["category"] == "Quantitative Aptitude":
        return QUANT_PARENT
    if topic["category"] == "Exam-Specific Guides" and topic["subtopic"] == "defence":
        return PARENTS["defence-exams"]
    return PARENTS.get(topic["subtopic"], [])


def hub_for(folder):
    return f"{folder}/index.html"


# ---------- state ----------

def load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    return {"pages": {}, "batches": {}}


def save_state(state):
    os.makedirs(CONTENT, exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(state, fh, indent=2, ensure_ascii=False, sort_keys=True)
        fh.write("\n")


def page_state(state, pid):
    return state["pages"].setdefault(pid, {"status": "planned", "history": []})


def set_status(state, pid, status, note="", **extra):
    assert status in STATUSES + ["rejected"], status
    ps = page_state(state, pid)
    ps["status"] = status
    ps.update(extra)
    ps["history"].append({"date": today(), "status": status, "note": note})


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def draft_path(pid):
    return os.path.join(DRAFTS_DIR, f"{pid}.html")


def file_hash(path):
    if not os.path.exists(path):
        return None
    # newline="" keeps CRLF as written, so this matches sha() of the text the pipeline wrote
    with open(path, encoding="utf-8", newline="") as fh:
        return sha(fh.read())


def load_plan_rows():
    if not os.path.exists(PLAN_CSV):
        return []
    with open(PLAN_CSV, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def url_of(path):
    return HOST + "/" + path
