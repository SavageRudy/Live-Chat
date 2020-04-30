import os
import json
from datetime import datetime

from flask import Flask, render_template, request, redirect, make_response, session
from flask_socketio import SocketIO, emit, send, join_room, leave_room
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

engine = create_engine("postgres://pgshkwejwranqx:7aa8f81ba918c9658503bc4238b00405f4ba836c938a18db7c1867f6224cc3b5@ec2-79-125-26-232.eu-west-1.compute.amazonaws.com:5432/d8vhm079i736jq") #DATABASE_URL as been set as a environment variable and its the url of th server database(in postgre)
db = scoped_session(sessionmaker(bind=engine))

app = Flask(__name__)
app.config["SECRET_KEY"] = 'Livec'
app.config['SESSION_TYPE'] = 'filesystem'
socketio = SocketIO(app)

Channels = []

class Message:
    messageID = -1
    userName = ""
    Message = ""
    timeStamp = ""
    messageType = "" #client/server

    def __init__(self, messageID= -1, userName="", Message="", timeStamp="", messageType=""):
        self.messageID = messageID
        self.userName = userName
        self.Message = Message
        self.timeStamp = datetime.now()
        self.messageType = messageType

    def todict(self):
        
        return {
            "msg_id": self.messageID,
            "username": self.userName,
            "time_stamp": self.timeStamp.strftime("%d/%m/%Y %H:%M:%S"),
            "msg": self.Message,
            "type": self.messageType
        }

        

# This event is fired when user connects to the socket (Unnamed event)
@socketio.on('connect')
def handler():

    response = "User: {0} connected".format(session['username']) #session persists in socket io connections as well 0_ooo

    #send a msg back to the user to confirm the connection "User: <username> connected"
    #send(response)

@socketio.on('joinroom')
def join(room_name):


    msg = "{0} has joined the chat".format(session['username'])
    timestamp = datetime.now()
    username = 'server'
    msg_type= 0

    join_room(room_name)

    result = db.execute("INSERT INTO messages(username, message, timestamp, type, room_name) VALUES ('{0}', '{1}', '{2}', {3}, '{4}') RETURNING id".format(username, msg, timestamp , msg_type, room_name))
    message_id = result.fetchone()[0]
    db.commit()

    new_msg = Message(userName=username,timeStamp= timestamp, messageType=msg_type, Message=msg)


    send(new_msg.todict(),room=room_name)

@socketio.on('leaveroom')
def leave(room_name):

    msg = "{0} has left the chat".format(session['username'])
    timestamp = datetime.now()
    username = 'server'
    msg_type= 0

    leave_room(room_name)

    result = db.execute("INSERT INTO messages(username, message, timestamp, type, room_name) VALUES ('{0}', '{1}', '{2}', {3}, '{4}') RETURNING id".format(username, msg, timestamp , msg_type, room_name))
    message_id = result.fetchone()[0]
    db.commit()

    new_msg = Message(userName=username,timeStamp= timestamp, messageType=msg_type, Message=msg)


    send(new_msg.todict(),room=room_name)

@socketio.on('send_message')
def send_room_message(data):

    data = json.loads(data)
    room_name = data['channelName']

    username = session['username']
    msg = data['message']
    timestamp = datetime.now()
    msg_type = 1

    """new_msg = Message.buildMessage(msg, username)
    new_msg.messageID = Channel.FindRoomAndAdd(room_name, new_msg)"""

    
    result = db.execute("INSERT INTO messages(username, message, timestamp, type, room_name) VALUES ('{0}', '{1}', '{2}', {3}, '{4}') RETURNING id".format(username, msg, timestamp , msg_type, room_name))
    message_id = result.fetchone()[0]
    db.commit()


    new_msg = Message(message_id, username, msg, timestamp, msg_type)

    send(new_msg.todict(), room=room_name)

@socketio.on('delete_message')
def delete_room_message(data):

    data = json.loads(data)
    room_name = data['channelName']
    msg_id = data['msg_id']

    username = session['username']

    db.execute("DELETE FROM messages WHERE room_name = '{0}' AND id = {1}".format(room_name, msg_id))

    emit('message_deleted',msg_id, room=room_name)
    

@app.route("/")
def index():

    # Check if "username" exists in session.
    if ('username' not in session):
        return render_template('setname.html')

    username = session['username']

    channel_list = []

    cursor = db.execute("SELECT * FROM rooms;")
    result = cursor.fetchall()

    for x in result:
        channel_list.append({
            "channelName": x['room_name'],
            "ownerName": x['username']
        })


    return render_template('index.html', username=username, channel_list=channel_list)

@app.route('/chat/<channel_name>')
def join_chatroom(channel_name):

    # Check if "username" exists in session.
    if ('username' not in session):
        return render_template('setname.html')

    my_username = session['username']

    cursor = db.execute("SELECT * FROM messages WHERE room_name = '{0}'".format(channel_name))
    result = cursor.fetchall()

    messages = []


    for x in result:
        message_id = x['id']
        username = x['username']
        time_stamp = x['timestamp']
        message_type = x['type']
        message = x['message']
        msg = Message(message_id, username, message, time_stamp, message_type)

        messages.append(msg)

    return render_template('chatroom.html', username=my_username, channel_name=channel_name, messages=messages)

@app.route("/setname", methods=["POST"])
def setname():

    if request.method == "POST":
        #get input
        username = request.form.get('username')

        #set 'username' in session
        session['username'] = username

        return redirect('/')

@app.route('/channels', methods=['GET'])
def getchannels():

    my_channels = []
    for x in Channels:
        my_channels.append(x.__dict__)

    return json.dumps(my_channels)

@app.route('/channel/create', methods=['POST', 'GET'])
def createChannel():

    if request.method == 'GET':

        # Check if "username" exists in session.
        if ('username' not in session):
            return render_template('setname.html')

        username = session['username']

        return render_template('createchannel.html', username=username)

    elif request.method == 'POST':

        data = request.form

        new_channel = data.get('channelName')

        db.execute("INSERT INTO rooms(room_name, username) VALUES ('{0}', '{1}')".format(new_channel, session['username']))
        db.commit()

        return(redirect("/chat/{0}".format(new_channel)))





if __name__ == "__main__":
    socketio.run(app)