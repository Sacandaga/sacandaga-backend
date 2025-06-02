import sqlite3
import uuid
from flask import Flask, request, jsonify
from flask_cors import CORS

APP_NAME = "Sacandaga Calendar Backend"

# --- Database Setup ---
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
            backgroundColor TEXT NOT NULL,
            start TEXT NOT NULL,
            end TEXT NOT NULL,
            description TEXT
        )
    ''')
    conn.commit()
    conn.close()

# --- Flask App Setup ---
app = Flask(APP_NAME)
CORS(app) # Enable CORS for all routes, allowing requests from your web app

# --- Helper Functions ---
def event_to_dict(event_row):
    """Converts a database row (sqlite3.Row) to a dictionary."""
    if event_row is None:
        return None
    return dict(event_row)

# --- API Endpoints ---

@app.route('/', methods=['GET'])
def root():
    """Root route to test API availability."""
    try:
        message = "Welcome to the Sacandaga Calendar Backend API!"
        return jsonify(message), 200
    except Exception as e:
        print(f"Error fetching all events: {e}")
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
        required_fields = ['title', 'backgroundColor', 'start', 'end']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"error": f"Missing or empty required field: {field}"}), 400

        new_event = {
            "id": str(uuid.uuid4()),
            "title": data['title'],
            "backgroundColor": data['backgroundColor'],
            "start": data['start'],
            "end": data['end'],
            "description": data.get('description') # Optional field
        }

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO events (id, title, backgroundColor, start, end, description)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (new_event['id'], new_event['title'], new_event['backgroundColor'],
              new_event['start'], new_event['end'], new_event['description']))
        conn.commit()
        conn.close()

        return jsonify(new_event), 201
    except Exception as e:
        print(f"Error creating event: {e}")
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
        print(f"Error fetching all events: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

@app.route('/event/<string:event_id>', methods=['GET'])
def get_event_by_id(event_id):
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
        print(f"Error fetching event by ID {event_id}: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

@app.route('/event/<string:event_id>', methods=['PATCH'])
def update_event(event_id):
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
        if 'backgroundColor' in data:
            update_fields.append("backgroundColor = ?")
            update_values.append(data['backgroundColor'])
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
        print(f"Error updating event {event_id}: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

@app.route('/event/<string:event_id>', methods=['DELETE'])
def delete_event(event_id):
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
        print(f"Error deleting event {event_id}: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

# --- Main Execution ---
if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000) # Listens on http://localhost:5000
