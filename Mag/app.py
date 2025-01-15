from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
import os
from pdfminer.high_level import extract_text
from gensim import corpora
from gensim.models import LdaModel
import spacy
import re

app = Flask(__name__)

# Folder do przechowywania przesłanych plików
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = os.path.abspath(UPLOAD_FOLDER)  # Użyj absolutnej ścieżki

# Dozwolone rozszerzenia plików
ALLOWED_EXTENSIONS = {'pdf'}

# Funkcja sprawdzająca rozszerzenie pliku
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Strona główna
@app.route('/')
def home():
    return render_template('index.html', filename=request.args.get('filename'))

# Strona do obsługi wgrywania pliku PDF
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file part'
    file = request.files['file']
    
    # Jeśli nie wybrano pliku
    if file.filename == '':
        return 'No selected file'
    
    if file and allowed_file(file.filename):
        filename = file.filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        print(f"Uploading file: {filename} to {filepath}")  # Logi do konsoli
        file.save(filepath)
        return redirect(url_for('home', filename=filename))
    else:
        return 'Invalid file format'

# Strona do wyświetlania pliku PDF (do użytku z <iframe>)
@app.route('/uploads/<filename>')
def display_pdf(filename):
    print(f"Serving PDF: {filename}")  # Logi do konsoli
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except FileNotFoundError:
        return 'File not found', 404

# Nowa funkcja do znajdowania słów kluczowych
@app.route('/find_words', methods=['POST'])
def find_words():
    filename = request.form.get('filename')
    if not filename:
        return jsonify({'error': 'No file selected'}), 400
    
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404

    # Ekstrakcja tekstu z PDF
    text = extract_text(filepath)

    # Preprocessing tekstu
    nlp = spacy.load("pl_core_news_sm")
    doc = nlp(text)
    tokens = [
        token.lemma_ for token in doc 
        if not token.is_stop and not token.is_punct and not token.is_digit
        and len(token.text.strip()) > 2  # Pomija bardzo krótkie tokeny
    ]
    tokens = [re.sub(r'\s+', '', token) for token in tokens]

    # Tworzenie słownika i korpusu
    dictionary = corpora.Dictionary([tokens])
    corpus = [dictionary.doc2bow(tokens)]

    # Tworzenie modelu LDA
    lda_model = LdaModel(corpus, num_topics=1, id2word=dictionary, passes=15)

    # Wyciąganie słów kluczowych (tematów)
    topics = lda_model.print_topics(num_words=15)  # Ograniczenie do 10 słów
    highlighted_phrases = []

    # Przygotowanie fraz z podkreśleniami
    for topic_id, topic in topics:
        words = topic.split('+')
        for word_weight in words:
            word = word_weight.split('*')[-1].strip().strip('"')
            highlighted_phrases.append(f"<mark>{word}</mark>")

    # Zwrócenie tylko pierwszych 10 słów kluczowych
    highlighted_phrases = highlighted_phrases[:15]

    return jsonify({'highlighted_phrases': highlighted_phrases})

if __name__ == '__main__':
    # Tworzymy folder do przechowywania plików, jeśli nie istnieje
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    
    app.run(debug=True)
