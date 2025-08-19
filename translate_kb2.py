from deep_translator import GoogleTranslator

def translate_en_to_te(text: str) -> str:
    return GoogleTranslator(source='en', target='te').translate(text)

def translate_te_to_en(text: str) -> str:
    return GoogleTranslator(source='te', target='en').translate(text)


# -------------------------
# ✅ Test Case
# -------------------------
english_text = "Apply neem oil to control pests in tomato crops."
telugu_text = "టమోటా పంటలో పురుగులను నియంత్రించడానికి వేప నూనె రాయండి."

print("English → Telugu:", translate_en_to_te(english_text))
print("Telugu → English:", translate_te_to_en(telugu_text))
