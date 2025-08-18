import cloudinary.uploader

# Cloudinary configuration
cloudinary.config(
    cloud_name="dczhgkjpa",
    api_key="838981728989476",
    api_secret="0qgudi-oz4c8KNRUFsk7lTsXX3M"
)

def upload_image(temp_path):
    return cloudinary.uploader.upload(temp_path)

def delete_image(public_id):
    cloudinary.uploader.destroy(public_id)