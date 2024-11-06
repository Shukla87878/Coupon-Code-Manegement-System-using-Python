from flask import Flask, jsonify, request, render_template
from flask_sqlalchemy import SQLAlchemy
import random
import string
from datetime import datetime
import logging

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///coupons.db'
db = SQLAlchemy(app)

# Set up logging configuration
logging.basicConfig(filename='app.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s')

class Coupon(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(6), unique=True, nullable=False)
    discount_type = db.Column(db.String(20), nullable=False)  # 'Absolute', 'Percentage', 'Fixed Price'
    discount_value = db.Column(db.Float, nullable=False)
    validity_start = db.Column(db.DateTime, nullable=True)
    validity_end = db.Column(db.DateTime, nullable=True)
    user_age_group = db.Column(db.String, nullable=True)  # e.g., '18-25'
    days_from_signup = db.Column(db.String, nullable=True)  # e.g., '[1,2,5]'
    is_deleted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def apply_coupon(self, user, product_price):
        """Method to apply coupon logic"""
        if self.discount_type == 'Absolute':
            return max(0, product_price - self.discount_value)
        elif self.discount_type == 'Percentage':
            return max(0, product_price - (product_price * (self.discount_value / 100)))
        elif self.discount_type == 'Fixed Price':
            return self.discount_value

    def __repr__(self):
        return f"Coupon('{self.code}', '{self.discount_type}', '{self.discount_value}')"

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)  # Added name attribute
    signup_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    age_group = db.Column(db.String, nullable=True)

    def get_days_since_signup(self):
        """Method to get days since signup"""
        return (datetime.utcnow() - self.signup_date).days
    
    def __repr__(self):
        return f"User('{self.name}', '{self.signup_date}', '{self.age_group}')"

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/simulate_user.html', methods=['GET'])
def simulate_user_page():
    return render_template('simulate_user.html')

@app.route('/simulate_user', methods=['POST'])
def simulate_user():
    """Simulate creating a user with specific details"""
    try:
        data = request.get_json()  # Get the JSON data from the request
        
        # Validate input data
        if not data:
            return jsonify({'message': 'No data provided'}), 400

        name = data.get('name')
        signup_date = data.get('signup_date')
        age_group = data.get('age_group', None)

        # Ensure the required fields are provided
        if not name:
            return jsonify({'message': 'Name is required for creating a user'}), 400
        if not signup_date:
            return jsonify({'message': 'Signup date is required for creating a user'}), 400

        # Try to parse the signup date
        try:
            # Expecting signup_date to be in 'YYYY-MM-DD' format
            signup_date = datetime.strptime(signup_date, '%Y-%m-%d')
        except ValueError:
            return jsonify({'message': 'Invalid signup date format, must be YYYY-MM-DD'}), 400

        # Create the new user
        user = User(name=name, signup_date=signup_date, age_group=age_group)
        db.session.add(user)
        db.session.commit()

        return jsonify({'message': 'User created successfully', 'user_id': user.id}), 201

    except Exception as e:
        logging.error(f"Error creating user: {e}")
        return jsonify({'message': f'Error creating user: {e}'}), 500

@app.route('/apply_coupon/<int:user_id>', methods=['POST'])
def apply_coupon(user_id):
    """Apply coupon to a product based on user and coupon criteria"""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'message': 'Invalid request, no data provided'}), 400

    product_price = data.get('product_price')
    coupon_code = data.get('coupon_code')

    if not product_price or not coupon_code:
        return jsonify({'message': 'Product price and coupon code are required'}), 400

    coupon = Coupon.query.filter_by(code=coupon_code, is_deleted=False).first()
    if not coupon:
        return jsonify({'message': 'Coupon not found or is deleted'}), 404

    # Handle user age group validation
    if coupon.user_age_group:
        age_group = user.age_group
        if not age_group or age_group not in coupon.user_age_group.split(','):
            return jsonify({'message': 'User not eligible for this coupon based on age group'}), 403

    # Handle days since signup validation
    days_since_signup = user.get_days_since_signup()
    if coupon.days_from_signup:
        try:
            valid_days = [int(day) for day in coupon.days_from_signup.strip('[]').split(',')]
            if days_since_signup not in valid_days:
                return jsonify({'message': 'User not eligible for this coupon based on days since signup'}), 403
        except ValueError:
            return jsonify({'message': 'Invalid days from signup data in coupon'}), 400

    discounted_price = coupon.apply_coupon(user, product_price)

    return jsonify({'discounted_price': discounted_price}), 200

@app.route('/coupons', methods=['GET'])
def list_coupons():
    """List all coupons"""
    try:
        coupons = Coupon.query.filter_by(is_deleted=False).all()
        logging.info('Coupons listed successfully')
        return jsonify([{'id': c.id, 'code': c.code, 'discount_type': c.discount_type, 'discount_value': c.discount_value} for c in coupons])
    except Exception as e:
        logging.error(f'Error listing coupons: {e}')
        return jsonify({'message': 'Error listing coupons'}), 500

@app.route('/coupon/create', methods=['POST'])
def create_coupon():
    """Create a new coupon"""
    try:
        if not request.is_json:
            return jsonify({'message': 'Invalid input format, must be JSON'}), 400
        
        data = request.get_json()
        
        if 'discount_type' not in data or 'discount_value' not in data:
            return jsonify({'message': 'Missing required fields'}), 400
        
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        
        coupon = Coupon(
            code=code,
            discount_type=data['discount_type'],
            discount_value=data['discount_value'],
            user_age_group=data.get('user_age_group', ''),
            days_from_signup=data.get('days_from_signup', '')
        )
        
        db.session.add(coupon)
        db.session.commit()
        
        logging.info('Coupon created successfully')
        return jsonify({'message': 'Coupon created successfully', 'code': code}), 201
    except Exception as e:
        logging.error(f'Error creating coupon: {e}')
        return jsonify({'message': f'Error creating coupon: {e}'}), 500

@app.route('/coupon/update/<int:coupon_id>', methods=['PUT'])
def update_coupon(coupon_id):
    """Update coupon details"""
    try:
        coupon = db.session.get(Coupon, coupon_id)
        if not coupon or coupon.is_deleted:
            return jsonify({'message': 'Coupon not found'}), 404

        data = request.get_json()
        if 'discount_type' in data:
            coupon.discount_type = data['discount_type']
        if 'discount_value' in data:
            coupon.discount_value = data['discount_value']
        if 'user_age_group' in data:
            coupon.user_age_group = data['user_age_group']
        if 'days_from_signup' in data:
            coupon.days_from_signup = data['days_from_signup']

        db.session.commit()
        logging.info('Coupon updated successfully')
        return jsonify({'message': 'Coupon updated successfully'}), 200
    except Exception as e:
        logging.error(f'Error updating coupon: {e}')
        return jsonify({'message': f'Error updating coupon: {e}'}), 500

@app.route('/coupon/delete/<int:coupon_id>', methods=['DELETE'])
def delete_coupon(coupon_id):
    """Delete a coupon"""
    try:
        coupon = Coupon.query.get(coupon_id)
        if not coupon or coupon.is_deleted:
            return jsonify({'message': 'Coupon not found'}), 404

        coupon.is_deleted = True
        db.session.commit()

        logging.info(f'Coupon with ID {coupon_id} marked as deleted')
        return jsonify({'message': 'Coupon deleted successfully'}), 200
    except Exception as e:
        logging.error(f'Error deleting coupon: {e}')
        return jsonify({'message': f'Error deleting coupon: {e}'}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create database tables if they do not exist
    app.run(debug=True)  # Run the Flask app