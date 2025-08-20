import streamlit as st
import pandas as pd
from PIL import Image
import os
import random

# Ordner für Bilder erstellen, falls er nicht existiert
os.makedirs("bilder", exist_ok=True)

# Daten laden oder neue Datei erstellen
try:
    df = pd.read_csv("blumen.csv")
except FileNotFoundError:
    df = pd.DataFrame(columns=["deutsch", "latein", "familie", "bild_path", "correct_count"])
    df.to_csv("blumen.csv", index=False)
# CSV für Antworten laden oder erstellen
try:
    answers_df = pd.read_csv("antworten.csv")
except FileNotFoundError:
    answers_df = pd.DataFrame(columns=["deutsch", "latein", "familie", "deutsch_guess", "latein_guess", "familie_guess", "korrekt"])
    answers_df.to_csv("antworten.csv", index=False)

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
            new_entry = pd.DataFrame({
                "deutsch": [deutsch],
                "latein": [latein],
                "familie": [familie],
                "bild_path": [bild_path],
                "correct_count": [0]
            })
            df = pd.concat([df, new_entry], ignore_index=True)
            df.to_csv("blumen.csv", index=False)
            st.success(f"Blume {deutsch} hinzugefügt!")

# --- Blumen lernen ---
st.header("Blumen lernen")
if not df.empty:
    weights = df["correct_count"].max() - df["correct_count"] + 1
    flower = df.sample(weights=weights).iloc[0]
    
    st.image(flower["bild_path"], width=300)
    
    deutsch_guess = st.text_input("Deutscher Name")
    latein_guess = st.text_input("Lateinischer Name")
    familie_guess = st.text_input("Familie")
    
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
        
        if korrekt:
            st.success("Alles korrekt! 🎉")
            df.loc[df["deutsch"] == flower["deutsch"], "correct_count"] += 1
        else:
            st.error("Nicht ganz richtig 😅")
            # Tipps anzeigen
            tips = []
            if not correct_deutsch:
                tips.append(f"Deutscher Name: {flower['deutsch'][0]}... ({len(flower['deutsch'])} Buchstaben)")
            if not correct_latein:
                tips.append(f"Lateinischer Name: {flower['latein'][0]}... ({len(flower['latein'])} Buchstaben)")
            if not correct_familie:
                tips.append(f"Familie: {flower['familie'][0]}... ({len(flower['familie'])} Buchstaben)")
            for tip in tips:
                st.info(tip)
            st.info(f"Richtige Antwort: {flower['deutsch']} / {flower['latein']} / {flower['familie']}")
        
        df.to_csv("blumen.csv", index=False)

# --- Fortschritt anzeigen ---
st.header("Lernfortschritt")
if not df.empty:
    total = len(df)
    learned = len(df[df["correct_count"] >= 3])
    st.write(f"Von {total} Blumen sind {learned} Blumen gut gelernt (≥3 richtige Antworten).")
    st.dataframe(df[["deutsch", "correct_count"]])
