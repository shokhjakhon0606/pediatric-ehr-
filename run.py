from app import create_app, db
from app.models import Doctor

app = create_app()

# Create tables + seed default doctor account
with app.app_context():
    db.create_all()

    default_email = "admin@ehr.com"
    default_username = "admin"

    existing = Doctor.query.filter_by(email=default_email).first()
    if not existing:
        d = Doctor(username=default_username, email=default_email)
        d.set_password("admin123")  # saves into password_hash
        db.session.add(d)
        db.session.commit()
        print("✅ Default doctor/admin created:", default_email)

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )