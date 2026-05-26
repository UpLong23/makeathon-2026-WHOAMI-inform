import cv2
import numpy as np
import pytesseract
from pytesseract import Output
import pandas as pd

from config import TESSERACT_CMD, logger

pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD


def preprocess(img_path):
    """
    Grayscale + Otsu thresholding + slight dilation.
    Dramatically improves Tesseract accuracy on invoice scans.
    """
    img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(f"Could not read image: {img_path}")
    _, img = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # Slight dilation to reconnect broken characters
    kernel = np.ones((1, 1), np.uint8)
    img = cv2.dilate(img, kernel, iterations=1)
    return img


def extract_text(img):
    """
    Reconstructs invoice layout using word-level positional data.
    Handles two-column layouts by grouping words into rows by vertical
    proximity, then sorting each row left-to-right with column spacing.
    """
    dict_data = pytesseract.image_to_data(img, output_type=Output.DICT)
    df = pd.DataFrame(dict_data)
    # display(df)
    print(df["conf"].max())
    print(df["conf"].min())
    df = df[(df["conf"] != -1) & (df["text"].str.strip() != "")].copy()
    df["conf"] = df["conf"].astype(int)

    coordinates = []
    for index, row in df.iterrows():
        if row["text"] != "":
            # top-left corner, bottom-right corner
            coordinates.append(
                [(row["left"], row["top"]), (row["left"]+row["width"], row["top"]+row["height"])])

    if df.empty:
        return "", dict_data

    df = df.sort_values(by=["top", "left"]).reset_index(drop=True)
    rows = []
    current_row = [df.iloc[0]]

    for i in range(1, len(df)):
        word = df.iloc[i]
        last = current_row[-1]
        same_line = abs(word["top"] - last["top"]) <= 12

        if same_line:
            current_row.append(word)
        else:
            rows.append(current_row)
            current_row = [word]

    rows.append(current_row)
    all_lefts = df["left"].values
    page_width = int(df["left"].max() + df["width"].max())
    midpoint = page_width // 2
    raw_text = ""

    for row_words in rows:
        row_words_sorted = sorted(row_words, key=lambda w: w["left"])
        line = ""
        prev_right = 0
        for word in row_words_sorted:
            left = word["left"]
            text = word["text"]
            width = word["width"]

            # Calculate gap between previous word and this one
            gap = left - prev_right

            if prev_right == 0:
                line += text
            elif gap > midpoint * 0.2:
                line += "\t" + text
            elif gap > 15:
                line += " " + text
            else:
                line += " " + text

            prev_right = left + width

        raw_text += line.strip() + "\n"

    return raw_text.strip(), dict_data, coordinates


def run_ocr(img_path: str) -> str:
    logger.info("Preprocessing image: %s", img_path)
    img = preprocess(img_path)
    logger.info("Running Tesseract OCR")
    raw_text, _, coordinates = extract_text(img)

    # Check ocr's bounary boxes
    sample_img = cv2.imread(img_path)
    for c in coordinates:
        # print(c[0], c[1])
        cv2.rectangle(sample_img, c[0], c[1], color=(0, 0, 255))
    cv2.imwrite("test.png", sample_img)

    logger.info("OCR extracted %d characters", len(raw_text))
    return raw_text
