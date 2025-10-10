from flask import Blueprint, request, jsonify, render_template, current_app
import os
from app.modules.booking_utils import handle_booking as real_book_slot
from app.routes.files import upload_file as real_upload_file
from app.routes.ai_router import route_message as real_handle_message
from app.modules.logger import get_logger
import logging
from flask_restx import Namespace, Resource, fields

api_bp = Blueprint('api', __name__)
logger = logging.getLogger(__name__)

api_ns = Namespace('api', description='REST API')

booking_model = api_ns.model('Booking', {
    'name': fields.String(required=True, description='Имя клиента'),
    'email': fields.String(required=True, description='Email клиента'),
    'date': fields.String(required=True, description='Дата бронирования'),
})

@api_bp.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    message = data.get("message", "")
    # Имитация ответа эксперта
    return jsonify(reply=f"Вы сказали: {message}")

@api_bp.route("/upload", methods=["POST"])
def upload():
    if 'file' not in request.files:
        return jsonify(error="Нет файла в запросе"), 400
    file = request.files["file"]
    os.makedirs("uploads", exist_ok=True)
    file_path = os.path.join("uploads", file.filename)
    file.save(file_path)
    return jsonify(file_id=file.filename)

@api_ns.route('/book')
class BookResource(Resource):
    @api_ns.expect(booking_model)
    @api_ns.response(200, 'Успешно')
    def post(self):
        """Создать бронирование"""
        data = request.get_json()
        # Здесь логика бронирования
        return {'success': True}, 200

@api_bp.route('/knowledge/<type>', methods=['GET'])
def get_knowledge(type):
    base_path = os.path.join(current_app.root_path, '..', 'knowledge_base')
    
    if type == 'training':
        training_info = []
        
        # FAQ и EMS данные
        files_to_read = [
            ('wakesurfing_tips.txt/FAQБАтут.txt', 'utf-8'),
            ('wakesurfing_tips.txt/EMS Training.txt', 'utf-8')
        ]
        
        for file_path, encoding in files_to_read:
            full_path = os.path.join(base_path, file_path)
            if os.path.exists(full_path):
                try:
                    with open(full_path, 'r', encoding=encoding) as f:
                        content = f.read()
                        # Фильтруем пустые строки и добавляем параграфы
                        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
                        training_info.extend(paragraphs)
                except Exception as e:
                    current_app.logger.error(f"Error reading {file_path}: {str(e)}")
        
        return jsonify(training_info)
        
    elif type == 'tricks':
        tricks_path = os.path.join(base_path, 'tricks.txt', 'Список трюков по вейксерфу.txt')
        try:
            if os.path.exists(tricks_path):
                with open(tricks_path, 'r', encoding='utf-8') as f:
                    tricks = [line.strip() for line in f.readlines() if line.strip()]
                    return jsonify(tricks)
        except Exception as e:
            current_app.logger.error(f"Error reading tricks file: {str(e)}")
            
    return jsonify({'error': 'Invalid knowledge type or file not found'})

@api_bp.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404
