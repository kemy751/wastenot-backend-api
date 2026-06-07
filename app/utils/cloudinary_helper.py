# app/utils/cloudinary_helper.py
"""
Central Cloudinary upload helper.
All file uploads go through upload_file() — returns a secure HTTPS URL.

Required environment variables:
  CLOUDINARY_CLOUD_NAME
  CLOUDINARY_API_KEY
  CLOUDINARY_API_SECRET

Install: pip install cloudinary
"""
import cloudinary
import cloudinary.uploader
import os

def _configure():
    cloudinary.config(
        cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME"),
        api_key    = os.environ.get("CLOUDINARY_API_KEY"),
        api_secret = os.environ.get("CLOUDINARY_API_SECRET"),
        secure     = True,
    )

def upload_file(file, folder: str = "greentag") -> str:
    """
    Upload a FileStorage or file-like object to Cloudinary.
    Returns the secure HTTPS URL of the uploaded file.

    :param file:   Flask FileStorage object (from request.files)
    :param folder: Cloudinary folder to organise uploads
    :raises Exception: if upload fails
    """
    _configure()
    result = cloudinary.uploader.upload(
        file,
        folder=folder,
        resource_type="image",
    )
    return result["secure_url"]