# MessMate — Smart Mess Meal Planning Website

🚀 **Live Demo:** [Open MessMate](https://messmate-0as4.onrender.com)

MessMate is a student-friendly website built with **HTML, CSS, JavaScript, Python (Flask), and SQLite**. Students register, sign in, view the weekly menu, choose food items, and reserve a serving slot. The administrator manages the menu and notices and sees demand estimates from actual student selections.

## Why MessMate is different

Traditional mess operations often prepare food based on rough estimates and serve students as they arrive. MessMate collects meal choices in advance and groups expected arrivals into slots. This helps the mess team estimate quantities, plan serving flow, and potentially reduce food waste and waiting time. It supports planning; it does not guarantee zero waste or eliminate every queue.

## Features

- Student registration and login; passwords are stored as secure password hashes.
- Student dashboard with today's menu, weekly menu, notices, meal selection, and serving slots.
- Students can update or cancel a meal selection for the current date.
- One administrator account configured through environment variables (not created through student registration).
- Admin dashboard with date-based meal bookings, per-item demand counts, meal totals, slot-wise booking counts, and booking details.
- Admin can edit the seven-day menu and post/delete notices. Menu and notices are visible to students.
- SQLite database is created automatically on first run.
- Responsive layout for desktop and mobile screens.

## Requirements

- Python 3.10 or newer
- pip
- A modern browser

## Run on Windows (PowerShell)

1. Extract this folder and open it in VS Code.
2. Open a terminal in the `MessMate_Fresh` folder.
3. Create and activate a virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

4. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

5. Configure the secret and administrator credentials in the same PowerShell terminal. Replace the example values with your own:

   ```powershell
   $env:MESSMATE_SECRET_KEY = "replace-with-a-long-random-secret"
   $env:MESSMATE_ADMIN_USERNAME = "Arushi"
   $env:MESSMATE_ADMIN_PASSWORD = "password-not-shown-here"
   $env:MESSMATE_DEBUG = "1"
   ```

6. Start the website:

   ```powershell
   python app.py
   ```

7. Open `http://127.0.0.1:5000`.

For local development, `MESSMATE_DEBUG=1` enables Flask's debugger. Set it to `0` or leave it unset outside local development. Do not deploy with the sample secret or a weak admin password.

## First-time setup

- Student: choose **Register**, create an account, then log in.
- Admin: open **Admin** in the navigation and log in with the environment-configured admin username and password.
- Admin: edit the weekly menu and publish a notice. Student pages display both.
- Student: choose today's food items and serving slot, then save the selection.
- Admin: open the dashboard, choose a date, and review item counts and slot demand.

Default menu rows are inserted automatically as starter data. Edit them from the admin dashboard.

## Data storage

- `messmate.db`: SQLite database containing student records, password hashes, weekly menu, notices, and meal selections.
- Browser: Flask session cookie contains signed session information; passwords are not stored in `localStorage`.
- `MESSMATE_SECRET_KEY` and admin credentials: supplied through environment variables, not stored in the database.

The database file is ignored by Git. Do not commit real student information or secrets.

## Project structure

```text
MessMate_Fresh/
├── app.py
├── requirements.txt
├── README.md
├── .env.example
├── .gitignore
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── register.html
│   ├── login.html
│   ├── admin_login.html
│   ├── student.html
│   └── admin.html
└── static/
    ├── style.css
    └── script.js
```

## Important limitations and next improvements

- Password reset is not automated because email verification and a mail delivery service are not configured. For this version, users should contact the administrator for identity verification. Never reset passwords solely from an unverified student ID.
- Serving slots are currently used for lunch-style service across meal types; customize the slots if breakfast/dinner have different serving windows.
- Item counts mean number of student selections, not grams or kilograms. To calculate purchasing quantities, add portion-size and inventory data.
- This is a learning/demo project. Before public deployment, add CSRF protection, rate limiting, secure account recovery, proper secret management, database backups, and production hosting configuration.

## GitHub upload

Create an empty repository named `MessMate`, then run these commands from this folder:

```bash
git init
git add .
git status
git commit -m "Build MessMate meal planning website"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/MessMate.git
git push -u origin main
```

Review `git status` before committing. Never commit `.env`, `messmate.db`, student records, or credentials.
