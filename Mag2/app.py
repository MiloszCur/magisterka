from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
import os
import requests
from pdfminer.high_level import extract_text
from gensim import corpora
from gensim.models import LdaModel
import spacy
import re

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = os.path.abspath(UPLOAD_FOLDER)
ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    return render_template('index.html', filename=request.args.get('filename'))

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file part'
    file = request.files['file']
    if file.filename == '':
        return 'No selected file'
    if file and allowed_file(file.filename):
        filename = file.filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        return redirect(url_for('home', filename=filename))
    return 'Invalid file format'

@app.route('/uploads/<filename>')
def display_pdf(filename):
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except FileNotFoundError:
        return 'File not found', 404

@app.route('/find_words', methods=['POST'])
def find_words():
    filename = request.form.get('filename')
    if not filename:
        return jsonify({'error': 'No file selected'}), 400
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    text = extract_text(filepath)
    return jsonify({'highlighted_phrases': extract_keywords(text)})

@app.route('/fetch_acts', methods=['POST'])
def fetch_acts():
    publisher_map = {
        "DziennikUstaw": "DU",
        "MonitorPolski": "MP"
    }
    
    publisher = request.form.get('publisher')
    year = request.form.get('year')
    count = int(request.form.get('count', 10))  # Domyślnie pobieramy 10 aktów, jeśli nie podano

    if publisher not in publisher_map:
        return jsonify({'error': 'Invalid publisher'}), 400
    
    # URL do pobrania listy aktów w danym roku
    api_url = f'http://api.sejm.gov.pl/eli/acts/{publisher_map[publisher]}/{year}'
    
    try:
        response = requests.get(api_url)
        print(f"Fetching URL: {api_url}")  
        print(f"Response Status Code: {response.status_code}")  

        if response.status_code != 200:
            return jsonify({'error': f'Could not fetch acts, status {response.status_code}', 'details': response.text}), 500

        data = response.json()
        acts = data.get("items", [])[:count]  # Pobierz pierwsze `count` aktów

        # Ekstrakcja słów kluczowych dla każdego aktu
        keyword_map = {}
        for act in acts:
            title = act.get('title', '')
            content = act.get('content', '')
            
            # Wyciąganie słów kluczowych z treści lub tytułu
            keywords = extract_keywords(content if content else title)
            act['highlighted_phrases'] = keywords
            
            # Tworzymy URL do pełnej wersji aktu (przykład)
            act_id = act.get('id')  # Załóżmy, że mamy identyfikator aktu
            if act_id:
                act['url'] = f'http://api.sejm.gov.pl/eli/acts/{publisher_map[publisher]}/{year}/{act_id}'
            else:
                act['url'] = None  # Jeśli nie ma ID, nie generujemy linku

            # Mapa słów kluczowych do aktów
            for keyword in keywords:
                if keyword not in keyword_map:
                    keyword_map[keyword] = []
                keyword_map[keyword].append(act['title'])

        return jsonify({'acts': acts, 'keyword_map': keyword_map})
    except Exception as e:
        return jsonify({'error': 'Exception occurred', 'details': str(e)}), 500

@app.route('/find_words_api', methods=['POST'])
def find_words_api():
    text = request.form.get('text')
    if not text:
        return jsonify({'error': 'No text provided'}), 400
    return jsonify({'highlighted_phrases': extract_keywords(text)})

def extract_keywords(text):
    # Używamy spacy do przetwarzania tekstu
    nlp = spacy.load("pl_core_news_sm")
    doc = nlp(text)

    # Preprocessing tekstu: lematyzacja, usuwanie stop-słów, usuwanie znaków specjalnych i cyfr
    tokens = [
        token.lemma_ for token in doc 
        if not token.is_stop and not token.is_punct and not token.is_digit
        and len(token.text.strip()) > 2  # Pomija bardzo krótkie tokeny
    ]
    
    # Dodatkowe czyszczenie (usuwanie spacji i nowych linii)
    tokens = [re.sub(r'\s+', '', token) for token in tokens]

    # Przygotowanie słownika i korpusu
    dictionary = corpora.Dictionary([tokens])
    corpus = [dictionary.doc2bow(tokens)]

    # Tworzymy model LDA
    lda_model = LdaModel(corpus, num_topics=1, id2word=dictionary, passes=15)

    # Wyciąganie tematów (słów kluczowych)
    topics = lda_model.print_topics(num_words=5)  # Zwracamy 5 najlepszych słów kluczowych
    highlighted_phrases = []

    for _, topic in topics:
        words = topic.split('+')
        for word_weight in words:
            try:
                word = word_weight.split('*')[-1].strip().strip('"')
                highlighted_phrases.append(f"<mark>{word}</mark>")
            except Exception as e:
                print(f"Error processing word: {word_weight}, Error: {e}")

    return highlighted_phrases[:5]  # Zwracamy tylko pierwsze 5 słów kluczowych

if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)
