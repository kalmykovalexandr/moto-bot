import cloudinary.uploader

from config import *

# Cloudinary configuration
cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET
)

def upload_image(temp_path):
    return cloudinary.uploader.upload(temp_path)

def delete_image(public_id):
    cloudinary.uploader.destroy(public_id)