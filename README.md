# Blindsoft Image Describer (Self-Hosted)

A fully accessible Discord bot designed to help blind and low-vision users by describing images and reading text using Google's Gemini AI and Tesseract OCR.

**Repository:** [https://github.com/averlice/blindsoft-image-describer](https://github.com/averlice/blindsoft-image-describer)

## Features

*   **Image Description:** Uses Google's Gemini 2.5 models to provide detailed, accessibility-focused descriptions of attached images.
*   **OCR (Optical Character Recognition):** Extracts text from images using Tesseract, useful for reading screenshots or documents.
*   **Accessibility First:** All bot responses are formatted to be screen-reader friendly.

## Installation & Setup

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/averlice/blindsoft-image-describer.git
    cd blindsoft-image-describer
    ```

2.  **Install Python Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Install Tesseract OCR:**
    *   **Windows:** Download the installer from [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki). Install it to the default location (`C:\Program Files\Tesseract-OCR`).
    *   **Linux:** `sudo apt-get install tesseract-ocr`
    *   **macOS:** `brew install tesseract`

4.  **Configuration:**
    *   Rename `.env.example` to `.env`.
    *   Open `.env` and fill in your credentials:
        ```env
        DISCORD_BOT_TOKEN=your_discord_bot_token
        OWNER_ID=your_discord_user_id
        GEMINI_API_KEY=your_gemini_api_key
        ```

5.  **Run the Bot:**
    ```bash
    python main.py
    ```

## Commands

The default prefix is `alii!`.

*   `alii!describe`: Attach an image to get a detailed description.
*   `alii!ocr`: Attach an image (or provide a URL) to extract text from it.
*   `alii!ping`: Check bot latency and uptime.
*   `alii!help`: List all available commands.

---
*Powered by Blindsoft*