import streamlit as st
import pandas as pd
import os
import base64
from github import Github

# --- GitHub-Infos ---
GITHUB_USER = "DST81"
REPO_NAME = "blumen_app"
BRANCH = "main"

token = st.secrets['github_token']
g = Github(token)
repo = g.get_user(GITHUB_USER).get_repo(REPO_NAME)

# --- Hilfsfunktionen für GitHub ---
def save_file_to_github(local_path, repo_path, message="update file", binary=False):
    with open(local_path, "rb") as f:
        content = f.read()
    try:
        contents = repo.get_contents(repo_path, ref=BRANCH)
        if binary:
            repo.update_file(repo_path, message, base64.b64encode(content).decode(), contents.sha, branch=BRANCH)
        else:
            repo.update_file(repo_path, message, content.decode("utf-8"), contents.sha, branch=BRANCH)
    except:
        if binary:
            repo.create_file(repo_path, message, base64.b64encode(content).decode(), branch=BRANCH)
        else:
            repo.create_file(repo_path, message, content.decode("utf-8"), branch=BRANCH)

# --- Ordner für Bilder ---
os.makedirs("bilder", exist_ok=True)

# --- CSVs laden oder anlegen ---
try:
    df = pd.read_csv("blumen.csv")
except FileNotFoundError:
    df = pd.DataFrame(columns=["deutsch", "latein", "familie", "bild_url", "correct_count"])
    df.to_csv("blumen.csv", index=False)
    save_file_to_github("blumen.csv", "blumen.csv", "init blumen.csv")

try:
    answers_df = pd.read_csv("antworten.csv")
except FileNotFoundError:
    answers_df = pd.DataFrame(columns=[
        "deutsch", "latein", "familie",
        "deutsch_guess", "latein_guess", "familie_guess", "korrekt"
    ])
    answers_df.to_csv("antworten.csv", index=False)
    save_file_to_github("antworten.csv", "antworten.csv", "init antworten.csv")

# --- Session-State für aktuelle Blume ---
if "current_flower_idx" not in st.session_state:
    st.session_state.current_flower_idx = None

st.title("Blumen lernen 🌸")

# --- Neue Blume hinzufügen ---
st.header("Neue Blume hinzufügen")
with st.form("add_flower"):
    deutsch = st.text_input("Deutscher Name")
    latein = st.text_input("Lateinischer Name")
    familie = st.text_input("Familie")
    bild = st.file_uploader("Bild hochladen", type=["png", "jpg", "jpeg"])
    submitted = st.form_submit_button("Hinzufügen")
    if submitted:
        if bild:
            bild_path = f"bilder/{bild.name}"
            with open(bild_path, "wb") as f:
                f.write(bild.getbuffer())
            with open(bild_path, "rb") as f:
                content = f.read()
            repo_path = f"bilder/{bild.name}"
            try:
                contents = repo.get_contents(repo_path, ref=BRANCH)
                repo.update_file(contents.path, f"Update {bild.name}", content, contents.sha, branch=BRANCH)
            except:
                repo.create_file(repo_path, f"Add {bild.name}", content, branch=BRANCH)

            bild_url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{REPO_NAME}/{BRANCH}/{repo_path}"

            new_entry = pd.DataFrame({
                "deutsch": [deutsch],
                "latein": [latein],
                "familie": [familie],
                "bild_url": [bild_url],
                "correct_count": [0]
            })
            df = pd.concat([df, new_entry], ignore_index=True)
            df.to_csv("blumen.csv", index=False)
            save_file_to_github("blumen.csv", "blumen.csv", "update blume hinzugefügt")

            st.success(f"Blume {deutsch} hinzugefügt!")

# --- Blumen lernen ---
st.header("Blumen lernen")

def get_next_flower():
    to_learn = df[df["correct_count"] < 3]
    if len(to_learn) == 0:
        return None
    weights = 3 - to_learn["correct_count"]
    return to_learn.sample(weights=weights).iloc[0]

    # --- Direkt nach Wahl der nächsten Blume ---
    if st.session_state.current_flower_idx is None or st.session_state.get("last_correct", False):
        next_flower = get_next_flower()  # z.B. df.sample(weights=...)
        if next_flower is not None:
            st.session_state.current_flower_idx = next_flower.name
            st.session_state.last_correct = False
            # Textfelder zurücksetzen
            st.session_state.deutsch_input = ""
            st.session_state.latein_input = ""
            st.session_state.familie_input = ""
    

    else:
        st.session_state.current_flower_idx = None

if st.session_state.current_flower_idx is None:
    st.balloons()
    st.success("🎉 Du hast alle Blumen mindestens 3-mal korrekt beantwortet! Super! 🎉")
else:
    flower = df.loc[st.session_state.current_flower_idx]
    st.image(flower["bild_url"], width=300)

    deutsch_guess = st.text_input("Deutscher Name", key="deutsch_input")
    latein_guess = st.text_input("Lateinischer Name", key="latein_input")
    familie_guess = st.text_input("Familie", key="familie_input")

    if st.button("Antwort prüfen"):
        correct_deutsch = deutsch_guess.strip().lower() == flower["deutsch"].lower()
        correct_latein = latein_guess.strip().lower() == flower["latein"].lower()
        correct_familie = familie_guess.strip().lower() == flower["familie"].lower()

        korrekt = correct_deutsch and correct_latein and correct_familie

        # Antworten speichern
        answers_df = pd.concat([answers_df, pd.DataFrame({
            "deutsch": [flower["deutsch"]],
            "latein": [flower["latein"]],
            "familie": [flower["familie"]],
            "deutsch_guess": [deutsch_guess],
            "latein_guess": [latein_guess],
            "familie_guess": [familie_guess],
            "korrekt": [korrekt]
        })], ignore_index=True)
        answers_df.to_csv("antworten.csv", index=False)
        save_file_to_github("antworten.csv", "antworten.csv", "update antworten")

        if korrekt:
            st.success("Alles korrekt! 🎉")
            df.loc[flower.name, "correct_count"] += 1
            df.to_csv("blumen.csv", index=False)
            save_file_to_github("blumen.csv", "blumen.csv", "update progress")
            st.session_state.last_correct = True  # nächste Blume wird automatisch geladen
        else:
            st.error("Nicht ganz richtig 😅")
            tips = []
            if not correct_deutsch:
                tip = "".join([c if i < len(deutsch_guess) and deutsch_guess[i].lower() == c.lower() else c for i, c in enumerate(flower["deutsch"])])
                tips.append(f"Deutscher Name Tipp: {tip}")
            if not correct_latein:
                tip = "".join([c if i < len(latein_guess) and latein_guess[i].lower() == c.lower() else c for i, c in enumerate(flower["latein"])])
                tips.append(f"Lateinischer Name Tipp: {tip}")
            if not correct_familie:
                tip = "".join([c if i < len(familie_guess) and familie_guess[i].lower() == c.lower() else c for i, c in enumerate(flower["familie"])])
                tips.append(f"Familie Tipp: {tip}")
            for tip in tips:
                st.info(tip)

# --- Bisherige Antworten anzeigen ---
st.subheader("Deine bisherigen Antworten")
for idx, row in answers_df.iterrows():
    deutsch_color = "green" if row["deutsch_guess"].strip().lower() == row["deutsch"].lower() else "red"
    latein_color = "green" if row["latein_guess"].strip().lower() == row["latein"].lower() else "red"
    familie_color = "green" if row["familie_guess"].strip().lower() == row["familie"].lower() else "red"

    st.markdown(
        f"**Deutscher Name:** <span style='color:{deutsch_color}'>{row['deutsch_guess']}</span> | "
        f"**Lateinischer Name:** <span style='color:{latein_color}'>{row['latein_guess']}</span> | "
        f"**Familie:** <span style='color:{familie_color}'>{row['familie_guess']}</span>",
        unsafe_allow_html=True
    )

# --- Lernfortschritt ---
st.header("Lernfortschritt")
if not df.empty:
    total = len(df)
    learned = len(df[df["correct_count"] >= 3])
    st.write(f"Von {total} Blumen sind {learned} Blumen gut gelernt (≥3 richtige Antworten).")
    st.dataframe(df[["deutsch", "correct_count"]])
# Button zum Neu-Lernen / Zurücksetzen
if st.button("Neu starten"):
    # Alle Fortschritte zurücksetzen
    df["correct_count"] = 0
    df.to_csv("blumen.csv", index=False)
    save_file_to_github("blumen.csv", "blumen.csv", "reset progress")
    
    # Session-States zurücksetzen
    st.session_state.current_flower_idx = None
    st.session_state.last_correct = False
    st.session_state.deutsch_input = ""
    st.session_state.latein_input = ""
    st.session_state.familie_input = ""
    st.experimental_rerun()  # neu laden, damit alles geleert wird
