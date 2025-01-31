from rake_nltk import Rake
from pdfminer.high_level import extract_text

# Wydobycie tekstu z pliku PDF
file_path = "ustawa.pdf"
text = extract_text(file_path)

# Inicjalizacja RAKE
rake = Rake()

# Przetwarzanie tekstu w celu wyodrębnienia słów kluczowych
rake.extract_keywords_from_text(text)

# Wyciąganie słów kluczowych
keywords_rake = rake.get_ranked_phrases()

print("Słowa kluczowe (RAKE):", keywords_rake[:10])  # Pokazuje 10 najważniejszych fraz
