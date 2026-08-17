from flask import Flask, render_template
from flask_wtf.csrf import CSRFError

from app.config import Config
from app.extensions import csrf, db, migrate
from app.services.auth_service import current_user


def create_app(config_object=Config):
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(config_object)

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    from app.routes.auth import bp as auth_bp
    from app.routes.contacts import bp as contacts_bp
    from app.routes.home import bp as home_bp
    from app.routes.invoices import bp as invoices_bp
    from app.routes.matters import bp as matters_bp
    from app.routes.tasks import bp as tasks_bp

    for blueprint in (auth_bp, home_bp, matters_bp, invoices_bp, contacts_bp, tasks_bp):
        app.register_blueprint(blueprint)

    @app.context_processor
    def inject_globals():
        return {
            "current_user": current_user(),
            "app_name": app.config["APP_NAME"],
            "environment_label": app.config["ENVIRONMENT_LABEL"],
        }

    @app.errorhandler(CSRFError)
    def csrf_error(_error):
        return render_template("errors/400.html"), 400

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(_error):
        db.session.rollback()
        return render_template("errors/500.html"), 500

    return app
