from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS, cross_origin

from pathlib import Path
import matplotlib
import warnings
import json
import time

matplotlib.use('Agg')
warnings.filterwarnings('ignore')

from programs.model import Model
from programs.result import Result
from programs.summarize import summarize

app = Flask(__name__, static_folder='../build', static_url_path='/')
app.config.from_object('config')
UPLOAD_FOLDER = app.config['UPLOAD_FOLDER']
EXAMPLE_FOLDER = app.config['EXAMPLE_FOLDER']
CORS(app, support_credentials=True)


@app.errorhandler(404)
def not_found(e):
    return app.send_static_file('index.html')


@app.route('/')
def index():
    return app.send_static_file('index.html')


@app.route('/api/uploads/<path:filename>')
def download_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route('/api/example/<path:filename>')
def download_example(filename):
    return send_from_directory(EXAMPLE_FOLDER, filename)


@app.route('/api/model', methods=['POST'])
def run(upload_folder=UPLOAD_FOLDER):
    job = {
        'id': request.form.get('id'),
        'date': request.form.get('date'),
        'email-address': request.form.get('email-address'),
        'has-gams': request.form.get('has-gams') == 'true',
        'data-contrib': request.form.get('data-contrib') == 'true',
        'cut-offs': [1.5, 2.5]
    }

    upload_folder = Path(upload_folder)
    job_folder = upload_folder / job['id']
    job_folder.mkdir(exist_ok=True)

    # get files
    files = request.files

    # load model
    model = Model(has_gams=job['has-gams'])
    results = []
    for i in files:
        # load result
        img = model.load_image(files[i])
        pred = model.predict()
        result = Result(i, files[i].filename, img, pred)
        result.run(upload_folder=job_folder)
        results.append(result.to_output())

    output = {
        'data': {
            'summary': summarize(results),
            'results': results
        },
        'statusOK': True
    }

    with open(job_folder / 'output.json', 'w') as f:
        json.dump(output, f)
    return output


@app.route('/api/result', methods=['POST'])
def return_result(upload_folder=UPLOAD_FOLDER, example_folder=EXAMPLE_FOLDER):
    job_id = request.get_json()['id']
    if job_id == 'example':
        result_dir = Path(example_folder)
    else:
        result_dir = Path(upload_folder) / job_id
    result_path = result_dir / 'output.json'
    if result_path.exists():
        with open(result_path) as f:
            return json.load(f)
    else:
        return {'statusOK': False}


if __name__ == '__main__':
    app.run(debug=True)
