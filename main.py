from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, send_from_directory, session
import requests, json, os, time, logging, uuid
from collections import defaultdict
import sqlite3
from markupsafe import escape
from dotenv import load_dotenv
from flask_caching import Cache
from flask_compress import Compress

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("secret_key", "default_secret")
API_KEY = os.getenv("api_key")
UPLOAD_IMAGE_URL = 'https://api.imgbb.com/1/upload'

cache = Cache(app, config={
    'CACHE_TYPE': 'SimpleCache',
    'CACHE_DEFAULT_TIMEOUT': 30,
})
Compress(app)

secret_board_images = []
SECRET_BOARD_MAX = 10

from datetime import datetime

@app.template_filter('datetimeformat')
def datetimeformat(value, format='%Y-%m-%d %H:%M:%S'):
    if not value:
        return ''
    if isinstance(value, (int, float)):
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

DB_PATH = 'images.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')
    return conn

def init_db():
    conn = get_db()
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

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS text_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp INTEGER NOT NULL,
            board_name TEXT NOT NULL,
            post_id TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            content TEXT NOT NULL
        )
    ''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_images_board ON images(board_name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_images_id ON images(image_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_comments_image ON comments(image_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_text_posts_ts ON text_posts(timestamp DESC)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_text_posts_id ON text_posts(post_id)')

    conn.commit()
    conn.close()

init_db()

class imgBoardFunctions:
    def __init__(self):
        self.image_data = defaultdict(list)

    def add_image(self, image_url, board_name, caption_of_image):
        timestamp = int(time.time())
        image_id = str(uuid.uuid4())

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO images (timestamp, image_url, board_name, image_id, caption_of_image)
            VALUES (?, ?, ?, ?, ?)
        ''', (timestamp, image_url, board_name, image_id, caption_of_image))
        conn.commit()
        conn.close()

        cache.delete_memoized(board, board_name)
        logging.info(f'Image uploaded successfully: {image_url} with caption: {caption_of_image}')


@app.after_request
def add_cache_headers(response):
    if request.path.startswith('/static/'):
        response.cache_control.max_age = 86400
        response.cache_control.public = True
    return response


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
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO comments (image_id, comment, comment_timestamp) VALUES (?, ?, ?)',
                (image_id, safe_comment, timestamp)
            )
            cursor.execute('SELECT board_name FROM images WHERE image_id = ?', (image_id,))
            row = cursor.fetchone()

        if row:
            board_name = row[0]
            cache.delete_memoized(board, board_name)
            return redirect(url_for('board', board_name=board_name))
        else:
            flash('Image not found', 'error')
            return redirect(url_for('index'))
    except Exception as e:
        logging.error(f'Error saving comment: {e}')
        flash('Failed to save comment', 'error')
        return redirect(request.referrer or url_for('index'))


@app.route('/<board_name>')
@cache.memoize(timeout=15)
def board(board_name):
    conn = get_db()
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


@app.route('/text-board')
@cache.memoize(timeout=15)
def text_board():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT title, content, timestamp, post_id
        FROM text_posts
        ORDER BY timestamp DESC
    ''')
    posts = cursor.fetchall()
    conn.close()

    posts_data = [
        {'title': post[0], 'content': post[1], 'timestamp': post[2], 'post_id': post[3]}
        for post in posts
    ]

    return render_template('text-board.html', posts=posts_data)


@app.route('/create-text-post', methods=['POST'])
def create_text_post():
    title = request.form.get('title')
    content = request.form.get('content')

    if not title or not content:
        flash('Title and content are required', 'error')
        return redirect(url_for('text_board'))

    if len(content.split()) > 1234:
        flash('Post content cannot exceed 1234 words', 'error')
        return redirect(url_for('text_board'))

    timestamp = int(time.time())
    post_id = str(uuid.uuid4())
    board_name = 'text-board'

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO text_posts (timestamp, board_name, post_id, title, content)
        VALUES (?, ?, ?, ?, ?)
    ''', (timestamp, board_name, post_id, title, content))
    conn.commit()
    conn.close()

    cache.delete_memoized(text_board)
    return redirect(url_for('text_board'))


@app.route('/api/post/<post_id>')
def get_post(post_id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT title, content, timestamp
        FROM text_posts
        WHERE post_id = ?
    ''', (post_id,))
    post = cursor.fetchone()
    conn.close()

    if post:
        post_data = {
            'title': post[0],
            'content': post[1],
            'timestamp': post[2]
        }
        return jsonify(post_data)
    else:
        return jsonify({'error': 'Post not found'}), 404


@app.route('/delete/<image_id>', methods=['POST'])
def delete_image(image_id):
    password = request.form.get('password')
    if password != os.getenv("delete_password"):
        return jsonify({'error': 'Incorrect password'}), 403

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM images WHERE image_id = ?', (image_id,))
        cursor.execute('DELETE FROM comments WHERE image_id = ?', (image_id,))
        conn.commit()
        cache.clear()
        logging.info(f'Image with ID {image_id} deleted successfully.')
        return jsonify({'message': 'Image deleted successfully'})
    except sqlite3.Error as e:
        logging.error(f'Error deleting image: {e}')
        return jsonify({'error': 'Failed to delete image'}), 500
    finally:
        conn.close()


@app.route('/favicon.ico')
def favicon():
    return send_from_directory('static', 'icon.png')


@app.route('/secret', methods=['GET', 'POST'])
def secret_board():
    if request.method == 'POST':
        if request.form.get('passphrase'):
            answer = request.form.get('passphrase', '').strip().lower()
            expected = os.getenv('secret_answer', '').strip().lower()
            if answer == expected:
                session['secret_authorized'] = True
                return redirect(url_for('secret_board'))
            return render_template('secret.html', gate=True, error=True)

        if not session.get('secret_authorized'):
            return redirect(url_for('secret_board'))

        image = request.files.get('image')
        caption = request.form.get('caption', '')

        if not image:
            return jsonify({'error': 'No image provided'}), 400

        try:
            files = {'image': image}
            params = {'key': API_KEY}
            response = requests.post(UPLOAD_IMAGE_URL, files=files, params=params)
            response.raise_for_status()
            data = response.json()

            if not data.get('success'):
                return jsonify({'error': 'Upload failed'}), 400

            entry = {
                'url': data['data']['url'],
                'caption': caption,
                'timestamp': int(time.time()),
                'id': str(uuid.uuid4())[:8],
            }
            secret_board_images.append(entry)

            while len(secret_board_images) > SECRET_BOARD_MAX:
                secret_board_images.pop(0)

            return redirect(url_for('secret_board'))
        except requests.RequestException as e:
            logging.error(f'Secret board upload error: {e}')
            return jsonify({'error': 'Upload failed'}), 500

    if not session.get('secret_authorized'):
        return render_template('secret.html', gate=True)

    return render_template('secret.html', images=list(reversed(secret_board_images)))


@app.route('/api/secret')
def secret_board_api():
    if not session.get('secret_authorized'):
        return jsonify({'error': 'unauthorized'}), 401
    return jsonify({
        'count': len(secret_board_images),
        'max': SECRET_BOARD_MAX,
        'images': list(reversed(secret_board_images)),
    })


if __name__ == '__main__':
    app.run(debug=False)
