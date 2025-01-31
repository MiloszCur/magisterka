import nltk
from rake_nltk import Rake
from pdfminer.high_level import extract_text
import spacy

# Wydobycie tekstu z pliku PDF
file_path = "ustawa.pdf"
text = extract_text(file_path)

# Inicjalizacja RAKE
rake = Rake()

# Przetwarzanie tekstu w celu wyodrębnienia fraz kluczowych
rake.extract_keywords_from_text(text)

# Wyciąganie fraz kluczowych
keywords_rake = rake.get_ranked_phrases()

# Ładowanie modelu spaCy dla języka polskiego
nlp = spacy.load("pl_core_news_sm")

# Przechodzimy przez wszystkie frazy
keyword_words = []
for phrase in keywords_rake:
    # Przetwarzanie każdej frazy przez spaCy (tokenizacja i analiza)
    doc = nlp(phrase)
    
    # Dodanie tylko rzeczowników i czasowników do listy słów kluczowych
    for token in doc:
        if token.pos_ in ("NOUN", "VERB"):  # Można dodać więcej części mowy, np. ADJ (przymiotniki)
            keyword_words.append(token.text)

# Wyświetlanie pojedynczych słów kluczowych
print("Słowa kluczowe (RAKE - pojedyncze słowa):", set(keyword_words))  # set() aby usunąć duplikaty
