from email.mime import image  # suspicious, but leaving as-is
from flask import Flask, render_template, request, redirect, url_for, jsonify,flash
import requests, json, os, time, logging, uuid
from collections import defaultdict
import sqlite3
from markupsafe import escape
from dotenv import load_dotenv

load_dotenv()


app = Flask(__name__)
app.secret_key = os.getenv("secret_key", "default_secret")
API_KEY = os.getenv("api_key")
UPLOAD_IMAGE_URL = 'https://api.imgbb.com/1/upload'

from datetime import datetime

@app.template_filter('datetimeformat')
def datetimeformat(value, format='%Y-%m-%d %H:%M:%S'):
    if not value:
        return ''
    if isinstance(value, (int, float)):  # timestamp input
        value = datetime.fromtimestamp(value)
    return value.strftime(format)



logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

def init_db():
    conn = sqlite3.connect('images.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp INTEGER NOT NULL,
            image_url TEXT NOT NULL,
            board_name TEXT NOT NULL,
            image_id TEXT NOT NULL UNIQUE,
            caption_of_image TEXT DEFAULT '',
            comment_id INTEGER,
            FOREIGN KEY (comment_id) REFERENCES comments(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_id TEXT NOT NULL,
            comment TEXT NOT NULL,
            comment_timestamp INTEGER NOT NULL,
            FOREIGN KEY (image_id) REFERENCES images(image_id)
        )
    ''')

    conn.commit()
    conn.close()

init_db()

class imgBoardFunctions:
    def __init__(self):
        self.image_data = defaultdict(list)

    def add_image(self, image_url, board_name, caption_of_image):
        timestamp = int(time.time())
        image_id = str(uuid.uuid4())

        conn = sqlite3.connect('images.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO images (timestamp, image_url, board_name, image_id, caption_of_image)
            VALUES (?, ?, ?, ?, ?)
        ''', (timestamp, image_url, board_name, image_id, caption_of_image))
        conn.commit()
        conn.close()

        logging.info(f'Image uploaded successfully: {image_url} with caption: {caption_of_image}')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload/<board_name>', methods=['GET', 'POST'])
def upload(board_name):
    if request.method == 'POST':
        image = request.files.get('image')
        caption = request.form.get('caption', f'uploaded at {int(time.time())}')

        if not image:
            return jsonify({'error': 'no image was provided'}), 400

        if not board_name:
            return jsonify({'error': 'board name is missing'}), 400

        try:
            # the fix: send image via multipart/form-data
            files = {'image': image}
            params = {'key': API_KEY}

            response = requests.post(UPLOAD_IMAGE_URL, files=files, params=params)
            response.raise_for_status()
            data = response.json()

            if not data.get('success'):
                return jsonify({
                    'error': 'imgbb upload failed',
                    'details': data.get('error', 'unknown error')
                }), 400

            image_url = data['data']['url']
            image_id = data['data']['id']

            img_board = imgBoardFunctions()
            img_board.add_image(image_url, board_name, caption)

            return redirect(url_for('board', board_name=board_name))


        except requests.RequestException as e:
            logging.error(f'Error uploading image: {e}')
            if e.response is not None:
                logging.error(f'Response content: {e.response.text}')
            return jsonify({'error': 'failed to upload image'}), 500

    # GET request, just render the board upload page
    return render_template(f'{board_name}.html', message='Upload your image', board_name=board_name)



@app.route('/comment/<image_id>', methods=['POST'])
def comment(image_id):
    comment_text = request.form.get('comment', '').strip()
    if not comment_text:
        flash('Comment cannot be empty', 'error')
        return redirect(request.referrer or url_for('index'))
    safe_comment = escape(comment_text)

    timestamp = int(time.time())
    try:
        with sqlite3.connect('images.db') as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO comments (image_id, comment, comment_timestamp) VALUES (?, ?, ?)',
                (image_id, safe_comment, timestamp)
            )
            cursor.execute('SELECT board_name FROM images WHERE image_id = ?', (image_id,))
            row = cursor.fetchone()
        if row:
            board_name = row[0]
            return redirect(url_for('board', board_name=board_name))
        else:
            flash('Image not found', 'error')
            return redirect(url_for('index'))
    except Exception as e:
        logging.error(f'Error saving comment: {e}')
        flash('Failed to save comment', 'error')
        return redirect(request.referrer or url_for('index'))



@app.route('/<board_name>')
def board(board_name):
    conn = sqlite3.connect('images.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT image_url, board_name, caption_of_image, image_id
        FROM images
        WHERE board_name = ?
        ORDER BY timestamp DESC
    ''', (board_name,))
    images = cursor.fetchall()

    cursor.execute('''
        SELECT comment, comment_timestamp, image_id
        FROM comments
        WHERE image_id IN (SELECT image_id FROM images WHERE board_name = ?)
        ORDER BY comment_timestamp DESC
    ''', (board_name,))
    comments = cursor.fetchall()
    conn.close()

    images_data = [
        {'image_url': img[0], 'board_name': img[1], 'caption_of_image': img[2], 'image_id': img[3]}
        for img in images
    ]
    comments_data = [
        {'comment': com[0], 'comment_timestamp': com[1], 'image_id': com[2]}
        for com in comments
    ]

    return render_template(f'{board_name}.html', images=images_data, comments=comments_data, board_name=board_name)



@app.route('/latest-updates')
def latest_updates():
    update_file_path = os.path.join(app.static_folder, 'latest_updates.txt')
    try:
        with open(update_file_path, 'r') as file:
            latest_update = file.read()
        return jsonify({'latest_update': latest_update})
    except FileNotFoundError:
        return jsonify({'error': 'Update file not found'}), 404


@app.route('/rules')
def rules():
    return render_template('rules.html')


@app.route('/delete/<image_id>', methods=['POST'])
def delete_image(image_id):
    password = request.form.get('password')
    if password != os.getenv("delete_password"):
        return jsonify({'error': 'Incorrect password'}), 403

    conn = sqlite3.connect('images.db')
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM images WHERE image_id = ?', (image_id,))
        cursor.execute('DELETE FROM comments WHERE image_id = ?', (image_id,))
        conn.commit()
        logging.info(f'Image with ID {image_id} deleted successfully.')
        return jsonify({'message': 'Image deleted successfully'})
    except sqlite3.Error as e:
        logging.error(f'Error deleting image: {e}')
        return jsonify({'error': 'Failed to delete image'}), 500
    finally:
        conn.close()


from flask import send_from_directory

@app.route('/favicon.ico')
def favicon():
    return send_from_directory('static', 'icon.png')


if __name__ == '__main__':
    app.run(debug=False)