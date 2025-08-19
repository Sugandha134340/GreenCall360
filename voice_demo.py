import os
import tempfile
import speech_recognition as sr
from gtts import gTTS
import playsound
from agri_assistant import AgriAgent

# Init models
recognizer = sr.Recognizer()
agent = AgriAgent("organic_farming_curated_kb.csv")

import pygame

def speak(text, lang="en"):
    """Convert text to speech using gTTS + play with pygame."""
    try:
        from gtts import gTTS
        import tempfile

        # Generate MP3
        tts = gTTS(text=text, lang=lang, slow=False)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
            tts.save(f.name)
            audio_file = f.name

        # Init pygame mixer and play
        pygame.mixer.init()
        pygame.mixer.music.load(audio_file)
        pygame.mixer.music.play()

        # Wait until playback finishes
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)

    except Exception as e:
        print("[TTS Error]", e)

def listen_and_answer():
    with sr.Microphone() as source:
        print("🎤 Speak your question (Telugu or English)...")
        recognizer.adjust_for_ambient_noise(source, duration=1)
        audio = recognizer.listen(source)

        try:
            # Try Telugu first
            user_text = recognizer.recognize_google(audio, language="te-IN")
            detected_lang = "te"
        except sr.UnknownValueError:
            try:
                # Fallback to English
                user_text = recognizer.recognize_google(audio, language="en-IN")
                detected_lang = "en"
            except sr.UnknownValueError:
                print("❌ Could not understand audio.")
                return
            except sr.RequestError as e:
                print(f"⚠️ Google STT request failed (English): {e}")
                return
        except sr.RequestError as e:
            print(f"⚠️ Google STT request failed (Telugu): {e}")
            return

        print("You said:", user_text)

        # Pass to AgriAgent
        out = agent.answer(user_text)
        print("Assistant:", out["answer_out"])
        print("DEBUG Detected Lang:", out["output_lang"])

        # ✅ Speak response in correct language
        speak(out["answer_out"], lang=out["output_lang"])


if __name__ == "__main__":
    while True:
        listen_and_answer()
