from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from app.forms.contact_form import ContactForm
from app.database.models import db
from app.modules.sheets import append_row
from app.database.models import Contact
import re

contact_bp = Blueprint('contact', __name__, template_folder='../templates')


@contact_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    form = ContactForm()

    # Try normal WTForms validation, but fall back to a simple regex-based
    # validation if the Email validator dependency is missing (email_validator).
    is_valid = False
    try:
        is_valid = form.validate_on_submit()
    except Exception as e:
        # Log the exception for diagnosis and attempt a lightweight fallback
        current_app.logger.exception('Form validation failed; applying fallback validator')
        # Fallback: basic presence checks and a simple email regex
        if request.method == 'POST':
            name = (request.form.get('name') or '').strip()
            email = (request.form.get('email') or '').strip()
            message = (request.form.get('message') or '').strip()
            simple_email_ok = re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email)
            if name and simple_email_ok and message and 2 <= len(name) <= 100 and 5 <= len(message) <= 2000:
                # Populate form data so downstream code reads from same place
                form.name.data = name
                form.email.data = email
                form.message.data = message
                is_valid = True
            else:
                flash('Ошибка валидации формы. Пожалуйста, проверьте поля.', 'danger')

    if is_valid:
        name = form.name.data
        email = form.email.data
        message = form.message.data
        try:
            # Сохраняем в БД
            contact_obj = Contact(name=name, email=email, message=message)
            db.session.add(contact_obj)
            db.session.commit()
            # Сохраняем в Google Sheets
            append_row('ContactMessages', [name, email, message])
            flash('Ваше сообщение отправлено!', 'success')
            return redirect(url_for('contact.contact'))
        except Exception:
            db.session.rollback()
            flash('Ошибка при отправке сообщения. Попробуйте позже.', 'danger')

    return render_template('contact.html', form=form)
    