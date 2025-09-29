from flask import Flask, request, jsonify
import psycopg
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

# Supabase credentials - set these as environment variables or replace with literal strings (NOT recommended for production)
DB_HOST = os.getenv('SUPABASE_DB_HOST', 'tiokiqoympxwfrjsefsy.supabase.co')
DB_NAME = os.getenv('SUPABASE_DB_NAME', 'bus-db')
DB_USER = os.getenv('SUPABASE_DB_USER', 'Suma')
DB_PASS = os.getenv('SUPABASE_DB_PASS', 'Bus@123')
DB_PORT = os.getenv('SUPABASE_DB_PORT', '5432')

conn = psycopg.connect(
    host=DB_HOST,
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASS,
    port=DB_PORT
)

@app.route('/')
def home():
    return "Bus tracking backend running."

# POST endpoint to receive live bus GPS data
@app.route('/location/update', methods=['POST'])
def location_update():
    data = request.json
    bus_id = data.get('bus_id')
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    
    if not all([bus_id, latitude, longitude]):
        return jsonify({'error': 'Missing parameters'}), 400

    cur = conn.cursor()
    try:
        # Insert new location in bus_locations with current timestamp
        cur.execute("""
            INSERT INTO bus_locations (bus_id, latitude, longitude, updated_at)
            VALUES (%s, %s, %s, NOW());
        """, (bus_id, latitude, longitude))
        
        # Upsert into latest_positions table (update if bus_id exists, else insert)
        cur.execute("""
            INSERT INTO latest_positions (bus_id, latitude, longitude, updated_at)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (bus_id) DO UPDATE SET
                latitude = EXCLUDED.latitude,
                longitude = EXCLUDED.longitude,
                updated_at = EXCLUDED.updated_at;
        """, (bus_id, latitude, longitude))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
    
    return jsonify({'status': 'Location updated successfully'}), 200


# GET endpoint to fetch latest bus location by bus_id
@app.route('/location/latest/<bus_id>', methods=['GET'])
def latest_location(bus_id):
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT latitude, longitude, updated_at 
            FROM latest_positions 
            WHERE bus_id = %s
        """, (bus_id,))
        result = cur.fetchone()
        if not result:
            return jsonify({'error': 'Bus ID not found'}), 404
        latitude, longitude, updated_at = result
        return jsonify({
            'bus_id': bus_id,
            'latitude': latitude,
            'longitude': longitude,
            'updated_at': updated_at.isoformat()
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()

# GET endpoint to fetch all buses
@app.route('/buses', methods=['GET'])
def get_buses():
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT bus_id, bus_number, route, assigned_driver
            FROM buses
        """)
        rows = cur.fetchall()
        buses = []
        for r in rows:
            buses.append({
                'bus_id': r[0],
                'bus_number': r[1],
                'route': r[2],
                'assigned_driver': r[3]
            })
        return jsonify(buses), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
