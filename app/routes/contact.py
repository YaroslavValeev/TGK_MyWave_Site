from flask import Blueprint, render_template, request, flash, redirect, url_for
from app.forms.contact_form import ContactForm
from app.database.models import db
from app.modules.sheets import append_row
from app.database.models import Contact

contact_bp = Blueprint('contact', __name__, template_folder='../templates')

@contact_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
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
        except Exception as e:
            db.session.rollback()
            flash('Ошибка при отправке сообщения. Попробуйте позже.', 'danger')
    return render_template('contact.html', form=form)
    