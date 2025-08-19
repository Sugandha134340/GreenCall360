import re
import pandas as pd
import PyPDF2

# ---------- Step 1: Extract text from PDF ----------
def extract_text_from_pdf(pdf_path):
    text = ""
    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text += page.extract_text() + "\n"
    return text

# ---------- Step 2: Build dataset from regex ----------
def build_dataset(text):
    # Regex pattern for sections like "Crop: Tomato", "Fertilizers: ..." etc.
    pattern = re.compile(
        r"Crop\s*:\s*(?P<crop>[A-Za-z ]+)\s*"
        r"(?:Soil\s*:\s*(?P<soil>.*?))?\s*"
        r"(?:Fertilizers\s*:\s*(?P<fertilizers>.*?))?\s*"
        r"(?:Pesticides\s*:\s*(?P<pesticides>.*?))?\s*"
        r"(?:Steps\s*:\s*(?P<steps>.*?))?(?=\nCrop:|\Z)",
        re.DOTALL | re.IGNORECASE,
    )

    rows = []
    for match in pattern.finditer(text):
        rows.append({
            "crop": match.group("crop"),
            "soil": match.group("soil"),
            "fertilizers": match.group("fertilizers"),
            "pesticides": match.group("pesticides"),
            "steps": match.group("steps"),
        })
    
    df = pd.DataFrame(rows)
    return df

# ---------- Step 3: Build Knowledge Base ----------
def build_kb(df):
    kb = []
    for _, row in df.iterrows():
        crop = row["crop"]
        if pd.notna(row["soil"]):
            kb.append({"query": f"What soil is best for {crop}?", "answer": row["soil"]})
        if pd.notna(row["fertilizers"]):
            kb.append({"query": f"What fertilizers are recommended for {crop}?", "answer": row["fertilizers"]})
        if pd.notna(row["pesticides"]):
            kb.append({"query": f"What pesticides are suggested for {crop}?", "answer": row["pesticides"]})
        if pd.notna(row["steps"]):
            kb.append({"query": f"What are the steps to grow {crop} organically?", "answer": row["steps"]})
    return pd.DataFrame(kb)

# ---------- Step 4: Run pipeline ----------
if __name__ == "__main__":
    pdf_path = r"C:\Users\sugan\OneDrive\Documents\Capitol-One-Hackathon\Organic_framing_guide.pdf"
    text = extract_text_from_pdf(pdf_path)

    dataset = build_dataset(text)
    dataset.to_csv("organic_crops_dataset.csv", index=False)
    print("✅ Dataset saved as organic_crops_dataset.csv")

    kb = build_kb(dataset)
    kb.to_csv("organic_crops_kb.csv", index=False)
    print("✅ Knowledge Base saved as organic_crops_kb.csv")
