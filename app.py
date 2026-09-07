import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime, date, timedelta
import re, html, hashlib, json, os
from urllib.parse import quote, urlparse

st.set_page_config(page_title="KS5 Progression Hub", page_icon="🎓", layout="wide")

TODAY = date.today()
DATA_FILE = "ks5_progression_custom.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/139 Safari/537.36"}

NORTH_WEST_UNIVERSITIES = {
    "University of Liverpool": ("Liverpool", "liverpool.ac.uk"),
    "Liverpool John Moores University": ("Liverpool", "ljmu.ac.uk"),
    "Liverpool Hope University": ("Liverpool", "hope.ac.uk"),
    "Edge Hill University": ("Ormskirk", "edgehill.ac.uk"),
    "University of Chester": ("Chester", "chester.ac.uk"),
    "University of Manchester": ("Manchester", "manchester.ac.uk"),
    "Manchester Metropolitan University": ("Manchester", "mmu.ac.uk"),
    "University of Salford": ("Salford", "salford.ac.uk"),
    "University of Bolton": ("Bolton", "bolton.ac.uk"),
    "University of Central Lancashire": ("Preston", "uclan.ac.uk"),
    "Lancaster University": ("Lancaster", "lancaster.ac.uk"),
    "University of Cumbria": ("Carlisle", "cumbria.ac.uk"),
    "Liverpool Institute for Performing Arts": ("Liverpool", "lipa.ac.uk"),
}

CAREER_KEYWORDS = {
    "All categories": [],
    "Digital & Technology": ["digital","software","computing","computer","cyber","technology","data","artificial intelligence","programming","developer","it"],
    "Engineering": ["engineering","engineer","mechanical","electrical","civil","aerospace","manufacturing","automotive","design engineer"],
    "Business & Administration": ["business","management","administration","operations","project management","marketing","human resources","hr"],
    "Finance & Legal": ["finance","accounting","accountancy","banking","economics","tax","audit","legal","law"],
    "Health & Science": ["health","healthcare","nursing","science","laboratory","pharmacy","medicine","clinical","biomedical"],
    "Creative & Media": ["creative","media","film","television","design","graphic","journalism","music","performing arts","advertising"],
    "Construction": ["construction","quantity surveying","building","property","architecture","surveying"],
    "Education": ["education","teaching","teacher","early years","childcare"],
}

WEEKLY_ACTIONS = [
    ("🔎 Career Research","Choose one career you're considering and spend 20 minutes finding out what qualifications, skills and routes are needed.","Write down 3 things you have learned."),
    ("📄 Build Your CV","Create your first CV or improve your existing one. Include your education, experience, achievements and skills.","Finish one section of your CV."),
    ("🎓 Compare University Courses","Choose one subject you might study and compare three university courses. Look at entry requirements and modules.","Write down your favourite course and why."),
    ("🎓 Explore Degree Apprenticeships","Find three degree apprenticeship routes linked to careers you are interested in.","Save three opportunities and check their entry requirements."),
    ("💼 Find Work Experience","Search for one work-experience, volunteering or employer opportunity connected to an area you might pursue.","Identify one opportunity you could apply for."),
    ("🧠 Skills Audit","Think about the career or course you want. Identify the skills employers or universities are looking for.","Choose one skill you can develop this term."),
    ("✍️ Personal Statement","Write 100–150 words explaining why you are interested in your chosen subject or career.","Save your first draft."),
    ("🏫 Book an Open Day","Find an upcoming university open day and investigate whether it is worth attending.","Book one open day or add it to your calendar."),
    ("🏢 Research Employers","Choose three employers you might like to work for and investigate their graduate or apprenticeship routes.","Save three employer websites."),
    ("🎤 Interview Practice","Practise answering five common interview questions, using examples from school, college, work or your interests.","Record or write your strongest answer."),
    ("🌐 Improve Your Profile","Review your online professional profile or create one. Make sure your skills, interests and achievements are clear.","Add one achievement or skill."),
    ("📚 Super-Curricular Learning","Spend 30 minutes learning something beyond your normal lessons in a subject you might study.","Record what you learned and one question it raised."),
]

if "items" not in st.session_state: st.session_state["items"] = []
if "custom_items" not in st.session_state: st.session_state["custom_items"] = []
if "removed" not in st.session_state: st.session_state["removed"] = set()
if "last_refresh" not in st.session_state: st.session_state["last_refresh"] = ""
if "source_status" not in st.session_state: st.session_state["source_status"] = {}

def load_custom():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return []

def save_custom(items):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(items, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

if not st.session_state["custom_items"]:
    st.session_state["custom_items"] = load_custom()

def clean(x):
    if not x: return ""
    return re.sub(r"\s+", " ", BeautifulSoup(str(x), "html.parser").get_text(" ", strip=True)).strip()

def get(url, timeout=15):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        return r.text if r.status_code == 200 else ""
    except Exception:
        return ""

def make_id(*parts):
    return hashlib.md5("|".join(map(str, parts)).encode()).hexdigest()[:12]

def parse_date(value):
    if not value: return None
    if isinstance(value, date): return value
    value = str(value).strip()
    for fmt in ("%d %B %Y","%d %b %Y","%A %d %B %Y","%a %d %b %Y","%d/%m/%Y","%d-%m-%Y","%Y-%m-%d","%d %B","%d %b"):
        try:
            d = datetime.strptime(value, fmt).date()
            return d if "%Y" in fmt else d.replace(year=TODAY.year)
        except Exception:
            pass
    return None

def fmt(value):
    d = parse_date(value)
    return d.strftime("%d %b %Y") if d else str(value or "")

def days(value):
    d = parse_date(value)
    return (d - TODAY).days if d else None

MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
DATE_RE = re.compile(rf"\b(\d{{1,2}}\s+(?:{MONTHS})\s+\d{{4}}|\d{{1,2}}\s+(?:{MONTHS})|(?:{MONTHS})\s+\d{{1,2}},\s+\d{{4}})\b", re.I)

def nearest_future_date(text):
    found = []
    for raw in DATE_RE.findall(text or ""):
        d = parse_date(raw)
        if d and d >= TODAY:
            found.append(d)
    return min(found) if found else None

def make_item(title, organisation="", category="", description="", event_date="", closing_date="", location="", url="", source="", tags=None, priority=0, verified=False, level="", featured=False):
    return {
        "id": make_id(title, organisation, event_date, url),
        "title": clean(title), "organisation": clean(organisation), "category": category,
        "description": clean(description), "event_date": clean(event_date), "closing_date": clean(closing_date),
        "location": clean(location), "url": url, "source": source, "tags": tags or [],
        "priority": priority, "verified": verified, "level": level, "featured": featured
    }

def search_web(query, max_results=8):
    url = "https://html.duckduckgo.com/html/?q=" + quote(query)
    text = get(url, 20)
    if not text: return []
    soup = BeautifulSoup(text, "html.parser")
    out = []
    for result in soup.select(".result"):
        a = result.select_one(".result__a")
        s = result.select_one(".result__snippet")
        if not a: continue
        out.append({
            "title": clean(a.get_text(" ", strip=True)),
            "url": a.get("href", ""),
            "description": clean(s.get_text(" ", strip=True) if s else "")
        })
        if len(out) >= max_results: break
    return out

def infer_location(text):
    for place in ["Liverpool","Manchester","Chester","Preston","Lancaster","Salford","Bolton","Carlisle","Blackburn","Warrington","Wirral"]:
        if place.lower() in text.lower(): return place
    return "North West / UK"

def degree_route(text):
    t = text.lower()
    return any(x in t for x in ["degree apprenticeship","degree apprenticeships","level 6 apprenticeship","level 7 apprenticeship","higher apprenticeship","higher apprenticeships","chartered apprenticeship"])

def infer_level(text):
    t = text.lower()
    if "level 7" in t: return "Level 7"
    if "level 6" in t or "degree apprenticeship" in t: return "Level 6"
    if "higher apprenticeship" in t: return "Higher"
    return "Higher / Degree"

def search_open_days(months_ahead):
    items, status = [], {}
    cutoff = TODAY + timedelta(days=months_ahead * 30)
    for uni, (city, domain) in NORTH_WEST_UNIVERSITIES.items():
        results = search_web(f'site:{domain} ("open day" OR "open days") 2026 OR 2027', 5)
        count = 0
        for r in results:
            combined = r["title"] + " " + r["description"]
            if "open day" not in combined.lower(): continue
            d = nearest_future_date(combined)
            if not d or d > cutoff: continue
            diff = (d - TODAY).days
            if diff <= 7: tags, priority = ["🔥 This week","📍 North West"], 900
            elif diff <= 14: tags, priority = ["📅 Coming up","📍 North West"], 700
            else: tags, priority = ["📍 North West"], 450
            items.append(make_item(f"{uni} — Open Day", uni, "🏫 University Open Day",
                "University open day. Check the original university page for booking and course-specific information.",
                fmt(d), "", city, r["url"], f"{uni} official website", tags, priority))
            count += 1
        status[uni] = f"{count} event(s) found" if count else "No dated event found"
    return items, status

def search_degree_apprenticeships(career):
    queries = [
        '"degree apprenticeship" "Liverpool" 2026 OR 2027',
        '"degree apprenticeship" "Manchester" 2026 OR 2027',
        '"degree apprenticeship" "North West" 2026 OR 2027',
        '"higher apprenticeship" "North West" 2026 OR 2027',
        '"level 6 apprenticeship" "Liverpool"',
        '"level 6 apprenticeship" "Manchester"',
        '"level 7 apprenticeship" "North West"',
    ]
    keys = CAREER_KEYWORDS.get(career, [])
    queries += [f'"degree apprenticeship" "{k}" "North West"' for k in keys[:4]]
    items, seen = [], set()
    for q in queries:
        for r in search_web(q, 8):
            combined = r["title"] + " " + r["description"]
            if not degree_route(combined): continue
            key = r["url"] or r["title"]
            if key in seen: continue
            seen.add(key)
            d = nearest_future_date(combined)
            closing = fmt(d) if d else ""
            diff = days(closing)
            if diff is not None and diff <= 3: priority, tags = 1000, ["🔴 Closing soon","🎓 Degree apprenticeship"]
            elif diff is not None and diff <= 7: priority, tags = 950, ["🔥 This week","🎓 Degree apprenticeship"]
            else: priority, tags = 800, ["🎓 Degree apprenticeship"]
            loc = infer_location(combined)
            if loc != "North West / UK": tags.append("📍 North West")
            items.append(make_item(r["title"], urlparse(r["url"]).netloc if r["url"] else "",
                "🎓 Degree Apprenticeship", r["description"], "", closing, loc, r["url"], "Web search",
                tags, priority, False, infer_level(combined)))
    return items

def search_apprenticeships(career):
    queries = ['"apprenticeship vacancy" Liverpool 2026','"apprenticeship vacancy" Manchester 2026','"apprenticeships" "North West" 2026']
    queries += [f'apprenticeship vacancy "{k}" Liverpool Manchester 2026' for k in CAREER_KEYWORDS.get(career, [])[:3]]
    items, seen = [], set()
    for q in queries:
        for r in search_web(q, 6):
            combined = r["title"] + " " + r["description"]
            if "apprenticeship" not in combined.lower() or degree_route(combined): continue
            key = r["url"] or r["title"]
            if key in seen: continue
            seen.add(key)
            d = nearest_future_date(combined)
            closing = fmt(d) if d else ""
            diff = days(closing)
            priority = 850 if diff is not None and diff <= 3 else 750 if diff is not None and diff <= 7 else 350
            items.append(make_item(r["title"], urlparse(r["url"]).netloc if r["url"] else "",
                "🎓 Apprenticeship", r["description"], "", closing, infer_location(combined),
                r["url"], "Web search", ["🎓 Apprenticeship"], priority))
    return items

def career_match(item, career):
    if career == "All categories": return True
    text = " ".join([item.get("title",""),item.get("description",""),item.get("organisation","")]).lower()
    return any(k.lower() in text for k in CAREER_KEYWORDS.get(career, []))

def refresh_all(career, months):
    open_days, status = search_open_days(months)
    degree = search_degree_apprenticeships(career)
    apprentices = search_apprenticeships(career)
    dates = [make_item("UCAS application deadlines", "UCAS", "📅 Key Date",
        "Check the official UCAS timetable for the application cycle and course you are using.",
        "", "", "", "https://www.ucas.com/", "UCAS", ["📅 Key date"], 500, True)]
    custom = [x for x in st.session_state["custom_items"] if x.get("id") not in st.session_state["removed"]]
    all_items = open_days + degree + apprentices + dates + custom
    if career != "All categories":
        all_items = [x for x in all_items if x.get("category") in ["🏫 University Open Day","📅 Key Date"] or x.get("source")=="College added" or career_match(x,career)]
    seen, result = set(), []
    for x in all_items:
        key = (x.get("title","").lower(),x.get("organisation","").lower(),x.get("event_date","").lower(),x.get("url","").lower())
        if key not in seen:
            seen.add(key); result.append(x)
    return result, status

def score(item):
    s = int(item.get("priority",0))
    tags = item.get("tags",[])
    if "🔴 Closing soon" in tags: s += 500
    if "🔥 This week" in tags: s += 350
    if "📍 North West" in tags: s += 250
    if item.get("category") == "🎓 Degree Apprenticeship": s += 300
    if item.get("featured"): s += 450
    if item.get("source") == "College added": s += 400
    c, e = days(item.get("closing_date")), days(item.get("event_date"))
    if c is not None: s += 600 if c <= 3 else 400 if c <= 7 else 150 if c <= 14 else 0
    if e is not None: s += 450 if e <= 7 else 200 if e <= 14 else 0
    return s

def ranked(items):
    return sorted(items, key=score, reverse=True)

def highlights(items):
    r, selected = ranked(items), []
    urgent = [x for x in r if days(x.get("closing_date")) is not None and days(x.get("closing_date")) <= 7]
    for x in urgent:
        if x not in selected: selected.append(x)
        if len(selected) >= 2: break
    for x in r:
        if x.get("category")=="🏫 University Open Day" and days(x.get("event_date")) is not None and days(x.get("event_date")) <= 30 and x not in selected:
            selected.append(x); break
    for x in r:
        if x.get("category")=="🎓 Degree Apprenticeship" and x not in selected:
            selected.append(x); break
    for x in r:
        if x.get("source")=="College added" and x.get("featured") and x not in selected:
            selected.append(x); break
    for x in r:
        if x not in selected:
            selected.append(x)
        if len(selected) >= 5: break
    return selected[:5]

def weekly_action():
    return WEEKLY_ACTIONS[(TODAY.isocalendar().week-1) % len(WEEKLY_ACTIONS)]

def bulletin(items):
    action = weekly_action()
    lines = [
        "🎓 KS5 PROGRESSION — THIS WEEK",
        f"Week commencing {TODAY.strftime('%d %B %Y')}",
        "",
        "💡 YOUR ACTION THIS WEEK",
        action[0], action[1], f"✅ {action[2]}", "",
        "🔥 DON'T MISS", ""
    ]
    for x in highlights(items):
        lines.append("• " + x.get("title","Opportunity"))
        if x.get("organisation"): lines.append("  " + x["organisation"])
        if x.get("event_date"): lines.append("  📅 " + x["event_date"])
        if x.get("closing_date"): lines.append("  ⏰ Closes " + x["closing_date"])
        if x.get("location"): lines.append("  📍 " + x["location"])
        if x.get("url"): lines.append("  🔗 " + x["url"])
        lines.append("")
    lines += ["📚 Want more?","Open the KS5 Progression Hub to explore all current opportunities."]
    return "\n".join(lines)

st.markdown("""
<style>
.hero{padding:2rem;border-radius:18px;margin-bottom:1.5rem;background:linear-gradient(135deg,#172554,#1e3a8a);color:white}
.hero h1{font-size:2.5rem;margin-bottom:.3rem}.hero p{font-size:1.1rem}
.card{padding:1.2rem;border-radius:15px;border:1px solid #e5e7eb;margin-bottom:.8rem;background:white}
.action{padding:1.5rem;border-radius:18px;border:2px solid #dbeafe;background:#eff6ff;margin-bottom:1rem}
.muted{color:#6b7280;font-size:.85rem}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("🎛️ Bulletin Controls")
    career = st.selectbox("Career area", list(CAREER_KEYWORDS))
    months = st.slider("University look-ahead (months)",1,6,2)
    if st.button("🚀 BUILD THIS WEEK'S BULLETIN", type="primary", use_container_width=True):
        with st.spinner("Checking universities, apprenticeships and opportunities..."):
            st.session_state["items"], st.session_state["source_status"] = refresh_all(career,months)
            st.session_state["last_refresh"] = datetime.now().strftime("%d %B %Y at %H:%M")
        st.rerun()

st.markdown(f"""
<div class="hero">
<h1>🎓 KS5 Progression Hub</h1>
<p>What do students actually need to know this week?</p>
<p>📍 North West universities &nbsp;•&nbsp; 🎓 Degree apprenticeships &nbsp;•&nbsp; 💼 Opportunities &nbsp;•&nbsp; 💡 Weekly action</p>
</div>
""", unsafe_allow_html=True)

if not st.session_state["items"]:
    st.info("### Ready to build this week's progression update\n\nClick **BUILD THIS WEEK'S BULLETIN** in the sidebar. The Hub will search for North West university open days, degree/higher apprenticeships, live apprenticeship opportunities, key dates and your own college activities.")
    st.stop()

items = [x for x in st.session_state["items"] if x.get("id") not in st.session_state["removed"]]
top = highlights(items)
open_days = [x for x in items if x.get("category")=="🏫 University Open Day"]
degree = [x for x in items if x.get("category")=="🎓 Degree Apprenticeship"]
apprentices = [x for x in items if x.get("category")=="🎓 Apprenticeship"]
college = [x for x in items if x.get("source")=="College added"]

a,b,c,d,e = st.columns(5)
a.metric("🔥 This week's picks",len(top))
b.metric("🏫 Open days",len(open_days))
c.metric("🎓 Degree apprenticeships",len(degree))
d.metric("💼 Apprenticeships",len(apprentices))
e.metric("🏫 College activities",len(college))
if st.session_state["last_refresh"]: st.caption("Last refreshed: " + st.session_state["last_refresh"])

tabs = st.tabs(["🔥 This Week","💡 Weekly Action","🎓 Degree Apprenticeships","🏫 North West Open Days","💼 Apprenticeships","📅 Key Dates","🏫 College Activities","📢 Teams Bulletin","➕ Add Activity","🔎 All Opportunities","⚙️ Sources"])

def card(x):
    st.markdown(f"""<div class="card">
    <h3>{html.escape(x.get("title",""))}</h3>
    <p><strong>{html.escape(x.get("organisation",""))}</strong></p>
    <p>{html.escape(x.get("description",""))}</p>
    <p>📅 {html.escape(x.get("event_date",""))} &nbsp; ⏰ {html.escape(x.get("closing_date",""))} &nbsp; 📍 {html.escape(x.get("location",""))}</p>
    </div>""", unsafe_allow_html=True)
    if x.get("url"): st.link_button("🔗 View opportunity",x["url"])

with tabs[0]:
    st.header("🔥 This Week")
    st.write("The small number of things students are most likely to need to know now.")
    act=weekly_action()
    st.markdown(f"""<div class="action"><div class="muted">💡 YOUR ACTION THIS WEEK</div><h2>{html.escape(act[0])}</h2><p>{html.escape(act[1])}</p><strong>✅ {html.escape(act[2])}</strong></div>""",unsafe_allow_html=True)
    st.subheader("🔥 Don't miss")
    for x in top: card(x)

with tabs[1]:
    st.header("💡 Weekly Student Action")
    act=weekly_action()
    st.markdown(f"""<div class="action"><h2>{html.escape(act[0])}</h2><p>{html.escape(act[1])}</p><strong>✅ {html.escape(act[2])}</strong></div>""",unsafe_allow_html=True)
    st.write("The action rotates weekly so the bulletin always gives students something practical to do.")

with tabs[2]:
    st.header("🎓 Degree & Higher Apprenticeships")
    q=st.text_input("🔎 Search",key="degq")
    data=[x for x in degree if q.lower() in (x.get("title","")+" "+x.get("description","")+" "+x.get("location","")).lower()]
    for x in ranked(data): card(x)

with tabs[3]:
    st.header("🏫 North West University Open Days")
    q=st.text_input("🔎 Search university",key="uniq")
    data=[x for x in open_days if q.lower() in (x.get("title","")+" "+x.get("organisation","")+" "+x.get("location","")).lower()]
    data.sort(key=lambda x: parse_date(x.get("event_date")) or date.max)
    for x in data: card(x)

with tabs[4]:
    st.header("💼 Apprenticeships")
    q=st.text_input("🔎 Search",key="appq")
    data=[x for x in apprentices if q.lower() in (x.get("title","")+" "+x.get("description","")+" "+x.get("location","")).lower()]
    for x in ranked(data): card(x)

with tabs[5]:
    st.header("📅 Key Dates")
    for x in [x for x in items if x.get("category")=="📅 Key Date"]: card(x)

with tabs[6]:
    st.header("🏫 College Activities")
    for x in college: card(x)
    if not college: st.info("No college activities have been added yet.")

with tabs[7]:
    st.header("📢 Microsoft Teams Bulletin")
    st.success("This is deliberately short: one weekly action plus a maximum of five priority items.")
    text=bulletin(items)
    st.text_area("Copy into Microsoft Teams",text,height=600)
    st.download_button("📥 Download Teams bulletin",text,file_name=f"KS5_Progression_{TODAY.isoformat()}.txt",mime="text/plain",use_container_width=True)

with tabs[8]:
    st.header("➕ Add Your Own Activity or Event")
    with st.form("add"):
        title=st.text_input("Activity / event title",placeholder="e.g. CV Workshop")
        organisation=st.text_input("Organisation",value="College")
        kind=st.selectbox("Type",["🏫 College Activity","💼 Work Experience","🎓 University Session","🎓 Apprenticeship Session","📅 College Deadline","🎤 Employer Talk","📝 Application Workshop","Other"])
        desc=st.text_area("Short description")
        event=st.date_input("Date",TODAY)
        closing=st.date_input("Closing / booking date",TODAY)
        location=st.text_input("Location",placeholder="Careers Centre / Room 12 / Online")
        url=st.text_input("Booking / information link",placeholder="https://...")
        featured=st.checkbox("🔥 Feature this in this week's bulletin",True)
        submit=st.form_submit_button("➕ Add activity",type="primary")
        if submit:
            if not title.strip(): st.error("Please enter a title.")
            else:
                x=make_item(title,organisation,kind,desc,event.strftime("%d %B %Y"),closing.strftime("%d %B %Y"),location,url,"College added",["🏫 College activity"],850,True,"",featured)
                st.session_state["custom_items"].append(x); save_custom(st.session_state["custom_items"])
                st.session_state["items"].append(x); st.success("Activity added."); st.rerun()

with tabs[9]:
    st.header("🔎 All Opportunities")
    q=st.text_input("🔎 Search everything",key="allq")
    data=[x for x in items if q.lower() in (x.get("title","")+" "+x.get("organisation","")+" "+x.get("description","")+" "+x.get("location","")).lower()]
    st.caption(f"{len(data)} results")
    for x in ranked(data): card(x)

with tabs[10]:
    st.header("⚙️ Sources & Coverage")
    st.write("The Hub uses public web search for discovery and links students back to the original source. Always check the original page before applying or booking.")
    st.subheader("🏫 North West university watchlist")
    for uni,(city,domain) in NORTH_WEST_UNIVERSITIES.items(): st.write(f"**{uni}** — {city} — {domain}")
    st.divider()
    for source,status in st.session_state["source_status"].items():
        st.write(f"**{source}:**")
        if isinstance(status,dict):
            for uni,result in status.items(): st.write(f"- {uni}: {result}")
        else: st.write(status)

st.divider()
st.caption(f"🎓 KS5 Progression Hub • Weekly progression intelligence • {TODAY.strftime('%d %B %Y')}")
