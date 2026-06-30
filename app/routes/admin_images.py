"""Admin routes for managing images"""
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required
from app.utils.decorators import admin_required
from app.services.images_service import save_image, get_image_url
import os

admin_images_bp = Blueprint('admin_images', __name__, url_prefix='/admin/images')

@admin_images_bp.route('/')
@login_required
@admin_required
def index():
    """Show image management interface"""
    return render_template('admin/images.html')

@admin_images_bp.route('/upload', methods=['POST'])
@login_required
@admin_required
def upload():
    """Handle image upload"""
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400

    file = request.files['image']
    if not file:
        return jsonify({'error': 'No file selected'}), 400

    try:
        # Save image with resizing
        upload_folder = os.path.join(current_app.static_folder, 'images')
        filename = save_image(file, upload_folder)
        
        if not filename:
            return jsonify({'error': 'Invalid file type'}), 400
            
        return jsonify({
            'success': True,
            'filename': filename,
            'urls': {
                'thumb': get_image_url(filename, 'thumb'),
                'small': get_image_url(filename, 'small'),
                'medium': get_image_url(filename, 'medium'),
                'large': get_image_url(filename, 'large'),
                'original': get_image_url(filename)
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error uploading image: {e}")
        return jsonify({'error': 'Error uploading image'}), 500

@admin_images_bp.route('/list')
@login_required
@admin_required
def list_images():
    """Get list of all images with their variations"""
    try:
        images_dir = os.path.join(current_app.static_folder, 'images')
        images = []
        
        for filename in os.listdir(images_dir):
            if os.path.isfile(os.path.join(images_dir, filename)):
                images.append({
                    'filename': filename,
                    'urls': {
                        'thumb': get_image_url(filename, 'thumb'),
                        'small': get_image_url(filename, 'small'),
                        'medium': get_image_url(filename, 'medium'),
                        'large': get_image_url(filename, 'large'),
                        'original': get_image_url(filename)
                    }
                })
                
        return jsonify({'images': images})
    except Exception as e:
        current_app.logger.error(f"Error listing images: {e}")
        return jsonify({'error': 'Error listing images'}), 500