# C2 Framework Project

## Project Overview
This project is a **Command and Control (C2) Framework** developed as part of a cybersecurity learning project.  
The goal of this system is to understand how communication happens between a **central server** and multiple **agents** in a controlled and educational environment.

This project is being built to learn:
- client-server communication
- secure data exchange
- dashboard monitoring
- team collaboration using Git and GitHub

## Objectives
- Understand the working of **client-server architecture**
- Build a basic **C2 server**
- Develop an **agent** that connects to the server
- Implement **encrypted communication**
- Create a **dashboard** to view connected agents
- Learn structured teamwork and project development

## System Components

### 1. C2 Server
The main part of the framework.  
It listens for agent connections, manages communication, and controls the system.

### 2. Agent
A small client-side program that connects to the server and responds to requests.

### 3. Encryption Module
Used to secure communication between the server and agent.

### 4. Communication Protocol
Defines how data is sent and received in a structured format.

### 5. Dashboard
A user interface to monitor agent activity and system status.

## Project Structure
c2-framework-project
│
├── server/           # C2 server implementation
├── agent/            # Agent program
├── encryption/       # Encryption logic
├── communication/    # Communication protocol
├── dashboard/        # Web dashboard
│
├── docs/             # Project documentation
├── logs/             # Server logs
├── data/             # Stored data / agent records
├── tests/            # Testing scripts
│
├── README.md
├── .gitignore
└── requirements.txt

## Team Members
Name	Role
Nahila Mazgaonkar	Team Lead / Documentation / Coordination
Gayatri Gode	C2 Server Developer
Ramashish Gupta	Agent Developer
Ayan Khan	Encryption & Communication Engineer
Ismail Khan	Dashboard Developer

## Technologies Used
Python
Flask / FastAPI
HTML
CSS
JavaScript
Git & GitHub

## Architecture Diagram
                        +----------------------+
                        |      Dashboard       |
                        |  (Monitor / Control) |
                        +----------+-----------+
                                   |
                                   | API / Requests
                                   v
+--------------------------------------------------------------+
|                         C2 SERVER                            |
|--------------------------------------------------------------|
| - Accepts agent connections                                  |
| - Stores agent details                                       |
| - Sends commands                                             |
| - Receives responses                                         |
| - Maintains logs                                             |
+-------------------------+--------------------+---------------+
                          |                    |
                          |                    |
                          v                    v
               +----------------+     +----------------------+
               | Communication  |     | Encryption Module    |
               | Protocol Layer |     | Encrypt / Decrypt    |
               +--------+-------+     +----------+-----------+
                        |                         |
                        +-----------+-------------+
                                    |
                                    v
                           +------------------+
                           |      Agent       |
                           |------------------|
                           | - Connects       |
                           | - Sends info     |
                           | - Receives cmd   |
                           | - Executes task  |
                           +------------------+
## Workflow Diagram
[Start Project]
      |
      v
[Server Starts Running]
      |
      v
[Agent Starts]
      |
      v
[Agent Connects to Server]
      |
      v
[Secure Communication Established]
      |
      v
[Agent Sends Basic Information]
      |
      v
[Server Stores Agent Data]
      |
      v
[Dashboard Displays Connected Agent]
      |
      v
[Server Sends Command]
      |
      v
[Agent Receives Command]
      |
      v
[Agent Executes Task]
      |
      v
[Agent Sends Response Back]
      |
      v
[Dashboard Updates Status]
      |
      v
[End / Continue Monitoring]

## Basic Working Flow
The server starts first.

The agent program runs and tries to connect to the server.

A communication channel is created.
Encryption is applied to secure messages.
The agent sends basic information to the server.
The server records the connected agent.
The dashboard shows the connected agent status.
The server can send commands to the agent.
The agent processes the command and sends a response back.

## Project Roadmap
Phase 1: Project Setup
Create GitHub repository
Create project folder
Add README, .gitignore, and requirements.txt
Assign work to team members

Phase 2: System Design
Design architecture of the C2 framework
Define communication flow
Decide message format between server and agent
Plan encryption method

Phase 3: Core Development
Build basic server
Build basic agent
Establish initial connection between server and agent
Exchange simple messages

Phase 4: Secure Communication
Add encryption and decryption
Protect transmitted data
Test secure message exchange

Phase 5: Dashboard Development
Build dashboard interface
Show connected agents
Display agent details and responses

Phase 6: Testing and Debugging
Test each module separately
Fix connection errors
Verify communication flow
Check dashboard updates

Phase 7: Final Integration
Combine server, agent, encryption, and dashboard
Perform end-to-end testing
Prepare documentation
Final project review and presentation

## Learning Outcomes
By completing this project, the team will understand:
how client-server systems work
how agents communicate with a central server
how encryption helps protect communication
how dashboards can be used for monitoring
how to work as a team using GitHub

## Disclaimer
This project is developed only for educational and research purposes in a controlled environment.
It should be used only in authorized lab setups and never for unauthorized or harmful activities.
