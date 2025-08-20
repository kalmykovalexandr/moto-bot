import cloudinary
import cloudinary.uploader

from configs.config import CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET
)


def upload_image(temp_path: str):
    return cloudinary.uploader.upload(temp_path)


def delete_image(public_id: str):
    cloudinary.uploader.destroy(public_id)
