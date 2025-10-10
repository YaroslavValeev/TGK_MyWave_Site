from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, IntegerField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange

class ReviewForm(FlaskForm):
    name = StringField('Ваше имя', validators=[DataRequired(), Length(min=2, max=100)])
    rating = IntegerField('Оценка', validators=[DataRequired(), NumberRange(min=1, max=5)])
    text = TextAreaField('Отзыв', validators=[DataRequired(), Length(min=5, max=1000)])
    submit = SubmitField('Оставить отзыв') 