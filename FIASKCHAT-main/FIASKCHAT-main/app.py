import os
from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from flask_socketio import join_room, leave_room, send, SocketIO
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config["SECRET_KEY"] = "hjhjsdahhds"
app.config["UPLOAD_FOLDER"] = "static/avatars"
app.config["ALLOWED_EXTENSIONS"] = {"png", "jpg", "jpeg", "gif"}
socketio = SocketIO(app)

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

rooms = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]

@app.route("/", methods=["POST", "GET"])
def home():
    session.clear()
    if request.method == "POST":
        name = request.form.get("name")
        room_name = request.form.get("code")
        action = request.form.get("action")

        if not name or not room_name:
            return render_template("home.html", error="Please enter a name and room.", code=room_name, name=name, rooms=rooms)

        room = room_name.strip()
        if len(room) > 50:
            return render_template("home.html", error="Room name must be 50 characters or fewer.", code=room, name=name, rooms=rooms)

        if action == "create":
            if room in rooms:
                return render_template("home.html", error="Room name already taken.", code=room, name=name, rooms=rooms)
            rooms[room] = {
                "members": [],
                "messages": [],
                "avatars": {},
                "fonts": {},
                "font_colors": {}  # NEW: track font colors
            }
        elif action == "join":
            if room not in rooms:
                return render_template("home.html", error="Room does not exist.", code=room, name=name, rooms=rooms)
        else:
            return render_template("home.html", error="Invalid action.", code=room, name=name, rooms=rooms)

        session["room"] = room
        session["name"] = name
        return redirect(url_for("room"))

    return render_template("home.html", rooms=rooms)

@app.route("/room")
def room():
    room = request.args.get("code", session.get("room"))
    if room is None or session.get("name") is None or room not in rooms:
        return redirect(url_for("home"))
    return render_template("room.html", code=room, messages=rooms[room]["messages"], users=rooms[room]["members"])

@app.route("/upload_avatar", methods=["POST"])
def upload_avatar():
    room = session.get("room")
    user_name = session.get("name")

    if room not in rooms or "avatar" not in request.files:
        return jsonify({"error": "Invalid request"}), 400

    avatar_file = request.files["avatar"]
    if avatar_file.filename == "" or not allowed_file(avatar_file.filename):
        return jsonify({"error": "Invalid file type"}), 400

    filename = secure_filename(avatar_file.filename)
    avatar_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    avatar_file.save(avatar_path)

    avatar_url = url_for("static", filename=f"avatars/{filename}")
    rooms[room]["avatars"][user_name] = avatar_url

    socketio.emit("updateUserList", {
        "members": rooms[room]["members"],
        "avatars": rooms[room]["avatars"]
    }, room=room)

    # Also emit font and color settings to the new user only
    for user, font in rooms[room]["fonts"].items():
        socketio.emit("fontChange", {"user": user, "font": font}, room=request.sid)
    for user, color in rooms[room].get("font_colors", {}).items():
        socketio.emit("fontColorChange", {"user": user, "color": color}, room=request.sid)

    return jsonify({"avatar_url": avatar_url}), 200

@socketio.on("message")
def message(data):
    room = session.get("room")
    if room not in rooms:
        return

    content = {
        "name": session.get("name"),
        "message": data["data"]
    }
    send(content, to=room)
    rooms[room]["messages"].append(content)
    print(f"{session.get('name')} said: {data['data']}")

@socketio.on("fontChange")
def handle_font_change(data):
    room = session.get("room")
    user = session.get("name")
    font = data.get("font", "Arial")

    if room in rooms and user:
        rooms[room]["fonts"][user] = font
        socketio.emit("fontChange", {"user": user, "font": font}, room=room)

@socketio.on("fontColorChange")
def handle_font_color_change(data):
    room = session.get("room")
    user = session.get("name")
    color = data.get("color", "#000000")

    if room in rooms and user:
        rooms[room]["font_colors"][user] = color
        socketio.emit("fontColorChange", {"user": user, "color": color}, room=room)

@socketio.on("broadcast_code")
def broadcast_code(data):
    room = session.get("room")
    sender = session.get("name")
    code = data.get("code", "")

    if room in rooms and sender and code:
        socketio.emit("broadcast_code", {"code": code, "sender": sender}, room=room)
        print(f"{sender} broadcasted code to room {room}")

@socketio.on("connect")
def connect(auth):
    room = session.get("room")
    name = session.get("name")

    if not room or not name or room not in rooms:
        return

    join_room(room)
    if name not in rooms[room]["members"]:
        rooms[room]["members"].append(name)

    send({"name": "System", "message": f"{name} has entered the room", "type": "system"}, to=room)
    print(f"{name} joined room {room}")

    socketio.emit("updateUserList", {
        "members": rooms[room]["members"],
        "avatars": rooms[room]["avatars"]
    }, room=room)

    # On connect, broadcast user's own font and color back to them
    for user, font in rooms[room]["fonts"].items():
        socketio.emit("fontChange", {"user": user, "font": font}, room=request.sid)
    for user, color in rooms[room]["font_colors"].items():
        socketio.emit("fontColorChange", {"user": user, "color": color}, room=request.sid)

@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("name")

    leave_room(room)
    if room in rooms:
        rooms[room]["members"] = [m for m in rooms[room]["members"] if m != name]
        if not rooms[room]["members"]:
            del rooms[room]

    send({"name": "System", "message": f"{name} has left the room", "type": "system"}, to=room)
    print(f"{name} has left the room {room}")

    if room in rooms:
        socketio.emit("updateUserList", {
            "members": rooms[room]["members"],
            "avatars": rooms[room]["avatars"]
        }, room=room)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=3000, debug=True)
