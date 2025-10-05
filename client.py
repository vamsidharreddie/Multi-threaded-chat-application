import socket
import threading
import sys
import time # Import time for brief sleeps in non-blocking scenarios

# --- Client Setup ---
nickname = input("Choose a nickname: ")
password = ""

# Determine password based on nickname
if nickname == 'admin':
    password = input("Enter the admin password (admin123): ")
else:
    # IMPORTANT: The server requires a general password for all users
    password = input("Enter the server password (chat@123): ")

# Handle Room Selection Input (Needed early to send to server later)
room_id = input("Enter room ID to join or create (e.g., 'general'): ")
if not room_id:
    room_id = 'general'
    print("Using default room: 'general'")
    
# Connect to the server
try:
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(('127.0.0.1', 5555))
    print("Attempting connection and handshake...")
except socket.error as e:
    print(f"Error connecting to server: {e}")
    sys.exit()

# Flag to control thread execution
stop_thread = False

# --- Receive Thread ---
def receive():
    global stop_thread
    handshake_complete = False
    
    while not stop_thread:
        try:
            # Check for data availability before blocking indefinitely
            msg = client.recv(1024).decode('ascii')
            
            if not msg:
                raise ConnectionError("Server closed connection.")

            # --- Handshake Logic (Multi-step) ---
            if not handshake_complete:
                if msg == "PASS":
                    # Step 1: Server asks for global/admin password
                    client.send(password.encode('ascii'))
                    continue
                elif msg == "NICK":
                    # Step 2: Server asks for nickname (after password check)
                    client.send(nickname.encode('ascii'))
                    continue
                elif msg == "ROOM":
                    # Step 3: Server asks for Room ID (after NICK/ban check)
                    client.send(room_id.encode('ascii'))
                    continue
                elif msg == "refused":
                    # Final state: Password failed
                    print("Connection refused! Incorrect server password or admin credentials.")
                    stop_thread = True
                    client.close()
                    break
                elif msg == "BAN":
                    # Final state: Ban check failed
                    print("You are banned from the server.")
                    stop_thread = True
                    client.close()
                    break
                elif msg.startswith("CONNECTED|"):
                    # Final state: Connection successful
                    current_room = msg.split('|')[1]
                    print(f"--- Successfully connected to room '{current_room}' ---")
                    print("Type /history to load past messages or /kick [user] (if admin).")
                    handshake_complete = True
                    continue # Continue loop to process next message

            # --- Regular Message/Broadcast Logic ---
            
            # Message received *after* handshake is complete
            if msg.startswith("You are kicked by the admin"):
                print(msg)
                stop_thread = True
                client.close()
                break
            else:
                # Regular chat message, server broadcast, or history response
                print(msg)
                
        except (ConnectionAbortedError, ConnectionResetError, ConnectionError) as e:
            # Handle client disconnection (kicked or forced exit)
            print(f"Connection lost. {e}")
            stop_thread = True
            client.close()
            break
        except Exception as e:
            # General error handling
            print(f"An unexpected error occurred in receive: {e}")
            stop_thread = True
            client.close()
            break

# --- Write Thread ---
def write():
    global stop_thread
    while not stop_thread:
        try:
            message_text = input("")
            
            if not message_text.strip():
                continue # Don't send empty messages
            
            # --- Command Handling ---
            if message_text.startswith('/'):
                command_parts = message_text.split(maxsplit=2)
                command = command_parts[0]

                if command == '/history':
                    # Send special command to server to load history
                    client.send("CMD_HISTORY".encode('ascii'))
                
                elif nickname == 'admin':
                    if command == '/kick' and len(command_parts) == 2:
                        kick_nick = command_parts[1]
                        client.send(f"KICK {kick_nick}".encode('ascii'))
                    elif command == '/ban' and len(command_parts) == 2:
                        ban_nick = command_parts[1]
                        client.send(f"BAN {ban_nick}".encode('ascii'))
                    else:
                        print("Unknown or incomplete admin command. Usage: /kick [nickname] or /ban [nickname]")
                else:
                    print("Commands can only be used by an admin (or /history).")
            
            # --- Regular Message ---
            else:
                # Note: The server expects the nickname to be prepended here for database logging.
                msg = f"{nickname} : {message_text}"
                client.send(msg.encode('ascii'))
        
        except EOFError:
            print("Input stream closed. Exiting write thread.")
            stop_thread = True
            break
        except Exception as e:
            print(f"Error sending message: {e}. Disconnecting...")
            stop_thread = True
            client.close()
            break

# Start threads for receiving and writing messages
receive_thread = threading.Thread(target=receive)
receive_thread.start()

write_thread = threading.Thread(target=write)
write_thread.start()
