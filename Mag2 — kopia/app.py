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

@app.route('/upload')
def upload():
    return render_template('upload.html', filename=request.args.get('filename'))

@app.route('/main')
def main():
    return render_template('main.html', filename=request.args.get('filename'))

@app.route('/upload', methods=['POST', 'GET'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            return 'No file part'
        
        file = request.files['file']
        if file.filename == '':
            return 'No selected file'
        
        if file and allowed_file(file.filename):
            filename = file.filename
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            # Zmieniamy przekierowanie na stronę uploadu
           # return redirect(url_for('upload_file', filename=filename))
            return redirect(url_for('upload', filename=filename))

    return 'Invalid file format'

 #   return render_template('upload.html')
'''
@app.route('/upload', methods=['POST', 'GET'])
def upload_file():
    if request.method == 'POST':
        # Sprawdzamy, czy plik istnieje w formularzu
        if 'file' not in request.files:
            return 'No file part'
        
        file = request.files['file']
        
        # Sprawdzamy, czy plik ma nazwę
        if file.filename == '':
            return 'No selected file'
        
        # Sprawdzamy, czy plik ma dozwolone rozszerzenie
        if file and allowed_file(file.filename):
            filename = file.filename
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            # Zapisujemy plik w folderze
            file.save(filepath)

            # Przekierowanie na stronę z uploadem
            return redirect(url_for('upload_file', filename=filename))

    # Renderowanie strony upload
    return render_template('upload.html')'''

@app.route('/uploads/<filename>')
def display_pdf(filename):
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except FileNotFoundError:
        return 'File not found', 404
    

@app.route('/find_words', methods=['POST', 'GET'])
def find_words():
    if request.method == 'POST':
        filename = request.form.get('filename')
        if not filename:
            return jsonify({'error': 'No file selected'}), 400
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 404
        text = extract_text(filepath)
        return jsonify({'highlighted_phrases': extract_keywords(text)})
    return render_template('upload.html')


@app.route('/fetch_acts', methods=['POST', 'GET'])
def fetch_acts():
    publisher_map = {
        "DziennikUstaw": "DU",
        "MonitorPolski": "MP"
    }
    
    publisher = request.form.get('publisher')
    print(f"Publisher: {publisher}")  # Debugowanie, żeby sprawdzić wartość
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
            act_id = act.get('id') ##

             #  link do strony z treścią aktu
            #act_url = url_for('display_act', act_id=act_id) if act_id else None
        ##    act_url = f'http://api.sejm.gov.pl/eli/acts/{publisher_map[publisher]}/{year}/{act_id}' if act_id else None
            
             # Tworzymy link na podstawie roku i numeru aktu
            if act_id:
                act_url = f'https://dziennikustaw.gov.pl/DU/{year}/{act_id}'
            else:
                act_url = None  # Jeśli brak ID, nie generujemy linku

            act['url'] = act_url  # Dodajemy link do aktu
            
            # Wyciąganie słów kluczowych z treści lub tytułu
            keywords = extract_keywords(content if content else title)
            act['highlighted_phrases'] = keywords
            
            # Tworzymy URL do pełnej wersji aktu (przykład)
          ###  act_id = act.get('id')  # Załóżmy, że mamy identyfikator aktu
         ###   if act_id:
        ###        act['url'] = f'http://api.sejm.gov.pl/eli/acts/{publisher_map[publisher]}/{year}/{act_id}'
    ###        else:
      ###          act['url'] = None  # Jeśli nie ma ID, nie generujemy linku

            # Mapa słów kluczowych do aktów
            for keyword in keywords:
                if keyword not in keyword_map:
                    keyword_map[keyword] = []
                keyword_map[keyword].append(act['title'])

        return jsonify({'acts': acts, 'keyword_map': keyword_map})
    except Exception as e:
        return jsonify({'error': 'Exception occurred', 'details': str(e)}), 500

@app.route('/act/<act_id>')
def display_act(act_id):
    api_url = f'http://api.sejm.gov.pl/eli/acts/details/{act_id}'
    try:
        response = requests.get(api_url)
        if response.status_code != 200:
            return 'Act not found', 404

        act_data = response.json()
        return render_template('act.html', act=act_data)
    except Exception as e:
        return f'Error loading act: {str(e)}', 500

    

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

    # Lista nazw miesięcy
    months = ["styczeń", "luty", "marzec", "kwiecień", "maj", "czerwiec", "lipiec", "sierpień", "wrzesień", "październik", "listopad", "grudzień"]
    excluded_words = ["ustawa", "rozporządzenie", "dzień"]

    # Preprocessing tekstu: lematyzacja, usuwanie stop-słów, usuwanie znaków specjalnych i cyfr
    tokens = [
        token.lemma_ for token in doc 
        if not token.is_stop and not token.is_punct and not token.is_digit
        and len(token.text.strip()) > 2  # Pomija bardzo krótkie tokeny
        and token.text.lower() not in months  # Pomija nazwy miesięcy
        and token.lemma_.lower() not in months  # Dodane sprawdzenie lematyzowanej formy tokenu
        and token.text.lower() not in excluded_words  # Pomija słowa na liście wykluczeń
        and token.lemma_.lower() not in excluded_words  # Pomija lematyzowane formy słów na liście wykluczeń
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
