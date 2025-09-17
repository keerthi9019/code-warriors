
import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
import pickle
import json

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///freshkeeper.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    food_items = db.relationship('FoodItem', backref='user', lazy=True, cascade='all, delete-orphan')

class FoodItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    purchase_date = db.Column(db.Date, nullable=False)
    predicted_expiry = db.Column(db.Date, nullable=False)
    actual_expiry = db.Column(db.Date, nullable=True)
    storage_condition = db.Column(db.String(50), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    is_consumed = db.Column(db.Boolean, default=False)
    is_wasted = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    ingredients = db.Column(db.Text, nullable=False)  # JSON string
    instructions = db.Column(db.Text, nullable=False)
    prep_time = db.Column(db.Integer, nullable=False)  # minutes
    category = db.Column(db.String(50), nullable=False)

class PreservationTip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    food_category = db.Column(db.String(50), nullable=False)
    tip_title = db.Column(db.String(200), nullable=False)
    tip_content = db.Column(db.Text, nullable=False)
    effectiveness_rating = db.Column(db.Integer, nullable=False)  # 1-5 stars

# ML Model for Expiration Prediction
class ExpirationPredictor:
    def __init__(self):
        self.model = None
        self.is_trained = False

    def prepare_features(self, food_name, category, storage_condition, purchase_date):
        # Create feature vector for prediction
        features = {
            'days_since_purchase': (datetime.now().date() - purchase_date).days,
            'storage_temp': self._get_storage_temp(storage_condition),
            'food_type_score': self._get_food_type_score(category),
            'seasonal_factor': self._get_seasonal_factor()
        }
        return np.array(list(features.values())).reshape(1, -1)

    def _get_storage_temp(self, condition):
        temps = {'refrigerated': 4, 'frozen': -18, 'pantry': 20, 'room_temp': 22}
        return temps.get(condition, 20)

    def _get_food_type_score(self, category):
        scores = {'dairy': 3, 'meat': 2, 'vegetables': 5, 'fruits': 4, 'grains': 8, 'canned': 10}
        return scores.get(category, 5)

    def _get_seasonal_factor(self):
        month = datetime.now().month
        if month in [6, 7, 8]:  # Summer
            return 0.8
        elif month in [12, 1, 2]:  # Winter
            return 1.2
        return 1.0

    def predict_expiry_days(self, food_name, category, storage_condition, purchase_date):
        # Fallback prediction based on food category if model not trained
        default_days = {
            'dairy': 7,
            'meat': 3,
            'vegetables': 5,
            'fruits': 7,
            'grains': 365,
            'canned': 730
        }
        return default_days.get(category, 7)

# Initialize predictor
predictor = ExpirationPredictor()

# Routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        # Check if user exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('Email already exists')
            return redirect(url_for('register'))

        # Create new user
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )

        db.session.add(user)
        db.session.commit()

        flash('Registration successful!')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Get user's food items
    food_items = FoodItem.query.filter_by(user_id=current_user.id, is_consumed=False, is_wasted=False).all()

    # Calculate expiring items (within 3 days)
    expiring_soon = []
    for item in food_items:
        days_until_expiry = (item.predicted_expiry - datetime.now().date()).days
        if days_until_expiry <= 3:
            expiring_soon.append({
                'item': item,
                'days_left': days_until_expiry
            })

    # Calculate stats
    total_items = len(food_items)
    items_expiring = len(expiring_soon)

    return render_template('dashboard.html', 
                         food_items=food_items,
                         expiring_soon=expiring_soon,
                         total_items=total_items,
                         items_expiring=items_expiring)

@app.route('/add_food', methods=['GET', 'POST'])
@login_required
def add_food():
    if request.method == 'POST':
        name = request.form['name']
        category = request.form['category']
        purchase_date = datetime.strptime(request.form['purchase_date'], '%Y-%m-%d').date()
        storage_condition = request.form['storage_condition']
        quantity = float(request.form['quantity'])
        unit = request.form['unit']

        # Predict expiry date
        predicted_days = predictor.predict_expiry_days(name, category, storage_condition, purchase_date)
        predicted_expiry = purchase_date + timedelta(days=predicted_days)

        # Create new food item
        food_item = FoodItem(
            name=name,
            category=category,
            purchase_date=purchase_date,
            predicted_expiry=predicted_expiry,
            storage_condition=storage_condition,
            quantity=quantity,
            unit=unit,
            user_id=current_user.id
        )

        db.session.add(food_item)
        db.session.commit()

        flash(f'Added {name} to your inventory!')
        return redirect(url_for('inventory'))

    return render_template('add_food.html')

@app.route('/inventory')
@login_required
def inventory():
    food_items = FoodItem.query.filter_by(user_id=current_user.id).all()
    return render_template('inventory.html', food_items=food_items)

@app.route('/recipes')
@login_required
def recipes():
    # Get expiring ingredients
    expiring_items = FoodItem.query.filter_by(
        user_id=current_user.id, 
        is_consumed=False, 
        is_wasted=False
    ).filter(
        FoodItem.predicted_expiry <= datetime.now().date() + timedelta(days=3)
    ).all()

    # Get sample recipes (in a real app, this would use an API)
    sample_recipes = Recipe.query.all()

    return render_template('recipes.html', 
                         expiring_items=expiring_items,
                         recipes=sample_recipes)

@app.route('/preservation')
@login_required
def preservation():
    tips = PreservationTip.query.all()
    return render_template('preservation.html', tips=tips)

@app.route('/donate')
@login_required
def donate():
    return render_template('donate.html')

@app.route('/analytics')
@login_required
def analytics():
    # Calculate waste statistics
    all_items = FoodItem.query.filter_by(user_id=current_user.id).all()
    total_items = len(all_items)
    wasted_items = len([item for item in all_items if item.is_wasted])
    consumed_items = len([item for item in all_items if item.is_consumed])

    waste_percentage = (wasted_items / total_items * 100) if total_items > 0 else 0

    # Monthly waste data for chart
    monthly_data = {}
    for item in all_items:
        month = item.created_at.strftime('%Y-%m')
        if month not in monthly_data:
            monthly_data[month] = {'total': 0, 'wasted': 0}
        monthly_data[month]['total'] += 1
        if item.is_wasted:
            monthly_data[month]['wasted'] += 1

    return render_template('analytics.html',
                         total_items=total_items,
                         wasted_items=wasted_items,
                         consumed_items=consumed_items,
                         waste_percentage=waste_percentage,
                         monthly_data=monthly_data)

@app.route('/update_item_status/<int:item_id>/<status>')
@login_required
def update_item_status(item_id, status):
    item = FoodItem.query.get_or_404(item_id)

    if item.user_id != current_user.id:
        flash('Unauthorized access')
        return redirect(url_for('inventory'))

    if status == 'consumed':
        item.is_consumed = True
    elif status == 'wasted':
        item.is_wasted = True

    db.session.commit()
    flash(f'Item marked as {status}')
    return redirect(url_for('inventory'))

# Initialize database and sample data
def init_db():
    with app.app_context():
        db.create_all()

        # Add sample recipes if none exist
        if Recipe.query.count() == 0:
            sample_recipes = [
                Recipe(
                    title="Vegetable Stir Fry",
                    ingredients='["Mixed vegetables", "Soy sauce", "Garlic", "Oil"]',
                    instructions="Heat oil in pan. Add garlic, then vegetables. Stir fry for 5-7 minutes. Add soy sauce.",
                    prep_time=15,
                    category="vegetables"
                ),
                Recipe(
                    title="Fruit Smoothie",
                    ingredients='["Overripe fruits", "Yogurt", "Honey", "Ice"]',
                    instructions="Blend all ingredients until smooth. Serve immediately.",
                    prep_time=5,
                    category="fruits"
                ),
                Recipe(
                    title="Leftover Soup",
                    ingredients='["Leftover vegetables", "Broth", "Herbs", "Salt"]',
                    instructions="Simmer vegetables in broth for 20 minutes. Season with herbs and salt.",
                    prep_time=25,
                    category="vegetables"
                )
            ]

            for recipe in sample_recipes:
                db.session.add(recipe)

        # Add sample preservation tips
        if PreservationTip.query.count() == 0:
            sample_tips = [
                PreservationTip(
                    food_category="fruits",
                    tip_title="Keep Bananas Fresh Longer",
                    tip_content="Wrap banana stems in plastic wrap to slow ripening. Store bananas away from other fruits.",
                    effectiveness_rating=4
                ),
                PreservationTip(
                    food_category="vegetables",
                    tip_title="Revive Wilted Greens",
                    tip_content="Soak wilted lettuce and herbs in ice water for 10-15 minutes to restore crispness.",
                    effectiveness_rating=5
                ),
                PreservationTip(
                    food_category="dairy",
                    tip_title="Freeze Milk Before Expiry",
                    tip_content="Milk can be frozen up to 3 months. Thaw in refrigerator and shake well before use.",
                    effectiveness_rating=3
                )
            ]

            for tip in sample_tips:
                db.session.add(tip)

        db.session.commit()

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
