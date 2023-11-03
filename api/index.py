from flask import Flask, flash, render_template, request, redirect, session, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from cryptography.fernet import Fernet
from urllib.parse import quote_plus
# removed due to vercel read-only file system
# from urlextract import URLExtract # urlextract~=1.8.0
from datetime import datetime
from markupsafe import Markup
from bson import ObjectId
import random
import string

# extractor = URLExtract()
# extractor.update_when_older(7)  # updates when list is older that 7 days

key = Fernet.generate_key()
AuthKey = Fernet(b'JrzqZnhrBUPp-o8qa2A55tVeJYxPeZwXW-yxVerFPpU=')  # in use to encrypt passwords
MongoKey = Fernet(b'o25rmQEhFT8QSGUfuZa8eY5FyOf9jCNB89eOg4zv9Oo=')  # in use to encrypt messages
# JSKey = Fernet(b'wR1uf-ktcdUF7tCbQW9xDbUP8AxsXtB7yIr9xT572dI=')

# encoded_text = MongoKey.encrypt(bytes('Hello stackoverflow!', 'utf-8'))
# decoded_text = MongoKey.decrypt(encoded_text).decode('utf-8')
# print(encoded_text)
# print(decoded_text)

app = Flask(__name__)
app.secret_key = b'ydaUwB6N9VfeqIhTeEY+Efj54Y/CRIGn1+/eZ8Ca9Xd4DMBLQVG7R+Rt0I+pg8s+'
socketio = SocketIO(app)

''' 
# ** For local use **

username = quote_plus('asamaste')
password = quote_plus('P!GS@REP!NK')
MONGODB_URI = "mongodb+srv://{}:{}@messages.igbjxpf.mongodb.net/?retryWrites=true&w=majority" \
    .format(username, password)
'''

# ** For vercel use **

username = quote_plus('vercel-admin-user')
password = quote_plus('GgJIrAGkaYlC6YwC')
MONGODB_URI = "mongodb+srv://{}:{}@messages.igbjxpf.mongodb.net/myFirstDatabase?retryWrites=true&w=majority" \
    .format(username, password)

# Create a new client and connect to the server
myclient = MongoClient(uri, server_api=ServerApi('1'))
# Send a ping to confirm a successful connection
try:
    myclient.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

res = ''.join(random.choices(string.ascii_uppercase +
                             string.digits, k=4))

# print result
print("The generated random string : " + str(res))


def getEmail():
    if 'userID' in session:
        mydb = myclient['userdata']
        mycol = mydb['credentials']
        data = mycol.find_one({"_id": ObjectId(session['userID'])})
        if data:
            return {'email': data['email'], 'name': data['name']}
        else:
            session.pop('userID')
    return None


def reformat_links(message):
    arr = []
    # urls = extractor.find_urls(message)
    urls = []
    if urls:
        for x in message.split():
            if x in urls:
                print(x)
                if x[:4] != 'http':
                    address = 'https://' + x
                else:
                    address = x
                x = "%link%{}%link%".format(address)
            arr.append(x)
    else:
        arr = message.split()
    return arr


def reformat_links_sockets(message):
    arr = []
    # urls = extractor.find_urls(message)
    urls = []
    if urls:
        for x in message.split():
            if x in urls:
                print(x)
                if x[:4] != 'http':
                    address = 'https://' + x
                else:
                    address = x
                x = "<a href='{}'>{}</a>".format(address, address)
                if address[:25] == 'https://open.spotify.com/':
                    x = x + '<p></p><iframe style="border-radius:12px" src="https://open.spotify.com/embed/{}" width="100%" height="152" frameBorder="0" allowfullscreen="" allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture" loading="lazy"></iframe>'.format(
                        address[25:])
            arr.append(x)
    else:
        arr = message.split()
    return arr


@app.route("/favicon.ico")
@app.route("/logo.svg")
def favicon():
    return send_from_directory('assets', 'comments-regular.svg')


@app.errorhandler(404)
def not_found(e):
    return redirect("/", code=302)


@app.route("/")
def home():
    email = getEmail()
    if email:
        return render_template("index.html", name=email['name'])
    return render_template("index.html")


@socketio.on('disconnect')
def disconnect():
    email = getEmail()
    email['data'] = email['name'] + ' disconnected'
    leave_room(room)
    print(room)
    print('Client disconnected', email)
    emit('my response', email)


@socketio.on('chatroom')
def handle_my_custom_event(json, methods=['GET', 'POST']):
    email = getEmail()
    if email['email'] == json['user_name']:
        print('received my event: ' + str(json))
        if 'data' in json:
            join_room(json['room'])
            json['user_name'] = email['name'].split()[0]
        elif 'moremessages' in json:
            mydb = myclient['chatrooms']
            mycol = mydb[json['room']]
            print(json['num'])
            docs = mycol.count_documents({}) - int(json['num'])
            print(docs)
            if docs == 0:
                y = 0
                data = {}
            elif docs < 5:
                json['num'] = int(json['num']) + docs
                data = mycol.find().sort('_id', -1).limit(5)
                for x in data:
                    y = x['_id']
                data = mycol.find().sort('_id', 1).limit(docs)
                json['nomoremessages'] = 'No More Messages Incoming'
            else:
                json['num'] = int(json['num']) + 5
                data = mycol.find({'_id': {'$lt': ObjectId(json['id'])}}).sort('_id', -1).limit(5)
                for x in data:
                    y = x['_id']
                data = mycol.find({'_id': {'$gte': y}}).sort('_id', 1).limit(5)
            array = []
            for x in data:
                array.append({'user': x['user'],
                              'message': reformat_links_sockets(MongoKey.decrypt(x['message']).decode('utf-8')),
                              'timestamp': x['timestamp']})
            json['data'] = list(reversed(array))
            json['moremessages'] = 'More Messages Incoming'
            json['id'] = str(y)
            emit('my response', json)
            return
        elif 'message' in json:
            mydb = myclient['chatrooms']
            mycol = mydb[json['room']]
            user = email['name']
            message = json['message']
            message = " ".join(reformat_links_sockets(message))
            encmessage = MongoKey.encrypt(bytes(json['message'], 'utf-8'))
            json['message'] = message
            timestamp = datetime.now().strftime("%a %d %b | %H:%M")
            json['timestamp'] = timestamp
            json['user_name'] = user
            mydict = {"user": user, "message": encmessage, "timestamp": timestamp}
            x = mycol.insert_one(mydict)
            print(x.inserted_id)
        emit('my response', json, room=json['room'])
    else:
        print('**RECIEVED INVALID AUTHENTICATION ATTEMPT**: ' + str(json))


@app.route("/login/", methods=["POST", "GET"])
@app.route("/login/<chatroom>", methods=["POST", "GET"])
def login(chatroom=None):
    email = getEmail()
    if email:
        return redirect("/", code=302)
    else:
        if request.method == 'POST':
            email = request.form['email']
            pword = request.form['password']

            mydb = myclient['userdata']
            mycol = mydb['credentials']
            data = mycol.find_one({"email": email})
            if not email.strip() or not password.strip():
                flash('Please fill out all fields.')
                return render_template("login.html")
            elif data and pword == AuthKey.decrypt(data['password']).decode('utf-8'):
                session['userID'] = str(data['_id'])
                print(chatroom)
                if chatroom:
                    return redirect("/" + chatroom, code=302)
                    # return room(chatroom, True)
                return redirect("/", code=302)
            flash('Incorrect username/password.')
            return render_template("login.html")
        else:
            return render_template("login.html")


@app.route("/register/", methods=["POST", "GET"])
@app.route("/register/<chatroom>", methods=["POST", "GET"])
def register(chatroom=None):
    email = getEmail()
    if email:
        return redirect("/", code=302)
    else:
        if request.method == 'POST':
            name = request.form['name']
            email = request.form['email']
            pword = request.form['password']
            if not email.strip() or not name.strip() or not request.form['password'].strip():
                flash('Please fill out all fields.')
                return render_template("register.html")

            mydb = myclient['userdata']
            mycol = mydb['credentials']
            data = mycol.find_one({"name": name})
            if data:
                flash('Name already exists.')
                return render_template("register.html")

            mydb = myclient['userdata']
            mycol = mydb['credentials']
            data = mycol.find_one({"email": email})
            if data:
                flash('Email already exists.')
                return render_template("register.html")

            pword = AuthKey.encrypt(bytes(pword, 'utf-8'))
            mydict = {"name": name, "email": email, "password": pword}
            x = mycol.insert_one(mydict)
            session['userID'] = str(x.inserted_id)
            print(x.inserted_id)
            print(chatroom)
            if chatroom:
                return room(chatroom, True)
            return render_template("index.html", name=name)
        else:
            return render_template("register.html")


@app.route("/log-out")
def logout():
    if 'userID' in session:
        session.pop('userID')
    return redirect("/", code=302)


@app.route("/settings")
def settings():
    email = getEmail()
    if email:
        return render_template("settings.html", name=email['name'], email=email['email'])
    else:
        return redirect("/login", code=302)


@app.route("/<chatroom>")
def room(chatroom, login=None):
    print(len(chatroom))
    if len(chatroom) != 4:
        return redirect("/", code=302)
    for x in chatroom:
        if x.islower():
            return redirect("/", code=302)
    email = getEmail()
    if email:
        mydb = myclient['chatrooms']
        mycol = mydb[chatroom]

        if login:
            request.method = 'GET'
        elif request.method == 'POST':
            user = email
            message = request.form['message']
            timestamp = datetime.now().strftime("%a %d %b | %H:%M")
            mydict = {"user": user, "message": message, "timestamp": timestamp}
            x = mycol.insert_one(mydict)
            print(x.inserted_id)
        docs = mycol.count_documents({})
        if docs == 0:
            y = 0
            q = 0
            data = {}
        elif docs < 10:
            q = docs
            data = mycol.find().sort('_id', -1).limit(10)
            for x in data:
                y = x['_id']
            data = mycol.find().sort('_id', 1).limit(docs)
        else:
            q = 5
            data = mycol.find().sort('_id', -1).limit(10)
            for x in data:
                y = x['_id']
            data = mycol.find({'_id': {'$gte': y}}).sort('_id', 1).limit(10)
        return render_template("room.html", room=chatroom, chat_database=data, email=email['email'], name=email['name'],
                               key=MongoKey, reformat=reformat_links, markup=Markup,
                               hasmessages=docs, maxcol=y, colnum=q)
    return render_template("login.html", room=chatroom)


@app.route("/settings/upd/", methods=["POST", "GET"])
def updateData():
    mail = getEmail()
    if not mail:
        return "Invalid session."
    else:
        if request.method == 'POST':
            req = request.form['req']
            email = mail['email']
            Name = mail['name']

            mydb = myclient['userdata']
            mycol = mydb['credentials']

            if req == 'ChangeName':
                newName = request.form['name']
                if not email.strip() or not Name.strip() or not newName.strip():
                    return "Please fill out all fields."
                elif newName == Name:
                    return "Cannot enter the same Name."

                data = mycol.find_one({"name": Name})
                if not data:
                    return "Invalid session."

                data = mycol.find_one({"email": email})
                if not data:
                    return "Invalid session."

                myquery = {"email": email}
                newvalues = {"$set": {"name": newName}}
                mycol.update_one(myquery, newvalues)
                return "Name updated."
            elif req == 'ChangeEmail':
                newEmail = request.form['email']
                if not email.strip() or not Name.strip() or not newEmail.strip():
                    return "Please fill out all fields."
                elif newEmail == email:
                    return "Cannot enter the same Email."

                data = mycol.find_one({"name": Name})
                if not data:
                    return "Invalid session."

                data = mycol.find_one({"email": email})
                if not data:
                    return "Invalid session."

                myquery = {"email": email}
                newvalues = {"$set": {"email": newEmail}}
                mycol.update_one(myquery, newvalues)
                return "Email updated."
            elif req == 'ChangePassword':
                data = mycol.find_one({"_id": ObjectId(session['userID'])})
                password = data['password'] # check old password
                oldPassword = request.form['oldPassword']
                newPassword = request.form['newPassword']
                newPassword = AuthKey.encrypt(bytes(newPassword, 'utf-8'))

                if not email.strip() or not Name.strip() or not oldPassword.strip()or not newPassword.strip():
                    return "Please fill out all fields."
                elif oldPassword == AuthKey.decrypt(password).decode('utf-8'):
                    return "Cannot enter the same Password."

                data = mycol.find_one({"name": Name})
                if not data:
                    return "Invalid session."

                data = mycol.find_one({"email": email})
                if not data:
                    return "Invalid session."

                myquery = {"email": email}
                newvalues = {"$set": {"password": newPassword}}
                mycol.update_one(myquery, newvalues)
                return "Password updated."
        else:
            return "Invalid GET request."


if __name__ == '__main__':
    socketio.run(app, host='127.0.0.1', debug=True,
                 allow_unsafe_werkzeug=True)
