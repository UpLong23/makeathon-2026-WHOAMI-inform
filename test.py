import kagglehub

# Download latest version
path = kagglehub.dataset_download("osamahosamabdellatif/high-quality-invoice-images-for-ocr")

print("Path to dataset files:", path)