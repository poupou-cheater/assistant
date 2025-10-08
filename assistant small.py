import os
import sys
import json
import time
import re
import pyaudio
import tkinter as tk
from tkinter import messagebox
from vosk import Model, KaldiRecognizer
from num2words import num2words
from datetime import datetime, timedelta
from pycaw.pycaw import AudioUtilities
import webbrowser
import keyboard
import random
import io
import threading

# === Capture de la sortie console ===
class ConsoleCapture:
    def __init__(self):
        self.buffer = io.StringIO()
        self.original_stdout = sys.stdout

    def write(self, text):
        self.buffer.write(text)
        if self.original_stdout is not None:
            self.original_stdout.write(text)

    def flush(self):
        if self.original_stdout is not None:
            self.original_stdout.flush()

    def get_content(self):
        return self.buffer.getvalue()

console_capture = ConsoleCapture()
sys.stdout = console_capture

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

os.environ['VOSK_LOG_LEVEL'] = '0'

MODEL_PATH = resource_path("vosk-model-small-fr-0.22")
SAMPLE_RATE = 16000
CHUNK = 512

if not os.path.exists(MODEL_PATH):
    print("❌ Erreur : dossier modèle introuvable.")
    print("👉 Place 'vosk-model-small-fr-0.22' dans ce répertoire.")
    exit(1)

def show_commands_popup():
    commands = [
        "• « quelle heure » → donne l'heure",
        "• « quel jour » / « quel mois » / « date complète »",
        "• « silence » → mute/démute Discord",
        "• « ouvre youtube »",
        "• « ouvre tiktok »",
        "• « pause », « suivant », « précédent »",
        "• « augmente/diminue le volume »",
        "• « dans combien de temps ce mois » → ex: 1 mois et 4 jours",
        "• « agenda ajouter [truc] dans une heure »",
        "• « donne mon agenda »",
        "• « statut : 10 » ou « statut : devoirs »",
        "• Si statut = nombre : « statut plus 5 », « statut moins 2 »",
        "• « quel est mon statut »",
        "• « affiche les logs »"
    ]
    message = "Voici mes commandes disponibles :\n\n" + "\n".join(commands)
    temp_root = tk.Tk()
    temp_root.withdraw()
    messagebox.showinfo("Commandes Disponibles", message)
    temp_root.destroy()

JOURS_FR = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS_FR = ["janvier", "février", "mars", "avril", "mai", "juin",
           "juillet", "août", "septembre", "octobre", "novembre", "décembre"]

def get_jour_semaine():
    return JOURS_FR[datetime.now().weekday()]

def get_jour_mois():
    return datetime.now().strftime("%d")

def get_mois():
    return MOIS_FR[datetime.now().month - 1]

def get_annee():
    return datetime.now().strftime("%Y")

def get_date_complete():
    return f"{get_jour_semaine()} {get_jour_mois()} {get_mois()} {get_annee()}"

def heure_parlee():
    h = time.localtime().tm_hour
    m = time.localtime().tm_min
    h_text = num2words(h, lang='fr')
    m_text = num2words(m, lang='fr')
    return f"Il est {h_text} heures {m_text}."

def human_like_hotkey():
    keyboard.press('ctrl')
    time.sleep(0.01 + random.uniform(0, 0.01))
    keyboard.press('shift')
    time.sleep(0.01 + random.uniform(0, 0.01))
    keyboard.press('alt')
    time.sleep(0.01 + random.uniform(0, 0.01))
    keyboard.press('m')
    time.sleep(0.05 + random.uniform(0, 0.03))
    keyboard.release('m')
    time.sleep(0.01)
    keyboard.release('alt')
    keyboard.release('shift')
    keyboard.release('ctrl')

def show_logs_popup():
    content = console_capture.get_content()
    if not content.strip():
        content = "Aucun log disponible."
    log_window = tk.Tk()
    log_window.title("Logs")
    log_window.geometry("600x400")
    text_area = tk.Text(log_window, wrap=tk.WORD)
    text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    text_area.insert(tk.END, content)
    text_area.config(state=tk.DISABLED)
    btn_ok = tk.Button(log_window, text="OK", command=log_window.destroy)
    btn_ok.pack(pady=5)
    log_window.mainloop()

def parler(texte):
    try:
        sessions = AudioUtilities.GetAllSessions()
        volumes_backup = {}
        attenuation_ratio = 0.25
        for session in sessions:
            if session.Process and session.Process.name():
                try:
                    vol = session.SimpleAudioVolume
                    if vol:
                        current = vol.GetMasterVolume()
                        volumes_backup[session.Process.name()] = current
                        if session.Process.name().lower() not in ["python.exe", "pythonw.exe"]:
                            vol.SetMasterVolume(current * attenuation_ratio, None)
                except:
                    pass

        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty('voice', 'HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Speech\\Voices\\Tokens\\TTS_MS_FR-FR_HORTENSE_11.0')
        engine.setProperty('rate', 155)
        engine.setProperty('volume', 1.0)
        engine.say(texte)
        engine.runAndWait()
        engine.stop()

        time.sleep(0.05)
        for session in sessions:
            if session.Process and session.Process.name() in volumes_backup:
                try:
                    vol = session.SimpleAudioVolume
                    if vol:
                        original = volumes_backup[session.Process.name()]
                        vol.SetMasterVolume(original, None)
                except:
                    pass
    except Exception as e:
        print(f"⚠️ Erreur synthèse vocale : {e}")

def traiter_commande(texte: str):
    texte = texte.lower().strip()

    # === Commandes média ===
    if "silence" in texte:
        human_like_hotkey()
        return None

    if any(kw in texte for kw in ["pause musique", "met pause", "mets pause", "musique pause", "pause"]):
        keyboard.press_and_release('play/pause media')
        return None

    if any(kw in texte for kw in ["suivant", "piste suivante", "chanson suivante"]):
        keyboard.press_and_release('next track')
        return None

    if any(kw in texte for kw in ["précédent", "piste précédente", "chanson précédente"]):
        keyboard.press_and_release('previous track')
        return None

    if any(kw in texte for kw in ["augmente volume", "monte le volume", "monte volume"]):
        keyboard.press_and_release('volume up')
        return None

    if any(kw in texte for kw in ["diminu volume", "baisse le volume"]):
        keyboard.press_and_release('volume down')
        return None

    # === Date / Heure ===
    if any(kw in texte for kw in ["quelle jour", "quel jour"]):
        return get_jour_semaine()

    if any(kw in texte for kw in ["quelle mois", "quel moi"]):
        return get_mois()

    if any(kw in texte for kw in ["date exacte", "date complète"]):
        return get_date_complete()

    if any(kw in texte for kw in ["le combien", "nul combien", "le comble"]):
        return get_jour_mois()

    if any(kw in texte for kw in ["quelle heure", "il est quelle heure", "heure est-il", "keller", "killer"]):
        return heure_parlee()

    if any(kw in texte for kw in ["ouvre youtube", "ouvre tube", "ouvre youtub"]):
        webbrowser.open("https://www.youtube.com/")
        return None

    if any(kw in texte for kw in ["tic toc compte", "tip top compte", "tic top compte", "tip toc compte", "ouvre tiktok"]):
        webbrowser.open("https://www.tiktok.com/@poupou_fps")
        return None

    if any(kw in texte for kw in ["que fais tu", "que fais-tu", "tes commandes", "liste commandes", "donne tes commandes"]):
        show_commands_popup()
        return None

    if "affiche les logs" in texte:
        show_logs_popup()
        return None

    # === NOUVEAU : "dans combien de temps ce mois" ===
    if "dans combien de temps ce mois" in texte or "combien de temps ce mois" in texte:
        now = datetime.now()
        mois_prochain = now.month + 1
        annee_cible = now.year
        if mois_prochain > 12:
            mois_prochain = 1
            annee_cible += 1
        premier_du_mois_prochain = datetime(annee_cible, mois_prochain, 1)
        delta = premier_du_mois_prochain - now
        total_jours = delta.days
        if total_jours < 0:
            total_jours = 0
        mois = total_jours // 30
        jours = total_jours % 30
        if mois == 0:
            return f"Il reste {jours} jours."
        elif mois == 1:
            return f"Il reste 1 mois et {jours} jours."
        else:
            return f"Il reste {mois} mois et {jours} jours."

    # === NOUVEAU : Agenda avec nombres en lettres ===
    if "agenda ajouter" in texte:
        # Remplacer les nombres en lettres par des chiffres
        remplacements = {
            "une": "1", "deux": "2", "trois": "3", "quatre": "4", "cinq": "5",
            "six": "6", "sept": "7", "huit": "8", "neuf": "9", "dix": "10",
            "onze": "11", "douze": "12", "treize": "13", "quatorze": "14", "quinze": "15",
            "vingt": "20", "trente": "30", "quarante": "40", "cinquante": "50"
        }
        texte_modif = texte
        for mot, chiffre in remplacements.items():
            texte_modif = texte_modif.replace(mot, chiffre)

        match = re.search(r"agenda ajouter\s+(.+?)\s+dans\s+(\d+)\s*(minute|minutes|heure|heures)", texte_modif)
        if match:
            event = match.group(1).strip()
            try:
                duree = int(match.group(2))
                unite = match.group(3)
                maintenant = datetime.now()
                if "minute" in unite:
                    rappel = maintenant + timedelta(minutes=duree)
                else:
                    rappel = maintenant + timedelta(hours=duree)
                with open("agenda.txt", "a", encoding="utf-8") as f:
                    f.write(f"{rappel.isoformat()} | {event}\n")
                return f"Événement ajouté : {event} à {rappel.strftime('%H:%M')}."
            except:
                pass
        return "Dis : agenda ajouter [truc] dans X minutes/heures (ex: une heure, 30 minutes)"

    if "c'est quoi mon agenda" in texte or "donne mon agenda" in texte:
        try:
            with open("agenda.txt", "r", encoding="utf-8") as f:
                lignes = f.readlines()
            if lignes:
                recent = lignes[-5:]
                events = []
                for ligne in recent:
                    parts = ligne.strip().split(" | ", 1)
                    if len(parts) == 2:
                        try:
                            dt = datetime.fromisoformat(parts[0])
                            events.append(f"- {parts[1]} à {dt.strftime('%H:%M')}")
                        except:
                            continue
                if events:
                    return "Voici ton agenda :\n" + "\n".join(events)
            return "Agenda vide."
        except FileNotFoundError:
            return "Agenda vide."

    # === NOUVEAU : Gestion intelligente du statut ===
    if "statut :" in texte:
        nouveau = texte.split("statut :", 1)[1].strip()
        with open("statut.txt", "w", encoding="utf-8") as f:
            f.write(nouveau)
        return f"Statut mis à jour : {nouveau}."

    if "statut plus" in texte or "statut moins" in texte:
        try:
            with open("statut.txt", "r", encoding="utf-8") as f:
                contenu = f.read().strip()
            if contenu.lstrip('-').isdigit():
                valeur = int(contenu)
                match = re.search(r"statut\s+(plus|moins)\s+(\d+)", texte)
                if match:
                    operateur = match.group(1)
                    delta = int(match.group(2))
                    nouvelle_valeur = valeur + delta if operateur == "plus" else valeur - delta
                    with open("statut.txt", "w", encoding="utf-8") as f:
                        f.write(str(nouvelle_valeur))
                    return f"Statut mis à jour : {nouvelle_valeur}."
                else:
                    return "Dis : statut plus 5 ou statut moins 2"
            else:
                return "Le statut n'est pas un nombre. Utilise « statut : [nouveau] » pour le changer."
        except FileNotFoundError:
            return "Aucun statut défini. Commence par « statut : 10 »."

    if "quel est mon statut" in texte:
        try:
            with open("statut.txt", "r", encoding="utf-8") as f:
                stat = f.read().strip()
            return f"Ton statut est : {stat}."
        except FileNotFoundError:
            return "Aucun statut défini."

    return None

# === Chargement du modèle ===
print("🧠 Chargement du modèle français...")
model = Model(MODEL_PATH)
print("✅ Prêt ! Dis une commande.")

# === Micro ===
p = pyaudio.PyAudio()
stream = p.open(
    format=pyaudio.paInt16,
    channels=1,
    rate=SAMPLE_RATE,
    input=True,
    frames_per_buffer=CHUNK
)

rec = KaldiRecognizer(model, SAMPLE_RATE)
rec.SetWords(True)

try:
    print("🎙️ En attente...")
    while True:
        data = stream.read(CHUNK, exception_on_overflow=False)
        if rec.AcceptWaveform(data):
            result = json.loads(rec.Result())
            text = result.get("text", "").strip()
            if text:
                print(f"🗣️ Tu as dit : {text}")
                reponse = traiter_commande(text)
                if reponse:
                    print(f"🔊 {reponse}")
                    while stream.get_read_available() > 0:
                        stream.read(stream.get_read_available(), exception_on_overflow=False)
                    parler(reponse)
                print("🎙️ En attente...")
except KeyboardInterrupt:
    print("\n👋 Arrêt.")
finally:
    stream.stop_stream()
    stream.close()
    p.terminate()