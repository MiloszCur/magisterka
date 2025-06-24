from sklearn.feature_extraction.text import TfidfVectorizer
from pdfminer.high_level import extract_text
import spacy

# Wydobycie tekstu z pliku PDF
file_path = "ustawa.pdf"
text = extract_text(file_path)

# Ładowanie modelu języka polskiego w spaCy
nlp = spacy.load("pl_core_news_sm")

# Przetwarzanie tekstu z PDF przez spaCy (tokenizacja, usuwanie stop-słów)
doc = nlp(text)
tokens = [token.text for token in doc if not token.is_stop and not token.is_punct and len(token.text.strip()) > 1]

# Tworzenie ciągu tekstowego do analizy TF-IDF
processed_text = ' '.join(tokens)

# Inicjalizacja TF-IDF (usunięcie max_features=10, aby nie ograniczać liczby cech)
tfidf_vectorizer = TfidfVectorizer(stop_words=None)

# Dopasowanie TF-IDF do przetworzonego tekstu
tfidf_matrix = tfidf_vectorizer.fit_transform([processed_text])
feature_names = tfidf_vectorizer.get_feature_names_out()

# Wyodrębnienie słów kluczowych na podstawie wartości TF-IDF
tfidf_scores = tfidf_matrix.toarray()[0]
keywords_tfidf = [(feature_names[i], tfidf_scores[i]) for i in range(len(tfidf_scores))]

# Sortowanie wyników według wartości TF-IDF (malejąco)
keywords_tfidf_sorted = sorted(keywords_tfidf, key=lambda x: x[1], reverse=True)

# Wyświetlanie wyników
print("Słowa kluczowe (TF-IDF):", [kw[0] for kw in keywords_tfidf_sorted])
