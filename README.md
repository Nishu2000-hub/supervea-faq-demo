# Deploying the FAQ bot for team testing

Each tester supplies their own Supervea key and provider key in the sidebar.
Nothing is stored server-side and keys are not shared between sessions.

## Deploy

```bash
cd app_demo
git init
git add app.py kb.py requirements.txt .gitignore README.md
git commit -m "Supervea FAQ bot caching demo"
git remote add origin https://github.com/<you>/supervea-faq-demo.git
git push -u origin main
```

Check `git status` before committing and confirm `.env` is not listed. If it
was ever committed, rotate both keys — git history keeps it.

Then at share.streamlit.io: sign in with GitHub, New app, pick the repo, main
file `app.py`, Deploy. It builds in a couple of minutes and gives you a URL.

Send the URL plus: enter your own two keys in the sidebar, ask a question
twice, watch the second one come back as a HIT.

## Two things to tell people

**The URL is publicly reachable.** Streamlit Community Cloud apps aren't
private on the free tier. Anyone with the link can open it, though they'd need
their own keys to do anything. Share it internally, don't post it publicly.

**The app server sees the provider key in transit.** That's inherent to a
hosted app. For internal testing it's fine; if anyone is uneasy, they can clone
the repo and run it locally with a `.env` instead.

## Why deploying is useful beyond convenience

Streamlit Cloud runs in the US. Sahil's numbers were measured from India, where
roughly 1 second of every call is network round-trip — visible in the hits,
which land at ~1,050 ms wall-clock against ~85 ms self-reported by the gateway.

Running the same app from a US host isolates that. If gateway misses still take
~19 seconds from Streamlit Cloud, the latency is in the gateway. If they drop
to ~4 seconds, a large part of it was the round-trip from India. Either answer
is worth having, and it costs one test run.

## Local install

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # fill in keys and pricing
streamlit run app.py
```