import os
from app import create_app

# Get Flask environment from environment variable
env = os.getenv("FLASK_ENV", "development")

# Create app
app = create_app(env)

if __name__ == "__main__":
    # Get host and port from environment or use defaults
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", 4000))
    debug = env == "development"
    
    # Run app
    app.run(
        host=host,
        port=port,
        debug=debug,
        use_reloader=debug,
    )
