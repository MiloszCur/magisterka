from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
import os
import requests
from pdfminer.high_level import extract_text
from gensim import corpora
from gensim.models import LdaModel
import spacy
import re
import morfeusz2  # dodane

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = os.path.abspath(UPLOAD_FOLDER)
ALLOWED_EXTENSIONS = {'pdf'}

CUSTOM_STOP_WORDS = {
    "dzień", "dni", "grudzień", "styczeń", "luty", "marzec", "kwiecień", "maj", "czerwiec",
    "lipiec", "sierpień", "wrzesień", "październik", "listopad", "sobota", "niedziela",
    "poniedziałek", "wtorek", "środa", "czwartek", "piątek", "roku", "rok"
}

# inicjalizacja Morfeusz2 raz globalnie, by nie ładować wielokrotnie
morfeusz = morfeusz2.Morfeusz()

# Globalne załadowanie modelu SpaCy tylko raz
nlp = spacy.load("pl_core_news_sm")


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

@app.route('/find_words_api', methods=['POST'])
def find_words_api():
    text = request.form.get('text')
    if not text:
        return jsonify({'error': 'No text provided'}), 400
    return jsonify({'highlighted_phrases': extract_keywords(text)})

@app.route('/fetch_acts', methods=['POST'])
def fetch_acts():
    publisher_map = {
        "DziennikUstaw": "DU",
        "MonitorPolski": "MP"
    }

    publisher = request.form.get('publisher')
    year = request.form.get('year')
    count = int(request.form.get('count', 10))

    if publisher not in publisher_map:
        return jsonify({'error': 'Invalid publisher'}), 400

    publisher_code = publisher_map[publisher]
    api_url = f'https://api.sejm.gov.pl/eli/acts/{publisher_code}/{year}'

    try:
        response = requests.get(api_url)
        if response.status_code != 200:
            return jsonify({'error': f'Could not fetch acts, status {response.status_code}', 'details': response.text}), 500

        data = response.json()
        acts_data = data.get("items", [])[:count]

        keyword_map = {}
        download_map = {}
        released_by_map = {}
        acts = []

        for act in acts_data:
            title = act.get('title', '')
            eli = act.get('ELI', '')
            pos = act.get('pos', '')
            act_type = 'Nieznany'

            if eli and pos:
                details_url = f"https://api.sejm.gov.pl/eli/acts/{publisher_code}/{year}/{pos}"
                details_resp = requests.get(details_url)
                if details_resp.status_code == 200:
                    details = details_resp.json()
                    act_type = details.get("type", "Nieznany")

            download_url = f"https://api.sejm.gov.pl/eli/acts/{eli}/text.pdf" if eli else "PDF not available"

            keywords = extract_keywords(title)

            act_entry = {
                'title': title,
                'ELI': eli,
                'download_url': download_url,
                'type': act_type
            }
            acts.append(act_entry)
            download_map[title] = download_url

            # Dummy data: przypisz "MIN. FINANSÓW" jako domyślny organ
            released_by_map[title] = ["MIN. FINANSÓW"]

            for keyword in keywords:
                if keyword not in keyword_map:
                    keyword_map[keyword] = []
                keyword_map[keyword].append(title)

        return jsonify({
            'acts': acts,
            'keyword_map': keyword_map,
            'download_map': download_map,
            'released_by_map': released_by_map
        })

    except Exception as e:
        return jsonify({'error': 'Exception occurred', 'details': str(e)}), 500

def extract_keywords(text):
  #  nlp = spacy.load("pl_core_news_sm")
   # doc = nlp(text)
    doc = nlp(text)  # ← użycie globalnego `nlp`

    tokens = [
        token.lemma_.lower() for token in doc
        if not token.is_stop
        and not token.is_punct
        and not token.is_digit
        and len(token.text.strip()) > 2
        and token.lemma_.lower() not in CUSTOM_STOP_WORDS
    ]

    tokens = [re.sub(r'\s+', '', token) for token in tokens]

    if not tokens:
        return []

    dictionary = corpora.Dictionary([tokens])
    corpus = [dictionary.doc2bow(tokens)]

    try:
        lda_model = LdaModel(corpus, num_topics=1, id2word=dictionary, passes=15)
        topics = lda_model.print_topics(num_words=10)  # 10 słów dla lepszej analizy
        highlighted_phrases = []

        for _, topic in topics:
            words = topic.split('+')
            for word_weight in words:
                try:
                    word = word_weight.split('*')[-1].strip().strip('"')
                    highlighted_phrases.append(word)
                except Exception as e:
                    print(f"Error processing word: {word_weight}, Error: {e}")

        # Analiza Morfeusz2 i sortowanie według lematów
        analyzed = []
        for w in highlighted_phrases:
            analyses = morfeusz.analyse(w)
            if analyses:
                lemma = analyses[0][2][1]  # lemat
                tag = analyses[0][2][2]    # tag gramatyczny
                analyzed.append((w, lemma, tag))
            else:
                analyzed.append((w, w, ''))

        # Sortowanie alfabetycznie po lemacie
        analyzed_sorted = sorted(analyzed, key=lambda x: x[1])

        # Zwróć max 10 słów kluczowych posortowanych
        return [a[0] for a in analyzed_sorted][:3]

    except Exception as e:
        print(f"Error during LDA keyword extraction: {e}")
        return []

if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)
