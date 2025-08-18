import os

import cloudinary.uploader

# Cloudinary configuration
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

def upload_image(temp_path):
    return cloudinary.uploader.upload(temp_path)

def delete_image(public_id):
    cloudinary.uploader.destroy(public_id)