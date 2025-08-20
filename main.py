import streamlit as st
import pandas as pd
from PIL import Image
import os

# Ordner für Bilder erstellen, falls er nicht existiert
os.makedirs("bilder", exist_ok=True)

# Daten laden oder neue Datei erstellen
try:
    df = pd.read_csv("blumen.csv")
except FileNotFoundError:
    df = pd.DataFrame(columns=["deutsch", "latein", "familie", "bild_path"])
    df.to_csv("blumen.csv", index=False)

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
                "bild_path": [bild_path]
            })
            df = pd.concat([df, new_entry], ignore_index=True)
            df.to_csv("blumen.csv", index=False)
            st.success(f"Blume {deutsch} hinzugefügt!")

# --- Blumen lernen ---
st.header("Blumen lernen")
if not df.empty:
    flower = df.sample(1).iloc[0]  # zufällige Blume
    st.image(flower["bild_path"], width=300)
    
    deutsch_guess = st.text_input("Deutscher Name")
    latein_guess = st.text_input("Lateinischer Name")
    familie_guess = st.text_input("Familie")
    
    if st.button("Antwort prüfen"):
        correct_deutsch = deutsch_guess.strip().lower() == flower["deutsch"].lower()
        correct_latein = latein_guess.strip().lower() == flower["latein"].lower()
        correct_familie = familie_guess.strip().lower() == flower["familie"].lower()
        
        if correct_deutsch and correct_latein and correct_familie:
            st.success("Alles korrekt! 🎉")
        else:
            st.error("Nicht ganz richtig 😅")
            st.info(f"Richtige Antwort: {flower['deutsch']} / {flower['latein']} / {flower['familie']}")
else:
    st.info("Noch keine Blumen vorhanden. Bitte zuerst welche hinzufügen.")

