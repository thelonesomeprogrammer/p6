from flask import Flask, jsonify
from flask_cors import CORS
from threading import Thread
import atexit
from time import sleep

class worker:
    def __init__(self):
        self.running = True

    def run(self):
        while self.running:
            print("working")
            sleep(2)

    def stop(self):
        self.running = False

threads = []
w = worker()
Thread(target=w.run).start()
threads.append(w)

def close_running_threads():
    for t in threads:
        t.stop()


# create flask app
app = Flask(__name__)
CORS(app)

# main flask page
@app.route('/')
def index():
    return "API is running"

@app.route('/api/health')
def health():
    return jsonify({"status": "healthy", "message": "Backend connected!"})


## Main funcion, only initiate the Flask app
def main(args=None):
    atexit.register(close_running_threads) # call the function to close things properly when the server is down
    app.run(host='0.0.0.0', port=5000, debug=False)

if __name__ == '__main__':
    main()
