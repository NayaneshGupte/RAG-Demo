from app import create_app

app = create_app()

if __name__ == "__main__":
    # Use port 5001 to avoid conflict with Apple AirPlay on port 5000
    app.run(host='0.0.0.0', port=5001, debug=False)
