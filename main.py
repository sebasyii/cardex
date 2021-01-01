import os
from datetime import datetime
from pathlib import Path

import requests
from flask import Flask, render_template, redirect, request, flash
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///car.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "A RANDOM KEY"
PATH = os.path.join(app.root_path, 'static/images')
app.config['UPLOAD_FOLDER'] = PATH
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
db = SQLAlchemy(app)
Migrate(app, db)


# Models

class Car(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    make = db.Column(db.String(200))
    model = db.Column(db.String(200))
    sub_model = db.Column(db.String(200))
    version = db.Column(db.String(200))
    price = db.Column(db.Float)
    image = db.Column(db.String(200))
    date_created = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"{self.make} {self.model} {self.sub_model} {self.version} {self.price}"


@app.template_filter()
def currencyFormat(value):
    value = float(value)
    return "${:,.2f}".format(value)


@app.route('/')
def index():
    cars = Car.query.order_by(Car.date_created).all()
    if not cars:
        flash("Oh! You do not have any cars listing. Please add one!")
    return render_template("index.html", cars=cars)


@app.route('/admin')
def admin():
    return render_template("admin.html")


@app.route('/add', methods=['POST', 'GET'])
def add():
    if request.method == "POST":
        car_make = request.form.get('car_make')
        car_model = request.form.get('car_model')
        car_submodel = request.form.get('car_submodel')
        car_version = request.form.get('car_version')
        car_price = request.form.get('car_price')
        car_image = request.files['file']

        new_car_db_model = Car(make=car_make, model=car_model, sub_model=car_submodel, version=car_version,
                               price=car_price, image="")
        try:
            if car_make and car_model and car_submodel and car_version and car_price:
                try:
                    f = secure_filename(car_image.filename)
                    car_image.save(os.path.join(app.config['UPLOAD_FOLDER'], f))
                    url = os.path.join('images', car_image.filename)
                    new_car_db_model.image = url
                except:
                    return 'There was an issue saving your Image'
                db.session.add(new_car_db_model)
                db.session.commit()
            return redirect(request.url)
        except:
            return 'There was an issue adding your Car Model.'
    else:
        return render_template("add.html")


@app.route('/<make>/<model>/<sub_model>/')
def car_page(make, model, sub_model):
    labels = []
    class_values_dict = []
    car = Car.query.filter_by(make=make).filter_by(model=model).filter_by(sub_model=sub_model).first_or_404()
    resp = requests.get(
        "https://data.gov.sg/api/action/datastore_search?resource_id=f7bbdc43-c568-4e60-9afa-b77ba5a14aa0")
    if resp.status_code == 200:
        data = resp.json()["result"]["records"]
        labels = list(set([content['month'] for content in data]))
        labels = sorted(labels)
        cat_a_values = [content["premium"] for content in data if content["vehicle_class"] == 'Category A']
        cat_b_values = [content["premium"] for content in data if content["vehicle_class"] == 'Category B']
        cat_c_values = [content["premium"] for content in data if content["vehicle_class"] == 'Category C']
        cat_d_values = [content["premium"] for content in data if content["vehicle_class"] == 'Category D']
        cat_e_values = [content["premium"] for content in data if content["vehicle_class"] == 'Category E']
        lst_of_values = [cat_a_values, cat_b_values, cat_c_values, cat_d_values, cat_e_values]

        vehicle_class = list(set(content["vehicle_class"] for content in data))
        vehicle_class = sorted(vehicle_class)
        class_values_dict = dict(zip(vehicle_class, lst_of_values))
        print(class_values_dict)

    if car:
        return render_template('car.html', car=car, title="COE Premiums over the Years", labels=labels,
                               values=class_values_dict)
    else:
        redirect('/')


@app.route('/delete/<int:id>')
def delete_car(id):
    car_obj = Car.query.get_or_404(id)

    try:
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], Path(car_obj.image).name))
        db.session.delete(car_obj)
        db.session.commit()
        return redirect('/')
    except:
        return 'There was a problem deleting that task.'


@app.route('/update/<int:id>', methods=["POST", "GET"])
def update_car_info(id):
    car_info = Car.query.get_or_404(id)

    if request.method == "POST":
        curr_image = car_info.image

        car_info.make = request.form.get('car_make')
        car_info.model = request.form.get('car_model')
        car_info.submodel = request.form.get('car_submodel')
        car_info.version = request.form.get('car_version')
        car_info.price = request.form.get('car_price')
        car_info.image = request.files['file']
        # If the file data has changed, remove all picture and then update the picture
        if car_info.image:
            try:
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], Path(curr_image).name))
            except:
                pass
            f = secure_filename(car_info.image.filename)
            car_info.image.save(os.path.join(app.config['UPLOAD_FOLDER'], car_info.image.filename))
            url = os.path.join('images', car_info.image.filename)
            car_info.image = url

        else:
            car_info.image = curr_image
        try:
            db.session.commit()
            return redirect('/')
        except:
            return 'There was a problem updating that Car listing.'

    else:
        return render_template("update.html", car=car_info)


if __name__ == '__main__':
    app.run(debug=True, port=8080)
