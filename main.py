from flask import Flask, render_template, request, flash, redirect, url_for, send_file
import requests
import json
import os
import time

app = Flask(__name__)
app.secret_key = 'anystring'  # Change this to your actual secret key

# API key for ImgBB
API_KEY = 'key'

# URL for uploading images to ImgBB
UPLOAD_URL = 'https://api.imgbb.com/1/upload'

# File to store uploaded image URLs
IMAGE_FILE = 'uploaded_images.json'


def upload_image_to_imgbb(image):
    try:
        files = {'image': image}
        params = {'key': API_KEY}
        response = requests.post(UPLOAD_URL, files=files, params=params)
        response.raise_for_status()
        data = response.json()
        return data['data']['url']
    except requests.exceptions.RequestException as e:
        print(f"Error uploading image: {e}")
        return None


def save_uploaded_images(images):
    with open(IMAGE_FILE, 'w') as file:
        json.dump(images, file)


def load_uploaded_images():
    try:
        with open(IMAGE_FILE, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return []
    except Exception as e:
        print(f"Error loading uploaded images: {e}")
        return []


def delete_image(image_index):
    try:
        uploaded_images = load_uploaded_images()
        del uploaded_images[image_index]
        save_uploaded_images(uploaded_images)
        flash('Image has been deleted.', 'success')
    except IndexError:
        flash('Invalid image index.', 'error')
    except Exception as e:
        print(f"Error deleting image: {e}")
        flash('An unexpected error occurred. Please try again later.', 'error')


@app.route('/')
def index():
    uploaded_images = load_uploaded_images()
    return render_template('index.html', images=uploaded_images)


@app.route('/upload', methods=['POST'])
def upload():
    try:
        if 'image' in request.files:
            image = request.files['image']
            title = f"{request.form.get('title')} - Uploaded at {int(time.time())}"
            image_url = upload_image_to_imgbb(image)
            if image_url:
                uploaded_images = load_uploaded_images()
                uploaded_images.insert(0, {'url': image_url, 'title': title, 'comments': []})
                save_uploaded_images(uploaded_images)
                flash('Image uploaded successfully!', 'success')
            else:
                flash('Failed to upload image. Please try again later.', 'error')
    except Exception as e:
        print(f"Error uploading image: {e}")
        flash('An unexpected error occurred. Please try again later.', 'error')
    return redirect(url_for('index'))


@app.route('/add_comment/<int:image_index>', methods=['POST'])
def add_comment(image_index):
    try:
        comment = request.form.get('comment')
        if comment:
            uploaded_images = load_uploaded_images()
            if image_index < len(uploaded_images):
                image = uploaded_images[image_index]
                if 'comments' not in image:
                    image['comments'] = []
                if len(image['comments']) < 3:
                    image['comments'].append(comment)
                else:
                    image['comments'][:-1] = image['comments'][1:]
                    image['comments'][-1] = comment
                save_uploaded_images(uploaded_images)
            else:
                flash('Invalid image index.', 'error')
        else:
            flash('Comment cannot be empty.', 'error')
    except Exception as e:
        print(f"Error adding comment: {e}")
        flash('An unexpected error occurred. Please try again later.', 'error')
    return redirect(url_for('index'))


@app.route('/delete_image/<int:image_index>', methods=['POST'])
def delete_image_with_password(image_index):
    try:
        password = request.form.get('password')
        # Check if the provided password matches the expected password
        if password == 'your_password':
            delete_image(image_index)
        else:
            flash('Incorrect password.', 'error')
    except Exception as e:
        # Log the error or handle it appropriately
        print(f"Error deleting image: {e}")
        flash('An unexpected error occurred. Please try again later.', 'error')

    return redirect(url_for('index'))


@app.route('/arc-sw.js')
def serve_js():
    return send_file('arc-sw.js')


if __name__ == '__main__':
    app.run(debug=True)
