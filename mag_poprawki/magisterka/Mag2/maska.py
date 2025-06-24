from transformers import pipeline

# Użycie pipeline do analizy tekstu (np. wykrywanie słów kluczowych na podstawie maski)
pipe = pipeline("fill-mask", model="sdadas/polish-roberta-large-v2")

# Przykładowy tekst z maską
text = "Ustawa o <mask> publicznych."

# Wypełnianie maski
result = pipe(text)

# Wyświetlanie wyników
print("Wyniki pipeline (wypełnianie maski):", result)
