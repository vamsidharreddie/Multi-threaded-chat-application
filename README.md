Modular Multi-Room Chat Server (Python)
This project is a thread-safe, multi-user chat application built in Python using the socket and threading libraries. It supports multiple independent chat rooms, secure password authentication, and features a modular design for easy maintenance, including a dedicated database layer for message persistence.

🚀 Features
Modular Architecture: Separation of concerns into dedicated files: server.py, client.py, and database.py.

Multi-Room Support: Users can join or create any number of independent chat rooms, each identified by a unique ID (e.g., 'general', 'dev-team').

Thread Safety: Utilizes threading.Lock to ensure concurrent operations on shared data (like client lists and rooms) are safe and prevent race conditions.

Password Authentication: Requires a server password (chat@123) for all connections, and a separate password for the admin account (admin123).

Admin Tools: The admin user can issue server commands:

/kick [nickname] to instantly disconnect a user from the room.

/ban [nickname] to kick a user and prevent them from reconnecting (via ban.txt).

Persistent Storage (MySQL): Designed to save and retrieve messages from a MySQL database for chat history. (Requires manual setup of the table).

🛠️ Prerequisites
Before running the application, ensure you have the following installed:

Python 3.x: (Used to run the server and client files).

MySQL Server: (The database server where messages will be stored).

MySQL Connector (Simulated): The current database.py uses placeholders. In a real-world scenario, you would need to install a library like mysql-connector-python.

⚙️ Setup and Installation
Step 1: File Structure
Ensure you have the following three files in the same directory:

/chat-project   
├── server.py
├── client.py
└── database.py

Step 2: MySQL Database Setup (CRITICAL)
The server requires a specific database structure to exist before it can run.

Connect to your MySQL server using the command line or a client tool (e.g., MySQL Workbench).

Create the Database and Table by executing the following SQL commands:

# Create the database if it doesn't exist
CREATE DATABASE IF NOT EXISTS chat_db;

# Switch to the new database
USE chat_db;

# Create the table required for message storage and history
CREATE TABLE messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    room_id VARCHAR(255) NOT NULL,
    nickname VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

Step 3: Run the Server
Start the server first in a dedicated terminal window:

python server.py

The server will display status messages, including connection logs and database interaction logs.

Step 4: Run the Client
Open a new terminal window for each user you wish to connect:

python client.py

The client will prompt you for the following information in sequence:

Nickname: (e.g., 'Alice', 'admin')

Password: (chat@123 for regular users, admin123 for admin).

Room ID: (e.g., 'general', 'test-room').

⌨️ Usage and Commands
Client Interaction
Command

Description

Notes

Normal Message

Type any message and press Enter.

Message is prepended with [RoomID] [Nickname]:

/history

Sends a request to the server to load all messages saved in the current room's database history.



Admin Commands (Admin User Only)
Command

Usage

Description

/kick [nickname]

/kick Bob

Forces the specified user out of the current room.

/ban [nickname]

/ban Bob

Kicks the user and adds their nickname to ban.txt, permanently preventing them from reconnecting.

🎯 Future Improvements
This project can be enhanced with the following features:

Secure Authentication: Implement strong password hashing (e.g., using bcrypt) instead of plain-text password comparison.

User List Command: Add a /users command to allow users to see a list of everyone currently in their room.

Private Messaging: Implement server-side logic to handle direct messages (DM) between two specific users (e.g., /msg [user] [content]).

Client UI: Use a library like prompt_toolkit or build a GUI with Tkinter to provide a much cleaner and more organized chat interface, separating input from the message feed.
