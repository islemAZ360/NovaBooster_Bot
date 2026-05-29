from flask import Flask, render_template, jsonify, Response
import os
from bot_script import run_automation, run_automation_stream

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/generate', methods=['POST'])
def generate_link():
    try:
        # Run the automation script
        result = run_automation()
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/generate_stream', methods=['GET'])
def generate_stream():
    return Response(run_automation_stream(), mimetype='text/event-stream')

if __name__ == '__main__':
    # Use PORT provided by Render (or 5000 locally)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
