import os
import json
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv  # <-- Load dotenv

# Load variables from the .env file
load_dotenv()

from google import genai
from seed_data import recipes_data

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super-secret-recipematch-key'
basedir = os.path.abspath(os.path.dirname(__name__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'recipematch.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Initialize the GenAI Client securely using the environment variable
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ================= DB MODELS =================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150))
    email = db.Column(db.String(150), unique=True)
    password_hash = db.Column(db.String(256))

class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    recipe_name = db.Column(db.String(200))
    description = db.Column(db.Text)
    prep_time = db.Column(db.Integer)
    difficulty = db.Column(db.String(50))
    category = db.Column(db.String(100), default="Main Course")
    ingredients = db.relationship('RecipeIngredient', backref='recipe', lazy=True, cascade="all, delete-orphan")
    instructions = db.relationship('RecipeInstruction', backref='recipe', lazy=True, cascade="all, delete-orphan")

class RecipeIngredient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'))
    name = db.Column(db.String(100)) 
    quantity = db.Column(db.String(50))
    unit = db.Column(db.String(50))

class RecipeInstruction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'))
    step_number = db.Column(db.Integer)
    instruction = db.Column(db.Text)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ================= ROUTES =================
@app.route('/')
def index():
    return render_template('landing.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'error')
            return redirect(url_for('register'))
        user = User(full_name=request.form.get('full_name'), email=email, password_hash=generate_password_hash(request.form.get('password')))
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('discover'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form.get('email')).first()
        if user and check_password_hash(user.password_hash, request.form.get('password')):
            login_user(user)
            return redirect(url_for('discover'))
        flash('Invalid credentials.', 'error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/discover')
@login_required
def discover():
    all_recipes = Recipe.query.all()
    categorized_recipes = {}
    for recipe in all_recipes:
        categorized_recipes.setdefault(recipe.category, []).append(recipe)
    return render_template('discover.html', categorized_recipes=categorized_recipes)

@app.route('/search', methods=['POST'])
@login_required
def search():
    query = request.form.get('search_query', '').strip()
    if not query: 
        return redirect(url_for('discover'))
    recipes = Recipe.query.filter(Recipe.recipe_name.ilike(f'%{query}%')).all()
    results = [{'recipe': r, 'match_pct': 100, 'missing_count': 0, 'missing_names': []} for r in recipes]
    return render_template('recipe_results.html', results=results, query=query)

@app.route('/generate-ai-recipe', methods=['POST'])
@login_required
def generate_ai_recipe():
    query = request.form.get('search_query', '').strip()
    custom_ings = request.form.getlist('custom_ingredients')
    
    all_inputs = []
    if query: 
        all_inputs.append(query)
    all_inputs.extend(custom_ings)
    
    if not all_inputs:
        flash('Please type ingredients or a recipe idea first.', 'error')
        return redirect(url_for('discover'))

    prompt = f"""
    The user entered: "{', '.join(all_inputs)}".
    Invent a creative recipe using these.
    Respond STRICTLY in valid JSON format:
    {{
        "recipe_name": "Name", "description": "Desc", "prep_time": 25, "difficulty": "Medium",
        "ingredients": [ {{"name": "ing", "quantity": "amt", "unit": "unit"}} ],
        "instructions": [ "Step 1", "Step 2" ]
    }}
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        raw_text = response.text.strip()
        
        if "```json" in raw_text:
            raw_text = raw_text.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_text:
            raw_text = raw_text.split("```")[1].split("```")[0].strip()
            
        ai_recipe = json.loads(raw_text)
        return render_template('ai_recipe_details.html', recipe=ai_recipe, original_ingredients=all_inputs)
    except Exception as e:
        flash(f'AI chef is busy: {str(e)}', 'error')
        return redirect(url_for('discover'))

@app.route('/recipe/<int:id>')
def recipe_details(id):
    recipe = Recipe.query.get_or_404(id)
    return render_template('recipe_details.html', recipe=recipe)

@app.route('/add-recipe', methods=['GET', 'POST'])
@login_required
def add_recipe():
    if request.method == 'POST':
        recipe = Recipe(
            user_id=current_user.id,
            recipe_name=request.form.get('recipe_name'),
            description=request.form.get('description'),
            prep_time=request.form.get('prep_time'),
            difficulty=request.form.get('difficulty'),
            category=request.form.get('category')
        )
        db.session.add(recipe)
        db.session.flush()
        
        names = request.form.getlist('ingredient_name[]')
        quants = request.form.getlist('quantity[]')
        units = request.form.getlist('unit[]')
        for i in range(len(names)):
            if names[i]: 
                db.session.add(RecipeIngredient(recipe_id=recipe.id, name=names[i], quantity=quants[i], unit=units[i]))
                
        steps = request.form.getlist('instruction[]')
        for i, step_text in enumerate(steps):
            if step_text.strip(): 
                db.session.add(RecipeInstruction(recipe_id=recipe.id, step_number=i+1, instruction=step_text))
                
        db.session.commit()
        flash('Recipe added successfully!', 'success')
        return redirect(url_for('recipe_details', id=recipe.id))
    return render_template('add_recipe.html')

# ================= DATABASE INITIALIZATION & SEEDING =================
with app.app_context():
    db.create_all()
    if not User.query.first():
        test_user = User(full_name="Admin", email="admin@test.com", password_hash=generate_password_hash("password"))
        db.session.add(test_user)
        db.session.flush()

        for r_data in recipes_data:
            recipe = Recipe(
                user_id=test_user.id,
                recipe_name=r_data["name"],
                description=f"Delicious homemade {r_data['name']}.",
                prep_time=r_data["time"],
                difficulty="Easy" if r_data["time"] <= 15 else "Medium",
                category=r_data["cat"]
            )
            db.session.add(recipe)
            db.session.flush()

            for ing in r_data["ings"]:
                db.session.add(RecipeIngredient(recipe_id=recipe.id, name=ing[0], quantity=ing[1], unit=ing[2]))
            for idx, step in enumerate(r_data["inst"]):
                db.session.add(RecipeInstruction(recipe_id=recipe.id, step_number=idx+1, instruction=step))

        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)