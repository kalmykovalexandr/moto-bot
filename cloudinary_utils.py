import os

import cloudinary.uploader

# Cloudinary configuration
# cloudinary.config(
#     cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
#     api_key=os.getenv("CLOUDINARY_API_KEY"),
#     api_secret=os.getenv("CLOUDINARY_API_SECRET")
# )

cloudinary.config(
    cloud_name="djzcaugul",
    api_key="973924154917292",
    api_secret="tiYTBhu78EXnkQLXqUi-0sR_uUc"
)

def upload_image(temp_path):
    return cloudinary.uploader.upload(temp_path)

def delete_image(public_id):
    cloudinary.uploader.destroy(public_id)