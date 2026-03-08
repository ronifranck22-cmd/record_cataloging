# 🎵 Record Cataloging

Dashboard for browsing and managing the family vinyl record collection.

## Tech Stack

- **Streamlit** — Python web dashboard
- **Firebase Firestore** — Document database
- **Pandas** — Data manipulation

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Firebase

1. Go to [Firebase Console](https://console.firebase.google.com/) → project `record-cataloging-4c0ed`.
2. Enable **Firestore** (Native mode).
3. Go to **Project Settings → Service Accounts → Generate New Private Key**.
4. Copy the fields from the downloaded JSON into `.streamlit/secrets.toml` (see the template).

### 3. Import existing data (one-time)

Populate `records.csv` with your data, then:

```bash
streamlit run import_csv.py
```

### 4. Run the dashboard

```bash
streamlit run app.py
```

## Deployment (Free)

1. Push to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io) and connect this repo.
3. Set `app.py` as the main file.
4. Add `.streamlit/secrets.toml` contents in the Streamlit Cloud Secrets settings.
5. Deploy — you'll get a public URL.

## CSV Schema

| Column | Type | Example |
|---|---|---|
| `box_number` | int | `1` |
| `artist` | str | `אביב גפן` |
| `name` | str | `זה רק אור הירח` |
| `version` | str | `סינגל` |
| `estimated_price_ils` | int | `200` |
