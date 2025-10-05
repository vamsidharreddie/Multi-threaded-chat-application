import socket
import threading
import sys
import time
from database_connection import connect_db, save_message, load_messages # Import DB functions

host = '127.0.0.1'
port = 5555
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Use a try-except block for graceful shutdown if the port is in use
try:
    server.bind((host, port))
except socket.error as e:
    print(f"Error binding server: {e}")
    sys.exit()

server.listen()
print("Server is listening...")

# Old lists removed. We now use rooms{} for multi-room support.
# clients = [] 
# nick_names = [] 

# Use a lock to ensure thread-safe access to shared lists and dictionary
lock = threading.Lock()

# --- Room Management Class and Global Dictionary ---
class Room:
    """Manages clients and nicknames within a single chat room."""
    def __init__(self, room_id):
        self.id = room_id
        self.clients = []
        self.nick_names = []
        
# Global dictionary to hold rooms: {room_id: Room object}
rooms = {}

# Helper function to get the client's current room and nickname
def get_client_info(client):
    """Finds the Room object and nickname the given client socket belongs to."""
    with lock:
        for room in rooms.values():
            if client in room.clients:
                index = room.clients.index(client)
                return room, room.nick_names[index]
    return None, None

def broad_cast(room, msg):
    """Sends a message to all clients in a specific room, cleaning up dead connections."""
    
    # Acquire the lock to ensure list access is synchronized
    with lock:
        # Create a copy of the list to iterate over safely, 
        clients_to_broadcast = list(room.clients)
    
    for client in clients_to_broadcast:
        try:
            client.send(msg)
        except:
            # If sending fails, it means the client has disconnected.
            with lock:
                if client in room.clients:
                    try:
                        index = room.clients.index(client)
                        nick_name = room.nick_names[index]
                        room.clients.pop(index)
                        room.nick_names.pop(index)
                        client.close()
                        print(f"Removed dead connection for {nick_name} in room {room.id}.")
                        
                    except (ValueError, IndexError):
                        pass

def kick_user(room, name):
    """Kicks a user from the specified room and broadcasts the action."""
    # Acquire the lock before modifying the lists
    with lock:
        try:
            index = room.nick_names.index(name)
            client_to_kick = room.clients[index]
            
            # 1. Send kick message to the target client
            client_to_kick.send("You are kicked by the admin".encode('ascii'))
            client_to_kick.close()
            
            # 2. Remove the client from the lists
            room.clients.pop(index)
            room.nick_names.pop(index)
            
            print(f"{name} is kicked from room {room.id}.")

        except ValueError:
            print(f"User '{name}' not found in room {room.id}.")
        except IndexError:
            print(f"Error kicking user '{name}', lists are out of sync in room {room.id}.")
    
    # Broadcast the kick message outside the kick_user lock context
    broad_cast(room, f"{name} is kicked by the admin".encode('ascii'))

def handle(client):
    """Handles all messages and commands from a single client within a room."""
    current_room = None
    nick_name = None 
    
    try:
        # Wait until the client is fully initialized in the receive thread
        while current_room is None:
            current_room, nick_name = get_client_info(client)
            if current_room is None:
                time.sleep(0.1) # Wait briefly
        
        # Main message loop
        while True:
            message = client.recv(1024)
            if not message:
                break # Client disconnected gracefully
            
            decoded_msg = message.decode('ascii')
            
            # --- Command Handling ---
            if decoded_msg.startswith('KICK'):
                if nick_name != 'admin':
                    client.send("Command refused! You are not admin.".encode('ascii'))
                    continue
                
                name_to_kick = decoded_msg[5:].strip()
                kick_user(current_room, name_to_kick)
            
            elif decoded_msg.startswith('BAN'):
                if nick_name != 'admin':
                    client.send("Command refused! You are not admin.".encode('ascii'))
                    continue
                
                name_to_ban = decoded_msg[4:].strip()
                kick_user(current_room, name_to_ban) # Kick the user first
                with open('ban.txt', 'a') as f:
                    f.write(f"{name_to_ban}\n")
                    print(f"{name_to_ban} is banned globally.")
            
            elif decoded_msg.startswith('CMD_HISTORY'):
                # Handle /history command from client
                history = load_messages(current_room.id)
                client.send(history.encode('ascii'))
            
            # --- Regular Message/Broadcast/DB Storage ---
            else:
                full_message_str = message.decode('ascii')
                
                # Check if the message is in the format "{nickname} : {message_content}"
                if " : " in full_message_str:
                    try:
                        # Split is safer than slicing to isolate parts
                        parts = full_message_str.split(' : ', 1)
                        sender_nick = parts[0]
                        message_content = parts[1]
                        
                        # --- DB INTEGRATION ---
                        save_message(current_room.id, sender_nick, message_content)
                        
                        # Prepend room ID to message for clarity
                        broadcast_msg = f"[{current_room.id}] {full_message_str}".encode('ascii')
                        broad_cast(current_room, broadcast_msg)
                    except Exception as e:
                        print(f"Error processing user message: {e}")
                        broad_cast(current_room, message) # Broadcast original message as fallback
                else:
                    # If it's not a standard chat message, just broadcast it
                    broad_cast(current_room, message)

    except Exception as e:
        print(f"Error handling client {nick_name}: {e}")
    finally:
        # Proper cleanup of the client from the room
        if current_room and nick_name:
            with lock:
                if client in current_room.clients:
                    try:
                        index = current_room.clients.index(client)
                        current_room.clients.pop(index)
                        current_room.nick_names.pop(index)
                        client.close()
                        print(f"{nick_name} disconnected from room {current_room.id}.")
                    except (ValueError, IndexError):
                        pass

            # Broadcast the disconnection notification to the room
            broad_cast(current_room, f"{nick_name} left the chat!".encode('ascii'))


def receive():
    # --- DB CONNECTION AT SERVER STARTUP ---
    if not connect_db(): 
        print("Exiting server due to mandatory database failure.")
        sys.exit(1)
        
    while True:
        try:
            client, addr = server.accept()
            
            # --- 1. Password Check (for all users) ---
            client.send("PASS".encode('ascii')) # Prompt for password
            password = client.recv(1024).decode('ascii')
            
            is_admin = False
            # Define global password and admin password
            if password == 'admin123':
                is_admin = True
                pass_ok = True
            elif password == 'chat@123':
                pass_ok = True
            else:
                pass_ok = False
            
            if not pass_ok:
                client.send("refused".encode('ascii'))
                client.close()
                continue
                
            # --- 2. Nickname and Ban Check ---
            client.send("NICK".encode('ascii')) # Prompt for nickname
            nick_name = client.recv(1024).decode('ascii')
            
            if is_admin:
                nick_name = 'admin' # Force admin nickname if password matches
            
            # Check for global ban
            with open('ban.txt', 'r') as f:
                banned_users = [line.strip() for line in f.readlines()]
            
            if nick_name in banned_users:
                client.send("BAN".encode('ascii'))
                client.close()
                continue
            
            # --- 3. Room ID Selection ---
            client.send("ROOM".encode('ascii')) # Prompt for room ID
            room_id = client.recv(1024).decode('ascii').strip()
            
            if not room_id:
                room_id = 'general' # Use a standard general room if none is provided
            
            # Add to or create room
            with lock:
                if room_id not in rooms:
                    rooms[room_id] = Room(room_id)
                    print(f"Created new room: {room_id}")
                
                current_room = rooms[room_id]
                current_room.clients.append(client)
                current_room.nick_names.append(nick_name)
            
            # --- 4. Final Connection ---
            print(f"Client {nick_name} connected to room {room_id} from {str(addr)}")
            
            # Send connection message back to client
            client.send(f"CONNECTED|{room_id}".encode('ascii'))
            
            broad_cast(current_room, f"{nick_name} joined room {room_id}.".encode('ascii'))
            
            t = threading.Thread(target=handle, args=(client,))
            t.start()
        except KeyboardInterrupt:
            print("\nServer shutting down.")
            server.close()
            break
        except Exception as e:
            print(f"Error in receive loop: {e}")

receive()
