"""
Supervea FAQ bot — caching demo.

Every number on screen is measured from the response, never estimated.
Cost uses published provider rates from .env and states them on screen.

Run:  streamlit run app.py
"""

import hashlib
import json
import os
import random
import statistics
import time
import urllib.error
import urllib.request

import streamlit as st

from kb import KNOWLEDGE_BASE, REPEATED, PARAPHRASED, NOVEL

# ---------------------------------------------------------------- config

def load_env(path=".env"):
    if not os.path.exists(path):
        return
    for line in open(path):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


load_env()

BASE_URL = os.environ.get("SUPERVEA_BASE_URL", "https://api.supervea.com").rstrip("/")
PROXY = f"{BASE_URL}/api/v1/proxy"
SUPERVEA_KEY = os.environ.get("SUPERVEA_KEY", "")
PROVIDER_KEY = os.environ.get("PROVIDER_KEY", "")
MODEL = os.environ.get("MODEL", "claude-sonnet-4-6")
MOCK_KEY = "mock-openai-key-for-pilot-testing"
IS_MOCK = PROVIDER_KEY == MOCK_KEY or not PROVIDER_KEY

PRICE_IN = float(os.environ.get("PRICE_IN_PER_MTOK") or 0)
PRICE_OUT = float(os.environ.get("PRICE_OUT_PER_MTOK") or 0)
PRICE_SOURCE = os.environ.get("PRICE_SOURCE", "not set")

IS_ANTHROPIC = MODEL.startswith("claude")
THROTTLE_S = 2.1  # free tier is 30 req/min

st.set_page_config(page_title="Supervea FAQ bot", layout="wide")

st.markdown("""
<style>
  .block-container { padding-top: 2rem; max-width: 1500px; }
  [data-testid="stMetricValue"] { font-size: 3.4rem; font-weight: 650; color: #14264F; }
  [data-testid="stMetricLabel"] { font-size: 1.05rem; color: #5A6480; }
  .row { display:flex; gap:14px; align-items:center; padding:11px 16px;
         margin-bottom:7px; border-radius:7px; font-size:1.05rem; }
  .hit  { background:#E7F6EC; border-left:6px solid #1B8A4B; }
  .miss { background:#F1F3F7; border-left:6px solid #8A94AC; }
  .err  { background:#FDECEC; border-left:6px solid #C0392B; }
  .tag  { font-weight:700; width:62px; }
  .q    { flex:1; color:#14264F; }
  .ms   { font-variant-numeric:tabular-nums; color:#5A6480; width:110px; text-align:right; }
  .note { color:#5A6480; font-size:0.92rem; }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------------- credentials
# Locally, keys come from .env. On a shared deployment there is no .env, so
# each person enters their own in a dialog on first load. Held in this browser
# session only — never written to disk, never shared between users.
DEFAULT_MODEL = MODEL


@st.dialog("Connect your keys")
def key_dialog():
    st.write("Your keys stay in this browser session. They are not stored on "
             "the server and are not visible to other users.")
    sv = st.text_input("Supervea key", type="password", placeholder="sv_free_...")
    pk = st.text_input("Provider key", type="password",
                       placeholder="Anthropic or OpenAI key")
    md = st.text_input("Model", value=DEFAULT_MODEL)

    st.caption("Provider rates, USD per million tokens. Defaults are the "
               "published Claude Sonnet 4.6 rates — change these if you are "
               "using a different model.")
    c1, c2 = st.columns(2)
    pin = c1.number_input("Input $/M", value=3.00, min_value=0.0, step=0.5, format="%.2f")
    pout = c2.number_input("Output $/M", value=15.00, min_value=0.0, step=0.5, format="%.2f")

    if st.button("Start", type="primary", use_container_width=True):
        if sv.strip() and pk.strip():
            st.session_state.sv = sv.strip()
            st.session_state.pk = pk.strip()
            st.session_state.model = md.strip() or DEFAULT_MODEL
            st.session_state.pin = pin
            st.session_state.pout = pout
            st.session_state.psrc = f"entered by user: ${pin:.2f}/M in, ${pout:.2f}/M out"
            st.rerun()
        else:
            st.error("Both keys are required.")


if not (SUPERVEA_KEY and PROVIDER_KEY):
    SUPERVEA_KEY = st.session_state.get("sv", "")
    PROVIDER_KEY = st.session_state.get("pk", "")
    MODEL = st.session_state.get("model", DEFAULT_MODEL)

if not (PRICE_IN or PRICE_OUT):
    PRICE_IN = st.session_state.get("pin", 0.0)
    PRICE_OUT = st.session_state.get("pout", 0.0)
    PRICE_SOURCE = st.session_state.get("psrc", PRICE_SOURCE)

IS_MOCK = PROVIDER_KEY == MOCK_KEY or not PROVIDER_KEY
HAVE_KEYS = bool(SUPERVEA_KEY and PROVIDER_KEY)

# ---------------------------------------------------------------- state

def fresh_run():
    st.session_state.salt = f"{time.time_ns():x}"
    st.session_state.calls = []      # measured call records
    st.session_state.baseline = {}   # cache_key -> usage+cost of its original MISS
    st.session_state.last = None     # most recent answer, kept across reruns


if "salt" not in st.session_state:
    fresh_run()


def system_prompt():
    # Salt gives each filming take a fresh cache namespace, so a warm cache from
    # an earlier rehearsal can't fake a high hit rate. Constant within a run.
    return f"{KNOWLEDGE_BASE}\n\n[build {st.session_state.salt}]"


def cache_key(question):
    return hashlib.sha256((system_prompt() + "\x00" + question).encode()).hexdigest()

# ---------------------------------------------------------------- transport

def _post(url, body, headers, timeout=120):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST")
    for k, v in headers.items():
        req.add_header(k, v)
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw, hdrs, status = r.read().decode("utf-8", "replace"), \
                {k.lower(): v for k, v in r.headers.items()}, r.status
    except urllib.error.HTTPError as e:
        raw, hdrs, status = e.read().decode("utf-8", "replace"), \
            {k.lower(): v for k, v in e.headers.items()}, e.code
    except Exception as e:
        return None, {}, {"error": str(e)}, (time.perf_counter() - t0) * 1000
    wall = (time.perf_counter() - t0) * 1000
    try:
        return status, hdrs, json.loads(raw), wall
    except json.JSONDecodeError:
        return status, hdrs, {"error": raw[:300]}, wall


def _usage(body):
    u = body.get("usage") or {}
    return (u.get("prompt_tokens") or u.get("input_tokens") or 0,
            u.get("completion_tokens") or u.get("output_tokens") or 0)


def _content(body):
    try:
        if "choices" in body:
            return body["choices"][0]["message"]["content"]
        if "content" in body and isinstance(body["content"], list):
            return "".join(b.get("text", "") for b in body["content"])
    except Exception:
        pass
    return ""


def call_gateway(question):
    status, hdrs, body, wall = _post(
        f"{PROXY}/chat/completions",
        {"model": MODEL, "max_tokens": 400,
         "messages": [{"role": "system", "content": system_prompt()},
                      {"role": "user", "content": question}]},
        {"Content-Type": "application/json",
         "Authorization": f"Bearer {PROVIDER_KEY}",
         "X-Supervea-Key": SUPERVEA_KEY},
    )
    tin, tout = _usage(body)
    return {
        "route": "gateway", "question": question, "status": status, "wall_ms": wall,
        "cache": hdrs.get("x-supervea-cache"),
        "gw_ms": hdrs.get("x-supervea-latency-ms"),
        "hdr_tokens_saved": hdrs.get("x-supervea-tokens-saved"),
        "tin": tin, "tout": tout, "content": _content(body),
        "error": body.get("error") if status != 200 else None,
    }


def call_direct(question):
    """Straight to the provider. Never used as a silent fallback."""
    if IS_ANTHROPIC:
        status, _, body, wall = _post(
            "https://api.anthropic.com/v1/messages",
            {"model": MODEL, "max_tokens": 400, "system": system_prompt(),
             "messages": [{"role": "user", "content": question}]},
            {"Content-Type": "application/json", "x-api-key": PROVIDER_KEY,
             "anthropic-version": "2023-06-01"},
        )
    else:
        status, _, body, wall = _post(
            "https://api.openai.com/v1/chat/completions",
            {"model": MODEL, "max_tokens": 400,
             "messages": [{"role": "system", "content": system_prompt()},
                          {"role": "user", "content": question}]},
            {"Content-Type": "application/json",
             "Authorization": f"Bearer {PROVIDER_KEY}"},
        )
    tin, tout = _usage(body)
    return {"route": "direct", "question": question, "status": status, "wall_ms": wall,
            "cache": None, "gw_ms": None, "hdr_tokens_saved": None,
            "tin": tin, "tout": tout, "content": _content(body),
            "error": body.get("error") if status != 200 else None}

# ---------------------------------------------------------------- accounting

def cost_of(tin, tout):
    if not (PRICE_IN or PRICE_OUT):
        return None
    return (tin / 1e6) * PRICE_IN + (tout / 1e6) * PRICE_OUT


def record(rec, question):
    """Attribute savings. On a HIT you avoided what that same request cost when
    it missed, so we bill the saving against the recorded MISS for that key."""
    k = cache_key(question)
    rec["saved_tokens"] = 0
    rec["saved_usd"] = 0.0
    rec["imputed"] = False

    if rec["cache"] == "MISS" and rec["status"] == 200 and (rec["tin"] or rec["tout"]):
        st.session_state.baseline[k] = (rec["tin"], rec["tout"])

    if rec["cache"] == "HIT":
        if rec["tin"] or rec["tout"]:
            tin, tout = rec["tin"], rec["tout"]
        elif k in st.session_state.baseline:
            tin, tout = st.session_state.baseline[k]
            rec["imputed"] = True
        else:
            tin = tout = 0
        rec["saved_tokens"] = tin + tout
        rec["saved_usd"] = cost_of(tin, tout) or 0.0

    st.session_state.calls.append(rec)


def ask(question, route):
    rec = call_gateway(question) if route == "gateway" else call_direct(question)
    record(rec, question)
    return rec

# ---------------------------------------------------------------- ui

st.title("Supervea FAQ bot")

if not HAVE_KEYS:
    key_dialog()
    st.stop()

if IS_MOCK:
    st.error("**SANDBOX MODE — do not film.** PROVIDER_KEY is the mock key, so "
             "responses are synthetic and every latency and cost figure below is "
             "meaningless. Set a real PROVIDER_KEY before recording.")
if not (PRICE_IN or PRICE_OUT):
    st.warning("Pricing is not set, so cost saved will stay at $0.00. "
               "Fill PRICE_IN_PER_MTOK and PRICE_OUT_PER_MTOK in .env.")

with st.sidebar:
    st.subheader("Run")
    route = st.radio("Send requests", ["gateway", "direct"],
                     format_func=lambda r: "Via Supervea gateway" if r == "gateway"
                     else "Direct to provider")
    st.caption(f"Model `{MODEL}` · {'sandbox' if IS_MOCK else 'live provider key'}")
    st.caption(f"Rates: {PRICE_SOURCE}")
    st.caption(f"Cache namespace `{st.session_state.salt}`")
    if st.button("Start a fresh run", use_container_width=True):
        fresh_run()
        st.rerun()

    st.divider()
    st.subheader("Simulated traffic")
    n = st.slider("Requests", 6, 40, 20)
    mix = st.select_slider("Repeat weighting", ["light", "typical", "heavy"], "typical")
    weights = {"light": (0.35, 0.15, 0.50),
               "typical": (0.50, 0.20, 0.30),
               "heavy": (0.65, 0.20, 0.15)}[mix]
    st.caption(f"{weights[0]:.0%} repeats · {weights[1]:.0%} paraphrases · "
               f"{weights[2]:.0%} novel — quoted with every hit rate")
    go = st.button("Run traffic", type="primary", use_container_width=True)

calls = st.session_state.calls
gw = [c for c in calls if c["route"] == "gateway" and c["status"] == 200]
hits = [c for c in gw if c["cache"] == "HIT"]
misses = [c for c in gw if c["cache"] == "MISS"]
direct = [c for c in calls if c["route"] == "direct" and c["status"] == 200]

m = st.columns(5)
m[0].metric("Cache hit rate", f"{len(hits)/len(gw)*100:.0f}%" if gw else "—",
            help="Measured this run only")
m[1].metric("Tokens saved", f"{sum(c['saved_tokens'] for c in calls):,}")
m[2].metric("Cost saved", f"${sum(c['saved_usd'] for c in calls):.4f}")
m[3].metric("Median hit", f"{statistics.median([c['wall_ms'] for c in hits]):.0f} ms"
            if hits else "—")
m[4].metric("Median miss", f"{statistics.median([c['wall_ms'] for c in misses]):.0f} ms"
            if misses else "—")

if direct:
    st.caption(f"Direct-to-provider median for comparison: "
               f"{statistics.median([c['wall_ms'] for c in direct]):.0f} ms "
               f"over {len(direct)} calls.")
if any(c.get("imputed") for c in calls):
    st.caption("Some hits returned no usage block; their token counts are taken "
               "from the original miss for that same request.")

st.divider()
left, right = st.columns([1, 1])

with left:
    st.subheader("Ask a question")
    q = st.text_input("Question", placeholder="What are the free tier limits?",
                      label_visibility="collapsed")
    if st.button("Send") and q.strip():
        with st.spinner("Calling…"):
            st.session_state.last = ask(q.strip(), route)
        st.rerun()

    last = st.session_state.get("last")
    if last:
        if last["error"]:
            st.error(f"HTTP {last['status']}: {json.dumps(last['error'])[:300]}")
        else:
            badge = last["cache"] or "DIRECT"
            colour = "#1B8A4B" if badge == "HIT" else "#5A6480"
            st.markdown(
                f"<div style='margin:14px 0 10px'>"
                f"<span style='background:{colour};color:#fff;padding:4px 12px;"
                f"border-radius:5px;font-weight:700;font-size:0.95rem'>{badge}</span>"
                f"<span style='margin-left:12px;color:#5A6480;font-size:1.05rem;"
                f"font-variant-numeric:tabular-nums'>{last['wall_ms']:.0f} ms</span>"
                f"</div>", unsafe_allow_html=True)
            st.markdown(
                f"<div style='font-size:1.25rem;line-height:1.65;color:#14264F'>"
                f"{last['content']}</div>", unsafe_allow_html=True)

with right:
    st.subheader("Request stream")
    stream = st.empty()

    def render():
        rows = []
        for c in reversed(st.session_state.calls[-14:]):
            if c["status"] != 200:
                cls, tag = "err", f"HTTP {c['status']}"
            elif c["cache"] == "HIT":
                cls, tag = "hit", "HIT"
            elif c["cache"] == "MISS":
                cls, tag = "miss", "MISS"
            else:
                cls, tag = "miss", "DIRECT"
            rows.append(
                f"<div class='row {cls}'><div class='tag'>{tag}</div>"
                f"<div class='q'>{c['question'][:74]}</div>"
                f"<div class='ms'>{c['wall_ms']:.0f} ms</div></div>")
        stream.markdown("".join(rows) or
                        "<div class='note'>No requests yet.</div>",
                        unsafe_allow_html=True)

    render()

if go:
    pool = (random.choices(REPEATED, k=round(n * weights[0]))
            + random.choices(PARAPHRASED, k=round(n * weights[1]))
            + random.sample(NOVEL, min(len(NOVEL), round(n * weights[2]))))
    random.shuffle(pool)
    bar = st.progress(0.0)
    for i, question in enumerate(pool):
        ask(question, route)
        render()
        bar.progress((i + 1) / len(pool))
        time.sleep(THROTTLE_S)
    bar.empty()
    st.rerun()

with st.expander("Measurement notes"):
    st.markdown(f"""
Latency is client wall-clock, which includes the network hop to the gateway;
`x-supervea-latency-ms` is recorded separately and is always lower. On a miss
the gateway is **slower** than going direct, because of that extra hop.

Cost saved is computed here from the measured `usage` block and the published
rates in `.env` ({PRICE_SOURCE}) — not from the gateway's own
`estimated_cost_saved_usd`, whose basis isn't documented. Compare the two
before filming; if they disagree, say which one you're showing.

Each request is stateless: fixed system prompt plus one user message, no
conversation history. Carrying history would make every cache key unique after
the first turn and nothing would ever hit.

Hit rate depends entirely on the traffic mix, which is why the mix is shown
alongside it. Model `{MODEL}`, {len(st.session_state.calls)} calls this run.
""")