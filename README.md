


# Python Image Board

This is a simple image board web application built with Python Flask. Users can upload images, which are then displayed on the image board. The images are stored using the ImgBB API, and the application includes basic error handling, comment functionality, and image deletion.

## Setup

### 1. Clone the Repository

Clone this repository to your local machine:

```bash
git clone https://github.com/KorryKatti/Python-Image-Board.git
```

### 2. Install Dependencies

Navigate to the project directory and install the required dependencies using pip:

```bash
cd Python-Image-Board

# Method 1: using pip
pip install -r requirements.txt

# Method 2: using poetry
poetry install
```

### 3. Configure the Application

Before running the application, you need to obtain an API key from ImgBB. Sign up on the [ImgBB website](https://imgbb.com/) to get your API key.

Once you have the API key, create a \`.env\` file in the root directory of the project and add the following:

```
api_key=YOUR_IMGBB_API_KEY
secret_key=YOUR_SECRET_KEY
```

Replace `YOUR_IMGBB_API_KEY` and `YOUR_SECRET_KEY` with your actual API key and a secret key of your choice.

### 4. Run the Application

You can now run the Flask application using the following command:

```bash
python main.py
```

The application will start running on [http://127.0.0.1:5000/](http://127.0.0.1:5000/).

### 5. Access the Application

Open your web browser and navigate to [http://127.0.0.1:5000/](http://127.0.0.1:5000/) to access the image board application. You can upload images, and they will be displayed on the image board.

## Features

- Upload images to the board.
- Add comments to uploaded images.
- Delete uploaded images (with password protection).
- Images are hosted on ImgBB via their API.

## Participating in Hacktoberfest 2024

This repository is open for contributions as part of Hacktoberfest 2024. Contributions are welcome! Feel free to create issues and submit pull requests.

### Contribution Guidelines

Read [CONTRIBUTING.md](CONTRIBUTING.md)

1. Fork the repository.
2. Make your changes and commit them (\`git commit -m 'Add some feature'\`).
3. Push to the branch (\`git push origin feature-branch\`).
4. Open a pull request.
