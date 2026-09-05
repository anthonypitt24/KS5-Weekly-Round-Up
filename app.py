import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime, date, timedelta
from urllib.parse import urljoin, urlencode
import re
import html
import time


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="KS5 Progression Hub",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# GLOBAL SETTINGS
# ============================================================

TODAY = date.today()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/139.0 Safari/537.36"
    )
}

REQUEST_TIMEOUT = 20

UCAS_EVENTS_URL = (
    "https://www.ucas.com/explore/search/events"
)

GOV_APPRENTICESHIP_URL = (
    "https://www.findapprenticeship.service.gov.uk/apprenticeships"
)

AMAZING_APPRENTICESHIPS_URL = (
    "https://www.amazingapprenticeships.com/"
    "higher-degree-listing/"
)

FORAGE_URL = "https://www.theforage.com/simulations"

NCS_URL = "https://nationalcareers.service.gov.uk/"

MAX_APPRENTICESHIPS = 40
MAX_OPEN_DAYS = 30


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
<style>

body {
    background-color: #f5f7fb;
}

.hero {
    padding: 32px;
    border-radius: 22px;
    background: linear-gradient(
        135deg,
        #172554 0%,
        #1d4ed8 55%,
        #2563eb 100%
    );
    color: white;
    margin-bottom: 25px;
}

.hero h1 {
    font-size: 42px;
    margin-bottom: 6px;
}

.hero p {
    font-size: 18px;
    margin-bottom: 0;
}

.card {
    background: white;
    padding: 20px;
    border-radius: 17px;
    border: 1px solid #e5e7eb;
    margin-bottom: 15px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.04);
}

.card:hover {
    box-shadow: 0 8px 24px rgba(0,0,0,0.07);
}

.section-title {
    font-size: 26px;
    font-weight: 800;
    margin-top: 15px;
}

.badge {
    display: inline-block;
    padding: 5px 10px;
    border-radius: 999px;
    background: #e0e7ff;
    color: #3730a3;
    font-size: 12px;
    font-weight: 700;
    margin-right: 5px;
}

.badge-red {
    background: #fee2e2;
    color: #991b1b;
}

.badge-green {
    background: #dcfce7;
    color: #166534;
}

.badge-orange {
    background: #ffedd5;
    color: #9a3412;
}

.badge-blue {
    background: #dbeafe;
    color: #1e40af;
}

.small {
    font-size: 13px;
    color: #6b7280;
}

.priority {
    padding: 18px;
    border-radius: 15px;
    background: #fff7ed;
    border: 1px solid #fed7aa;
    margin-bottom: 12px;
}

.deadline {
    padding: 18px;
    border-radius: 15px;
    background: #fef2f2;
    border: 1px solid #fecaca;
    margin-bottom: 12px;
}

.bulletin {
    background: white;
    padding: 30px;
    border-radius: 18px;
    border: 1px solid #d1d5db;
}

.metric-box {
    background: white;
    border-radius: 15px;
    padding: 15px;
    border: 1px solid #e5e7eb;
}

</style>
""",
    unsafe_allow_html=True
)


# ============================================================
# SESSION STATE
# ============================================================

defaults = {
    "items": [],
    "last_refresh": None,
    "source_status": {},
    "custom_items": [],
    "removed_ids": set(),
    "bulletin_title": "KS5 PROGRESSION BULLETIN"
}

for key, value in defaults.items():

    if key not in st.session_state:

        st.session_state[key] = value


# ============================================================
# HELPERS
# ============================================================

def clean_text(text):

    if not text:
        return ""

    text = html.unescape(str(text))
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def normalise_url(url):

    if not url:
        return ""

    if url.startswith("/"):
        return "https://www.ucas.com" + url

    return url


def make_id(category, title, organisation="", url=""):

    raw = (
        f"{category}|{title}|"
        f"{organisation}|{url}"
    )

    return re.sub(
        r"[^a-zA-Z0-9]+",
        "-",
        raw.lower()
    )[:250]


def make_item(
    title,
    organisation,
    category,
    description="",
    location="",
    event_date="",
    closing_date="",
    start_date="",
    salary="",
    level="",
    url="",
    source="",
    posted_date="",
    tags=None,
    verified=True,
    priority=0
):

    if tags is None:
        tags = []

    return {
        "id": make_id(
            category,
            title,
            organisation,
            url
        ),
        "title": clean_text(title),
        "organisation": clean_text(organisation),
        "category": category,
        "description": clean_text(description),
        "location": clean_text(location),
        "event_date": event_date,
        "closing_date": closing_date,
        "start_date": start_date,
        "salary": salary,
        "level": level,
        "url": url,
        "source": source,
        "posted_date": posted_date,
        "tags": tags,
        "verified": verified,
        "priority": priority
    }


def parse_date(text):

    if not text:
        return None

    text = clean_text(text)

    patterns = [
        r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})",
        r"(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\s+(\d{4})",
        r"([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.I
        )

        if not match:
            continue

        try:

            groups = match.groups()

            if groups[0].isdigit():

                day = int(groups[0])
                month = groups[1]
                year = int(groups[2])

            else:

                month = groups[0]
                day = int(groups[1])
                year = int(groups[2])

            return datetime.strptime(
                f"{day} {month} {year}",
                "%d %B %Y"
            ).date()

        except Exception:
            pass

        try:

            groups = match.groups()

            if groups[0].isdigit():

                day = int(groups[0])
                month = groups[1]
                year = int(groups[2])

            else:

                month = groups[0]
                day = int(groups[1])
                year = int(groups[2])

            return datetime.strptime(
                f"{day} {month} {year}",
                "%d %b %Y"
            ).date()

        except Exception:
            pass

    return None


def format_date(value):

    if not value:
        return ""

    if isinstance(value, date):

        suffix = (
            "th"
            if 11 <= value.day <= 13
            else {
                1: "st",
                2: "nd",
                3: "rd"
            }.get(value.day % 10, "th")
        )

        return value.strftime(
            f"%-d{suffix} %B %Y"
        )

    return str(value)


def days_until(date_value):

    if not date_value:
        return None

    return (
        date_value - TODAY
    ).days


# ============================================================
# UCAS OPEN DAYS
# ============================================================

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_ucas_open_days(
    months_ahead=3,
    max_results=30
):

    results = []

    try:

        response = requests.get(
            UCAS_EVENTS_URL,
            params={
                "eventType": "Open day"
            },
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

    except Exception as e:

        return [], f"UCAS error: {e}"

    cutoff = (
        TODAY +
        timedelta(days=months_ahead * 31)
    )

    # --------------------------------------------------------
    # UCAS event links
    # --------------------------------------------------------

    links = soup.find_all(
        "a",
        href=True
    )

    seen = set()

    for link in links:

        href = link.get("href", "")

        if "/events/" not in href:
            continue

        title = clean_text(
            link.get_text(" ", strip=True)
        )

        if not title:
            continue

        if title.lower() in seen:
            continue

        seen.add(title.lower())

        full_url = normalise_url(href)

        # ----------------------------------------------------
        # Find surrounding event block
        # ----------------------------------------------------

        parent = link

        for _ in range(5):

            if parent.parent:
                parent = parent.parent

        block_text = clean_text(
            parent.get_text(
                " ",
                strip=True
            )
        )

        # ----------------------------------------------------
        # Extract date
        # ----------------------------------------------------

        date_match = re.search(
            r"(\d{1,2}(?:st|nd|rd|th)?\s+"
            r"[A-Za-z]+\s+\d{4})",
            block_text
        )

        event_date = None

        if date_match:

            event_date = parse_date(
                date_match.group(1)
            )

        if not event_date:

            continue

        if event_date < TODAY:

            continue

        if event_date > cutoff:

            continue

        # ----------------------------------------------------
        # Location
        # ----------------------------------------------------

        location = ""

        location_patterns = [
            r"\bLondon\b",
            r"\bManchester\b",
            r"\bLiverpool\b",
            r"\bBirmingham\b",
            r"\bLeicester\b",
            r"\bLeeds\b",
            r"\bBristol\b",
            r"\bBath\b",
            r"\bCambridge\b",
            r"\bOxford\b",
            r"\bBrighton\b",
            r"\bPoole\b",
            r"\bPreston\b",
            r"\bChester\b",
            r"\bBradford\b",
            r"\bNottingham\b",
            r"\bSheffield\b",
            r"\bNewcastle\b",
            r"\bEdinburgh\b",
            r"\bGlasgow\b",
            r"\bCardiff\b",
            r"\bBelfast\b"
        ]

        for pattern in location_patterns:

            match = re.search(
                pattern,
                block_text,
                re.I
            )

            if match:

                location = match.group(0)
                break

        # ----------------------------------------------------
        # Audience / type
        # ----------------------------------------------------

        description = (
            "Upcoming UCAS-listed event. "
            "Check the original event page for "
            "booking information and event details."
        )

        tags = [
            "University",
            "Open day",
            "UCAS"
        ]

        if "Undergraduate" in block_text:

            tags.append(
                "Undergraduate"
            )

        item = make_item(
            title=title,
            organisation="",
            category="🏫 University Open Day",
            description=description,
            location=location,
            event_date=format_date(
                event_date
            ),
            url=full_url,
            source="UCAS",
            tags=tags,
            verified=True,
            priority=100
        )

        results.append(item)

        if len(results) >= max_results:
            break

    # --------------------------------------------------------
    # Sort chronologically
    # --------------------------------------------------------

    def sort_key(item):

        d = parse_date(
            item["event_date"]
        )

        return d or date.max

    results.sort(
        key=sort_key
    )

    return results, "OK"


# ============================================================
# GOVERNMENT APPRENTICESHIPS
# ============================================================

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_apprenticeships(
    level="All levels",
    category="All categories",
    location="All locations",
    max_results=40
):

    results = []

    params = {}

    # --------------------------------------------------------
    # Government level IDs
    # --------------------------------------------------------

    level_map = {
        "Level 2": "2",
        "Level 3": "3",
        "Level 4": "4",
        "Level 5": "5",
        "Level 6": "6",
        "Level 7": "7"
    }

    if level in level_map:

        params["levelIds"] = (
            level_map[level]
        )

    # --------------------------------------------------------
    # Location
    # --------------------------------------------------------

    if location != "All locations":

        params["location"] = location

    params["sort"] = "AgeAsc"

    try:

        response = requests.get(
            GOV_APPRENTICESHIP_URL,
            params=params,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

    except Exception as e:

        return [], f"Government apprenticeship error: {e}"

    # --------------------------------------------------------
    # Find apprenticeship links
    # --------------------------------------------------------

    links = soup.find_all(
        "a",
        href=True
    )

    seen = set()

    for link in links:

        href = link.get("href", "")

        if "/apprenticeships/" not in href:
            continue

        title = clean_text(
            link.get_text(
                " ",
                strip=True
            )
        )

        if not title:
            continue

        if title.lower() in seen:
            continue

        # Avoid filter/navigation links
        if len(title) < 8:
            continue

        seen.add(
            title.lower()
        )

        # ----------------------------------------------------
        # Locate card text
        # ----------------------------------------------------

        parent = link

        for _ in range(6):

            if parent.parent:
                parent = parent.parent

        block_text = clean_text(
            parent.get_text(
                " ",
                strip=True
            )
        )

        # ----------------------------------------------------
        # Category filter
        # ----------------------------------------------------

        category_terms = {

            "Digital": [
                "digital",
                "software",
                "data",
                "cyber",
                "IT",
                "technology",
                "artificial intelligence",
                "AI"
            ],

            "Engineering": [
                "engineering",
                "engineer",
                "manufacturing"
            ],

            "Business & Administration": [
                "business",
                "administration",
                "office",
                "management"
            ],

            "Finance & Legal": [
                "finance",
                "account",
                "legal",
                "law",
                "audit"
            ],

            "Health & Science": [
                "health",
                "science",
                "laboratory",
                "pharmacy",
                "nursing"
            ],

            "Creative": [
                "creative",
                "design",
                "media",
                "content",
                "production"
            ],

            "Construction": [
                "construction",
                "building",
                "quantity survey"
            ],

            "Education": [
                "education",
                "teaching",
                "early years"
            ]
        }

        if category != "All categories":

            terms = category_terms.get(
                category,
                []
            )

            if not any(
                term.lower()
                in block_text.lower()
                for term in terms
            ):

                continue

        # ----------------------------------------------------
        # Employer
        # ----------------------------------------------------

        employer = ""

        lines = [
            clean_text(x)
            for x in parent.stripped_strings
        ]

        # Try to identify employer
        for line in lines:

            upper = line.upper()

            if (
                len(line) > 2
                and len(line) < 100
                and line != title
                and "Start date" not in line
                and "Training course" not in line
                and "Wage" not in line
                and "Closes" not in line
                and "Posted" not in line
            ):

                employer = line

                break

        # ----------------------------------------------------
        # Level
        # ----------------------------------------------------

        level_match = re.search(
            r"\(level\s+([2-7])\)",
            block_text,
            re.I
        )

        apprenticeship_level = ""

        if level_match:

            apprenticeship_level = (
                f"Level {level_match.group(1)}"
            )

        # ----------------------------------------------------
        # Start date
        # ----------------------------------------------------

        start_match = re.search(
            r"Start date\s+"
            r"(\d{1,2}\s+[A-Za-z]+\s+\d{4})",
            block_text,
            re.I
        )

        start_date = ""

        if start_match:

            start_date = (
                start_match.group(1)
            )

        # ----------------------------------------------------
        # Closing date
        # ----------------------------------------------------

        closing_date = ""

        close_patterns = [

            r"Closes\s+(?:in\s+\d+\s+days?\s+\()?"
            r"(\d{1,2}\s+[A-Za-z]+\s+\d{4})",

            r"Closes on\s+"
            r"[A-Za-z]+\s+"
            r"(\d{1,2}\s+[A-Za-z]+\s+\d{4})",

            r"Closes\s+tomorrow"
        ]

        for pattern in close_patterns:

            close_match = re.search(
                pattern,
                block_text,
                re.I
            )

            if close_match:

                if (
                    "tomorrow"
                    in close_match.group(0).lower()
                ):

                    closing_date = format_date(
                        TODAY +
                        timedelta(days=1)
                    )

                else:

                    closing_date = (
                        close_match.group(1)
                    )

                break

        # ----------------------------------------------------
        # Wage
        # ----------------------------------------------------

        wage_match = re.search(
            r"Wage\s+(.+?)(?=\s+Closes|\s+Posted|$)",
            block_text,
            re.I
        )

        salary = ""

        if wage_match:

            salary = clean_text(
                wage_match.group(1)
            )

        # ----------------------------------------------------
        # Posted date
        # ----------------------------------------------------

        posted_match = re.search(
            r"Posted\s+"
            r"(\d{1,2}\s+[A-Za-z]+\s+\d{4})",
            block_text,
            re.I
        )

        posted_date = ""

        if posted_match:

            posted_date = (
                posted_match.group(1)
            )

        # ----------------------------------------------------
        # Location
        # ----------------------------------------------------

        apprenticeship_location = ""

        location_match = re.search(
            r"(?:^|\s)"
            r"([A-Z][A-Za-z .&'-]+"
            r"(?:\s+\([A-Z0-9 ]+\))?"
            r"(?:\s+and\s+\d+\s+other locations)?"
            r")"
            r"\s+Start date",
            block_text
        )

        if location_match:

            apprenticeship_location = clean_text(
                location_match.group(1)
            )

        # ----------------------------------------------------
        # Closing soon
        # ----------------------------------------------------

        priority = 50
        tags = [
            "Government",
            "Live vacancy"
        ]

        closing_parsed = parse_date(
            closing_date
        )

        if closing_parsed:

            days = (
                closing_parsed - TODAY
            ).days

            if days <= 3:

                tags.append(
                    "🔴 Closing very soon"
                )

                priority = 1000

            elif days <= 7:

                tags.append(
                    "🔥 Closing soon"
                )

                priority = 900

        if "New" in block_text:

            tags.append(
                "🆕 New"
            )

            priority += 100

        # ----------------------------------------------------
        # Description
        # ----------------------------------------------------

        description = (
            f"Live apprenticeship vacancy. "
            f"{apprenticeship_level}. "
            f"Check the original Government listing "
            f"for the full training course, eligibility "
            f"and application details."
        )

        full_url = urljoin(
            GOV_APPRENTISHIP_BASE
            if "GOV_APPRENTISHIP_BASE" in globals()
            else "https://www.findapprenticeship.service.gov.uk",
            href
        )

        item = make_item(
            title=title,
            organisation=employer,
            category="🎓 Apprenticeship",
            description=description,
            location=apprenticeship_location,
            closing_date=closing_date,
            start_date=start_date,
            salary=salary,
            level=apprenticeship_level,
            url=full_url,
            source="GOV.UK Find an Apprenticeship",
            posted_date=posted_date,
            tags=tags,
            verified=True,
            priority=priority
        )

        results.append(item)

        if len(results) >= max_results:

            break

    # --------------------------------------------------------
    # Sort by priority
    # --------------------------------------------------------

    results.sort(
        key=lambda x: (
            -x["priority"],
            parse_date(
                x["closing_date"]
            ) or date.max
        )
    )

    return results, "OK"


# ============================================================
# UCAS KEY DATES
# ============================================================

def get_ucas_key_dates():

    dates = [

        make_item(
            title=(
                "UCAS applications can be submitted"
            ),
            organisation="UCAS",
            category="📅 Key Date",
            description=(
                "Completed undergraduate applications "
                "for 2027 entry can be submitted to UCAS."
            ),
            event_date="1 September 2026",
            url=(
                "https://www.ucas.com/"
                "applying/applying-to-university/"
                "dates-and-deadlines-for-uni-applications"
            ),
            source="UCAS",
            tags=[
                "UCAS",
                "2027 entry"
            ],
            priority=300
        ),

        make_item(
            title=(
                "Oxford & Cambridge / Medicine, "
                "Dentistry & Veterinary deadline"
            ),
            organisation="UCAS",
            category="📅 Key Date",
            description=(
                "18:00 UK time deadline for applications "
                "to Oxford and Cambridge and most courses "
                "in medicine, dentistry and veterinary "
                "medicine/science."
            ),
            event_date="15 October 2026",
            closing_date="15 October 2026 at 18:00",
            url=(
                "https://www.ucas.com/applying/"
                "applying-to-university/"
                "dates-and-deadlines-for-uni-applications"
            ),
            source="UCAS",
            tags=[
                "🔴 Major deadline",
                "Oxbridge",
                "Medicine",
                "Dentistry",
                "Veterinary"
            ],
            priority=1000
        ),

        make_item(
            title=(
                "UCAS Equal Consideration Deadline"
            ),
            organisation="UCAS",
            category="📅 Key Date",
            description=(
                "Main equal consideration deadline for "
                "most undergraduate applications."
            ),
            event_date="13 January 2027",
            closing_date="13 January 2027 at 18:00",
            url=(
                "https://www.ucas.com/applying/"
                "applying-to-university/"
                "dates-and-deadlines-for-uni-applications"
            ),
            source="UCAS",
            tags=[
                "🟠 Major deadline",
                "2027 entry"
            ],
            priority=900
        ),

        make_item(
            title=(
                "UCAS Applications Entered Into Clearing"
            ),
            organisation="UCAS",
            category="📅 Key Date",
            description=(
                "Applications received after 30 June "
                "2027 are automatically entered into "
                "Clearing."
            ),
            event_date="30 June 2027",
            closing_date="30 June 2027 at 18:00",
            url=(
                "https://www.ucas.com/advisers/"
                "help-and-training/guides-resources-and-training/"
                "supporting-you-through-confirmation-and-clearing/"
                "confirmation-and-clearing-key-dates"
            ),
            source="UCAS",
            tags=[
                "Clearing"
            ],
            priority=600
        )
    ]

    # Keep only future dates
    future = []

    for item in dates:

        d = parse_date(
            item["event_date"]
        )

        if d and d >= TODAY:

            future.append(item)

    future.sort(
        key=lambda x:
        parse_date(
            x["event_date"]
        ) or date.max
    )

    return future


# ============================================================
# AMAZING APPRENTICESHIPS
# ============================================================

def get_amazing_apprenticeships():

    return [

        make_item(
            title=(
                "Higher & Degree Apprenticeship "
                "Vacancy Listing"
            ),
            organisation="Amazing Apprenticeships",
            category="🎓 Apprenticeship",
            description=(
                "Specialist higher and degree "
                "apprenticeship vacancy listing. "
                "Useful for students considering "
                "degree-level apprenticeships."
            ),
            location="UK",
            event_date="Current 2026 listings",
            url=AMAZING_APPRENTICESHIPS_URL,
            source="Amazing Apprenticeships",
            tags=[
                "Degree apprenticeship",
                "Higher apprenticeship",
                "Year 13"
            ],
            priority=500
        )
    ]


# ============================================================
# WORK EXPERIENCE / CAREER EXPERIENCE
# ============================================================

def get_work_experience():

    return [

        make_item(
            title=(
                "Forage – Free Virtual Work Experiences"
            ),
            organisation="Forage",
            category="💼 Work Experience",
            description=(
                "Free self-paced job simulations from "
                "major employers. Students can explore "
                "different careers, complete realistic "
                "tasks and build evidence of skills."
            ),
            location="Online",
            event_date="Available now",
            url=FORAGE_URL,
            source="Forage",
            tags=[
                "Virtual",
                "Free",
                "Work experience"
            ],
            priority=300
        ),

        make_item(
            title=(
                "National Careers Service"
            ),
            organisation="GOV.UK",
            category="💼 Work Experience",
            description=(
                "Explore careers, job profiles, skills "
                "and routes into different occupations."
            ),
            location="Online",
            event_date="Available now",
            url=NCS_URL,
            source="National Careers Service",
            tags=[
                "Career research"
            ],
            priority=100
        )
    ]


# ============================================================
# RESOURCES
# ============================================================

def get_resources():

    return [

        make_item(
            title="UCAS Discover",
            organisation="UCAS",
            category="⭐ Resource",
            description=(
                "Explore subjects, careers, universities "
                "and apprenticeships."
            ),
            location="Online",
            event_date="Available now",
            url="https://www.ucas.com/discover",
            source="UCAS",
            tags=[
                "University",
                "Apprenticeships",
                "Careers"
            ]
        ),

        make_item(
            title="Amazing Apprenticeships Resources",
            organisation="Amazing Apprenticeships",
            category="⭐ Resource",
            description=(
                "Student resources covering apprenticeships, "
                "employers, careers and applications."
            ),
            location="Online",
            event_date="Available now",
            url=(
                "https://www.amazingapprenticeships.com/"
                "resources/"
            ),
            source="Amazing Apprenticeships",
            tags=[
                "Apprenticeships"
            ]
        ),

        make_item(
            title="UCAS Apprenticeships",
            organisation="UCAS",
            category="⭐ Resource",
            description=(
                "Information about apprenticeships, "
                "including degree apprenticeships."
            ),
            location="Online",
            event_date="Available now",
            url="https://www.ucas.com/apprenticeships",
            source="UCAS",
            tags=[
                "Apprenticeships"
            ]
        )
    ]


# ============================================================
# FETCH EVERYTHING
# ============================================================

def refresh_all(
    level,
    category,
    location,
    months_ahead
):

    all_items = []

    statuses = {}

    # --------------------------------------------------------
    # UCAS
    # --------------------------------------------------------

    ucas_items, ucas_status = (
        fetch_ucas_open_days(
            months_ahead=months_ahead,
            max_results=MAX_OPEN_DAYS
        )
    )

    all_items.extend(
        ucas_items
    )

    statuses["UCAS"] = ucas_status

    # --------------------------------------------------------
    # Apprenticeships
    # --------------------------------------------------------

    app_items, app_status = (
        fetch_apprenticeships(
            level=level,
            category=category,
            location=location,
            max_results=MAX_APPRENTICESHIPS
        )
    )

    all_items.extend(
        app_items
    )

    statuses["GOV.UK Apprenticeships"] = (
        app_status
    )

    # --------------------------------------------------------
    # Other sources
    # --------------------------------------------------------

    all_items.extend(
        get_ucas_key_dates()
    )

    all_items.extend(
        get_amazing_apprenticeships()
    )

    all_items.extend(
        get_work_experience()
    )

    all_items.extend(
        get_resources()
    )

    # --------------------------------------------------------
    # Custom
    # --------------------------------------------------------

    all_items.extend(
        st.session_state.custom_items
    )

    # --------------------------------------------------------
    # Remove previously removed items
    # --------------------------------------------------------

    all_items = [
        x for x in all_items
        if x["id"]
        not in st.session_state.removed_ids
    ]

    # --------------------------------------------------------
    # Deduplicate
    # --------------------------------------------------------

    unique = {}
    
    for item in all_items:

        key = (
            item["title"].lower(),
            item["organisation"].lower(),
            item["url"]
        )

        if key not in unique:

            unique[key] = item

    all_items = list(
        unique.values()
    )

    return all_items, statuses


# ============================================================
# FILTER ITEMS
# ============================================================

def filter_items(
    items,
    section="All",
    search=""
):

    result = []

    search = search.lower().strip()

    for item in items:

        if section != "All":

            if item["category"] != section:

                continue

        if search:

            searchable = " ".join(
                [
                    item["title"],
                    item["organisation"],
                    item["description"],
                    item["location"],
                    item["level"],
                    " ".join(item["tags"])
                ]
            ).lower()

            if search not in searchable:

                continue

        result.append(item)

    return result


# ============================================================
# PRIORITY ITEMS
# ============================================================

def get_priority_items(items):

    priority = []

    for item in items:

        if item["priority"] >= 800:

            priority.append(item)

            continue

        closing = parse_date(
            item["closing_date"]
        )

        if closing:

            days = (
                closing - TODAY
            ).days

            if days <= 7:

                priority.append(item)

    priority.sort(
        key=lambda x:
        -x["priority"]
    )

    return priority[:8]


# ============================================================
# DISPLAY CARD
# ============================================================

def display_item(
    item,
    index,
    allow_remove=True
):

    tags_html = ""

    for tag in item["tags"][:5]:

        tags_html += (
            f'<span class="badge">{html.escape(tag)}</span>'
        )

    closing = parse_date(
        item["closing_date"]
    )

    urgency = ""

    if closing:

        days = (
            closing - TODAY
        ).days

        if days <= 3:

            urgency = (
                '<span class="badge badge-red">'
                '🔴 Closing very soon'
                '</span>'
            )

        elif days <= 7:

            urgency = (
                '<span class="badge badge-orange">'
                '🔥 Closing soon'
                '</span>'
            )

    st.markdown(
        f"""
        <div class="card">

        <div>
            {tags_html}
            {urgency}
        </div>

        <h3>{html.escape(item["title"])}</h3>

        <strong>
            {html.escape(item["organisation"])}
        </strong>

        <p>
            {html.escape(item["description"])}
        </p>

        <p>
            📍 {html.escape(item["location"])}
        </p>

        <p>
            📅 {html.escape(item["event_date"])}
        </p>

        {
            f'<p>⏰ Closing: {html.escape(item["closing_date"])}</p>'
            if item["closing_date"]
            else ""
        }

        {
            f'<p>🎓 {html.escape(item["level"])}</p>'
            if item["level"]
            else ""
        }

        {
            f'<p>💷 {html.escape(item["salary"])}</p>'
            if item["salary"]
            else ""
        }

        {
            f'<p>🚀 Start: {html.escape(item["start_date"])}</p>'
            if item["start_date"]
            else ""
        }

        <p class="small">
            Source: {html.escape(item["source"])}
            {" • ✓ Verified source" if item["verified"] else ""}
        </p>

        </div>
        """,
        unsafe_allow_html=True
    )

    c1, c2, c3 = st.columns(
        [2, 1, 1]
    )

    with c1:

        if item["url"]:

            st.link_button(
                "🔗 View original",
                item["url"]
            )

    with c2:

        if (
            allow_remove
            and st.button(
                "🗑️ Remove",
                key=(
                    f"remove_"
                    f"{item['id']}_{index}"
                )
            )
        ):

            st.session_state.removed_ids.add(
                item["id"]
            )

            st.rerun()

    with c3:

        if item["verified"]:

            st.success(
                "Verified",
                icon="✓"
            )


# ============================================================
# BULLETIN GENERATOR
# ============================================================

def create_bulletin(items):

    lines = []

    lines.append(
        "🎓 KS5 PROGRESSION BULLETIN"
    )

    lines.append(
        f"Week commencing "
        f"{TODAY.strftime('%d %B %Y')}"
    )

    lines.append("")

    lines.append(
        "Here are this week's live opportunities, "
        "university events, work experience options "
        "and important progression dates for KS5."
    )

    lines.append("")

    lines.append(
        "━━━━━━━━━━━━━━━━━━━━"
    )

    lines.append("")

    # --------------------------------------------------------
    # PRIORITIES
    # --------------------------------------------------------

    priorities = get_priority_items(
        items
    )

    if priorities:

        lines.append(
            "🚨 THIS WEEK'S PRIORITIES"
        )

        lines.append("")

        for item in priorities[:5]:

            lines.append(
                f"🔴 {item['title']}"
            )

            if item["organisation"]:

                lines.append(
                    f"Organisation: "
                    f"{item['organisation']}"
                )

            if item["closing_date"]:

                lines.append(
                    f"⏰ Closing: "
                    f"{item['closing_date']}"
                )

            lines.append(
                f"🔗 {item['url']}"
            )

            lines.append("")

        lines.append(
            "━━━━━━━━━━━━━━━━━━━━"
        )

        lines.append("")

    # --------------------------------------------------------
    # KEY DATES
    # --------------------------------------------------------

    key_dates = [
        x for x in items
        if x["category"] == "📅 Key Date"
    ]

    if key_dates:

        lines.append(
            "📅 KEY DATES"
        )

        lines.append("")

        for item in key_dates:

            lines.append(
                f"📅 {item['event_date']}"
            )

            lines.append(
                f"🔹 {item['title']}"
            )

            lines.append(
                item["description"]
            )

            if item["closing_date"]:

                lines.append(
                    f"⏰ {item['closing_date']}"
                )

            lines.append(
                f"🔗 {item['url']}"
            )

            lines.append("")

        lines.append(
            "━━━━━━━━━━━━━━━━━━━━"
        )

        lines.append("")

    # --------------------------------------------------------
    # OPEN DAYS
    # --------------------------------------------------------

    open_days = [
        x for x in items
        if x["category"]
        == "🏫 University Open Day"
    ]

    if open_days:

        lines.append(
            "🏫 UNIVERSITY OPEN DAYS"
        )

        lines.append("")

        for item in open_days[:15]:

            lines.append(
                f"📅 {item['event_date']}"
            )

            lines.append(
                f"🔹 {item['title']}"
            )

            if item["location"]:

                lines.append(
                    f"📍 {item['location']}"
                )

            lines.append(
                "🎓 Undergraduate / "
                "higher education event"
            )

            lines.append(
                f"🔗 {item['url']}"
            )

            lines.append("")

        lines.append(
            "━━━━━━━━━━━━━━━━━━━━"
        )

        lines.append("")

    # --------------------------------------------------------
    # APPRENTICESHIPS
    # --------------------------------------------------------

    apprenticeships = [
        x for x in items
        if x["category"]
        == "🎓 Apprenticeship"
    ]

    # Sort live vacancies first
    apprenticeships.sort(
        key=lambda x:
        (
            -x["priority"],
            parse_date(
                x["closing_date"]
            ) or date.max
        )
    )

    if apprenticeships:

        lines.append(
            "🎓 LIVE APPRENTICESHIPS"
        )

        lines.append("")

        for item in apprenticeships[:15]:

            lines.append(
                f"🔹 {item['title']}"
            )

            if item["organisation"]:

                lines.append(
                    f"Employer: "
                    f"{item['organisation']}"
                )

            if item["location"]:

                lines.append(
                    f"📍 {item['location']}"
                )

            if item["level"]:

                lines.append(
                    f"🎓 {item['level']}"
                )

            if item["salary"]:

                lines.append(
                    f"💷 {item['salary']}"
                )

            if item["start_date"]:

                lines.append(
                    f"🚀 Start: "
                    f"{item['start_date']}"
                )

            if item["closing_date"]:

                lines.append(
                    f"⏰ Closing: "
                    f"{item['closing_date']}"
                )

            if "🔴 Closing very soon" in item["tags"]:

                lines.append(
                    "🚨 CLOSING VERY SOON"
                )

            elif "🔥 Closing soon" in item["tags"]:

                lines.append(
                    "🔥 CLOSING SOON"
                )

            lines.append(
                f"🔗 {item['url']}"
            )

            lines.append("")

        lines.append(
            "━━━━━━━━━━━━━━━━━━━━"
        )

        lines.append("")

    # --------------------------------------------------------
    # WORK EXPERIENCE
    # --------------------------------------------------------

    work = [
        x for x in items
        if x["category"]
        == "💼 Work Experience"
    ]

    if work:

        lines.append(
            "💼 WORK EXPERIENCE & CAREER EXPERIENCE"
        )

        lines.append("")

        for item in work:

            lines.append(
                f"🔹 {item['title']}"
            )

            if item["organisation"]:

                lines.append(
                    f"Organisation: "
                    f"{item['organisation']}"
                )

            lines.append(
                item["description"]
            )

            if item["location"]:

                lines.append(
                    f"📍 {item['location']}"
                )

            lines.append(
                f"🔗 {item['url']}"
            )

            lines.append("")

        lines.append(
            "━━━━━━━━━━━━━━━━━━━━"
        )

        lines.append("")

    # --------------------------------------------------------
    # RESOURCES
    # --------------------------------------------------------

    resources = [
        x for x in items
        if x["category"]
        == "⭐ Resource"
    ]

    if resources:

        lines.append(
            "⭐ USEFUL RESOURCES"
        )

        lines.append("")

        for item in resources:

            lines.append(
                f"🔹 {item['title']}"
            )

            lines.append(
                item["description"]
            )

            lines.append(
                f"🔗 {item['url']}"
            )

            lines.append("")

        lines.append(
            "━━━━━━━━━━━━━━━━━━━━"
        )

        lines.append("")

    # --------------------------------------------------------
    # STUDENT CHALLENGE
    # --------------------------------------------------------

    lines.append(
        "🎯 THIS WEEK'S PROGRESSION CHALLENGE"
    )

    lines.append("")

    lines.append(
        "Do ONE thing this week that moves "
        "your post-18 plans forward:"
    )

    lines.append("")

    lines.append(
        "☐ Book a university open day"
    )

    lines.append(
        "☐ Apply for an apprenticeship"
    )

    lines.append(
        "☐ Research a career"
    )

    lines.append(
        "☐ Find work experience"
    )

    lines.append(
        "☐ Research a degree apprenticeship"
    )

    lines.append(
        "☐ Update your CV"
    )

    lines.append(
        "☐ Speak to your tutor or careers team"
    )

    lines.append("")

    lines.append(
        "━━━━━━━━━━━━━━━━━━━━"
    )

    lines.append("")

    lines.append(
        "⚠️ IMPORTANT"
    )

    lines.append(
        "Always check the original opportunity "
        "before applying. Dates, availability, "
        "eligibility and vacancies can change."
    )

    lines.append("")

    lines.append(
        "🎓 KS5 Progression Hub"
    )

    return "\n".join(lines)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("🎛️ Bulletin Controls")

    st.subheader(
        "🎓 Apprenticeship search"
    )

    selected_level = st.selectbox(
        "Level",
        [
            "All levels",
            "Level 2",
            "Level 3",
            "Level 4",
            "Level 5",
            "Level 6",
            "Level 7"
        ]
    )

    selected_category = st.selectbox(
        "Career area",
        [
            "All categories",
            "Digital",
            "Engineering",
            "Business & Administration",
            "Finance & Legal",
            "Health & Science",
            "Creative",
            "Construction",
            "Education"
        ]
    )

    selected_location = st.selectbox(
        "Apprenticeship location",
        [
            "All locations",
            "Liverpool",
            "Manchester",
            "Birmingham",
            "Leeds",
            "London",
            "Bristol",
            "Newcastle",
            "Sheffield",
            "Nottingham"
        ]
    )

    st.subheader(
        "🏫 University events"
    )

    months_ahead = st.slider(
        "Look ahead",
        min_value=1,
        max_value=12,
        value=3,
        step=1
    )

    st.divider()

    if st.button(
        "🚀 BUILD THIS WEEK'S BULLETIN",
        use_container_width=True,
        type="primary"
    ):

        with st.spinner(
            "Searching live progression sources..."
        ):

            items, statuses = refresh_all(
                selected_level,
                selected_category,
                selected_location,
                months_ahead
            )

            st.session_state.items = items

            st.session_state.source_status = (
                statuses
            )

            st.session_state.last_refresh = (
                datetime.now().strftime(
                    "%d %B %Y at %H:%M"
                )
            )

        st.success(
            "Bulletin refreshed!"
        )


# ============================================================
# HERO
# ============================================================

st.markdown(
    """
<div class="hero">

<h1>🎓 KS5 Progression Hub</h1>

<p>
Live apprenticeships • University open days •
Work experience • UCAS deadlines •
Progression resources
</p>

</div>
""",
    unsafe_allow_html=True
)


# ============================================================
# INTRO
# ============================================================

if not st.session_state.items:

    st.info(
        """
        👈 Use the controls on the left and click

        **🚀 BUILD THIS WEEK'S BULLETIN**

        The app will search the live Government
        apprenticeship service and UCAS events,
        then build a student-ready bulletin.
        """
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:

        st.metric(
            "🎓 Apprenticeships",
            "LIVE"
        )

    with c2:

        st.metric(
            "🏫 Open Days",
            "LIVE"
        )

    with c3:

        st.metric(
            "📅 Key Dates",
            "UCAS"
        )

    with c4:

        st.metric(
            "💼 Experience",
            "LIVE"
        )

    st.stop()


# ============================================================
# DATA
# ============================================================

items = st.session_state.items

apprenticeships = [
    x for x in items
    if x["category"]
    == "🎓 Apprenticeship"
]

open_days = [
    x for x in items
    if x["category"]
    == "🏫 University Open Day"
]

key_dates = [
    x for x in items
    if x["category"]
    == "📅 Key Date"
]

work_experience = [
    x for x in items
    if x["category"]
    == "💼 Work Experience"
]

resources = [
    x for x in items
    if x["category"]
    == "⭐ Resource"
]

priority_items = get_priority_items(
    items
)


# ============================================================
# DASHBOARD METRICS
# ============================================================

c1, c2, c3, c4, c5 = st.columns(5)

with c1:

    st.metric(
        "🎓 Live Apprenticeships",
        len(apprenticeships)
    )

with c2:

    st.metric(
        "🏫 Open Days",
        len(open_days)
    )

with c3:

    st.metric(
        "📅 Key Dates",
        len(key_dates)
    )

with c4:

    st.metric(
        "💼 Experience",
        len(work_experience)
    )

with c5:

    st.metric(
        "🚨 Priorities",
        len(priority_items)
    )


if st.session_state.last_refresh:

    st.caption(
        f"Last refreshed: "
        f"{st.session_state.last_refresh}"
    )


# ============================================================
# TABS
# ============================================================

tabs = st.tabs(
    [
        "🚨 Priorities",
        "🎓 Apprenticeships",
        "🏫 University Open Days",
        "📅 Key Dates",
        "💼 Work Experience",
        "📢 Teams Bulletin",
        "➕ Add Opportunity",
        "⚙️ Sources"
    ]
)


# ============================================================
# PRIORITIES
# ============================================================

with tabs[0]:

    st.header(
        "🚨 What needs attention?"
    )

    if not priority_items:

        st.success(
            "No major deadlines or closing-soon "
            "opportunities detected."
        )

    else:

        for index, item in enumerate(
            priority_items
        ):

            display_item(
                item,
                index
            )


# ============================================================
# APPRENTICESHIPS
# ============================================================

with tabs[1]:

    st.header(
        "🎓 Live Apprenticeships"
    )

    st.write(
        "Actual vacancies currently listed on "
        "the Government apprenticeship service."
    )

    search = st.text_input(
        "🔎 Search vacancies",
        placeholder=(
            "e.g. engineering, finance, "
            "digital, accounting..."
        ),
        key="apprenticeship_search"
    )

    filtered = filter_items(
        apprenticeships,
        section="🎓 Apprenticeship",
        search=search
    )

    if not filtered:

        st.warning(
            "No apprenticeships matched "
            "your search."
        )

    else:

        for index, item in enumerate(
            filtered
        ):

            display_item(
                item,
                index
            )


# ============================================================
# OPEN DAYS
# ============================================================

with tabs[2]:

    st.header(
        "🏫 University Open Days"
    )

    st.write(
        "Upcoming events found from the live "
        "UCAS events search."
    )

    if not open_days:

        st.warning(
            "No upcoming UCAS open days were "
            "found within the selected period."
        )

    else:

        for index, item in enumerate(
            open_days
        ):

            display_item(
                item,
                index
            )


# ============================================================
# KEY DATES
# ============================================================

with tabs[3]:

    st.header(
        "📅 Important Progression Dates"
    )

    for index, item in enumerate(
        key_dates
    ):

        display_item(
            item,
            index,
            allow_remove=False
        )


# ============================================================
# WORK EXPERIENCE
# ============================================================

with tabs[4]:

    st.header(
        "💼 Work Experience & Career Experience"
    )

    for index, item in enumerate(
        work_experience
    ):

        display_item(
            item,
            index
        )


# ============================================================
# TEAMS BULLETIN
# ============================================================

with tabs[5]:

    st.header(
        "📢 Microsoft Teams Bulletin"
    )

    bulletin = create_bulletin(
        items
    )

    st.markdown(
        """
        <div class="bulletin">
        Your bulletin is generated from the
        opportunities currently loaded into the hub.
        </div>
        """,
        unsafe_allow_html=True
    )

    st.text_area(
        "Teams-ready bulletin",
        bulletin,
        height=900
    )

    c1, c2 = st.columns(2)

    with c1:

        st.download_button(
            "📥 Download bulletin",
            bulletin,
            file_name=(
                "KS5_Progression_Bulletin_"
                f"{TODAY.isoformat()}.txt"
            ),
            mime="text/plain",
            use_container_width=True
        )

    with c2:

        st.success(
            "Copy the text above into Microsoft Teams."
        )


# ============================================================
# ADD OPPORTUNITY
# ============================================================

with tabs[6]:

    st.header(
        "➕ Add College Opportunity"
    )

    st.write(
        "Add your own college-specific event, "
        "employer visit, workshop, deadline or "
        "opportunity."
    )

    with st.form(
        "add_custom_opportunity"
    ):

        title = st.text_input(
            "Title"
        )

        organisation = st.text_input(
            "Organisation"
        )

        category = st.selectbox(
            "Category",
            [
                "🎓 Apprenticeship",
                "🏫 University Open Day",
                "📅 Key Date",
                "💼 Work Experience",
                "⭐ Resource",
                "🌟 Other Opportunity"
            ]
        )

        description = st.text_area(
            "Description"
        )

        event_date = st.text_input(
            "Date"
        )

        closing_date = st.text_input(
            "Closing date"
        )

        location = st.text_input(
            "Location"
        )

        url = st.text_input(
            "Link"
        )

        submit = st.form_submit_button(
            "➕ Add to bulletin"
        )

        if submit:

            if not title:

                st.error(
                    "Please enter a title."
                )

            else:

                new_item = make_item(
                    title=title,
                    organisation=organisation,
                    category=category,
                    description=description,
                    location=location,
                    event_date=event_date,
                    closing_date=closing_date,
                    url=url,
                    source="College added",
                    verified=False,
                    priority=50
                )

                st.session_state.custom_items.append(
                    new_item
                )

                st.session_state.items.append(
                    new_item
                )

                st.success(
                    "Added to the bulletin."
                )

                st.rerun()


# ============================================================
# SOURCES
# ============================================================

with tabs[7]:

    st.header(
        "⚙️ Data Sources"
    )

    st.write(
        "The hub deliberately keeps source information "
        "visible so staff can check the original listing."
    )

    source_info = {

        "GOV.UK Find an Apprenticeship": (
            GOV_APPRENTICESHIP_URL,
            "Live Government apprenticeship vacancies."
        ),

        "UCAS Events": (
            UCAS_EVENTS_URL,
            "University open days and other higher education events."
        ),

        "UCAS Deadlines": (
            "https://www.ucas.com/applying/"
            "applying-to-university/"
            "dates-and-deadlines-for-uni-applications",
            "Official UCAS application dates and deadlines."
        ),

        "Amazing Apprenticeships": (
            AMAZING_APPRENTICESHIPS_URL,
            "Higher and degree apprenticeship listings."
        ),

        "Forage": (
            FORAGE_URL,
            "Free virtual job simulations and career experiences."
        )
    }

    for name, data in source_info.items():

        url, description = data

        st.markdown(
            f"""
            ### {name}

            {description}

            {url}
            """
        )

        st.divider()


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "🎓 KS5 Progression Hub • "
    "Live-source progression bulletin • "
    f"Generated {TODAY.strftime('%d %B %Y')}"
)
