from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Float
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FloatField
from wtforms.validators import DataRequired, NumberRange
import requests
import os

app = Flask(__name__)
# set bootstrap 5
app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
Bootstrap5(app)
# set the TMDB API (header and parameters)
API_KEY = os.environ['API_KEY']
IMG_PATH = 'https://image.tmdb.org/t/p/original/'

headers = {
    "accept": "application/json",
}

params = {
    "api_key": API_KEY,
}


# create the DB
class Base(DeclarativeBase):
    pass


# configure a form to update movie data
class MovieForm(FlaskForm):
    new_rating = FloatField(label='New Rating', validators=[
        DataRequired(),
        NumberRange(min=0, max=10, message='Not Valid Number'),
    ])
    new_review = StringField(label='New Review', validators=[
        DataRequired(),
    ])
    submit = SubmitField('Submit')


# configure a form to add movie
class AddMovie(FlaskForm):
    title = StringField(label='Title', validators=[
        DataRequired(),
    ])
    submit = SubmitField('Submit')


# locate the DB
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///movies-collections.db"

db = SQLAlchemy(model_class=Base)
db.init_app(app)


# create a table
class Movies(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    rating: Mapped[str] = mapped_column(Float, nullable=False)
    raking: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    review: Mapped[str] = mapped_column(String, nullable=False)
    img_url: Mapped[str] = mapped_column(String, nullable=False)


# Create table schema in the database. Requires application context.
with app.app_context():
    db.create_all()


# function to add movies
def add_movie(title, year, description, rating, raking, review, img_url):
    with app.app_context():
        movie = Movies(
            title=title,
            year=year,
            description=description,
            rating=rating,
            raking=raking,
            review=review,
            img_url=img_url,
        )
        db.session.add(movie)
        db.session.commit()


@app.route("/")
def home():
    # get all the movies, order by rating
    with app.app_context():
        result = db.session.execute(db.select(Movies).order_by(Movies.rating))
        all_movies = result.scalars().all()
    # set up the ranking
    for i in range(len(all_movies)):
        all_movies[i].raking = len(all_movies) - i
    db.session.commit()

    return render_template("index.html", movies=all_movies)


@app.route("/edit/<movie_title>", methods=['GET', 'POST'])
def edit(movie_title):
    # create the form object
    form = MovieForm()
    # select movie by title
    with app.app_context():
        movie = db.session.execute(db.select(Movies).where(Movies.title == movie_title)).scalar()
    # update the rating and review
    if form.validate_on_submit():
        new_rating = request.form["new_rating"]
        new_review = request.form["new_review"]

        with app.app_context():
            movie_to_update = db.session.execute(db.select(Movies).where(Movies.title == movie_title)).scalar()
            movie_to_update.rating = new_rating
            movie_to_update.review = new_review
            db.session.commit()

        return redirect(url_for('home'))

    return render_template("edit.html", movie=movie, form=form)


@app.route("/delete/<movie_title>")
def delete(movie_title):
    # delete movie by title
    with app.app_context():
        movie_to_delete = db.session.execute(db.select(Movies).where(Movies.title == movie_title)).scalar()
        db.session.delete(movie_to_delete)
        db.session.commit()

    return redirect(url_for('home'))


@app.route("/add", methods=['GET', 'POST'])
def add():
    # create form object
    form = AddMovie()
    # from the API get movies with the match name
    if form.validate_on_submit():
        title = request.form["title"]
        url = f"https://api.themoviedb.org/3/search/movie?query={title}&include_adult=false&language=en-US&page=1"
        response = requests.get(url, headers=headers, params=params)
        movies_response = response.json()
        movies_data = movies_response['results']

        movies_result = [{'id': movie['id'], 'title': movie['original_title'], 'release_date': movie['release_date']}
                         for movie in movies_data]

        return render_template('select.html', movies=movies_result, movies_number=len(movies_result))

    return render_template("add.html", form=form)


@app.route("/select/<int:movie_id>")
def select(movie_id):
    # add basic information to the DB, from the selected movie
    url = f"https://api.themoviedb.org/3/movie/{movie_id}?language=en-US"
    response = requests.get(url, headers=headers, params=params)

    movie_data = response.json()

    add_movie(
        title=movie_data['original_title'],
        year=movie_data['release_date'].split("-")[0],
        description=movie_data['overview'],
        rating=0,
        raking=0,
        review='None',
        img_url=f'{IMG_PATH}{movie_data['poster_path']}'
    )

    return redirect(url_for('edit', movie_title=movie_data['original_title']))


if __name__ == '__main__':
    app.run(debug=True)
