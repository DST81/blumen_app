import streamlit as st
import pandas as pd
import os
import base64
from github import Github


st.set_page_config(
    page_title="Blumen lernen 🌸",
    page_icon="🌸",  # oder ein lokales Bild wie "icon.png"
    layout="centered"
)
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
for key in ["current_flower_idx", "last_correct", "deutsch_input", "latein_input", "familie_input"]:
    if key not in st.session_state:
        st.session_state[key] = None if "idx" in key else False if key=="last_correct" else ""

st.title("Blumen lernen 🌸")

# --- Neue Blume hinzufügen ---
with st.expander("Neue Blume hinzufügen"):

    with st.form("add_flower"):
        deutsch = st.text_input("Deutscher Name")
        latein = st.text_input("Lateinischer Name")
        familie = st.text_input("Familie")
        bild = st.file_uploader("Bild hochladen", type=["png", "jpg", "jpeg"])
        submitted = st.form_submit_button("Hinzufügen")
        if submitted:
            if bild:
                bild_path = f"bilder/{bild.name}"
                # Lokal speichern
                with open(bild_path, "wb") as f:
                    f.write(bild.getbuffer())
    
                # GitHub Upload (Base64 kodiert)
                with open(bild_path, "rb") as f:
                    content = f.read()
                repo_path = f"bilder/{bild.name}"
                try:
                    contents = repo.get_contents(repo_path, ref=BRANCH)
                    repo.update_file(
                        path=contents.path,
                        message=f"Update {bild.name}",
                        content=base64.b64encode(content).decode(),
                        sha=contents.sha,
                        branch=BRANCH
                    )
                except:
                    repo.create_file(
                        path=repo_path,
                        message=f"Add {bild.name}",
                        content=base64.b64encode(content).decode(),
                        branch=BRANCH
                    )
    
                # URL korrekt URL-encoded
                from urllib.parse import quote
                bild_url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{REPO_NAME}/{BRANCH}/bilder/{quote(bild.name)}"
    
                # Neue Blume in DataFrame speichern
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
def get_next_flower():
    to_learn = df[df["correct_count"] < 3]
    if to_learn.empty:
        return None
    weights = 3 - to_learn["correct_count"]
    return to_learn.sample(weights=weights).iloc[0]
# --- Blumen lernen ---
with st.expander("Blumen lernen"):



    # --- Auswahl der nächsten Blume ---
    if st.session_state.current_flower_idx is None or st.session_state.last_correct:
        next_flower = get_next_flower()
        if next_flower is not None:
            st.session_state.current_flower_idx = next_flower.name
            st.session_state.last_correct = False
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
    
        # --- Antwort prüfen ---
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
        
            # Nur die letzten 5 Antworten behalten
            answers_df = answers_df.tail(5)
        
            answers_df.to_csv("antworten.csv", index=False)
            save_file_to_github("antworten.csv", "antworten.csv", "update antworten")
        
            if korrekt:
                st.success("Alles korrekt! 🎉")
                df.loc[flower.name, "correct_count"] += 1
                df.to_csv("blumen.csv", index=False)
                save_file_to_github("blumen.csv", "blumen.csv", "update progress")
                st.session_state.last_correct = True
                st.rerun()  # sofort neue Blume laden
            else:
                st.error("Nicht ganz richtig 😅")
                
                # Tipps generieren
                import random
                tips = []
            
                for col, guess, correct in [
                    ("deutsch", deutsch_guess, correct_deutsch),
                    ("latein", latein_guess, correct_latein),
                    ("familie", familie_guess, correct_familie)
                ]:
                    if not correct:
                        # Sicherstellen, dass guess und solution Strings sind
                        guess = str(guess) if pd.notna(guess) else ""
                        solution = str(flower[col]) if pd.notna(flower[col]) else ""
                        
                        # Richtige Buchstaben beibehalten
                        revealed = "".join(
                            g if i < len(guess) and g.lower() == solution[i].lower() else "_"
                            for i, g in enumerate(solution)
                        )
                        
                        # Einen weiteren zufälligen Buchstaben aufdecken
                        hidden_indices = [i for i, c in enumerate(revealed) if c == "_"]
                        if hidden_indices:
                            i = random.choice(hidden_indices)
                            revealed = revealed[:i] + solution[i] + revealed[i+1:]
                        
                        tips.append(f"{col.capitalize()} Tipp: {revealed}")
                
                # Alle Tipps zusammen anzeigen
                if tips:
                    st.info("\n".join(tips))
    

# --- Lernfortschritt ---
with st.expander("Lernfortschritt"):
    if not df.empty:
        total = len(df)
        learned = len(df[df["correct_count"] >= 3])
        st.write(f"Von {total} Blumen sind {learned} Blumen gut gelernt (≥3 richtige Antworten).")
        st.dataframe(df[["deutsch", "correct_count"]])

if st.button("Neu starten"):
    df["correct_count"] = 0
    df.to_csv("blumen.csv", index=False)
    save_file_to_github("blumen.csv", "blumen.csv", "reset progress")

    answers_df = pd.DataFrame(columns=[
        "deutsch", "latein", "familie",
        "deutsch_guess", "latein_guess", "familie_guess", "korrekt"
    ])
    answers_df.to_csv("antworten.csv", index=False)
    save_file_to_github("antworten.csv", "antworten.csv", "reset answers")
    
    for key in ["current_flower_idx", "last_correct", "deutsch_input", "latein_input", "familie_input"]:
        st.session_state[key] = None if "idx" in key else False if key=="last_correct" else ""
    
    st.rerun()
