import streamlit as st
import pandas as pd
from PIL import Image
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

# --- Hilfsfunktion für GitHub ---
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
    if "bild_path" in df.columns and "bild_url" not in df.columns:
        df = df.rename(columns={"bild_path": "bild_url"})
        df.to_csv("blumen.csv", index=False)
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
    with open("antworten.csv", "r") as f:
        csv_content = f.read()
    try:
        contents = repo.get_contents("antworten.csv", ref=BRANCH)
        repo.update_file(contents.path, "update antworten.csv", csv_content, contents.sha, branch=BRANCH)
    except:
        repo.create_file("antworten.csv", "init antworten.csv", csv_content, branch=BRANCH)

# --- Streamlit App ---
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

if not df.empty:
    # Prüfen, ob alle Blumen mindestens 3-mal korrekt beantwortet wurden
    if (df["correct_count"] >= 3).all():
        st.balloons()
        st.success("🎉 Du hast alle Blumen mindestens 3-mal korrekt beantwortet! Super! 🎉")
    else:
        # Gewichtetes Sampling nur für Blumen mit <3 richtigen Antworten
        to_learn = df[df["correct_count"] < 3]
        weights = 3 - to_learn["correct_count"]
        flower = to_learn.sample(weights=weights).iloc[0]

        st.image(flower["bild_url"], width=300)

        deutsch_guess = st.text_input("Deutscher Name", key="deutsch")
        latein_guess = st.text_input("Lateinischer Name", key="latein")
        familie_guess = st.text_input("Familie", key="familie")

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
                df.loc[df["deutsch"] == flower["deutsch"], "correct_count"] += 1
            else:
                st.error("Nicht ganz richtig 😅")
                # Tipps generieren
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

            # Fortschritt sichern
            df.to_csv("blumen.csv", index=False)
            save_file_to_github("blumen.csv", "blumen.csv", "update progress")

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
