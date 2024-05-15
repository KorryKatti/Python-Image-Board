# Python file (app.py)

from flask import Flask, render_template, request, flash, redirect, url_for, send_file, session
import requests
import json
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'randomstrings'  # Change this to your actual secret key

# API key for ImgBB
API_KEY = 'imgbbapikey'

# URL for uploading images to ImgBB
UPLOAD_URL = 'https://api.imgbb.com/1/upload'

# File to store uploaded image URLs
IMAGE_FILE = 'uploaded_images.json'

# File to store total visitors count
VISITORS_FILE = 'total_visitors.txt'

def upload_image_to_imgbb(image):
    try:
        # Prepare the request data
        files = {'image': image}
        params = {'key': API_KEY}

        # Make the POST request to upload the image
        response = requests.post(UPLOAD_URL, files=files, params=params)
        response.raise_for_status()  # Raise an error for bad status codes

        # Parse the response JSON
        data = response.json()

        # Return the URL of the uploaded image
        return data['data']['url']
    except requests.exceptions.RequestException as e:
        # Log the error or handle it appropriately
        print(f"Error uploading image: {e}")
        return None

def save_uploaded_images(images):
    with open(IMAGE_FILE, 'w') as file:
        json.dump(images, file)

def load_uploaded_images():
    if os.path.exists(IMAGE_FILE):
        with open(IMAGE_FILE, 'r') as file:
            return json.load(file)
    else:
        return []

def load_total_visitors():
    if os.path.exists(VISITORS_FILE):
        with open(VISITORS_FILE, 'r') as file:
            return int(file.read())
    else:
        return 0

def save_total_visitors(count):
    with open(VISITORS_FILE, 'w') as file:
        file.write(str(count))

# Load uploaded images from file when the app starts
uploaded_images = load_uploaded_images()

# Load total visitors count from file
total_visitors = load_total_visitors()

# Function to update visitor stats
def update_visitor_stats():
    today = datetime.now().strftime('%Y-%m-%d')
    if 'visitors' not in session:
        session['visitors'] = {today: 1}
    else:
        if today in session['visitors']:
            session['visitors'][today] += 1
        else:
            session['visitors'][today] = 1

    # Increment total visitors count and save to file
    global total_visitors
    total_visitors += 1
    save_total_visitors(total_visitors)

@app.route('/')
def index():
    update_visitor_stats()  # Update visitor stats on each visit
    today_visitors = session['visitors'].get(datetime.now().strftime('%Y-%m-%d'), 0)
    return render_template('index.html', images=uploaded_images, total_visitors=total_visitors, today_visitors=today_visitors)

@app.route('/upload', methods=['POST'])
def upload():
    try:
        if 'image' in request.files:
            image = request.files['image']
            title = request.form.get('title')  # Get the title from the form
            # Upload the image to ImgBB and get the URL
            image_url = upload_image_to_imgbb(image)
            if image_url:
                # Add the image URL and title to the beginning of the list
                uploaded_images.insert(0, {'url': image_url, 'title': title})
                save_uploaded_images(uploaded_images)
                flash('Image uploaded successfully!', 'success')
            else:
                flash('Failed to upload image. Please try again later.', 'error')
    except Exception as e:
        # Log the error or handle it appropriately
        print(f"Error uploading image: {e}")
        flash('An unexpected error occurred. Please try again later.', 'error')

    return redirect(url_for('index'))

@app.route('/arc-sw.js')
def serve_js():
    return send_file('arc-sw.js')

if __name__ == '__main__':
    app.run(debug=True)
