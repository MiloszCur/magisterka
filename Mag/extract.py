from keybert import KeyBERT
from pdfminer.high_level import extract_text

# Wydobycie tekstu z pliku PDF
file_path = "ustawa.pdf"
text = extract_text(file_path)

# Inicjalizacja KeyBERT
kw_model = KeyBERT()

# Wyodrębnienie słów kluczowych
keywords_keybert = kw_model.extract_keywords(text, top_n=10)

# Wyświetlanie wyników
print("Słowa kluczowe (KeyBERT):", [kw[0] for kw in keywords_keybert])
