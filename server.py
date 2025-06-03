import logging
import sqlite3
import uuid
import os
import functools
from flask import Flask, request, jsonify
from flask_cors import CORS
from typing import Optional, Callable, Any
from dotenv import load_dotenv

# --- Configuration ---

load_dotenv()

PORT = int(os.environ.get('PORT', '5000'))

APP_ENV = os.environ.get('APP_ENV', 'development').lower()
IS_PROD = APP_ENV == 'production'

APP_NAME = 'Sacandaga Calendar Backend'

CLIENT_URL = 'https://sacandaga.fly.dev'

ORIGINS = [CLIENT_URL] if IS_PROD else ['*']

BEARER_TOKEN = os.environ.get('BEARER_TOKEN', None)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.info(f"Starting server in {'production' if IS_PROD else 'development'} mode...")

# --- Database Setup ---

# if IS_PROD:
#     DB_NAME = os.path.join('/app/db', 'calendar_events.db')
# else:
DB_NAME = 'calendar_events.db'

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row # Allows accessing columns by name
    return conn

def init_db():
    """Initializes the database and creates the events table if it doesn't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            background_color TEXT NOT NULL,
            start TEXT NOT NULL,
            end TEXT NOT NULL,
            description TEXT
        )
    ''')
    
    # Check if the events table is empty
    cursor.execute("SELECT COUNT(*) FROM events")
    if cursor.fetchone()[0] > 0:
        logger.info("Events table already contains data, skipping initial insert.")
    else:
        logger.info("Events table is empty, inserting initial data...")
        initial_events = [
            {
                "title": "Opening Weekend",
                "start": "2025-07-04",
                "end": "2025-07-06",
                "background_color": "#2365A1",
                "description": "Elaine, Rick, Mark, Danee"
            },
            {
                "title": "Michael & Katie",
                "start": "2025-07-25",
                "end": "2025-08-10",
                "background_color": "#388E3C",
                "description": None
            },
            {
                "title": "Scott, Doug, Mark, Elaine, Rick",
                "start": "2025-08-16",
                "end": "2025-08-23",
                "background_color": "#7B1FA2",
                "description": None
            },
            {
                "title": "Chris & Friends",
                "start": "2025-08-28",
                "end": "2025-09-02",
                "background_color": "#A0522D",
                "description": None
            }
        ]

        # Insert each event with a unique UUID
        for event in initial_events:
            event_id = str(uuid.uuid4())
            cursor.execute('''
                INSERT INTO events (id, title, background_color, start, end, description)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                event_id,
                event["title"],
                event["background_color"],
                event["start"],
                event["end"],
                event.get("description")
            ))
    
    conn.commit()
    conn.close()
    logger.info("Database initialized successfully.")

# --- Flask App Setup ---
app = Flask(APP_NAME)
CORS(app,
    origins=ORIGINS,
    methods=['GET', 'POST', 'PATCH', 'DELETE'],
    supports_credentials=False)

# Initialize the database when the application module is loaded.
# This ensures it runs when Gunicorn starts, before any requests are handled.
init_db()

# --- Helper Functions ---
def event_to_dict(event_row: Optional[sqlite3.Row]):
    """Converts a database row (sqlite3.Row) to a dictionary."""
    if event_row is None:
        return None
    return dict(event_row)

def validate_bearer_token(f: Callable[..., Any]):
    """Decorator to validate Bearer token for secured endpoints."""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        # Skip auth in development mode
        if not IS_PROD:
            logger.debug("Running in development mode, auth bypassed")
            return f(*args, **kwargs)
        
        # Continue with auth in production mode
        if not BEARER_TOKEN:
            logger.warning("BEARER_TOKEN not configured, auth disabled")
            return f(*args, **kwargs)
            
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({"error": "Authorization header missing"}), 401
            
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return jsonify({"error": "Invalid authorization header format"}), 401
            
        token = parts[1]
        if token != BEARER_TOKEN:
            return jsonify({"error": "Invalid bearer token"}), 401
            
        return f(*args, **kwargs)
    return decorated_function

# --- API Endpoints ---

@app.route('/', methods=['GET'])
@validate_bearer_token
def root():
    """Root route to test API availability."""
    try:
        message = "Welcome to the Sacandaga Calendar Backend API!"
        return jsonify(message), 200
    except Exception as e:
        logger.error(f"Error in root route: {e}", exc_info=True)
        return jsonify({"error": "An internal server error occurred"}), 500
    
@app.route('/event', methods=['GET'])
def get_all_events():
    """Returns a list of all events."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM events")
        events_rows = cursor.fetchall()
        conn.close()

        events = [event_to_dict(row) for row in events_rows]
        return jsonify(events), 200
    except Exception as e:
        logger.error(f"Error fetching all events: {e}", exc_info=True)
        return jsonify({"error": "An internal server error occurred"}), 500

@app.route('/event/<string:event_id>', methods=['GET'])
def get_event_by_id(event_id: str):
    """Returns a single event by its ID."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
        event_row = cursor.fetchone()
        conn.close()

        if event_row is None:
            return jsonify({"error": "Event not found"}), 404

        return jsonify(event_to_dict(event_row)), 200
    except Exception as e:
        logger.error(f"Error fetching event by ID {event_id}: {e}", exc_info=True)
        return jsonify({"error": "An internal server error occurred"}), 500

@app.route('/event', methods=['POST'])
def create_event():
    """
    Creates a new event.
    Expects a JSON body with event details.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON payload"}), 400

        # Validate required fields
        required_fields = ['title', 'background_color', 'start', 'end']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"error": f"Missing or empty required field: {field}"}), 400

        new_event = {
            "id": str(uuid.uuid4()),
            "title": data['title'],
            "background_color": data['background_color'],
            "start": data['start'],
            "end": data['end'],
            "description": data.get('description') # Optional field
        }

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO events (id, title, background_color, start, end, description)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (new_event['id'], new_event['title'], new_event['background_color'],
              new_event['start'], new_event['end'], new_event['description']))
        conn.commit()
        conn.close()

        return jsonify(new_event), 201
    except Exception as e:
        logger.error(f"Error creating event: {e}", exc_info=True)
        return jsonify({"error": "An internal server error occurred"}), 500

@app.route('/event/<string:event_id>', methods=['PATCH'])
def update_event(event_id: str):
    """
    Updates an existing event.
    Expects a JSON body with fields to update.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON payload"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if event exists
        cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
        existing_event = cursor.fetchone()
        if existing_event is None:
            conn.close()
            return jsonify({"error": "Event not found"}), 404

        # Build the update query dynamically
        update_fields = []
        update_values = []

        if 'title' in data:
            update_fields.append("title = ?")
            update_values.append(data['title'])
        if 'background_color' in data:
            update_fields.append("background_color = ?")
            update_values.append(data['background_color'])
        if 'start' in data:
            update_fields.append("start = ?")
            update_values.append(data['start'])
        if 'end' in data:
            update_fields.append("end = ?")
            update_values.append(data['end'])
        if 'description' in data: # Can be None to clear description
            update_fields.append("description = ?")
            update_values.append(data.get('description'))

        if not update_fields:
            conn.close()
            return jsonify({"error": "No fields to update provided"}), 400

        query = f"UPDATE events SET {', '.join(update_fields)} WHERE id = ?"
        update_values.append(event_id)

        cursor.execute(query, tuple(update_values))
        conn.commit()

        # Fetch the updated event
        cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
        updated_event_row = cursor.fetchone()
        conn.close()

        return jsonify(event_to_dict(updated_event_row)), 200
    except Exception as e:
        logger.error(f"Error updating event {event_id}: {e}", exc_info=True)
        return jsonify({"error": "An internal server error occurred"}), 500

@app.route('/event/<string:event_id>', methods=['DELETE'])
def delete_event(event_id: str):
    """Deletes an event by its ID."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if event exists before deleting
        cursor.execute("SELECT id FROM events WHERE id = ?", (event_id,))
        event_exists = cursor.fetchone()

        if not event_exists:
            conn.close()
            return jsonify({"error": "Event not found"}), 404

        cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
        conn.commit()
        conn.close()

        return jsonify({"message": "Event deleted successfully"}), 200
    except Exception as e:
        logger.error(f"Error deleting event {event_id}: {e}", exc_info=True)
        return jsonify({"error": "An internal server error occurred"}), 500

# --- Main Execution ---
if __name__ == '__main__':
    logger.info(f"Server listening on port {PORT}...")
    app.run(debug=not IS_PROD, port=PORT)
