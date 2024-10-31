# CODEXIFY - Online Library Management System

Codexify is a system designed to facilitate the management of library resources and user accounts through a web-based platform.


## Features

- User Authentication: Secure login and registration system for users and administrators.
- Browse Library: Users can view available sections and books within the library.
- User Profile Management: Update user profile details and visualize account activity.
- Book Requests: Users can request books for specified durations and return them within the due date. Automatic revocation for overdue books.
- Feedback System: Users can provide feedback on books they have read.
- Search Functionality: Search for books or sections using the implemented search bar for users.
- Admin Dashboard: CRUD operations for managing books, sections, requests, and users. Easy access to lists of issued requests and registered users.
- Admin Privileges: Manually revoke or undo revocation on issued books. Issue requests for custom time periods. Manage book information and feedback. View graphs to visualize user activity and library data.


## Getting Started

1. **Install Python:** If Python is not already installed, download and install it from https://www.python.org/downloads/.
2. **Setup Project:**
    - Unzip the project folder and open it in VSCode.
    - Navigate to the project directory in the VSCode cmd Terminal using the command: `cd .\Root\Code\`
3. **Install Virtual Environment:**
    - Install virtualenv using pip: `pip install virtualenv`
4. **Create Virtual Environment:**
    - Create a virtual environment named `.venv` in the project directory: `virtualenv .venv`
    - Run the following command to activate virtual environment: `.\.venv\Scripts\activate`
5. **Install Dependencies:**
    - Run the following command to install project dependencies listed in `requirements.txt`: `pip install -r requirements.txt`
6. **Run the Application:**
    - Start the Flask application by running: `flask run`
7. **Access the Application:**
    - Open a web browser and go to: `http://localhost:5000`


## Technologies Used

- Flask: Python web framework for building the application.
- SQLAlchemy: SQL toolkit and Object-Relational Mapping (ORM) library for database interaction.
- Jinja2: Template engine for rendering HTML templates.
- Bootstrap: Frontend framework for responsive design.
- APScheduler: Library for scheduling tasks in the background.
- Plotly: Library for creating interactive plots and graphs.
