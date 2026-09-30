from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

import sqlite3
from functools import wraps


# =========================================================
# FLASK APPLICATION
# =========================================================

app = Flask(__name__)

app.secret_key = "peer-debug-secret-key-change-this"


# =========================================================
# DATABASE CONNECTION
# =========================================================

DATABASE = "database.db"


def get_db():
    conn = sqlite3.connect(DATABASE)

    conn.row_factory = sqlite3.Row

    return conn


# =========================================================
# INITIALIZE DATABASE
# =========================================================

def init_db():

    conn = get_db()

    # ---------------- USERS ----------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            email TEXT UNIQUE NOT NULL,

            password TEXT NOT NULL,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


    # ---------------- HELP REQUESTS ----------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS help_requests (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            title TEXT NOT NULL,

            description TEXT NOT NULL,

            language TEXT NOT NULL,

            error TEXT,

            code TEXT,

            status TEXT DEFAULT 'open',

            helper_id INTEGER,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id)
                REFERENCES users(id),

            FOREIGN KEY (helper_id)
                REFERENCES users(id)
        )
    """)


    conn.commit()

    conn.close()


# =========================================================
# LOGIN REQUIRED DECORATOR
# =========================================================

def login_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if "user_id" not in session:

            flash("Please login first.")

            return redirect(url_for("login"))

        return function(*args, **kwargs)

    return wrapper


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    return render_template("frontend.html")


# =========================================================
# ABOUT
# =========================================================

@app.route("/about")
def about():

    return render_template("About page.html")


# =========================================================
# HELP
# =========================================================

@app.route("/help")
def help_page():

    return render_template("Help page.html")


# =========================================================
# REGISTER
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name", "").strip()

        email = request.form.get("email", "").strip().lower()

        password = request.form.get("password", "")


        # ---------------- VALIDATION ----------------

        if not name:

            return render_template(
                "Register page.html",
                error="Name is required."
            )


        if not email:

            return render_template(
                "Register page.html",
                error="Email is required."
            )


        if not password:

            return render_template(
                "Register page.html",
                error="Password is required."
            )


        if len(password) < 6:

            return render_template(
                "Register page.html",
                error="Password must contain at least 6 characters."
            )


        # ---------------- PASSWORD HASH ----------------

        hashed_password = generate_password_hash(password)


        # ---------------- DATABASE ----------------

        conn = get_db()

        try:

            conn.execute(
                """
                INSERT INTO users
                (name, email, password)

                VALUES (?, ?, ?)
                """,

                (
                    name,
                    email,
                    hashed_password
                )
            )

            conn.commit()

            conn.close()


            flash("Account created successfully. Please login.")

            return redirect(url_for("login"))


        except sqlite3.IntegrityError:

            conn.close()


            return render_template(
                "Register page.html",
                error="This email is already registered."
            )


    return render_template("Register page.html")


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()

        password = request.form.get("password", "")


        conn = get_db()


        user = conn.execute(
            """
            SELECT *

            FROM users

            WHERE email = ?
            """,

            (email,)
        ).fetchone()


        conn.close()


        # ---------------- CHECK USER ----------------

        if user and check_password_hash(
            user["password"],
            password
        ):

            session["user_id"] = user["id"]

            session["user_name"] = user["name"]

            session["user_email"] = user["email"]


            return redirect(
                url_for("dashboard")
            )


        return render_template(
            "Login page.html",
            error="Invalid email or password."
        )


    return render_template("Login page.html")


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    flash("You have been logged out.")

    return redirect(
        url_for("home")
    )


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
@login_required
def dashboard():

    conn = get_db()


    # ---------------- MY REQUESTS ----------------

    my_requests = conn.execute(
        """
        SELECT *

        FROM help_requests

        WHERE user_id = ?

        ORDER BY created_at DESC
        """,

        (session["user_id"],)
    ).fetchall()


    # ---------------- OPEN REQUESTS ----------------

    open_requests = conn.execute(
        """
        SELECT
            help_requests.*,
            users.name AS student_name

        FROM help_requests

        JOIN users
        ON help_requests.user_id = users.id

        WHERE help_requests.status = 'open'

        AND help_requests.user_id != ?

        ORDER BY help_requests.created_at DESC
        """,

        (session["user_id"],)
    ).fetchall()


    conn.close()


    return render_template(
        "dashboard.html",

        my_requests=my_requests,

        open_requests=open_requests
    )


# =========================================================
# ASK FOR HELP
# =========================================================

@app.route("/ask-help", methods=["GET", "POST"])
@login_required
def ask_help():

    if request.method == "POST":

        title = request.form.get(
            "title",
            ""
        ).strip()


        description = request.form.get(
            "description",
            ""
        ).strip()


        language = request.form.get(
            "language",
            ""
        ).strip()


        error = request.form.get(
            "error",
            ""
        ).strip()


        code = request.form.get(
            "code",
            ""
        ).strip()


        # ---------------- VALIDATION ----------------

        if not title:

            return render_template(
                "ask_help.html",
                error="Problem title is required."
            )


        if not description:

            return render_template(
                "ask_help.html",
                error="Problem description is required."
            )


        if not language:

            return render_template(
                "ask_help.html",
                error="Please select a programming language."
            )


        # ---------------- INSERT REQUEST ----------------

        conn = get_db()


        conn.execute(
            """
            INSERT INTO help_requests
            (
                user_id,
                title,
                description,
                language,
                error,
                code
            )

            VALUES (?, ?, ?, ?, ?, ?)
            """,

            (
                session["user_id"],
                title,
                description,
                language,
                error,
                code
            )
        )


        conn.commit()

        conn.close()


        flash(
            "Your help request has been submitted."
        )


        return redirect(
            url_for("dashboard")
        )


    return render_template(
        "ask_help.html"
    )


# =========================================================
# HELP A PEER
# =========================================================

@app.route("/help-peer")
@login_required
def help_peer():

    conn = get_db()


    requests = conn.execute(
        """
        SELECT
            help_requests.*,

            users.name AS student_name

        FROM help_requests

        JOIN users

        ON help_requests.user_id = users.id

        WHERE help_requests.status = 'open'

        AND help_requests.user_id != ?

        ORDER BY help_requests.created_at DESC
        """,

        (session["user_id"],)
    ).fetchall()


    conn.close()


    return render_template(
        "help_peer.html",
        requests=requests
    )


# =========================================================
# VIEW REQUEST
# =========================================================

@app.route("/request/<int:request_id>")
@login_required
def request_detail(request_id):

    conn = get_db()


    help_request = conn.execute(
        """
        SELECT
            help_requests.*,

            users.name AS student_name,

            helper.name AS helper_name

        FROM help_requests

        JOIN users

        ON help_requests.user_id = users.id

        LEFT JOIN users AS helper

        ON help_requests.helper_id = helper.id

        WHERE help_requests.id = ?
        """,

        (request_id,)
    ).fetchone()


    conn.close()


    if not help_request:

        flash("Request not found.")

        return redirect(
            url_for("dashboard")
        )


    return render_template(
        "request_detail.html",
        help_request=help_request
    )


# =========================================================
# ACCEPT REQUEST
# =========================================================

@app.route(
    "/request/<int:request_id>/accept",
    methods=["POST"]
)
@login_required
def accept_request(request_id):

    conn = get_db()


    help_request = conn.execute(
        """
        SELECT *

        FROM help_requests

        WHERE id = ?
        """,

        (request_id,)
    ).fetchone()


    if not help_request:

        conn.close()

        flash("Request not found.")

        return redirect(
            url_for("help_peer")
        )


    # Cannot accept own request

    if help_request["user_id"] == session["user_id"]:

        conn.close()

        flash(
            "You cannot accept your own request."
        )

        return redirect(
            url_for("help_peer")
        )


    # Check status

    if help_request["status"] != "open":

        conn.close()

        flash(
            "This request is no longer available."
        )

        return redirect(
            url_for("help_peer")
        )


    # Accept request

    conn.execute(
        """
        UPDATE help_requests

        SET
            status = 'accepted',
            helper_id = ?

        WHERE id = ?
        """,

        (
            session["user_id"],
            request_id
        )
    )


    conn.commit()

    conn.close()


    flash(
        "You accepted this help request."
    )


    return redirect(
        url_for(
            "request_detail",
            request_id=request_id
        )
    )


# =========================================================
# MARK REQUEST AS SOLVED
# =========================================================

@app.route(
    "/request/<int:request_id>/solve",
    methods=["POST"]
)
@login_required
def solve_request(request_id):

    conn = get_db()


    help_request = conn.execute(
        """
        SELECT *

        FROM help_requests

        WHERE id = ?
        """,

        (request_id,)
    ).fetchone()


    if not help_request:

        conn.close()

        flash("Request not found.")

        return redirect(
            url_for("dashboard")
        )


    # Only student or helper can solve

    if (
        help_request["user_id"] != session["user_id"]
        and
        help_request["helper_id"] != session["user_id"]
    ):

        conn.close()

        flash(
            "You are not allowed to modify this request."
        )

        return redirect(
            url_for(
                "request_detail",
                request_id=request_id
            )
        )


    conn.execute(
        """
        UPDATE help_requests

        SET status = 'solved'

        WHERE id = ?
        """,

        (request_id,)
    )


    conn.commit()

    conn.close()


    flash(
        "Request marked as solved."
    )


    return redirect(
        url_for(
            "request_detail",
            request_id=request_id
        )
    )


# =========================================================
# START APPLICATION
# =========================================================



init_db()

if __name__ == "__main__":
    app.run(debug=True)
