import os
import uuid
import firebase_admin
from firebase_admin import credentials, storage
from django.conf import settings

cred = credentials.Certificate(settings.FIREBASE_CERTIFICATE)
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        'storageBucket': settings.FIREBASE_STORAGE_BUCKET_URL
    })

def upload_image_to_firebase(image_file):
    try:
        bucket = storage.bucket()
        
        file_extension = os.path.splitext(image_file.name)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        
        blob = bucket.blob(f"thumbnails/{unique_filename}")
        blob.upload_from_file(image_file, content_type=image_file.content_type)
        
        blob.make_public()
        
        return blob.public_url
    
    except Exception as e:
        raise Exception(f"Failed to upload image to Firebase: {str(e)}") 