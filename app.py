import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import date, datetime, timedelta
from urllib.parse import urljoin
import re
import html


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="KS5 Progression Hub",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CONSTANTS
# ============================================================

TODAY = date.today()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/139.0 Safari/537.36"
    )
}

TIMEOUT = 25

UCAS_EVENTS_URL = (
    "https://www.ucas.com/explore/search/events"
)

UCAS_DEADLINES_URL = (
    "https://www.ucas.com/discover/advice-for-parents-"
    "guardians-and-carers/key-dates-and-the-application-journey"
)

GOV_APPRENTICESHIP_URL = (
    "https://www.findapprenticeship.service.gov.uk/apprenticeships"
)

AMAZING_LISTING_URL = (
    "https://www.amazingapprenticeships.com/"
    "higher-degree-listing/"
)

AMAZING_RESOURCES_URL = (
    "https://www.amazingapprenticeships.com/resources/"
)

UCAS_APPRENTICESHIPS_URL = (
    "https://www.ucas.com/apprenticeships"
)

UCAS_DISCOVER_URL = (
    "https://www.ucas.com/discover"
)

FORAGE_URL = (
    "https://www.theforage.com/simulations"
)

NCS_URL = (
    "https://nationalcareers.service.gov.uk/"
)


# ============================================================
# SESSION STATE
# ============================================================

if "items" not in st.session_state:
    st.session_state.items = []

if "removed" not in st.session_state:
    st.session_state.removed = set()

if "custom_items" not in st.session_state:
    st.session_state.custom_items = []

if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = None

if "source_status" not in st.session_state:
    st.session_state.source_status = {}


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
<style>

.main-title {
    font-size: 44px;
    font-weight: 800;
    margin-bottom: 4px;
}

.subtitle {
    font-size: 19px;
    color: #6b7280;
    margin-bottom: 20px;
}

.hero {
    padding: 30px;
    border-radius: 24px;
    color: white;
    background: linear-gradient(
        135deg,
        #172554,
        #1d4ed8,
        #2563eb
    );
    margin-bottom: 24px;
}

.hero h1 {
    margin: 0;
    font-size: 42px;
}

.hero p {
    margin-top: 10px;
    font-size: 18px;
}

.card {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 18px;
    padding: 20px;
    margin-bottom: 15px;
    box-shadow: 0 3px 14px rgba(0,0,0,0.04);
}

.card h3 {
    margin-top: 8px;
    margin-bottom: 6px;
}

.badge {
    display: inline-block;
    padding: 5px 9px;
    border-radius: 999px;
    background: #e0e7ff;
    color: #3730a3;
    font-size: 12px;
    font-weight: 700;
    margin-right: 5px;
    margin-bottom: 4px;
}

.red {
    background: #fee2e2;
    color: #991b1b;
}

.orange {
    background: #ffedd5;
    color: #9a3412;
}

.green {
    background: #dcfce7;
    color: #166534;
}

.blue {
    background: #dbeafe;
    color: #1e40af;
}

.small {
    color: #6b7280;
    font-size: 13px;
}

.priority {
    background: #fff7ed;
    border: 1px solid #fed7aa;
    border-radius: 18px;
    padding: 20px;
    margin-bottom: 15px;
}

.deadline {
    background: #fef2f2;
    border: 1px solid #fecaca;
    border-radius: 18px;
    padding: 20px;
    margin-bottom: 15px;
}

.bulletin {
    background: white;
    border: 1px solid #d1d5db;
    border-radius: 18px;
    padding: 25px;
}

</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# BASIC HELPERS
# ============================================================

def clean_text(value):
    """Clean scraped text safely."""

    if value is None:
        return ""

    value = html.unescape(str(value))
    value = re.sub(r"<[^>]*>", " ", value)
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def safe_get(url, params=None):
    """Safely download a webpage."""

    try:

        response = requests.get(
            url,
            params=params,
            headers=HEADERS,
            timeout=TIMEOUT,
        )

        response.raise_for_status()

        return response.text, "OK"

    except requests.RequestException as exc:

        return None, str(exc)

    except Exception as exc:

        return None, str(exc)


def ordinal(day):
    """Return 1st / 2nd / 3rd / 4th etc."""

    if 10 <= day % 100 <= 20:
        suffix = "th"

    else:
        suffix = {
            1: "st",
            2: "nd",
            3: "rd",
        }.get(day % 10, "th")

    return f"{day}{suffix}"


def format_date(value):
    """Format a Python date."""

    if not value:
        return ""

    return (
        f"{ordinal(value.day)} "
        f"{value.strftime('%B %Y')}"
    )


def parse_date(text):
    """Try several UK date formats."""

    if not text:
        return None

    text = clean_text(text)

    patterns = [
        r"(\d{1,2})(?:st|nd|rd|th)?\s+"
        r"([A-Za-z]+)\s+(\d{4})",

        r"([A-Za-z]+)\s+"
        r"(\d{1,2})(?:st|nd|rd|th)?"
        r"(?:,\s*|\s+)(\d{4})",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.I,
        )

        if not match:
            continue

        groups = match.groups()

        try:

            if groups[0].isdigit():

                day = int(groups[0])
                month = groups[1]
                year = int(groups[2])

            else:

                month = groups[0]
                day = int(groups[1])
                year = int(groups[2])

            for month_format in [
                "%B",
                "%b",
            ]:

                try:

                    return datetime.strptime(
                        f"{day} {month} {year}",
                        f"%d {month_format} %Y",
                    ).date()

                except ValueError:
                    pass

        except Exception:
            pass

    return None


def days_until(date_text):
    """Return number of days until a date."""

    parsed = parse_date(date_text)

    if not parsed:
        return None

    return (
        parsed - TODAY
    ).days


def make_id(
    category,
    title,
    organisation="",
    url="",
):
    raw = (
        f"{category}|"
        f"{title}|"
        f"{organisation}|"
        f"{url}"
    )

    return re.sub(
        r"[^a-z0-9]+",
        "-",
        raw.lower(),
    )[:250]


def make_item(
    *,
    title,
    organisation="",
    category="",
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
    priority=0,
    verified=True,
):

    if tags is None:
        tags = []

    return {
        "id": make_id(
            category,
            title,
            organisation,
            url,
        ),

        "title": clean_text(title),

        "organisation": clean_text(
            organisation
        ),

        "category": category,

        "description": clean_text(
            description
        ),

        "location": clean_text(
            location
        ),

        "event_date": clean_text(
            event_date
        ),

        "closing_date": clean_text(
            closing_date
        ),

        "start_date": clean_text(
            start_date
        ),

        "salary": clean_text(
            salary
        ),

        "level": clean_text(
            level
        ),

        "url": url,

        "source": clean_text(
            source
        ),

        "posted_date": clean_text(
            posted_date
        ),

        "tags": tags,

        "priority": priority,

        "verified": verified,
    }


# ============================================================
# UCAS OPEN DAYS
# ============================================================

@st.cache_data(
    ttl=1800,
    show_spinner=False,
)
def fetch_ucas_open_days(
    months_ahead=3,
    max_results=40,
):

    page, status = safe_get(
        UCAS_EVENTS_URL,
        params={
            "eventType": "Open day",
        },
    )

    if page is None:
        return [], status

    soup = BeautifulSoup(
        page,
        "html.parser",
    )

    cutoff = (
        TODAY
        + timedelta(
            days=months_ahead * 31
        )
    )

    results = []
    seen_urls = set()

    # UCAS currently exposes individual
    # event pages under /events/
    for link in soup.find_all(
        "a",
        href=True,
    ):

        href = link.get("href", "")

        if "/events/" not in href:
            continue

        full_url = urljoin(
            "https://www.ucas.com",
            href,
        )

        if full_url in seen_urls:
            continue

        title = clean_text(
            link.get_text(
                " ",
                strip=True,
            )
        )

        if not title:
            continue

        # We want actual open-day style events,
        # not every UCAS event.
        title_lower = title.lower()

        if (
            "open day" not in title_lower
            and "open-day" not in title_lower
            and "open evening" not in title_lower
            and "open event" not in title_lower
        ):
            continue

        seen_urls.add(full_url)

        # ----------------------------------------------------
        # Find a sensible surrounding block
        # ----------------------------------------------------

        block = link

        for _ in range(6):

            if block.parent is None:
                break

            block = block.parent

            text = clean_text(
                block.get_text(
                    " ",
                    strip=True,
                )
            )

            if 80 <= len(text) <= 1500:
                break

        block_text = clean_text(
            block.get_text(
                " ",
                strip=True,
            )
        )

        # ----------------------------------------------------
        # Date
        # ----------------------------------------------------

        date_match = re.search(
            r"(\d{1,2}(?:st|nd|rd|th)?\s+"
            r"[A-Za-z]+\s+\d{4})",
            block_text,
            re.I,
        )

        if not date_match:
            continue

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

        # Often the UCAS card has the location
        # after the event metadata.
        possible_locations = [
            "London",
            "Manchester",
            "Liverpool",
            "Birmingham",
            "Leeds",
            "Bristol",
            "Bath",
            "Oxford",
            "Cambridge",
            "Leicester",
            "Nottingham",
            "Sheffield",
            "Bradford",
            "York",
            "Newcastle",
            "Durham",
            "Chester",
            "Preston",
            "Lincoln",
            "Poole",
            "Guildford",
            "Brighton",
            "Cardiff",
            "Swansea",
            "Edinburgh",
            "Glasgow",
            "Aberdeen",
            "Dundee",
            "Belfast",
            "Coventry",
            "Reading",
            "Exeter",
            "Plymouth",
            "Canterbury",
            "Chelmsford",
            "Peterborough",
            "Milton Keynes",
            "Worcester",
            "Hereford",
            "Rotherham",
            "Bury",
            "Stirling",
        ]

        for city in possible_locations:

            if re.search(
                rf"\b{re.escape(city)}\b",
                block_text,
                re.I,
            ):

                location = city
                break

        # ----------------------------------------------------
        # Tags
        # ----------------------------------------------------

        tags = [
            "University event",
            "Open day",
            "UCAS",
        ]

        if "virtual" in block_text.lower():
            tags.append("Virtual")

        if "undergraduate" in block_text.lower():
            tags.append("Undergraduate")

        # ----------------------------------------------------
        # Priority
        # ----------------------------------------------------

        priority = 200

        days = (
            event_date - TODAY
        ).days

        if days <= 7:
            priority = 800

            tags.append(
                "🔥 This week"
            )

        elif days <= 14:
            priority = 600

            tags.append(
                "Soon"
            )

        # ----------------------------------------------------
        # Item
        # ----------------------------------------------------

        results.append(
            make_item(
                title=title,
                organisation="",
                category="🏫 University Open Day",
                description=(
                    "Upcoming event listed by UCAS. "
                    "Open the original UCAS event page "
                    "to check booking requirements, "
                    "times and full event information."
                ),
                location=location,
                event_date=format_date(
                    event_date
                ),
                url=full_url,
                source="UCAS",
                tags=tags,
                priority=priority,
                verified=True,
            )
        )

        if len(results) >= max_results:
            break

    # --------------------------------------------------------
    # Deduplicate
    # --------------------------------------------------------

    unique = {}

    for item in results:

        unique[
            item["url"]
        ] = item

    results = list(
        unique.values()
    )

    # --------------------------------------------------------
    # Sort
    # --------------------------------------------------------

    results.sort(
        key=lambda item: (
            parse_date(
                item["event_date"]
            )
            or date.max
        )
    )

    return results, "OK"


# ============================================================
# GOVERNMENT APPRENTICESHIPS
# ============================================================

@st.cache_data(
    ttl=1800,
    show_spinner=False,
)
def fetch_apprenticeships(
    level="All levels",
    career_area="All categories",
    max_results=50,
):

    params = {}

    level_map = {
        "Level 2": "2",
        "Level 3": "3",
        "Level 4": "4",
        "Level 5": "5",
        "Level 6": "6",
        "Level 7": "7",
    }

    if level in level_map:

        params["levelIds"] = (
            level_map[level]
        )

    page, status = safe_get(
        GOV_APPRENTICESHIP_URL,
        params=params,
    )

    if page is None:
        return [], status

    soup = BeautifulSoup(
        page,
        "html.parser",
    )

    results = []
    seen = set()

    # --------------------------------------------------------
    # Career keyword groups
    # --------------------------------------------------------

    career_terms = {

        "Digital": [
            "digital",
            "software",
            "developer",
            "programmer",
            "cyber",
            "data",
            "technology",
            "IT",
            "artificial intelligence",
            "AI",
            "automation",
        ],

        "Engineering": [
            "engineer",
            "engineering",
            "manufacturing",
            "mechanical",
            "electrical",
            "aerospace",
        ],

        "Business & Administration": [
            "business",
            "administration",
            "administrator",
            "management",
            "office",
            "operations",
            "project",
        ],

        "Finance & Legal": [
            "finance",
            "financial",
            "accountancy",
            "accounting",
            "audit",
            "legal",
            "law",
            "solicitor",
        ],

        "Health & Science": [
            "health",
            "nursing",
            "pharmacy",
            "science",
            "laboratory",
            "clinical",
            "dental",
        ],

        "Creative & Media": [
            "creative",
            "design",
            "graphic",
            "media",
            "marketing",
            "content",
            "film",
            "advertising",
        ],

        "Construction": [
            "construction",
            "quantity survey",
            "building",
            "civil engineering",
            "site",
            "property",
        ],

        "Education": [
            "teaching",
            "teacher",
            "education",
            "early years",
        ],
    }

    # --------------------------------------------------------
    # Find vacancy links
    # --------------------------------------------------------

    links = soup.find_all(
        "a",
        href=True,
    )

    for link in links:

        href = link.get(
            "href",
            "",
        )

        if "/apprenticeships/" not in href:
            continue

        title = clean_text(
            link.get_text(
                " ",
                strip=True,
            )
        )

        if len(title) < 8:
            continue

        title_lower = title.lower()

        # Ignore navigation/filter links
        bad_titles = [
            "find an apprenticeship",
            "search",
            "back",
            "next",
            "previous",
            "sign in",
        ]

        if title_lower in bad_titles:
            continue

        full_url = urljoin(
            "https://www.findapprenticeship.service.gov.uk",
            href,
        )

        if full_url in seen:
            continue

        seen.add(full_url)

        # ----------------------------------------------------
        # Find vacancy block
        # ----------------------------------------------------

        block = link

        for _ in range(8):

            if block.parent is None:
                break

            block = block.parent

            block_text = clean_text(
                block.get_text(
                    " ",
                    strip=True,
                )
            )

            if (
                100 <= len(block_text) <= 2200
                and (
                    "Start date"
                    in block_text
                    or "Wage"
                    in block_text
                    or "Closes"
                    in block_text
                )
            ):
                break

        block_text = clean_text(
            block.get_text(
                " ",
                strip=True,
            )
        )

        # ----------------------------------------------------
        # Career filter
        # ----------------------------------------------------

        if career_area != "All categories":

            terms = career_terms.get(
                career_area,
                [],
            )

            if not any(
                term.lower()
                in (
                    title + " " + block_text
                ).lower()
                for term in terms
            ):
                continue

        # ----------------------------------------------------
        # Level
        # ----------------------------------------------------

        level_match = re.search(
            r"\(level\s+([2-7])\)",
            block_text,
            re.I,
        )

        vacancy_level = ""

        if level_match:

            vacancy_level = (
                f"Level {level_match.group(1)}"
            )

        # ----------------------------------------------------
        # Training course
        # ----------------------------------------------------

        training = ""

        training_match = re.search(
            r"Training course\s+"
            r"(.+?)"
            r"(?=\s+Wage|\s+Closes|\s+Posted|$)",
            block_text,
            re.I,
        )

        if training_match:

            training = clean_text(
                training_match.group(1)
            )

        # ----------------------------------------------------
        # Wage
        # ----------------------------------------------------

        salary = ""

        wage_match = re.search(
            r"Wage\s+"
            r"(.+?)"
            r"(?=\s+Closes|\s+Posted|$)",
            block_text,
            re.I,
        )

        if wage_match:

            salary = clean_text(
                wage_match.group(1)
            )

        # ----------------------------------------------------
        # Start date
        # ----------------------------------------------------

        start_date = ""

        start_match = re.search(
            r"Start date\s+"
            r"(\d{1,2}\s+[A-Za-z]+\s+\d{4})",
            block_text,
            re.I,
        )

        if start_match:

            start_date = clean_text(
                start_match.group(1)
            )

        # ----------------------------------------------------
        # Closing date
        # ----------------------------------------------------

        closing_date = ""

        close_match = re.search(
            r"Closes"
            r".{0,100}?"
            r"(\d{1,2}\s+[A-Za-z]+\s+\d{4})",
            block_text,
            re.I,
        )

        if close_match:

            closing_date = (
                close_match.group(1)
            )

        else:

            # Handle "Closes today"
            if re.search(
                r"Closes\s+today",
                block_text,
                re.I,
            ):

                closing_date = format_date(
                    TODAY
                )

            elif re.search(
                r"Closes\s+tomorrow",
                block_text,
                re.I,
            ):

                closing_date = format_date(
                    TODAY
                    + timedelta(days=1)
                )

        # ----------------------------------------------------
        # Posted date
        # ----------------------------------------------------

        posted_date = ""

        posted_match = re.search(
            r"Posted\s+"
            r"(\d{1,2}\s+[A-Za-z]+\s+\d{4})",
            block_text,
            re.I,
        )

        if posted_match:

            posted_date = (
                posted_match.group(1)
            )

        # ----------------------------------------------------
        # Employer
        # ----------------------------------------------------

        employer = ""

        lines = [
            clean_text(line)
            for line in block.stripped_strings
        ]

        for line in lines:

            if not line:
                continue

            if line == title:
                continue

            if (
                line.startswith("Start date")
                or line.startswith("Training course")
                or line.startswith("Wage")
                or line.startswith("Closes")
                or line.startswith("Posted")
            ):
                continue

            if (
                "level" in line.lower()
                and len(line) < 50
            ):
                continue

            # The employer normally appears as a
            # short line after the vacancy title.
            if 2 < len(line) < 120:

                employer = line
                break

        # ----------------------------------------------------
        # Location
        # ----------------------------------------------------

        location = ""

        # Common pattern:
        # Employer
        # CITY (postcode)
        # Start date
        location_match = re.search(
            r"\b([A-Z][A-Za-z .'-]+)"
            r"\s+\([A-Z0-9 ]{2,10}\)"
            r"(?:\s+and\s+\d+\s+other locations)?"
            r"\s+Start date",
            block_text,
        )

        if location_match:

            location = clean_text(
                location_match.group(1)
            )

        # ----------------------------------------------------
        # Priority
        # ----------------------------------------------------

        priority = 100

        tags = [
            "Live vacancy",
            "GOV.UK",
        ]

        closing_parsed = parse_date(
            closing_date
        )

        if closing_parsed:

            days = (
                closing_parsed - TODAY
            ).days

            if days < 0:

                # Do not publish expired vacancies.
                continue

            elif days <= 3:

                priority = 1000

                tags.append(
                    "🔴 Closing very soon"
                )

            elif days <= 7:

                priority = 900

                tags.append(
                    "🔥 Closing soon"
                )

            elif days <= 14:

                priority = 500

                tags.append(
                    "Closing within 14 days"
                )

        # ----------------------------------------------------
        # New vacancy
        # ----------------------------------------------------

        posted_parsed = parse_date(
            posted_date
        )

        if posted_parsed:

            posted_days = (
                TODAY - posted_parsed
            ).days

            if 0 <= posted_days <= 7:

                tags.append(
                    "🆕 New this week"
                )

                priority += 200

        # ----------------------------------------------------
        # Degree apprenticeship
        # ----------------------------------------------------

        combined = (
            title
            + " "
            + training
            + " "
            + vacancy_level
        ).lower()

        if (
            "degree" in combined
            or vacancy_level in [
                "Level 6",
                "Level 7",
            ]
        ):

            tags.append(
                "🎓 Degree / higher"
            )

            priority += 100

        # ----------------------------------------------------
        # Description
        # ----------------------------------------------------

        description_parts = []

        if training:

            description_parts.append(
                training
            )

        description_parts.append(
            "Live apprenticeship vacancy "
            "listed on the Government "
            "Find an Apprenticeship service."
        )

        description = " ".join(
            description_parts
        )

        # ----------------------------------------------------
        # Add item
        # ----------------------------------------------------

        results.append(
            make_item(
                title=title,
                organisation=employer,
                category="🎓 Apprenticeship",
                description=description,
                location=location,
                closing_date=closing_date,
                start_date=start_date,
                salary=salary,
                level=vacancy_level,
                url=full_url,
                source=(
                    "GOV.UK Find an Apprenticeship"
                ),
                posted_date=posted_date,
                tags=tags,
                priority=priority,
                verified=True,
            )
        )

        if len(results) >= max_results:
            break

    # --------------------------------------------------------
    # Sort
    # --------------------------------------------------------

    results.sort(
        key=lambda item: (
            -item.get("priority", 0),
            parse_date(
                item.get(
                    "closing_date",
                    "",
                )
            )
            or date.max,
        )
    )

    return results, "OK"


# ============================================================
# UCAS KEY DATES
# ============================================================

def get_ucas_key_dates():

    dates = [

        (
            date(2026, 9, 1),
            "2027 entry UCAS applications can be submitted",
            "Students can submit completed undergraduate applications to UCAS.",
            ["UCAS", "2027 entry", "Applications"],
            800,
        ),

        (
            date(2026, 10, 1),
            "Conservatoire music applications deadline",
            "18:00 UK time deadline for conservatoire music applications.",
            ["UCAS", "Conservatoire"],
            700,
        ),

        (
            date(2026, 10, 15),
            "Oxford, Cambridge, Medicine, Dentistry & Veterinary deadline",
            (
                "18:00 UK time deadline for applications to "
                "Oxford and Cambridge and most courses in "
                "medicine, dentistry and veterinary "
                "medicine/science."
            ),
            [
                "🔴 Major deadline",
                "Oxbridge",
                "Medicine",
                "Dentistry",
                "Veterinary",
            ],
            1200,
        ),

        (
            date(2027, 1, 13),
            "UCAS Equal Consideration Deadline",
            (
                "18:00 UK time deadline for most undergraduate "
                "applications and most conservatoire undergraduate "
                "dance, drama and musical theatre courses."
            ),
            [
                "🔴 Major deadline",
                "2027 entry",
            ],
            1200,
        ),

        (
            date(2027, 2, 25),
            "UCAS Extra opens",
            (
                "Students who have used all five choices "
                "and are not holding an offer may be able "
                "to use Extra."
            ),
            [
                "UCAS Extra",
            ],
            700,
        ),

        (
            date(2027, 6, 30),
            "Last date for applications with choices",
            (
                "Applications received after this deadline "
                "are automatically entered into Clearing."
            ),
            [
                "Clearing",
            ],
            800,
        ),

        (
            date(2027, 7, 1),
            "UCAS Extra closes",
            "Final day of UCAS Extra for 2027 entry.",
            [
                "UCAS Extra",
            ],
            500,
        ),

        (
            date(2027, 7, 2),
            "Clearing opens",
            "UCAS Clearing vacancies become available.",
            [
                "Clearing",
            ],
            600,
        ),

        (
            date(2027, 9, 23),
            "Final date for 2027 entry applications",
            "18:00 UK time final date for 2027 entry applications.",
            [
                "Final deadline",
            ],
            700,
        ),

    ]

    results = []

    for (
        event_date,
        title,
        description,
        tags,
        priority,
    ) in dates:

        if event_date < TODAY:
            continue

        days = (
            event_date - TODAY
        ).days

        actual_tags = list(tags)

        if days <= 7:

            actual_tags.append(
                "🔥 This week"
            )

        elif days <= 30:

            actual_tags.append(
                "⏰ Coming soon"
            )

        results.append(
            make_item(
                title=title,
                organisation="UCAS",
                category="📅 Key Date",
                description=description,
                event_date=format_date(
                    event_date
                ),
                closing_date=(
                    f"{format_date(event_date)} "
                    "at 18:00 UK time"
                ),
                url=UCAS_DEADLINES_URL,
                source="UCAS",
                tags=actual_tags,
                priority=priority,
                verified=True,
            )
        )

    return results


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
                "Specialist listing of higher and degree "
                "apprenticeship vacancies. Particularly "
                "useful for Year 13 students considering "
                "degree-level apprenticeships."
            ),
            location="UK",
            event_date="Current listings",
            url=AMAZING_LISTING_URL,
            source="Amazing Apprenticeships",
            tags=[
                "Degree apprenticeship",
                "Higher apprenticeship",
                "Year 13",
            ],
            priority=350,
            verified=True,
        ),

        make_item(
            title=(
                "Apprenticeship Resources"
            ),
            organisation="Amazing Apprenticeships",
            category="⭐ Resource",
            description=(
                "Resources for students covering "
                "apprenticeships, employers, careers "
                "and applications."
            ),
            location="Online",
            event_date="Available now",
            url=AMAZING_RESOURCES_URL,
            source="Amazing Apprenticeships",
            tags=[
                "Apprenticeships",
                "Student resource",
            ],
            priority=300,
            verified=True,
        ),
    ]


# ============================================================
# WORK EXPERIENCE
# ============================================================

def get_work_experience():

    return [

        make_item(
            title=(
                "Forage – Virtual Work Experiences"
            ),
            organisation="Forage",
            category="💼 Work Experience",
            description=(
                "Free virtual job simulations from "
                "major employers. Students can explore "
                "different careers and complete realistic "
                "work-based tasks."
            ),
            location="Online",
            event_date="Available now",
            url=FORAGE_URL,
            source="Forage",
            tags=[
                "Virtual",
                "Free",
                "Work experience",
            ],
            priority=300,
            verified=True,
        ),

        make_item(
            title=(
                "National Careers Service"
            ),
            organisation="GOV.UK",
            category="💼 Work Experience",
            description=(
                "Explore careers, job profiles, "
                "skills and routes into occupations."
            ),
            location="Online",
            event_date="Available now",
            url=NCS_URL,
            source="National Careers Service",
            tags=[
                "Career research",
            ],
            priority=200,
            verified=True,
        ),
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
            url=UCAS_DISCOVER_URL,
            source="UCAS",
            tags=[
                "University",
                "Careers",
                "Apprenticeships",
            ],
            priority=250,
            verified=True,
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
            url=UCAS_APPRENTICESHIPS_URL,
            source="UCAS",
            tags=[
                "Apprenticeships",
            ],
            priority=250,
            verified=True,
        ),
    ]


# ============================================================
# BUILD DATASET
# ============================================================

def refresh_all(
    level,
    career_area,
    months_ahead,
):

    all_items = []
    statuses = {}

    # --------------------------------------------------------
    # UCAS
    # --------------------------------------------------------

    ucas_items, ucas_status = (
        fetch_ucas_open_days(
            months_ahead=months_ahead,
            max_results=40,
        )
    )

    all_items.extend(
        ucas_items
    )

    statuses["UCAS"] = ucas_status

    # --------------------------------------------------------
    # Government apprenticeships
    # --------------------------------------------------------

    apprenticeship_items, apprenticeship_status = (
        fetch_apprenticeships(
            level=level,
            career_area=career_area,
            max_results=50,
        )
    )

    all_items.extend(
        apprenticeship_items
    )

    statuses["Government Apprenticeships"] = (
        apprenticeship_status
    )

    # --------------------------------------------------------
    # Static official / specialist sources
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
    # College-created items
    # --------------------------------------------------------

    all_items.extend(
        st.session_state.custom_items
    )

    # --------------------------------------------------------
    # Remove manually removed items
    # --------------------------------------------------------

    all_items = [
        item
        for item in all_items
        if item.get("id")
        not in st.session_state.removed
    ]

    # --------------------------------------------------------
    # Validate
    # --------------------------------------------------------

    validated = []

    for item in all_items:

        if not isinstance(
            item,
            dict,
        ):
            continue

        if not item.get("title"):
            continue

        # Live opportunities must have a URL.
        if item.get(
            "category"
        ) in [
            "🎓 Apprenticeship",
            "🏫 University Open Day",
        ]:

            if not item.get("url"):
                continue

        validated.append(item)

    # --------------------------------------------------------
    # Deduplicate
    # --------------------------------------------------------

    unique = {}

    for item in validated:

        key = (
            item.get("category", ""),
            item.get("title", "").lower(),
            item.get("organisation", "").lower(),
            item.get("url", ""),
        )

        if key not in unique:

            unique[key] = item

    return list(
        unique.values()
    ), statuses


# ============================================================
# PRIORITY ENGINE
# ============================================================

def get_priorities(items):

    if not isinstance(
        items,
        list,
    ):
        return []

    priorities = []

    for item in items:

        if not isinstance(
            item,
            dict,
        ):
            continue

        priority = item.get(
            "priority",
            0,
        )

        try:
            priority = int(priority)

        except Exception:
            priority = 0

        closing = parse_date(
            item.get(
                "closing_date",
                "",
            )
        )

        event = parse_date(
            item.get(
                "event_date",
                "",
            )
        )

        is_priority = (
            priority >= 800
        )

        if closing:

            days = (
                closing - TODAY
            ).days

            if 0 <= days <= 7:

                is_priority = True

        if event:

            days = (
                event - TODAY
            ).days

            if 0 <= days <= 7:

                is_priority = True

        if is_priority:

            priorities.append(item)

    priorities.sort(
        key=lambda item: (
            -int(
                item.get(
                    "priority",
                    0,
                )
            ),
            parse_date(
                item.get(
                    "closing_date",
                    "",
                )
            )
            or parse_date(
                item.get(
                    "event_date",
                    "",
                )
            )
            or date.max,
        )
    )

    return priorities[:10]


# ============================================================
# CATEGORY FILTER
# ============================================================

def category_items(
    items,
    category,
):

    return [
        item
        for item in items
        if isinstance(item, dict)
        and item.get(
            "category"
        ) == category
    ]


# ============================================================
# SEARCH
# ============================================================

def search_items(
    items,
    search,
):

    if not search:
        return items

    search = search.lower().strip()

    results = []

    for item in items:

        searchable = " ".join(
            [
                str(
                    item.get(
                        "title",
                        "",
                    )
                ),

                str(
                    item.get(
                        "organisation",
                        "",
                    )
                ),

                str(
                    item.get(
                        "description",
                        "",
                    )
                ),

                str(
                    item.get(
                        "location",
                        "",
                    )
                ),

                str(
                    item.get(
                        "level",
                        "",
                    )
                ),

                " ".join(
                    item.get(
                        "tags",
                        [],
                    )
                ),
            ]
        ).lower()

        if search in searchable:

            results.append(item)

    return results


# ============================================================
# DISPLAY CARD
# ============================================================

def display_card(
    item,
    key_suffix,
    removable=True,
):

    if not isinstance(
        item,
        dict,
    ):
        return

    title = item.get(
        "title",
        "Untitled opportunity",
    )

    organisation = item.get(
        "organisation",
        "",
    )

    description = item.get(
        "description",
        "",
    )

    location = item.get(
        "location",
        "",
    )

    event_date = item.get(
        "event_date",
        "",
    )

    closing_date = item.get(
        "closing_date",
        "",
    )

    salary = item.get(
        "salary",
        "",
    )

    level = item.get(
        "level",
        "",
    )

    source = item.get(
        "source",
        "",
    )

    tags = item.get(
        "tags",
        [],
    )

    badges = ""

    for tag in tags[:6]:

        css_class = "badge"

        if (
            "Closing" in tag
            or "Major" in tag
            or "🔴" in tag
        ):

            css_class += " red"

        elif (
            "🔥" in tag
            or "Soon" in tag
        ):

            css_class += " orange"

        elif "New" in tag:

            css_class += " green"

        else:

            css_class += " blue"

        badges += (
            f'<span class="{css_class}">'
            f'{html.escape(tag)}'
            f'</span>'
        )

    extra = ""

    if organisation:

        extra += (
            f"<p><strong>"
            f"{html.escape(organisation)}"
            f"</strong></p>"
        )

    if location:

        extra += (
            f"<p>📍 "
            f"{html.escape(location)}"
            f"</p>"
        )

    if event_date:

        extra += (
            f"<p>📅 "
            f"{html.escape(event_date)}"
            f"</p>"
        )

    if closing_date:

        extra += (
            f"<p>⏰ Closing: "
            f"{html.escape(closing_date)}"
            f"</p>"
        )

    if level:

        extra += (
            f"<p>🎓 "
            f"{html.escape(level)}"
            f"</p>"
        )

    if salary:

        extra += (
            f"<p>💷 "
            f"{html.escape(salary)}"
            f"</p>"
        )

    st.markdown(
        f"""
<div class="card">

{badges}

<h3>{html.escape(title)}</h3>

{extra}

<p>{html.escape(description)}</p>

<p class="small">
Source: {html.escape(source)}
</p>

</div>
""",
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(
        [3, 1]
    )

    with col1:

        url = item.get(
            "url",
            "",
        )

        if url:

            st.link_button(
                "🔗 View original opportunity",
                url,
                use_container_width=False,
            )

    with col2:

        if removable:

            if st.button(
                "🗑️ Remove",
                key=(
                    "remove_"
                    + str(
                        item.get(
                            "id",
                            "",
                        )
                    )
                    + "_"
                    + key_suffix
                ),
            ):

                st.session_state.removed.add(
                    item.get(
                        "id",
                        "",
                    )
                )

                st.session_state.items = [
                    x
                    for x in st.session_state.items
                    if x.get("id")
                    != item.get("id")
                ]

                st.rerun()


# ============================================================
# BULLETIN BUILDER
# ============================================================

def build_bulletin(items):

    lines = []

    lines.append(
        "🎓 KS5 PROGRESSION BULLETIN"
    )

    lines.append(
        f"Week commencing "
        f"{format_date(TODAY)}"
    )

    lines.append("")

    lines.append(
        "Here are this week's live "
        "opportunities, university events, "
        "work experience options and key "
        "progression dates for KS5 students."
    )

    lines.append("")

    lines.append(
        "━━━━━━━━━━━━━━━━━━━━"
    )

    lines.append("")

    # ========================================================
    # PRIORITIES
    # ========================================================

    priorities = get_priorities(
        items
    )

    if priorities:

        lines.append(
            "🚨 THIS WEEK'S PRIORITIES"
        )

        lines.append("")

        for item in priorities[:6]:

            lines.append(
                f"🔴 {item['title']}"
            )

            if item.get(
                "organisation"
            ):

                lines.append(
                    f"Organisation: "
                    f"{item['organisation']}"
                )

            if item.get(
                "event_date"
            ):

                lines.append(
                    f"📅 {item['event_date']}"
                )

            if item.get(
                "closing_date"
            ):

                lines.append(
                    f"⏰ {item['closing_date']}"
                )

            if item.get(
                "url"
            ):

                lines.append(
                    f"🔗 {item['url']}"
                )

            lines.append("")

        lines.append(
            "━━━━━━━━━━━━━━━━━━━━"
        )

        lines.append("")

    # ========================================================
    # UNIVERSITY OPEN DAYS
    # ========================================================

    open_days = category_items(
        items,
        "🏫 University Open Day",
    )

    open_days.sort(
        key=lambda item:
        parse_date(
            item.get(
                "event_date",
                "",
            )
        )
        or date.max
    )

    if open_days:

        lines.append(
            "🏫 UNIVERSITY OPEN DAYS"
        )

        lines.append("")

        for item in open_days[:15]:

            lines.append(
                f"🔹 {item['title']}"
            )

            if item.get(
                "event_date"
            ):

                lines.append(
                    f"📅 {item['event_date']}"
                )

            if item.get(
                "location"
            ):

                lines.append(
                    f"📍 {item['location']}"
                )

            lines.append(
                "Check the original UCAS event "
                "page for booking information."
            )

            if item.get(
                "url"
            ):

                lines.append(
                    f"🔗 {item['url']}"
                )

            lines.append("")

        lines.append(
            "━━━━━━━━━━━━━━━━━━━━"
        )

        lines.append("")

    # ========================================================
    # APPRENTICESHIPS
    # ========================================================

    apprenticeships = category_items(
        items,
        "🎓 Apprenticeship",
    )

    apprenticeships.sort(
        key=lambda item: (
            -int(
                item.get(
                    "priority",
                    0,
                )
            ),
            parse_date(
                item.get(
                    "closing_date",
                    "",
                )
            )
            or date.max,
        )
    )

    if apprenticeships:

        lines.append(
            "🎓 LIVE APPRENTICESHIPS"
        )

        lines.append("")

        for item in apprenticeships[:20]:

            lines.append(
                f"🔹 {item['title']}"
            )

            if item.get(
                "organisation"
            ):

                lines.append(
                    f"Employer: "
                    f"{item['organisation']}"
                )

            if item.get(
                "location"
            ):

                lines.append(
                    f"📍 {item['location']}"
                )

            if item.get(
                "level"
            ):

                lines.append(
                    f"🎓 {item['level']}"
                )

            if item.get(
                "salary"
            ):

                lines.append(
                    f"💷 {item['salary']}"
                )

            if item.get(
                "start_date"
            ):

                lines.append(
                    f"🚀 Start: "
                    f"{item['start_date']}"
                )

            if item.get(
                "closing_date"
            ):

                lines.append(
                    f"⏰ Closing: "
                    f"{item['closing_date']}"
                )

            if (
                "🔴 Closing very soon"
                in item.get(
                    "tags",
                    [],
                )
            ):

                lines.append(
                    "🚨 CLOSING VERY SOON"
                )

            elif (
                "🔥 Closing soon"
                in item.get(
                    "tags",
                    [],
                )
            ):

                lines.append(
                    "🔥 CLOSING SOON"
                )

            if item.get(
                "url"
            ):

                lines.append(
                    f"🔗 {item['url']}"
                )

            lines.append("")

        lines.append(
            "━━━━━━━━━━━━━━━━━━━━"
        )

        lines.append("")

    # ========================================================
    # KEY DATES
    # ========================================================

    key_dates = category_items(
        items,
        "📅 Key Date",
    )

    key_dates.sort(
        key=lambda item:
        parse_date(
            item.get(
                "event_date",
                "",
            )
        )
        or date.max
    )

    if key_dates:

        lines.append(
            "📅 KEY UCAS DATES"
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

            lines.append(
                f"🔗 {item['url']}"
            )

            lines.append("")

        lines.append(
            "━━━━━━━━━━━━━━━━━━━━"
        )

        lines.append("")

    # ========================================================
    # WORK EXPERIENCE
    # ========================================================

    work = category_items(
        items,
        "💼 Work Experience",
    )

    if work:

        lines.append(
            "💼 WORK EXPERIENCE & CAREER EXPERIENCE"
        )

        lines.append("")

        for item in work:

            lines.append(
                f"🔹 {item['title']}"
            )

            if item.get(
                "organisation"
            ):

                lines.append(
                    f"Organisation: "
                    f"{item['organisation']}"
                )

            lines.append(
                item["description"]
            )

            if item.get(
                "location"
            ):

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

    # ========================================================
    # RESOURCES
    # ========================================================

    resources = category_items(
        items,
        "⭐ Resource",
    )

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

    # ========================================================
    # STUDENT CHALLENGE
    # ========================================================

    lines.append(
        "🎯 THIS WEEK'S PROGRESSION CHALLENGE"
    )

    lines.append("")

    lines.append(
        "Choose ONE thing to move your "
        "post-18 plans forward:"
    )

    lines.append("")

    lines.append(
        "☐ Book a university open day"
    )

    lines.append(
        "☐ Apply for an apprenticeship"
    )

    lines.append(
        "☐ Research a degree apprenticeship"
    )

    lines.append(
        "☐ Find work experience"
    )

    lines.append(
        "☐ Research a career"
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
        "⚠️ Always check the original "
        "opportunity before applying. "
        "Dates, availability and eligibility "
        "can change."
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

    st.header(
        "🎛️ Bulletin Controls"
    )

    st.subheader(
        "🎓 Apprenticeships"
    )

    selected_level = st.selectbox(
        "Apprenticeship level",
        [
            "All levels",
            "Level 2",
            "Level 3",
            "Level 4",
            "Level 5",
            "Level 6",
            "Level 7",
        ],
    )

    selected_career = st.selectbox(
        "Career area",
        [
            "All categories",
            "Digital",
            "Engineering",
            "Business & Administration",
            "Finance & Legal",
            "Health & Science",
            "Creative & Media",
            "Construction",
            "Education",
        ],
    )

    st.subheader(
        "🏫 University events"
    )

    months_ahead = st.slider(
        "Look ahead",
        min_value=1,
        max_value=12,
        value=3,
    )

    st.divider()

    if st.button(
        "🚀 BUILD / REFRESH BULLETIN",
        use_container_width=True,
        type="primary",
    ):

        with st.spinner(
            "Searching live progression sources..."
        ):

            new_items, statuses = refresh_all(
                selected_level,
                selected_career,
                months_ahead,
            )

            st.session_state.items = (
                new_items
            )

            st.session_state.source_status = (
                statuses
            )

            st.session_state.last_refresh = (
                datetime.now().strftime(
                    "%d %B %Y at %H:%M"
                )
            )

        st.success(
            "Bulletin refreshed."
        )

        st.rerun()


# ============================================================
# HERO
# ============================================================

st.markdown(
    f"""
<div class="hero">

<h1>🎓 KS5 Progression Hub</h1>

<p>
Live apprenticeships • University open days •
UCAS deadlines • Work experience •
Progression resources
</p>

</div>
""",
    unsafe_allow_html=True,
)


# ============================================================
# FIRST RUN
# ============================================================

if not st.session_state.items:

    st.info(
        """
### Ready to build this week's bulletin

The hub will search:

🎓 **Government apprenticeship vacancies**

🏫 **UCAS university open days**

📅 **Official UCAS deadlines**

💼 **Work experience / career experience**

⭐ **Amazing Apprenticeships resources**

Then it will turn everything into a
student-friendly Microsoft Teams bulletin.
"""
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "🎓 Apprenticeships",
            "LIVE",
        )

    with c2:
        st.metric(
            "🏫 Open Days",
            "LIVE",
        )

    with c3:
        st.metric(
            "📅 UCAS Dates",
            "LIVE",
        )

    with c4:
        st.metric(
            "💼 Experience",
            "LIVE",
        )

    st.stop()


# ============================================================
# DATA
# ============================================================

items = st.session_state.get(
    "items",
    [],
)

if not isinstance(
    items,
    list,
):
    items = []

# Safety validation
items = [
    item
    for item in items
    if isinstance(
        item,
        dict,
    )
]


# ============================================================
# SECTION COUNTS
# ============================================================

apprenticeships = category_items(
    items,
    "🎓 Apprenticeship",
)

open_days = category_items(
    items,
    "🏫 University Open Day",
)

key_dates = category_items(
    items,
    "📅 Key Date",
)

work_experience = category_items(
    items,
    "💼 Work Experience",
)

resources = category_items(
    items,
    "⭐ Resource",
)

priorities = get_priorities(
    items
)


# ============================================================
# DASHBOARD
# ============================================================

c1, c2, c3, c4, c5 = st.columns(5)

with c1:

    st.metric(
        "🎓 Apprenticeships",
        len(apprenticeships),
    )

with c2:

    st.metric(
        "🏫 Open Days",
        len(open_days),
    )

with c3:

    st.metric(
        "📅 Key Dates",
        len(key_dates),
    )

with c4:

    st.metric(
        "💼 Experience",
        len(work_experience),
    )

with c5:

    st.metric(
        "🚨 Priorities",
        len(priorities),
    )


if st.session_state.last_refresh:

    st.caption(
        "Last refreshed: "
        + st.session_state.last_refresh
    )


# ============================================================
# TABS
# ============================================================

tabs = st.tabs(
    [
        "🚨 Priorities",
        "🎓 Apprenticeships",
        "🏫 Open Days",
        "📅 Key Dates",
        "💼 Work Experience",
        "⭐ Resources",
        "📢 Teams Bulletin",
        "➕ Add Opportunity",
        "⚙️ Sources",
    ]
)


# ============================================================
# PRIORITIES
# ============================================================

with tabs[0]:

    st.header(
        "🚨 This week's priorities"
    )

    if not priorities:

        st.success(
            "No urgent opportunities detected."
        )

    else:

        for index, item in enumerate(
            priorities
        ):

            display_card(
                item,
                f"priority_{index}",
            )


# ============================================================
# APPRENTICESHIPS
# ============================================================

with tabs[1]:

    st.header(
        "🎓 Live Apprenticeships"
    )

    st.write(
        "These are actual vacancies found on "
        "the Government Find an Apprenticeship "
        "service, plus selected specialist "
        "higher/degree apprenticeship resources."
    )

    search = st.text_input(
        "🔎 Search apprenticeships",
        placeholder=(
            "Try: engineering, finance, "
            "digital, accounting, AI..."
        ),
    )

    filtered = search_items(
        apprenticeships,
        search,
    )

    if not filtered:

        st.warning(
            "No apprenticeships matched."
        )

    else:

        for index, item in enumerate(
            filtered
        ):

            display_card(
                item,
                f"apprenticeship_{index}",
            )


# ============================================================
# OPEN DAYS
# ============================================================

with tabs[2]:

    st.header(
        "🏫 Upcoming University Open Days"
    )

    st.info(
        "Only events with a date found on the "
        "UCAS event listing are included. "
        "Use the original UCAS link before "
        "publishing if you want a final manual check."
    )

    search = st.text_input(
        "🔎 Search open days",
        placeholder=(
            "Try: Manchester, engineering, "
            "Oxford, Liverpool..."
        ),
        key="open_day_search",
    )

    filtered = search_items(
        open_days,
        search,
    )

    if not filtered:

        st.warning(
            "No upcoming open days were found "
            "within your selected look-ahead period."
        )

    else:

        for index, item in enumerate(
            filtered
        ):

            display_card(
                item,
                f"open_day_{index}",
            )


# ============================================================
# KEY DATES
# ============================================================

with tabs[3]:

    st.header(
        "📅 UCAS Key Dates"
    )

    for index, item in enumerate(
        key_dates
    ):

        display_card(
            item,
            f"date_{index}",
            removable=False,
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

        display_card(
            item,
            f"work_{index}",
        )


# ============================================================
# RESOURCES
# ============================================================

with tabs[5]:

    st.header(
        "⭐ Progression Resources"
    )

    for index, item in enumerate(
        resources
    ):

        display_card(
            item,
            f"resource_{index}",
        )


# ============================================================
# TEAMS BULLETIN
# ============================================================

with tabs[6]:

    st.header(
        "📢 Microsoft Teams Bulletin"
    )

    bulletin = build_bulletin(
        items
    )

    st.text_area(
        "Copy this into Microsoft Teams",
        bulletin,
        height=900,
    )

    st.download_button(
        "📥 Download bulletin",
        bulletin,
        file_name=(
            "KS5_Progression_Bulletin_"
            + TODAY.isoformat()
            + ".txt"
        ),
        mime="text/plain",
        use_container_width=True,
    )

    st.success(
        "The bulletin is generated from the "
        "opportunities currently loaded into the hub."
    )


# ============================================================
# ADD COLLEGE OPPORTUNITY
# ============================================================

with tabs[7]:

    st.header(
        "➕ Add your own opportunity"
    )

    st.write(
        "Add a college event, employer visit, "
        "work experience placement, university "
        "session or other progression opportunity."
    )

    with st.form(
        "custom_opportunity"
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
            ],
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
            "Original link"
        )

        submitted = st.form_submit_button(
            "➕ Add to bulletin",
            type="primary",
        )

        if submitted:

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
                    event_date=event_date,
                    closing_date=closing_date,
                    location=location,
                    url=url,
                    source="College added",
                    tags=[
                        "College opportunity"
                    ],
                    priority=400,
                    verified=False,
                )

                st.session_state.custom_items.append(
                    new_item
                )

                st.session_state.items.append(
                    new_item
                )

                st.success(
                    "Added."
                )

                st.rerun()


# ============================================================
# SOURCES
# ============================================================

with tabs[8]:

    st.header(
        "⚙️ Sources & verification"
    )

    st.write(
        "The hub deliberately keeps original "
        "sources visible. This is important because "
        "opportunities and dates can change."
    )

    sources = [

        (
            "🎓 Government Find an Apprenticeship",
            GOV_APPRENTICESHIP_URL,
            "Live Government apprenticeship vacancies.",
        ),

        (
            "🏫 UCAS Open Days & Events",
            UCAS_EVENTS_URL,
            "University open days and higher education events.",
        ),

        (
            "📅 UCAS Key Dates",
            UCAS_DEADLINES_URL,
            "Official 2027 application dates.",
        ),

        (
            "⭐ Amazing Apprenticeships",
            AMAZING_LISTING_URL,
            "Higher and degree apprenticeship listing.",
        ),

        (
            "💼 Forage",
            FORAGE_URL,
            "Virtual work experience / job simulations.",
        ),

        (
            "💼 National Careers Service",
            NCS_URL,
            "Career profiles and progression information.",
        ),

    ]

    for name, url, description in sources:

        st.subheader(name)

        st.write(description)

        st.link_button(
            "Open source",
            url,
        )

        st.divider()


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "🎓 KS5 Progression Hub • "
    "Live-source progression bulletin • "
    f"{format_date(TODAY)}"
)
