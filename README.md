# Python Image Board

A simple image board built with Python and Flask.

## Features

*   **Image Boards:** Create and participate in image boards on different topics.
*   **Text Board:** A text-only board for discussions.
*   **Customizable Themes:** The look and feel of the boards can be customized with different themes, including glassy, acrylic, and Frutiger Aero.
*   **API:** A simple API to fetch text posts.

## Getting Started

1.  **Clone the repository:**

    ```
    git clone https://github.com/korrykatti/python-image-board.git
    ```

2.  **Install the dependencies:**

    ```
    pip install -r requirements.txt
    ```

3.  **Run the application:**

    ```
    python main.py
    ```

## Text Board API

You can fetch a single text post by its ID using the following API endpoint:

```
/api/post/<post_id>
```

**Example response:**

```json
{
    "title": "Hello, world!",
    "content": "This is my first post on the text board.",
    "timestamp": 1678886400
}
```