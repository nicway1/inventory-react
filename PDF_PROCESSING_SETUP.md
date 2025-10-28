# PDF Processing Setup for Knowledge Base

This document explains how to enable PDF import functionality for Knowledge Base articles.

## Required Python Libraries

To use the PDF import feature, you need to install the following libraries:

### 1. PyPDF2 (for text extraction)
```bash
pip install PyPDF2
```

### 2. PyMuPDF (for image extraction)
```bash
pip install PyMuPDF
```

## Installation Steps

1. Activate your virtual environment (if using one):
```bash
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows
```

2. Install the required packages:
```bash
pip install PyPDF2 PyMuPDF
```

3. Verify installation:
```bash
python3 -c "import PyPDF2; import fitz; print('PDF libraries installed successfully!')"
```

## Features

Once installed, the PDF import feature will:

1. **Extract Text**: Automatically extracts all text from the PDF and populates the article content with HTML formatting
2. **Auto-Insert Images**: Automatically extracts content images from the PDF and inserts them throughout the article
3. **Smart Image Filtering**: Automatically skips background images, logos, headers, and decorative elements:
   - Filters out small images (< 100x100 pixels)
   - Skips icons and logos (< 5KB file size)
   - Ignores background images (> 80% page coverage)
   - Removes header images (top 10% of page)
4. **Auto-fill Title**: Generates a title from the PDF filename or first line of text
5. **Auto-fill Summary**: Creates a summary from the first 200 characters
6. **Smart Formatting**: Intelligently formats paragraphs, headings, and text structure
7. **Preview**: Click "Preview" button to see how the article will look before publishing
8. **Text Cleaning**: Automatically fixes common PDF extraction issues like spaced-out characters

## Usage

1. Go to Knowledge Base > Create New Article
2. Click the "Upload PDF" button at the top of the form
3. Select a PDF file
4. Wait for processing (you'll see a spinner)
5. The form will be auto-filled with:
   - Title (from PDF)
   - Content (extracted text with images automatically inserted)
   - Summary (first 200 chars)
6. Click the "Preview" button to see how the article will look
7. Edit the content as needed
8. Choose status (Draft or Published)
9. Save the article

## Troubleshooting

### "PDF processing libraries not installed" error
- Make sure you've installed both PyPDF2 and PyMuPDF
- Restart your Flask application after installing the libraries

### Images not extracting
- Some PDFs may not contain embedded images (they might be scanned as one large image per page)
- Try a different PDF or manually upload images

### Text extraction issues
- Some PDFs (especially scanned documents) may not contain extractable text
- Consider using OCR tools for scanned PDFs

## File Storage

Extracted images are stored in:
```
static/uploads/knowledge/pdf_images/
```

Make sure this directory has write permissions.

## Alternative: Manual OCR

For scanned PDFs without extractable text, consider using:
- Tesseract OCR
- Adobe Acrobat's OCR feature
- Online OCR tools

Then export as a text-based PDF before importing.
