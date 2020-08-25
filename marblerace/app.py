#!/usr/bin/env python
from threading import Lock
from flask import Flask, render_template, session, request, \
    copy_current_request_context
from flask_socketio import SocketIO, emit, join_room, leave_room, \
    close_room, rooms, disconnect
from collections import OrderedDict
import random
import sys
# Set this variable to "threading", "eventlet" or "gevent" to test the
# different async modes, or leave it set to None for the application to choose
# the best option based on installed packages.
async_mode = None

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode)
thread = None
thread_lock = Lock()

marble_array = ["blue", "red", "green", "yellow", "pink", "purple", "black", "white", "orange", "cyan"]
marble_feature = ["old", "shiny", "bright", "opaque", "transparent", "swirly", "round", "big", "small", "fast"]
marble_behavior = ["spinning", "bouncing", "rolling", "twirling", "flipping", "crashing"]

marble_countries = ["Panama", "USA", "Greenland", "Russia", "Australia", "China", "India", "Austria", "Algeria", "Western Sahara"]

marble = []
marble_rank = []
while len(marble_countries) > 0:
    select_a_marble = random.choice(marble_countries)
    select_a_feature = random.choice(marble_feature)
    combine_marble_features = select_a_feature+" "+select_a_marble

    marble_countries.remove(select_a_marble)
    marble_feature.remove(select_a_feature)
    marble.append(combine_marble_features)
    marble_rank.append(0)

    #initial_standing = len(marble_countries)
    #marble_mid_race.update({combine_marble_features: 0})


def change_position():
    up_or_down = random.randrange(0,5)
    random_marble = random.randrange(0,len(marble))
    chosen_marble = marble[random_marble]
    if up_or_down is not 0:
        marble_rank[random_marble] = marble_rank[random_marble] + 1
    else:
        marble_rank[random_marble] - 1

    return chosen_marble

def get_top_three():
    ordered_list = [x for _,x in sorted(zip(marble_rank, marble))]
    points_list = [x for _,x in sorted(zip(marble, marble_rank))]
    return [ordered_list, points_list]

def background_thread():
    """Example of how to send server generated events to clients."""
    count = 0
    leaderboard = get_top_three()
    socketio.sleep(5)
    while count < 11:
        if count is 10:
            socketio.emit('the_end',
                      {'data': 'The race is over!  First place is '+ leaderboard[0][0] + ' second place is ' + leaderboard[0][1] + " and third place is " + leaderboard[0][2] +'!' , 'count': "The End"},
                      namespace='/test')
            socketio.emit('the_end',
                      {'data': 'Yay Matthew!  Yay Ben!' , 'count': "The End"},
                      namespace='/test')
            sys.exit(0)
        socketio.sleep(3)
        marble_picker1 = random.choice(marble)
        change_position()
        socketio.emit('my_response',
                      {'data': 'The ' + change_position() + ' marble is ' + random.choice(marble_behavior) +" around the "+ marble_picker1 + " marble!" , 'count': count},
                      namespace='/test')
        
        socketio.sleep(3)
        marble_picker1 = random.choice(marble)
        change_position()
        socketio.emit('my_response',
                      {'data': 'The ' + change_position() + ' marble is ' + random.choice(marble_behavior) +" around the "+ marble_picker1 + " marble!" , 'count': count},
                      namespace='/test')
        
        socketio.sleep(3)
        socketio.emit('my_response',
                      {'data': '__--== The leader is '+ str(leaderboard[0][0]) + ' followed by ' + str(leaderboard[0][1]) + " and " + str(leaderboard[0][2]) + '==--__'  , 'count': count},
                      namespace='/test')
        count += 2


@app.route('/')
def index():
    return render_template('index.html', async_mode=socketio.async_mode)


@socketio.on('my_event', namespace='/test')
def test_message(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': message['data'], 'count': session['receive_count']})


@socketio.on('my_broadcast_event', namespace='/test')
def test_broadcast_message(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': message['data'], 'count': session['receive_count']},
         broadcast=True)


@socketio.on('join', namespace='/test')
def join(message):
    join_room(message['room'])
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': 'In rooms: ' + ', '.join(rooms()),
          'count': session['receive_count']})


@socketio.on('leave', namespace='/test')
def leave(message):
    leave_room(message['room'])
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': 'In rooms: ' + ', '.join(rooms()),
          'count': session['receive_count']})


@socketio.on('close_room', namespace='/test')
def close(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response', {'data': 'Room ' + message['room'] + ' is closing.',
                         'count': session['receive_count']},
         room=message['room'])
    close_room(message['room'])


@socketio.on('my_room_event', namespace='/test')
def send_room_message(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': message['data'], 'count': session['receive_count']},
         room=message['room'])


@socketio.on('disconnect_request', namespace='/test')
def disconnect_request():
    @copy_current_request_context
    def can_disconnect():
        disconnect()

    session['receive_count'] = session.get('receive_count', 0) + 1
    # for this emit we use a callback function
    # when the callback function is invoked we know that the message has been
    # received and it is safe to disconnect
    emit('my_response',
         {'data': 'Disconnected!', 'count': session['receive_count']},
         callback=can_disconnect)


@socketio.on('my_ping', namespace='/test')
def ping_pong():
    emit('my_pong')


@socketio.on('connect', namespace='/test')
def test_connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(background_thread)
    emit('my_response', {'data': 'I love you Matthew!', 'count': 0})


@socketio.on('disconnect', namespace='/test')
def test_disconnect():
    print('Client disconnected', request.sid)


if __name__ == '__main__':
    socketio.run(app, debug=True)
