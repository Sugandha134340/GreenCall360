import os
import re
import math
import argparse
import pandas as pd
from collections import Counter
from deep_translator import GoogleTranslator

try:
    from langdetect import detect
except ImportError:
    detect = None  # fallback if langdetect not installed

KB_PATH = os.environ.get("AGRI_KB_PATH", "organic_farming_curated_kb.csv")

# ----------------------------
# Text utils
# ----------------------------
_PUNCT_RE = re.compile(r"[^\w\s]", flags=re.UNICODE)

STOPWORDS = {
    "the","a","an","and","or","for","to","of","in","on","at","is","are","was","were","be","by","with","do","does",
    "how","what","when","which","who","whom","whose","why","where","can","could","should","would"
}

def normalize(text: str) -> str:
    if not isinstance(text, str):
        text = "" if text is None else str(text)
    text = text.lower().strip()
    text = _PUNCT_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text)
    return text

def tokenize(text: str):
    return [t for t in normalize(text).split() if t and t not in STOPWORDS]

# ----------------------------
# Tiny TF-IDF-like retriever
# ----------------------------
class TinyTfidfKB:
    def __init__(self, df: pd.DataFrame, query_col="query", answer_col="answer"):
        self.query_col = query_col
        self.answer_col = answer_col
        self.df = df.fillna("")
        self.N = len(self.df)
        self.docs_tokens = []
        self.df_count = Counter()
        for q in self.df[self.query_col].tolist():
            toks = tokenize(q)
            self.docs_tokens.append(Counter(toks))
            for term in set(toks):
                self.df_count[term] += 1
        # precompute idf
        self.idf = {term: math.log((1 + self.N) / (1 + dfv)) + 1.0 for term, dfv in self.df_count.items()}

    def score(self, query: str, doc_tok_counts: Counter) -> float:
        q_toks = tokenize(query)
        if not q_toks:
            return 0.0
        q_tf = Counter(q_toks)

        def weight_vec(tf_counter):
            return {t: tf_counter[t] * self.idf.get(t, 0.0) for t in tf_counter}

        vq = weight_vec(q_tf)
        vd = weight_vec(doc_tok_counts)

        dot = sum(vq[t] * vd.get(t, 0.0) for t in vq)

        def norm(v):
            return math.sqrt(sum(w*w for w in v.values())) or 1e-9

        return dot / (norm(vq) * norm(vd))

    def search(self, query: str, top_k=3):
        scores = [(self.score(query, doc_tok_counts), i)
                  for i, doc_tok_counts in enumerate(self.docs_tokens)]
        scores.sort(reverse=True)
        return scores[:top_k]

    def best_answer(self, query: str, min_score=0.12):
        if self.N == 0:
            return None, 0.0, None
        top = self.search(query, top_k=1)
        if not top:
            return None, 0.0, None
        score, idx = top[0]
        if score < min_score:
            return None, score, idx
        ans = str(self.df.iloc[idx][self.answer_col]).strip()
        q = str(self.df.iloc[idx][self.query_col]).strip()
        return ans, score, q

# ----------------------------
# Translator wrapper
# ----------------------------
class EnTeTranslator:
    def __init__(self):
        self.en2te = GoogleTranslator(source="en", target="te")
        self.te2en = GoogleTranslator(source="te", target="en")

    def detect(self, text: str) -> str:
        # 1. Telugu Unicode characters
        if re.search(r"[\u0C00-\u0C7F]", text):
            return "te"
        # 2. Langdetect (if installed)
        if detect:
            try:
                if detect(text) == "te":
                    return "te"
            except:
                pass
        # 3. Heuristics for romanized Telugu
        roman_te_keywords = ["ela", "cheyali", "panta", "vithanam", "raalu", "neellu"]
        for w in roman_te_keywords:
            if w in text.lower():
                return "te"
        return "en"

    def te_to_en(self, text: str) -> str:
        try:
            return self.te2en.translate(text)
        except Exception:
            return text

    def en_to_te(self, text: str) -> str:
        try:
            return self.en2te.translate(text)
        except Exception:
            return text

    def auto_translate_to_en(self, text: str) -> tuple[str, str]:
        lang = self.detect(text)
        if lang == "te":
            return self.te_to_en(text), "te"
        return text, "en"

    def translate_from_en(self, text_en: str, target_lang: str) -> str:
        if target_lang == "te":
            return self.en_to_te(text_en)
        return text_en

# ----------------------------
# Agri Agent
# ----------------------------
class AgriAgent:
    def __init__(self, kb_path=KB_PATH):
        if not os.path.exists(kb_path):
            raise FileNotFoundError(f"KB CSV not found at: {kb_path}")
        df = pd.read_csv(kb_path)
        needed = {"query", "answer"}
        if not needed.issubset(set(df.columns)):
            raise ValueError(f"KB needs columns {needed}, got {list(df.columns)}")
        self.kb = TinyTfidfKB(df=df, query_col="query", answer_col="answer")
        self.tx = EnTeTranslator()

    def answer(self, user_text: str) -> dict:
        query_en, input_lang = self.tx.auto_translate_to_en(user_text)
        ans_en, score, kb_q = self.kb.best_answer(query_en)

        if not ans_en:
            ans_en = "Sorry, I couldn’t find a precise match. Please consult with a local agricultural officer."

        answer_out = self.tx.translate_from_en(ans_en, input_lang)

        return {
            "input_lang": input_lang,
            "output_lang": input_lang,  # final output language
            "query_en": query_en,
            "kb_match_query": kb_q,
            "kb_score": round(score, 4) if isinstance(score, float) else 0.0,
            "answer_en": ans_en,
            "answer_out": answer_out
        }

# ----------------------------
# CLI
# ----------------------------
def main():
    ap = argparse.ArgumentParser(description="Agri Assistant (EN↔TE) over CSV KB.")
    ap.add_argument("--kb", default=KB_PATH, help="Path to organic_crops_kb_clean.csv")
    ap.add_argument("--text", required=False, help="User question (English or Telugu)")
    args = ap.parse_args()

    agent = AgriAgent(kb_path=args.kb)

    if args.text:
        out = agent.answer(args.text)
        print(out["answer_out"])
    else:
        print("Agri Assistant (type 'quit' to exit)")
        while True:
            try:
                q = input("> ")
            except (EOFError, KeyboardInterrupt):
                break
            if q.strip().lower() in {"quit", "exit"}:
                break
            out = agent.answer(q)
            print(out["answer_out"])

if __name__ == "__main__":
    main()
