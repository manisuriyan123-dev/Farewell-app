"""
Batch 2026 Memory Vault - Main Application Module
A premium farewell platform for graduation memories
"""
from flask import Flask, render_template, url_for, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf import CSRFProtect
import os
import shutil

# Initialize extensions
from models import db
login_manager = LoginManager()
csrf = CSRFProtect()


def create_app(config_name='development'):
    """Create and configure the Flask application"""
    app = Flask(__name__, instance_relative_config=True)
    
    # Load configuration
    app.config.from_object('config.Config')
    
    # Ensure instance folder exists
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass
    # Ensure upload and music folders exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['MUSIC_FOLDER'], exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Login manager configuration
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        """Load user by ID for session management"""
        from models import User
        return User.query.get(int(user_id))

    @app.template_filter('upload_url')
    def upload_url_filter(path):
        """Build static URL for an uploaded file given any stored path/filename."""
        if not path:
            return ''
        filename = os.path.basename(path)
        upload_dir = current_app.config.get('UPLOAD_FOLDER')
        static_target = os.path.join(upload_dir, filename) if upload_dir else None
        if static_target and not os.path.exists(static_target):
            legacy_dir = os.path.join(os.getcwd(), 'uploads')
            legacy_path = os.path.join(legacy_dir, filename)
            if os.path.exists(legacy_path):
                os.makedirs(upload_dir, exist_ok=True)
                try:
                    shutil.copy2(legacy_path, static_target)
                except OSError:
                    pass
        return url_for('static', filename=f'uploads/{filename}')

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    # Register blueprints
    from routes.auth import auth_bp
    from routes.main import main_bp
    from routes.admin import admin_bp

    app.register_blueprint(auth_bp, url_prefix='')
    app.register_blueprint(main_bp, url_prefix='')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    @app.context_processor
    def inject_global_settings():
        """Inject music settings into all templates for the global player."""
        from models import Settings
        settings_obj = Settings.query.first()
        music_file_url = None
        music_title = None
        if settings_obj and settings_obj.music_file:
            music_file_url = url_for('static', filename=f'music/{settings_obj.music_file}')
            music_title = os.path.splitext(settings_obj.music_file)[0]

        return dict(
            global_music_settings={
                'enabled': settings_obj.music_enabled if settings_obj else True,
                'volume': settings_obj.music_volume if settings_obj else 0.2,
                'file': music_file_url,
                'title': music_title,
            }
        )

    # Create database tables
    with app.app_context():
        db.create_all()
        # Initialize default settings
        from models import Settings
        if not Settings.query.first():
            settings = Settings(
                graduation_date='2026-06-01',
                music_enabled=True,
                music_volume=0.2,
                uploads_open=True
            )
            db.session.add(settings)
            db.session.commit()

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
