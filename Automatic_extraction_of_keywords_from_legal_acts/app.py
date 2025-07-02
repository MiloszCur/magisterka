from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
import os
import requests
from pdfminer.high_level import extract_text
import spacy
import re
import morfeusz2
import yake

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = os.path.abspath(UPLOAD_FOLDER)
ALLOWED_EXTENSIONS = {'pdf'}

CUSTOM_STOP_WORDS = {
    "dzień", "dni", "grudzień", "styczeń", "luty", "marzec", "kwiecień", "maj", "czerwiec",
    "lipiec", "sierpień", "wrzesień", "październik", "listopad", "sobota", "niedziela",
    "poniedziałek", "wtorek", "środa", "czwartek", "piątek", "roku", "rok"
}

morfeusz = morfeusz2.Morfeusz()
nlp = spacy.load("pl_core_news_sm")


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_keywords(text):
    kw_extractor = yake.KeywordExtractor(
        lan="pl",
        n=2,
        dedupLim=0.9,
        top=20,
        features=None
    )

    raw_keywords = kw_extractor.extract_keywords(text)
    filtered_keywords = []

    text_lower = text.lower()
    seen_lemmas = set()

    for phrase, score in raw_keywords:
        phrase_clean = phrase.strip().lower()

         # wyklucz frazy typu 'minister:sm1'
        if re.search(r':\w+', phrase_clean):
            continue

         # Od razu odrzucamy frazy zawierające dwukropek
        if ':' in phrase_clean:
            continue

        if re.search(r'[:\d]', phrase_clean):
            continue

        if re.search(r'[^a-ząćęłńóśżź\s]', phrase_clean):
            continue

        if len(phrase_clean) < 3 or len(phrase_clean.split()) > 4:
            continue

        if not re.search(r'[a-zA-Ząćęłńóśżź]', phrase_clean):
            continue

        if re.fullmatch(r'[\d\s\W]+', phrase_clean):
            continue

        if text_lower.count(phrase_clean) > 10:
            continue

        analyses = morfeusz.analyse(phrase_clean)
        lemma = analyses[0][2][1].lower() if analyses else phrase_clean

        if lemma in CUSTOM_STOP_WORDS or phrase_clean in CUSTOM_STOP_WORDS:
            continue

        if lemma in seen_lemmas:
            continue

        if ':' in lemma or re.search(r'[^a-ząćęłńóśżź\s]', lemma):
            continue

        seen_lemmas.add(lemma)
       # filtered_keywords.append((phrase_clean, score))
        filtered_keywords.append((lemma, score))

        if len(filtered_keywords) >= 2:
            break

    return [phrase for phrase, _ in filtered_keywords]


def process_local_pdf(filepath, filename):
    text = extract_text(filepath)
    title = filename
    eli = filename.replace('.pdf', '')
    download_url = url_for('display_pdf', filename=filename)

    keywords = extract_keywords(text)

    keyword_map = {}
    for keyword in keywords:
        keyword_map.setdefault(keyword, []).append(title)

    acts = [{
        'title': title,
        'ELI': eli,
        'download_url': download_url,
        'type': 'Unknown' 
    }]

    download_map = {title: download_url}
    released_by_map = {title: ["Unknown Publisher"]} 

    return {
        'acts': acts,
        'keyword_map': keyword_map,
        'download_map': download_map,
        'released_by_map': released_by_map
    }


@app.route('/')
def home():
    return render_template('index.html', filename=request.args.get('filename'))


@app.route('/main')
def main():
    return render_template('main.html')

@app.route('/upload1')
def upload():
    filename = request.args.get('filename', '')
    return render_template('upload.html', filename=filename)


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and allowed_file(file.filename):
        filename = file.filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            # zamiast zwracać JSON, zrób redirect do upload1 z filename
            return redirect(url_for('upload', filename=filename))
        except Exception as e:
            return jsonify({'error': f'File processing error: {str(e)}'}), 500

    return jsonify({'error': 'Invalid file format'}), 400



@app.route('/uploads/<filename>')
def display_pdf(filename):
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except FileNotFoundError:
        return 'File not found', 404


@app.route('/extract_text')
def extract_text_route():
    pdf_url = request.args.get('pdf_url')
    if not pdf_url:
        return 'Missing pdf_url', 400

    if not pdf_url.startswith('/uploads/'):
        return 'Invalid pdf_url', 400
    filename = pdf_url[len('/uploads/'):]
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    if not os.path.exists(filepath):
        return 'File not found', 404

    try:
        text = extract_text(filepath)
        return text
    except Exception as e:
        return f'Error extracting text: {str(e)}', 500


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
            act_type = 'Unknown'
            released_by = ["Unknown publisher"]

            if eli and pos:
                details_url = f"https://api.sejm.gov.pl/eli/acts/{publisher_code}/{year}/{pos}"
                details_resp = requests.get(details_url)
                if details_resp.status_code == 200:
                    details = details_resp.json()
                    act_type = details.get("type", "Unknown")
                    if "releasedBy" in details and details["releasedBy"]:
                        released_by = details["releasedBy"]

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
            released_by_map[title] = released_by

            for keyword in keywords:
                keyword_map.setdefault(keyword, []).append(title)

        return jsonify({
            'acts': acts,
            'keyword_map': keyword_map,
            'download_map': download_map,
            'released_by_map': released_by_map
        })

    except Exception as e:
        return jsonify({'error': 'Exception occurred', 'details': str(e)}), 500


@app.route('/inflect', methods=['POST'])
def inflect_keyword():
    keyword = request.json.get("keyword", "").strip().lower()
    if not keyword:
        return jsonify([])

    forms_set = set()
    analyses = morfeusz.analyse(keyword)

    for _, _, (form, lemma, tag) in analyses:
        forms_set.add(form.lower())
        forms_set.add(lemma.lower())

        try:
            generated = morfeusz.generate(lemma)
            for _, (variant, _, _) in generated:
                forms_set.add(variant.lower())
        except:
            pass

    return jsonify(list(forms_set))


if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)
