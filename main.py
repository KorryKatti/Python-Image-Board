from email.mime import image
from flask import Flask, render_template, request, flash, redirect, url_for, send_file, jsonify
import requests
import json
import os
import time
import logging
from collections import defaultdict
from dotenv import load_dotenv

app = Flask(__name__)
app.secret_key = os.getenv("secret_key")  # Change this to your actual secret key

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler("app.log"),  # Log to a file
                        logging.StreamHandler()            # Also log to console
                    ])

# API key for ImgBB
API_KEY = os.getenv("api_key")

# URL for uploading images to ImgBB
UPLOAD_URL = 'https://api.imgbb.com/1/upload'

# File to store uploaded image URLs
IMAGE_FILE = 'uploaded_images.json'
GLOBAL_IMAGE_FILE = 'global_images.json'


def upload_image_to_imgbb(image):
    try:
        files = {'image': image}
        params = {'key': API_KEY}
        response = requests.post(UPLOAD_URL, files=files, params=params)
        response.raise_for_status()
        data = response.json()
        return data['data']['url']
    except requests.exceptions.RequestException as e:
        logging.error(f"Error uploading image: {e}")
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
        logging.error(f"Error loading uploaded images: {e}")
        return []

def save_global_uploaded_images(images):
    with open(GLOBAL_IMAGE_FILE, 'w') as file:
        json.dump(images, file)

def load_global_uploaded_images():
    try:
        with open(GLOBAL_IMAGE_FILE, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return []
    except Exception as e:
        print(f"Error loading uploaded images: {e}")
        return []

@app.route('/latest-updates')
def latest_updates():
    # Read the latest updates from the text file
    update_file_path = os.path.join(app.static_folder, 'latest_updates.txt')
    with open(update_file_path, 'r') as f:
        latest_update = f.read()
    return jsonify({'latest_update': latest_update})


def delete_image(image_index):
    try:
        uploaded_images = load_uploaded_images()
        del uploaded_images[image_index]
        save_uploaded_images(uploaded_images)
        flash('Image has been deleted.', 'success')
    except IndexError:
        flash('Invalid image index.', 'error')
    except Exception as e:
        logging.error(f"Error deleting image: {e}")
        flash('An unexpected error occurred. Please try again later.', 'error')

def delete_global_image(image_index):
    try:
        uploaded_images = load_global_uploaded_images()
        del uploaded_images[image_index]
        save_global_uploaded_images(uploaded_images)
        flash('Image has been deleted.', 'success')
        return uploaded_images
    except IndexError:
        flash('Invalid image index.', 'error')
    except Exception as e:
        print(f"Error deleting image: {e}")
        flash('An unexpected error occurred. Please try again later.', 'error')

@app.route('/global')
def global_page():
    uploaded_images = load_global_uploaded_images()
    return render_template('global.html',images=uploaded_images)

@app.route('/upload_global', methods=['POST'])
def upload_global():
    try:
        if 'image' in request.files:
            image = request.files['image']
            title = f"{request.form.get('title')} - Uploaded at {int(time.time())}"
            image_path = os.path.join('uploads', image.filename)  # Save original image temporarily
            image.save(image_path)  # Save the uploaded image temporarily
            
            # Resize the image
            resized_image_path = resize_image(image_path)

            # Upload the resized image to ImgBB
            with open(resized_image_path, 'rb') as resized_image:
                image_url = upload_image_to_imgbb(resized_image)
            
            if image_url:
                uploaded_images = load_global_uploaded_images()
                uploaded_images.insert(0, {'url': image_url, 'title': title, 'comments': []})
                save_global_uploaded_images(uploaded_images)
                flash('Image uploaded and resized successfully!', 'success')
            else:
                flash('Failed to upload image. Please try again later.', 'error')
            
            # Clean up temporary files
            os.remove(image_path)
            os.remove(resized_image_path)

    except Exception as e:
        logging.error(f"Error uploading image: {e}")
        flash('An unexpected error occurred. Please try again later.', 'error')
    return render_template('global.html', images=load_global_uploaded_images())


@app.route('/add_global_comment/<int:image_index>', methods=['POST'])
def add_global_comment(image_index):
    try:
        comment = request.form.get('comment')
        if comment:
            uploaded_images = load_global_uploaded_images()
            if image_index < len(uploaded_images):
                image = uploaded_images[image_index]
                if 'comments' not in image:
                    image['comments'] = []
                if len(image['comments']) < 3:
                    image['comments'].append(comment)
                else:
                    image['comments'][:-1] = image['comments'][1:]
                    image['comments'][-1] = comment
                save_global_uploaded_images(uploaded_images)
            else:
                flash('Invalid image index.', 'error')
        else:
            flash('Comment cannot be empty.', 'error')
    except Exception as e:
        print(f"Error adding comment: {e}")
        flash('An unexpected error occurred. Please try again later.', 'error')
    # return redirect(url_for('index'))
    return render_template('global.html', images=uploaded_images)

@app.route('/')
def index():
    uploaded_images = load_uploaded_images()
    return render_template('index.html')

@app.route('/thunder')
def thunder():
    uploaded_images = load_uploaded_images()
    return render_template('thunder.html', images=uploaded_images)


@app.route('/upload', methods=['POST'])
def upload():
    try:
        if 'image' in request.files:
            image = request.files['image']
            title = f"{request.form.get('title')} - Uploaded at {int(time.time())}"
            image_path = os.path.join('uploads', image.filename)  # Save original image temporarily
            image.save(image_path)  # Save the uploaded image temporarily
            
            # Resize the image
            resized_image_path = resize_image(image_path)

            # Upload the resized image to ImgBB
            with open(resized_image_path, 'rb') as resized_image:
                image_url = upload_image_to_imgbb(resized_image)
            
            if image_url:
                uploaded_images = load_uploaded_images()
                uploaded_images.insert(0, {'url': image_url, 'title': title, 'comments': []})
                save_uploaded_images(uploaded_images)
                flash('Image uploaded and resized successfully!', 'success')
            else:
                flash('Failed to upload image. Please try again later.', 'error')
            
            # Clean up temporary files
            os.remove(image_path)
            os.remove(resized_image_path)

    except Exception as e:
        logging.error(f"Error uploading image: {e}")
        flash('An unexpected error occurred. Please try again later.', 'error')
    return redirect(url_for('thunder'))



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
        logging.error(f"Error adding comment: {e}")
        flash('An unexpected error occurred. Please try again later.', 'error')
    return redirect(url_for('thunder'))


@app.route('/delete_image/<int:image_index>', methods=['POST'])
def delete_image_with_password(image_index):
    try:
        password = request.form.get('password')
        # Check if the provided password matches the expected password
        if password == 'your':
            delete_image(image_index)
        else:
            flash('Incorrect password.', 'error')
    except Exception as e:
        logging.error(f"Error deleting image: {e}")
        flash('An unexpected error occurred. Please try again later.', 'error')

    return redirect(url_for('thunder'))

@app.route('/delete_global_image/<int:image_index>', methods=['POST'])
def delete_global_image_with_password(image_index):
    try:
        password = request.form.get('password')
        # Check if the provided password matches the expected password
        if password == 'your':
            uploaded_images= delete_global_image(image_index)
            return render_template('global.html',images=uploaded_images)
        else:
            flash('Incorrect password.', 'error')
            uploaded_images= load_global_uploaded_images()
            return render_template('global.html',images=uploaded_images)
    except Exception as e:
        # Log the error or handle it appropriately
        print(f"Error deleting image: {e}")
        flash('An unexpected error occurred. Please try again later.', 'error')

    # return redirect(url_for('/global'))
    return render_template('global.html',images=uploaded_images)
if __name__ == '__main__':
    app.run(debug=True)
