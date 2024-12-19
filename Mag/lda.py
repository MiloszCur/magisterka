from pdfminer.high_level import extract_text
from gensim import corpora
from gensim.models import LdaModel
import spacy
import re

# Wydobycie tekstu z pliku PDF
file_path = "ustawa.pdf"
text = extract_text(file_path)

# Preprocessing tekstu (tokenizacja, usuwanie stop-słów, lematyzacja)
nlp = spacy.load("pl_core_news_sm")
doc = nlp(text)

# Usuwanie znaków specjalnych i cyfr
tokens = [
    token.lemma_ for token in doc 
    if not token.is_stop and not token.is_punct and not token.is_digit
    and len(token.text.strip()) > 2  # Pomija bardzo krótkie tokeny
]

# Usuwanie dodatkowych spacji i znaków nowych linii
tokens = [re.sub(r'\s+', '', token) for token in tokens]

# Przygotowanie słownika i korpusu
dictionary = corpora.Dictionary([tokens])
corpus = [dictionary.doc2bow(tokens)]

# Tworzenie modelu LDA
lda_model = LdaModel(corpus, num_topics=1, id2word=dictionary, passes=15)

# Wyciąganie słów kluczowych (tematów)
topics = lda_model.print_topics(num_words=10)
for topic in topics:
    print(topic)
