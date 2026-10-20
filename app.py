"""
Student Platform — Application Controller
==========================================

This file is the ROUTING LAYER only (MVC "Controller"). It owns:
    - Flask app configuration
    - Session / auth plumbing
    - Decorators for access control
    - Route -> module dispatch

It owns almost NO business logic. Every route should reduce to:

    @app.route(...)
    @login_required
    def some_route():
        return module.do_the_thing(request, session)

Business rules, validation, and persistence live in modules/*.py.

THIS IS THE COMPLETE, ALL-PHASES REWRITE (not just the foundation).
Every section discussed — auth, profile, students, professors, subjects
(hub + subpages), materials, assignments, ratings, difficulty, statistics,
prerequisites, calendar (subject + global/events), discussion, the
three-part notes system, favorites, history, dual-mode search,
notifications, messages, administration, and moderation — is wired up
below as real, callable routes.

ERROR PHILOSOPHY (three tiers, per your decision — apology page ims gone)
--------------------------------------------------------------------------
    1. Success            -> flash_success(), stay on / redirect to a normal page.
    2. Recoverable failure -> flash_error()/flash_warning(), stay on / redirect
                              to a normal page. NEVER leaves the user's flow.
    3. Fatal failure       -> abort(403) / abort(404) / an uncaught exception
                              / a raised FatalAppError. These are the ONLY
                              things that reach a dedicated error page
                              (403.html / 404.html / 500.html), rendered by
                              the error handlers below, not by any
                              hand-called helper.

AUTHORITY MODEL
--------------------------------------------------------------------------
    1       Student
    2-4     Administration (ADMIN_L2..ADMIN_L4) — lower admin tiers
    5-6     Senior Administration (SENIOR_ADMIN_L5..L6) — can moderate
            everyone below them, including lower admins
    7       Professor — NOT a moderation target for anyone. Professors can
            be rated like a subject can be rated, but no one (not even a
            senior admin) can warn/ban/edit a professor's account. This is
            enforced in the moderation routes below, not assumed away.

NOTES ON WHAT THE DATABASE DOES NOT YET SUPPORT
--------------------------------------------------------------------------
Per our discussion, several routes below are wired up even though the
current schema doesn't fully back them yet (multi-university enrollment,
discussion boards, messaging). Each of those is marked with a
"# DB GAP:" comment at the point it matters, and additionally gated by a
Features flag so it 404s cleanly instead of half-working.

A CONSOLIDATED LIST OF EVERY ASSUMPTION AND KNOWN ROUGH EDGE IN THIS FILE
IS GIVEN AT THE VERY BOTTOM, IN THE "REVIEW NOTES" DOCSTRING, WITH LINE
REFERENCES, SO YOU CAN AUDIT THEM WITHOUT RE-READING THE WHOLE FILE.
"""

import os
from enum import IntEnum
from functools import wraps
from typing import Callable, Iterable, Optional

# Load .env file if present (python-dotenv optional dependency)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
import modules.sql_helper_dictionary as sql_h
import modules.auth as auth
import modules.profile as profile
import modules.students as students
import modules.professors as professors
import modules.subjects as subjects
import modules.materials as materials
import modules.assignments as assignments
import modules.ratings as ratings
import modules.difficulty as difficulty
import modules.statistics as statistics
import modules.prerequisites as prerequisites
import modules.calendar as calendar_mod
import modules.discussion as discussion
import modules.notes as notes
import modules.favorites as favorites
import modules.history as history
import modules.search as search
import modules.events as events
import modules.messages as messages
import modules.notifications as notifications
import modules.admin as admin
import modules.moderation as moderation

###############################################################################
# Configuration
###############################################################################

class Config:
    """All Flask configuration in one place, env-driven with local defaults."""
    EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS", "studentflowapp2026@gmail.com")
    EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "")
    SECRET_KEY = os.environ.get("SECRET_KEY", os.urandom(32).hex())
    SESSION_TYPE = "filesystem"
    SESSION_PERMANENT = False
    SESSION_FILE_DIR = os.environ.get("SESSION_FILE_DIR", "./.flask_session")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("FLASK_ENV") == "production"
    MAX_CONTENT_LENGTH = 64 * 1024 * 1024  # 64MB upload ceiling
    DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"
    years = [1, 2, 3, 4]
    semesters = [1, 2]


class Features:
    """
    Feature flags. A route checks these and 404s if disabled, so an
    unfinished/undecided feature can sit in the file safely without being
    reachable, instead of being deleted and re-added later.
    """
    REQUIRE_UPLOAD_APPROVAL = True   # non-privileged uploads need admin approval
    ENABLE_DISCUSSIONS = True       # subject discussion boards — undecided per your notes
    ENABLE_MESSAGES = True           # you confirmed messaging should exist
    ENABLE_EVENTS = True
    ENABLE_NOTIFICATIONS = True
    ENABLE_CALENDAR = True 
    ENABLE_LIVE_SEARCH = True        # the one place you said JS/AJAX may be used
    MULTI_UNIVERSITY = False         # DB GAP: cross-university enrollment not modeled yet
    ENABLE_UPLOAD_FILES = False      # DB GAP: file storage not modeled yet, but the route is wired up

###############################################################################
# Domain enums
###############################################################################

class Authority(IntEnum):
    """Numeric authority level, as stored in the database. Ordered, so
    `>=` comparisons directly express 'at least this privileged'."""
    STUDENT = 1
    ADMIN_L2 = 2
    ADMIN_L3 = 3
    ADMIN_L4 = 4
    SENIOR_ADMIN_L5 = 5
    SENIOR_ADMIN_L6 = 6
    PROFESSOR = 7

    @classmethod
    def admin_levels(cls) -> tuple["Authority", ...]:
        return (cls.ADMIN_L2, cls.ADMIN_L3, cls.ADMIN_L4)

    @classmethod
    def senior_admin_levels(cls) -> tuple["Authority", ...]:
        return (cls.SENIOR_ADMIN_L5, cls.SENIOR_ADMIN_L6)
    @staticmethod
    def is_admin(authority: "Authority") -> bool:
        return authority in (*Authority.admin_levels(), *Authority.senior_admin_levels())


class AccountState(IntEnum):
    """Account standing, independent of authority level."""
    ACTIVE = 0
    WARNED = 1
    BANNED = 2


class ApprovalState(IntEnum):
    """Generic approval state, reused across subjects/materials/notes."""
    PENDING = 0
    APPROVED = 1
    REJECTED = 2


class FlashCategory:
    """Bootstrap-style flash categories; templates consume these as CSS classes."""
    SUCCESS = "success"
    INFO = "info"
    WARNING = "warning"
    DANGER = "danger"


###############################################################################
# Session contract
###############################################################################
# The ONE place that knows what lives in session[...]. Every other piece of
# code goes through UserSession, never through the raw `session` dict.

class UserSession:
    _USER_ID = "user_id"
    _EMAIL = "email"
    _AUTHORITY = "authority"
    _STATE = "state"
    _PROFILE_ID = "profile_id"
    _WARNING_COUNT = "warning_count"
    _WARNING_STATE = "warning_state"
    _avatar = "avatar"
    _NAME = "name"

    @staticmethod
    def start(
        *,
        avatar = "",
        user_id: int,
        email: str,
        authority: Authority,
        state: AccountState,
        profile_id: Optional[int] = None,
        warning_state: Optional[int] = 0,
        warning_count: int = 0,
        _NAME: str = "",

    ) -> None:
        session.clear()
        session[UserSession._USER_ID] = user_id
        session[UserSession._EMAIL] = email
        session[UserSession._NAME] = _NAME
        session[UserSession._avatar] = avatar
        session[UserSession._AUTHORITY] = int(authority)
        session[UserSession._STATE] = int(state)
        session[UserSession._PROFILE_ID] = profile_id
        session[UserSession._WARNING_COUNT] = warning_count
        session[UserSession._WARNING_STATE] = warning_state

    @staticmethod
    def end() -> None:
        session.clear()
    @staticmethod
    def update_avatar(avatar: str) -> None:
        session[UserSession._avatar] = avatar

    @staticmethod
    def is_logged_in() -> bool:
        return UserSession._USER_ID in session

    @staticmethod
    def user_id() -> Optional[int]:
        return session.get(UserSession._USER_ID)

    @staticmethod
    def email() -> Optional[str]:
        return session.get(UserSession._EMAIL)

    @staticmethod
    def profile_id() -> Optional[int]:
        return session.get(UserSession._PROFILE_ID)

    @staticmethod
    def authority() -> Optional[Authority]:
        value = session.get(UserSession._AUTHORITY)
        return Authority(value) if value is not None else None

    @staticmethod
    def state() -> Optional[AccountState]:
        value = session.get(UserSession._STATE)
        return AccountState(value) if value is not None else None

    @staticmethod
    def warning_count() -> int:
        return session.get(UserSession._WARNING_COUNT, 0)

    @staticmethod
    def warning_state() -> int:
        return session.get(UserSession._WARNING_STATE, 0)

    @staticmethod
    def is_professor() -> bool:
        return UserSession.authority() == Authority.PROFESSOR

    @staticmethod
    def is_admin() -> bool:
        authority = UserSession.authority()
        return (authority is not None and Authority.is_admin(authority))
    @staticmethod
    def get_avatar() -> str:
        return session.get(UserSession._avatar, "")
    @staticmethod
    def get_session() -> dict:
        return {
            "avatar": UserSession.get_avatar(),
            "user_id": UserSession.user_id(),
            "email": UserSession.email(),
            "authority": UserSession.authority(),
            "state": UserSession.state(),
            "profile_id": UserSession.profile_id(),
            "warning_count": UserSession.warning_count(),
            "warning_state": UserSession.warning_state(),
            "name": session.get(UserSession._NAME, ""),

        }
    @staticmethod
    def update_session(key, value) -> None:
        if key in [UserSession._avatar, UserSession._USER_ID, UserSession._EMAIL,
                   UserSession._AUTHORITY, UserSession._STATE, UserSession._PROFILE_ID,
                   UserSession._WARNING_COUNT, UserSession._WARNING_STATE, UserSession._NAME]:
                session[key] = value
                print(f"Updated session key '{key}' to value: {value}")
    @staticmethod
    def get_name() -> str:
        return session.get(UserSession._NAME, "")
    @staticmethod
    def owns_profile(profile_id: int) -> bool:
        return UserSession.profile_id() == profile_id
###############################################################################
# Fatal errors
###############################################################################

class FatalAppError(Exception):
    """
    Raise this from module-layer code for a genuine, unrecoverable failure
    (corrupt data, missing foreign key, broken invariant) that a flash
    message can't meaningfully resolve. Anything recoverable should be
    signalled with a module's own (bool, message) return instead, and the
    route flashes + stays on/returns to the page — it should never reach
    here.
    """
    def __init__(self, message: str = "A fatal error occurred."):
        super().__init__(message)
        self.message = message
###############################################################################
# Decorators
###############################################################################

def login_required(view: Callable) -> Callable:
    """Require an active, non-banned session. Redirects to login otherwise."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not UserSession.is_logged_in():
            flash_info("Please log in to continue.")
            return redirect(url_for("login", next=request.path))
        if UserSession.state() == AccountState.BANNED:
            UserSession.end()
            flash_error("Your account has been banned.")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def guest_only(view: Callable) -> Callable:
    """For login/register/forgot-password: bounce already-logged-in users home."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if UserSession.is_logged_in():
            return redirect(url_for("home"))
        return view(*args, **kwargs)
    return wrapped


def authority_required(
    *,
    minimum: Optional[Authority] = None,
    exactly: Optional[Authority] = None,
    one_of: Optional[Iterable[Authority]] = None,
) -> Callable:
    """
    Composable authority gate. Use exactly one of the three filters.
    Always implies login_required.
    """
    def decorator(view: Callable) -> Callable:
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            current = UserSession.authority()
            allowed = True
            if minimum is not None:
                allowed = current is not None and current >= minimum
            elif exactly is not None:
                allowed = current == exactly
            elif one_of is not None:
                allowed = current in set(one_of)
            if not allowed:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


# Thin, readable aliases built on authority_required.
professor_required = authority_required(exactly=Authority.PROFESSOR)
admin_required = authority_required(minimum=Authority.ADMIN_L2)
senior_admin_required = authority_required(minimum=Authority.SENIOR_ADMIN_L5)


def feature_required(flag_name: str) -> Callable:
    """Gate a route behind a Features flag; 404s cleanly if the feature is off."""
    def decorator(view: Callable) -> Callable:
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not getattr(Features, flag_name, False):
                abort(404)
            return view(*args, **kwargs)
        return wrapped
    return decorator


def owner_or_admin_required(get_owner_user_id: Callable) -> Callable:
    """
    Generic ownership gate: allows the resource owner OR an admin through,
    blocks everyone else with 403. `get_owner_user_id(*args, **kwargs)` must
    return the owning user_id for the resource being accessed, using the
    same args the route itself receives (e.g. a note_id from the URL).
    """
    def decorator(view: Callable) -> Callable:
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            owner_id = get_owner_user_id(*args, **kwargs)
            if UserSession.user_id() != owner_id and not UserSession.is_admin():
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


###############################################################################
# Flash + redirect helpers
###############################################################################

def flash_success(message: str) -> None:
    flash(message, FlashCategory.SUCCESS)


def flash_info(message: str) -> None:
    flash(message, FlashCategory.INFO)


def flash_warning(message: str) -> None:
    flash(message, FlashCategory.WARNING)


def flash_error(message: str) -> None:
    flash(message, FlashCategory.DANGER)


def go_back(default_endpoint: str = "home"):
    """Redirect to wherever the user came from, falling back to home."""
    return redirect(request.referrer or url_for(default_endpoint))


def wants_json() -> bool:
    """True if this request should get a JSON response (used by the few
    AJAX endpoints — live search and favorite-toggle)."""
    return request.accept_mimetypes["application/json"] >= request.accept_mimetypes["text/html"] \
        or request.args.get("format") == "json"


###############################################################################
# Application factory
###############################################################################

def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    try:
        from flask.sessions import Session as _FlaskSession
        _FlaskSession(app)
    except ImportError:
        pass

    register_error_handlers(app)
    register_routes(app)

    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    @app.context_processor
    def inject_user_session():
        return dict(UserSession=UserSession)

    return app


###############################################################################
# Error handlers — the entire "fatal error" story lives here
###############################################################################

def register_error_handlers(app: Flask) -> None:

    @app.errorhandler(403)
    def forbidden(_e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(FatalAppError)
    def fatal_app_error(e: FatalAppError):
        app.logger.error("FatalAppError: %s", e.message)
        return render_template("errors/500.html", message=e.message), 500

    @app.errorhandler(500)
    def internal_error(e):
        app.logger.exception("Unhandled exception")
        return render_template("errors/500.html", message="Something went wrong."), 500


###############################################################################
# Routes
###############################################################################

def register_routes(app: Flask) -> None:
    _register_auth_routes(app)
    _register_home_routes(app)
    _register_profile_routes(app)
    _register_student_routes(app)
    _register_professor_routes(app)
    _register_subject_routes(app)
    _register_material_routes(app)
    _register_assignment_routes(app)
    _register_rating_routes(app)
    _register_prerequisite_routes(app)
    _register_calendar_routes(app)
    _register_discussion_routes(app)
    _register_notes_routes(app)
    _register_favorite_routes(app)
    _register_history_routes(app)
    _register_search_routes(app)
    _register_notification_routes(app)
    _register_event_routes(app)
    _register_message_routes(app)
    _register_professor_tool_routes(app)
    _register_admin_routes(app)
    _register_moderation_routes(app)


# -----------------------------------------------------------------------
# Authentication
# -----------------------------------------------------------------------

def _register_auth_routes(app: Flask) -> None:
    @app.route("/")
    def index():
        return redirect(url_for("home")) if UserSession.is_logged_in() else redirect(url_for("login"))

    @app.route("/auth/login", methods=["GET", "POST"])
    @guest_only
    def login():
        if request.method == "POST":
            email = request.form.get("email", "").strip()
            password = request.form.get("password", "").strip()
            is_user=auth.authenticate(email, password)
            if is_user:
                if not is_user["approved"]:
                    flash_error("Your account is not approved yet. Please wait for admin approval, you can login as student but you will not be able to access any features until approved.")
                    is_user["status"]=1##status 1 means student
                if AccountState(is_user["state"])==AccountState.BANNED:
                    flash_error("Your account has been banned. Please contact support for more information.")
                    return redirect(url_for("login"))
                if AccountState(is_user["state"])==AccountState.WARNED:
                    flash_warning("Your account has been warned. Please contact support for more information.")
                UserSession.start(
                    user_id=is_user["id"],
                    email=is_user["email"],
                    authority=Authority(is_user["status"]),
                    state=AccountState(is_user.get("state", 0)),
                    profile_id=is_user.get("profile", {}).get("p_id"),
                    warning_state=is_user.get("state", 0),
                    warning_count=is_user.get("warning_count", 0),
                    _NAME=is_user.get("profile", {}).get("name", ""),
                    avatar=is_user.get("profile", {}).get("avatar", ""),
                )
                flash_success("Logged in successfully.")
                next_url = request.args.get("next")
                return redirect(next_url or url_for("home"))
            flash_error("Invalid email or password.")
            return redirect(url_for("login"))
        return render_template("auth/login.html")

    @app.route("/auth/logout")
    @login_required
    def logout():
        UserSession.end()
        flash_success("You have been logged out.")
        return redirect(url_for("login"))

    @app.route("/auth/register", methods=["GET", "POST"])
    @guest_only
    def register():##any change in the front end only ifect how i should handel module no logic is hear
        if request.method == "POST":
            all_fields=request.form.to_dict()
            ok, error = auth.register(all_fields)
            if not ok:
                flash_error(error or "Registration failed.")
                return redirect(url_for("register"))
            flash_success("Account created. You can now log in.")
            return redirect(url_for("login"))##will macke user register to home in final v 
        return render_template("auth/register.html")

    @app.route("/auth/forgot-password", methods=["GET", "POST"])
    @guest_only
    def forgot_password():
        if request.method == "POST":
            email = request.form.get("email", "").strip()
            # Always show the same message regardless of whether the email
            # exists, to avoid leaking which emails are registered.
            url=request.host_url.rstrip("/") #mut be reevisted 
            auth.request_password_reset(email,url)
            flash_info("If that email exists, a reset link has been sent.")
            return redirect(url_for("login"))
        return render_template("auth/forgot_password.html")

    @app.route("/auth/reset-password/<token>", methods=["GET", "POST"])
    @guest_only
    def reset_password(token: str):
        if request.method == "POST":
            reecheck_password = request.form.get("recheck_password", "")
            new_password = request.form.get("password", "")
            if new_password != reecheck_password:
                flash_error("Passwords do not match.")
                return redirect(url_for("reset_password", token=token))
            ok, error = auth.reset_password(token, new_password)
            if not ok:
                flash_error(error or "Could not reset password.")
                return redirect(url_for("reset_password", token=token))
            flash_success("Password updated. Please log in.")
            return redirect(url_for("login"))
        return render_template("auth/reset_password.html", token=token)


# -----------------------------------------------------------------------
# Home
# -----------------------------------------------------------------------

def _register_home_routes(app: Flask) -> None:

    @app.route("/home")
    @login_required
    def home():
        user_id55 = UserSession.user_id()
        user_prof = profile.get_profile(user_id55) or {}
        avatar = user_prof.get("avatar", "")
        UserSession.update_avatar(avatar)
        m = messages.list_messages(user_id55, unread_only="unread") if Features.ENABLE_MESSAGES else []
        context = {
            "notifications": notifications.list_notification(unread_only="unread", id=user_id55)
                              if Features.ENABLE_NOTIFICATIONS else [],
            "Features": Features,
            "user_profile": user_prof,
            "messages": m if Features.ENABLE_MESSAGES else [],
            "unread_message_count": len(m) if Features.ENABLE_MESSAGES else 0,
            "recent_messages": messages.list_messages(user_id55, unread_only=False)[:5] if Features.ENABLE_MESSAGES else [],
            "favorites": favorites.list_favorites(user_id55),
            "recent_history": history.get_history(user_id55, limit=5),
            "upcoming_events": events.list_events(user_id55) if Features.ENABLE_EVENTS else [],
            "is_admin": UserSession.is_admin(),
            "is_professor": UserSession.is_professor(),
        }
        return render_template("home/home.html", **context)


# -----------------------------------------------------------------------
# Profile
# -----------------------------------------------------------------------

def _register_profile_routes(app: Flask) -> None:

    @app.route("/profile")
    @login_required
    def profile_view():
        user_id = UserSession.user_id()
        data = profile.get_profile(user_id)
        if data is None:
            profile.update_profile(user_id, {"email": session.get("email", ""), "name": session.get("email", "").split("@")[0]})
            data = profile.get_profile(user_id)
        return render_template("profile/overview.html", profile=data)

    @app.route("/profile/edit", methods=["GET", "POST"])
    @login_required
    def profile_edit():
        if request.method == "POST":
            form_data = request.form.to_dict()
            if form_data.get("name"):
                UserSession.update_session(UserSession._NAME, form_data["name"])
            print(UserSession.get_session())
            form_data["avatar_up"] = request.files.get("avatar")  # Handle avatar upload
            ok, error = profile.update_profile(UserSession.user_id(), form_data)
            if not ok:
                flash_error(error or "Could not update profile.")
                return redirect(url_for("profile_edit"))
            flash_success("Profile updated.")
            return redirect(url_for("profile_view"))
        data = profile.get_profile(UserSession.user_id())
        return render_template("profile/edit.html", profile=data)
# -----------------------------------------------------------------------
# Students (public-ish directory + individual pages)
# -----------------------------------------------------------------------
###not a thing on itis own
def _register_student_routes(app: Flask) -> None:

    @app.route("/students")
    @login_required
    def student_list():
        query_filters = {"year": request.args.get("year"), "university": request.args.get("university")}
        return render_template("students.html", students=students.list_students(query_filters))

    @app.route("/student/<int:student_id>")
    @login_required
    def student_detail(student_id: int):
        data = students.get_student(student_id)
        if data is None:
            abort(404)
        return render_template("student/overview.html", student=data)

    @app.route("/gpa-calculator", methods=["GET", "POST"])
    @login_required
    def gpa_calculator():
        user_id = UserSession.user_id()
        if request.method == "POST":
            subject_id = request.form.get("subject_id", type=int)
            year = request.form.get("year", type=int) or 1
            semester = request.form.get("semester", type=int) or 1
            grade_val = request.form.get("grade", type=float)
            letter = request.form.get("letter", "").strip().upper() or None
            hours = request.form.get("hours_studied", type=float) or 0.0

            if not subject_id or grade_val is None:
                flash_error("Please select a valid subject and enter a grade.")
                return redirect(url_for("gpa_calculator"))

            ok, err = students.save_student_grade(
                user_id, subject_id, year, semester, grade_val, letter, hours
            )
            if not ok:
                flash_error(err or "Failed to record course grade.")
            else:
                flash_success("Course grade and GPA updated successfully.")
            return redirect(url_for("gpa_calculator"))

        all_subjects = subjects.list_subjects(user_id=user_id)
        grades_data = students.get_student_grades(user_id)
        user_prof = profile.get_profile(user_id) or {}

        return render_template(
            "student/gpa_calculator.html",
            subjects=all_subjects,
            grades_data=grades_data,
            profile=user_prof
        )

    @app.route("/gpa-calculator/delete/<int:grade_id>", methods=["POST"])
    @login_required
    def gpa_delete_grade(grade_id: int):
        user_id = UserSession.user_id()
        ok, err = students.delete_student_grade(user_id, grade_id)
        if not ok:
            flash_error(err or "Could not delete grade record.")
        else:
            flash_success("Grade entry removed and GPA recalculated.")
        return redirect(url_for("gpa_calculator"))


# -----------------------------------------------------------------------
# Professors — public pages, immune from moderation (see _register_moderation_routes)
# -----------------------------------------------------------------------

def _register_professor_routes(app: Flask) -> None:

    @app.route("/professors")
    @login_required
    def professor_list():
        return render_template("professors/profile.html", professors=professors.list_professors())

    @app.route("/professor/<int:professor_id>")
    @login_required
    def professor_detail(professor_id: int):
        data = professors.get_professor(professor_id)
        if data is None:
            abort(404)
        return render_template("professors/overview.html", professor=data)


# -----------------------------------------------------------------------
# Subjects — the hub. /subject/<id> shows ONLY the overview strip (name,
# code, year, semester, rating/difficulty/GPA/professor previews, and
# material/assignment/prerequisite previews). Every deeper view — full
# ratings, full statistics, discussion, notes, calendar, prerequisites in
# full — is its own dedicated subpage, per your explicit answer.
# -----------------------------------------------------------------------

def _register_subject_routes(app: Flask) -> None:

    @app.route("/subjects",methods=["GET", "POST"])
    @login_required
    def subject_list():
        if request.method == "POST":
            form_data = request.form.to_dict()
            print(form_data)
            subjects_list={}
            subjects_list["subjects"]=subjects.list_subjects(UserSession.user_id(),form_data)
            subjects_list["years"] = Config.years
            subjects_list["semesters"] = Config.semesters
            print(subjects_list)
            return render_template("subjects/serch.html", subjects=subjects_list )
        else:
            subjects_list={}
            subjects_list["subjects"] = subjects.list_subjects(UserSession.user_id())
            subjects_list["years"] = Config.years
            subjects_list["semesters"] = Config.semesters
            print("Subjects list:", subjects_list)  # Debugging line
            return render_template("subjects/serch.html", subjects=subjects_list)

    @app.route("/subject/add", methods=["GET", "POST"])
    @login_required
    def subject_add():
        s_dict={}
        s_dict["years"]=Config.years
        s_dict["Semester"]=Config.semesters
        if request.method == "POST":
            request_form_send = request.form.to_dict()
            ok, error, new_id = subjects.create_subject(request_form_send, int(UserSession.authority()), UserSession.user_id())
            if not ok:
                flash_error(error or "Could not create subject.")
                return redirect(url_for("subject_add"))
            if Features.REQUIRE_UPLOAD_APPROVAL and not UserSession.is_admin():
                flash_success("Subject submitted for admin approval.")
            else:
                flash_success("Subject created.")
            return redirect(url_for("subject_detail", subject_id=new_id))
        return render_template("subjects/add.html",s_data=s_dict)

    @app.route("/subject/<int:subject_id>", methods=["GET", "POST"])
    @login_required
    def subject_detail(subject_id: int):
        if request.method == "POST":
            form_data = request.form.get("favorite_action")
            if form_data == "add":
                ok,error= favorites.add_favorite(UserSession.user_id(), subject_id,"subject")
                if not ok:
                    flash_error(error or "Could not add subject to favorites.")
                    return redirect(url_for("subject_detail", subject_id=subject_id))
                flash_success("Subject added to favorites.")
                return redirect(url_for("subject_detail", subject_id=subject_id))
            elif form_data == "remove":
                ok,error= favorites.remove_favorite(UserSession.user_id(), subject_id,"subject")
                if not ok:
                    flash_error(error or "Could not remove subject from favorites.")
                    return redirect(url_for("subject_detail", subject_id=subject_id))
                flash_success("Subject removed from favorites.")
                return redirect(url_for("subject_detail", subject_id=subject_id))
        overview = subjects.get_subject_overview(subject_id, user_id=UserSession.user_id())
        if overview is None:
            abort(404)
        history.record_visit(UserSession.user_id(), "subject", subject_id)
        return render_template("subjects/subject_detail.html", subject=overview)
#####################
    @app.route("/subject/<int:subject_id>/edit", methods=["GET", "POST"])
    @admin_required
    def subject_edit(subject_id: int):
        if request.method == "POST":
            ok, error = subjects.edit_subject(subject_id, request.form)
            if not ok:
                flash_error(error or "Could not update subject.")
                return redirect(url_for("subject_edit", subject_id=subject_id))
            flash_success("Subject updated.")
            return redirect(url_for("subject_detail", subject_id=subject_id))
        overview = subjects.get_subject_overview(subject_id, user_id=UserSession.user_id())
        if overview is None:
            abort(404)
        return render_template("subjects/edit.html", subject=overview)

    @app.route("/subject/<int:subject_id>/delete", methods=["POST"])
    @admin_required
    def subject_delete(subject_id: int):
        ok, error = subjects.delete_subject(subject_id)
        if not ok:
            flash_error(error or "Could not delete subject.")
            return redirect(url_for("subject_detail", subject_id=subject_id))
        flash_success("Subject deleted.")
        return redirect(url_for("subject_list"))


# -----------------------------------------------------------------------
# Materials (subject subpage)
# -----------------------------------------------------------------------

def _register_material_routes(app: Flask) -> None:

    @app.route("/subject/<int:subject_id>/materials", methods=["GET", "POST"])
    @login_required
    def subject_materials(subject_id: int):
        user_id = UserSession.user_id()
        authority = UserSession.authority()

        # Extract filter criteria based on request method
        if request.method == "POST":
            filters = request.form.to_dict()
        else:
            filters = {
                "search": request.args.get("search", ""),
                "content_type": request.args.get("content_type", ""),
                "material_type": request.args.get("material_type", ""),
            }

        # Retrieve materials directly (unwrapped)
        materials_data = materials.list_materials(
            subject_id,
            user_id=user_id,
            filters=filters,
            authority=authority
        )

        # If list_materials returns a dict wrapped with a 'materials' key, unwrap it
        if isinstance(materials_data, dict) and "materials" in materials_data:
            materials_data = materials_data["materials"]

        subject_overview = subjects.get_subject_overview(subject_id, user_id=user_id)
        if not subject_overview:
            abort(404)

        return render_template(
            "subjects/materials.html",
            subject=subject_overview,
            materials=materials_data,
            active_category=filters.get("content_type", ""),
            active_sub_category=filters.get("material_type", ""),
            active_search=filters.get("search", ""),
        )

    @app.route("/subject/<int:subject_id>/material/upload", methods=["GET", "POST"])
    @login_required
    def material_upload(subject_id: int):
        if request.method == "POST":
            form_data = request.form.to_dict()
            ok, error, new_id = materials.upload_material(
                subject_id, form_data, UserSession.user_id(), UserSession.authority()
            )
            if not ok:
                flash_error(error or "Upload failed.")
                return redirect(url_for("material_upload", subject_id=subject_id,Features=Features))
            if Features.REQUIRE_UPLOAD_APPROVAL and not UserSession.is_admin():
                flash_success("Material uploaded and submitted for approval.")
            else:
                flash_success("Material uploaded.")
            return redirect(url_for("subject_materials",subject_id=subject_id))
        elif request.method == "GET":   

            return render_template("subjects/add_materual.html", subject_id=subject_id, Features=Features)
        abort(405)  # Method not allowed for other HTTP methods
###################

    @app.route("/subject/<int:subject_id>/material/<int:material_id>")
    @login_required
    def material_detail(subject_id: int, material_id: int):
        data = materials.get_material(material_id)
        if data is None:
            abort(404)
        history.record_visit(UserSession.user_id(), "material", material_id)
        return render_template("subjects/materials.html", subject=subjects.get_subject_overview(subject_id, UserSession.user_id()), materials=[data], active_material=data)

    @app.route("/subject/<int:subject_id>/material/<int:material_id>/edit", methods=["GET", "POST"])
    @login_required
    def material_edit(subject_id: int, material_id: int):
        if request.method == "POST":
            ok, error = materials.edit_material(material_id, request.form)
            if not ok:
                flash_error(error or "Could not update material.")
                return redirect(url_for("material_edit", subject_id=subject_id, material_id=material_id))
            flash_success("Material updated.")
            return redirect(url_for("subject_materials", subject_id=subject_id))
        data = materials.get_material(material_id)
        if data is None:
            abort(404)
        return render_template("material_edit.html", subject_id=subject_id, material=data)

    @app.route("/subject/<int:subject_id>/material/<int:material_id>/delete", methods=["POST"])
    @login_required
    def material_delete(subject_id: int, material_id: int):
        ok, error = materials.delete_material(material_id)
        if not ok:
            flash_error(error or "Could not delete material.")
            return redirect(url_for("subject_materials", subject_id=subject_id))
        flash_success("Material deleted.")
        return redirect(url_for("subject_materials", subject_id=subject_id))


# -----------------------------------------------------------------------
# Assignments (subject subpage)
# -----------------------------------------------------------------------

def _register_assignment_routes(app: Flask) -> None:

    @app.route("/subject/<int:subject_id>/assignments")
    @login_required
    def subject_assignments(subject_id: int):
        return render_template(
            "subject_assignments.html",
            subject_id=subject_id,
            assignments=assignments.list_assignments(subject_id),
        )

    @app.route("/subject/<int:subject_id>/assignment/<int:assignment_id>")
    @login_required
    def assignment_detail(subject_id: int, assignment_id: int):
        data = assignments.get_assignment(assignment_id)
        if data is None:
            abort(404)
        history.record_visit(UserSession.user_id(), "assignment", assignment_id)
        return render_template("assignment.html", subject_id=subject_id, assignment=data)


# -----------------------------------------------------------------------
# Ratings / Difficulty / Statistics (subject subpages)
# -----------------------------------------------------------------------

def _register_rating_routes(app: Flask) -> None:

    @app.route("/subject/<int:subject_id>/ratings", methods=["GET", "POST"])
    @login_required
    def subject_ratings(subject_id: int):
        subject_overview = subjects.get_subject_overview(subject_id, user_id=UserSession.user_id())
        if not subject_overview:
            abort(404)
        if request.method == "POST":
            raw_score = request.form.get("score") or request.form.get("raw_score")
            difficulty_score = request.form.get("difficulty")
            gpa = request.form.get("gpa")
            if not raw_score:
                flash_error("Please select a rating score between 1 and 5.")
                return redirect(url_for("subject_ratings", subject_id=subject_id))
            ok, err = ratings.add_rating(
                UserSession.user_id(), "subject", subject_id, int(raw_score),
                difficulty=int(difficulty_score) if difficulty_score else None,
                gpa=float(gpa) if gpa else None
            )
            if not ok:
                flash_error(err or "Could not submit rating.")
            else:
                flash_success("Rating submitted successfully.")
            return redirect(url_for("subject_ratings", subject_id=subject_id))

        ratings_data = ratings.get_ratings("subject", subject_id)
        user_rating = ratings.get_user_rating(UserSession.user_id(), "subject", subject_id)
        return render_template(
            "subjects/ratings.html",
            subject=subject_overview,
            ratings=ratings_data,
            user_rating=user_rating
        )

    @app.route("/subject/<int:subject_id>/difficulty", methods=["GET", "POST"])
    @login_required
    def subject_difficulty(subject_id: int):
        subject_overview = subjects.get_subject_overview(subject_id, user_id=UserSession.user_id())
        if not subject_overview:
            abort(404)
        if request.method == "POST":
            diff_score = request.form.get("difficulty") or request.form.get("score")
            if not diff_score:
                flash_error("Please select a difficulty level between 1 and 5.")
                return redirect(url_for("subject_difficulty", subject_id=subject_id))
            ok, err = difficulty.submit_difficulty(UserSession.user_id(), subject_id, int(diff_score))
            if not ok:
                flash_error(err or "Could not submit difficulty.")
            else:
                flash_success("Difficulty rating submitted successfully.")
            return redirect(url_for("subject_difficulty", subject_id=subject_id))

        diff_data = difficulty.get_difficulty(subject_id)
        return render_template(
            "subjects/difficulty.html",
            subject=subject_overview,
            difficulty=diff_data
        )

    @app.route("/subject/<int:subject_id>/statistics")
    @login_required
    def subject_statistics(subject_id: int):
        subject_overview = subjects.get_subject_overview(subject_id, user_id=UserSession.user_id())
        if not subject_overview:
            abort(404)
        stats = statistics.get_subject_stats(subject_id)
        return render_template(
            "statistics/index.html",
            subject=subject_overview,
            stats=stats
        )

# -----------------------------------------------------------------------
# Prerequisites (subject subpage)
# -----------------------------------------------------------------------

def _register_prerequisite_routes(app: Flask) -> None:

    @app.route("/subject/<int:subject_id>/prerequisites")
    @login_required
    def subject_prerequisites(subject_id: int):
        return render_template(
            "subject_prerequisites.html",
            subject_id=subject_id,
            prerequisites=prerequisites.get_prerequisites(subject_id),
        )


# -----------------------------------------------------------------------
# Calendar — subject-scoped subpage AND the global calendar (the global
# one lives with events, see _register_event_routes).
# -----------------------------------------------------------------------

def _register_calendar_routes(app: Flask) -> None:

    @app.route("/subject/<int:subject_id>/calendar")
    @login_required
    @feature_required("ENABLE_CALENDAR")
    def subject_calendar(subject_id: int):
        cal_data = calendar_mod.get_subject_calendar(subject_id)
        if not cal_data or not cal_data.get("subject"):
            abort(404)
        return render_template(
            "subject_calendar.html",
            subject_id=subject_id,
            calendar=cal_data,
        )


# -----------------------------------------------------------------------
# Discussion (subject subpage) — feature-flagged off by default per your
# "maybe this is unnecessary" note; the route exists and 404s cleanly
# until you decide to turn it on.
# -----------------------------------------------------------------------

def _register_discussion_routes(app: Flask) -> None:

    @app.route("/subject/<int:subject_id>/discussion", methods=["GET", "POST"])
    @login_required
    @feature_required("ENABLE_DISCUSSIONS")
    def subject_discussion(subject_id: int):
        if request.method == "POST":
            ok, error = discussion.create_post(subject_id, UserSession.user_id(), request.form)
            if not ok:
                flash_error(error or "Could not post.")
            else:
                flash_success("Posted.")
            return redirect(url_for("subject_discussion", subject_id=subject_id))
        return render_template(
            "subject_discussion.html", subject_id=subject_id, posts=discussion.list_posts(subject_id)
        )


# -----------------------------------------------------------------------
# Notes — three systems: public (subject subpage), My Notes (private,
# tree-by-subject), and drafts (private until publication is requested
# AND an admin approves it).
# -----------------------------------------------------------------------

def extract_all_notes(tree_data: dict) -> list[dict]:
    """Recursively extracts a flat list of all individual note dictionaries."""
    notes_list = []

    def _traverse(item):
        if isinstance(item, dict):
            if "id" in item and isinstance(item["id"], int):
                notes_list.append(item)
            else:
                for val in item.values():
                    _traverse(val)
        elif isinstance(item, list):
            for sub_item in item:
                _traverse(sub_item)

    _traverse(tree_data)
    return notes_list


def normalize_notes_tree(tree_data: dict) -> dict:
    """Converts indexed dict structures {0: note1, 1: note2} into clean lists [note1, note2]."""
    if not isinstance(tree_data, dict):
        return {}

    normalized = {}
    for category, items in tree_data.items():
        clean_notes = []
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    # If item is a container dict with numerical keys {0: note, 1: note}
                    for k, v in item.items():
                        if isinstance(v, dict) and "id" in v:
                            clean_notes.append(v)
                        elif k == "id":
                            clean_notes.append(item)
                            break
        normalized[category] = clean_notes
    return normalized


def _register_notes_routes(app: Flask) -> None:

    @app.route("/subject/<int:subject_id>/notes")
    @login_required
    def subject_notes(subject_id: int):
        """Public, admin-approved notes only."""
        return render_template(
            "subject_notes.html",
            subject_id=subject_id,
            notes=notes.get_public_notes(subject_id),
        )

    @app.route("/my-notes")
    @login_required
    def my_notes():
        """Private user notes organized in a tree structure by subject."""
        raw_tree = notes.get_my_notes_tree(UserSession.user_id(), entity_type="subject")
        clean_tree = normalize_notes_tree(raw_tree)
        
        return render_template("notes/note.html", tree=clean_tree)

    @app.route("/note/add", methods=["GET", "POST"])
    @login_required
    def note_add():
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            content = request.form.get("content", "").strip()
            entity_type = request.form.get("entity_type", "").strip()
            entity_id = request.form.get("subject_id")

            if entity_id and entity_id.isdigit():
                entity_id = int(entity_id)
            else:
                entity_id = None

            if not title or not content:
                flash_error("Please provide both a title and content for your note.")
                return render_template("notes/add_note.html", title=title, content=content)

            success, result = notes.create_note(
                content=content,
                subject_id=entity_id,
                entity_type=entity_type or "subject",
                entity_id=entity_id or None,
                title=title,
                authority=UserSession.authority(),
                user_id=UserSession.user_id(),
            )
            if success:
                flash_success("Note saved successfully!")
                return redirect(url_for("my_notes"))

            flash_error(f"Failed to save note: {result}")
            return render_template("notes/add_note.html", title=title, content=content)

        return render_template("notes/add_note.html", title="", content="")

    @app.route("/note/<int:note_id>/edit", methods=["GET", "POST"])
    @login_required
    def note_edit(note_id: int):
        if request.method == "POST":
            form_data = request.form.to_dict()
            content = form_data.get("content", "").strip()
            title = form_data.get("title", "").strip()

            ok, error = notes.edit_note(
                note_id, UserSession.user_id(), content, authority=UserSession.authority(), title=title
            )
            if not ok:
                flash_error(error or "Could not update note.")
                return redirect(url_for("note_edit", note_id=note_id))

            flash_success("Note updated.")
            return redirect(url_for("my_notes"))

        # Fetch current note data safely
        tree = notes.get_my_notes_tree(UserSession.user_id(), entity_type="subject")
        all_notes = extract_all_notes(tree)
        note_to_edit = next((n for n in all_notes if n.get("id") == note_id), None)

        if not note_to_edit:
            flash_error("Note not found or access denied.")
            return redirect(url_for("my_notes"))

        return render_template("notes/note_edit.html", note=note_to_edit)

    @app.route("/note/<int:note_id>/delete", methods=["POST"])
    @login_required
    def note_delete(note_id: int):
        ok, error = notes.delete_note(note_id, UserSession.user_id())
        if not ok:
            flash_error(error or "Could not delete note.")
        else:
            flash_success("Note deleted.")
        return redirect(url_for("my_notes"))

    @app.route("/note/<int:note_id>/publish", methods=["POST"])
    @login_required
    def note_request_publication(note_id: int):
        ok, error = notes.request_publication(note_id, UserSession.user_id())
        if not ok:
            flash_error(error or "Could not request publication.")
        else:
            flash_success("Publication requested — pending admin approval.")
        return redirect(url_for("my_notes"))
# -----------------------------------------------------------------------
# Favorites
# -----------------------------------------------------------------------

def _register_favorite_routes(app: Flask) -> None:

    @app.route("/favorites", methods=["GET", "POST"])
    @login_required
    def favorite_list():
        if request.method == "POST":
            name_filter = request.form.get("name", "").strip()
            type_filter = request.form.get("type", "").strip()
        else:
            name_filter = request.args.get("name", "").strip()
            type_filter = request.args.get("type", "").strip()

        favorites_raw = favorites.list_favorites(UserSession.user_id())
        data = []
        for entity_type, items in favorites_raw.items():
            for it in items:
                name = it.get("name") or it.get("title") or ""
                ent_id = it.get("id") or it.get("p_id")
                
                if name_filter and name_filter.lower() not in name.lower():
                    continue
                
                # Normalize key
                norm_type = entity_type[:-1] if entity_type.endswith('s') else entity_type
                
                if type_filter and type_filter != "all" and type_filter != norm_type:
                    continue
                
                data.append({
                    "entity_id": ent_id,
                    "subject_id": it.get("subject_id"),
                    "type": norm_type,
                    "name": name,
                    "favorited_at": it.get("favorited_at")
                })
        
        data.sort(key=lambda x: x.get("favorited_at", ""), reverse=True)

        return render_template(
            "favorites/index.html",
            data=data,
            name_filter=name_filter,
            type_filter=type_filter,
        )
    @app.route("/subject/<int:subject_id>/favorite", methods=["POST"])
    @login_required
    def favorite_toggle(subject_id: int):
        ok, error, is_favorited = favorites.toggle_favorite(UserSession.user_id(), subject_id)
        if not ok:
            if wants_json():
                return jsonify(success=False, error=error), 400
            flash_error(error or "Could not update favorites.")
            return go_back("subject_detail")
        if wants_json():
            return jsonify(success=True, favorited=is_favorited)
        flash_success("Favorites updated.")
        return go_back("subject_detail")


# -----------------------------------------------------------------------
# History
# -----------------------------------------------------------------------

def _register_history_routes(app: Flask) -> None:

    @app.route("/history")
    @login_required
    def history_view():
        return render_template("history.html", history=history.get_history(UserSession.user_id()))


# -----------------------------------------------------------------------
# Search — dual mode. No subject_id (or hitting /search*) = global.
# subject_id present (either as a query param or via the /subject/<id>/...
# convenience routes below) = scoped to that subject only.
# -----------------------------------------------------------------------

def _register_search_routes(app: Flask) -> None:

    @app.route("/search")
    @login_required
    def search_global():
        query = request.args.get("q", "")
        if wants_json() and Features.ENABLE_LIVE_SEARCH:
            return jsonify(search.search_all(query))
        return render_template("search.html", query=query, results=search.search_all(query))

    @app.route("/search/subjects")
    @login_required
    def search_subjects_route():
        query = request.args.get("q", "")
        results = search.search_subjects(query)
        if wants_json() and Features.ENABLE_LIVE_SEARCH:
            return jsonify(results=results)
        return render_template("search_subjects.html", query=query, results=results)

    @app.route("/search/materials")
    @login_required
    def search_materials_route():
        query = request.args.get("q", "")
        subject_id = request.args.get("subject_id", type=int)  # local search when present
        results = search.search_materials(query, subject_id)
        if wants_json() and Features.ENABLE_LIVE_SEARCH:
            return jsonify(results=results)
        return render_template("search_materials.html", query=query, subject_id=subject_id, results=results)

    @app.route("/search/professors")
    @login_required
    def search_professors_route():
        query = request.args.get("q", "")
        results = search.search_professors(query)
        if wants_json() and Features.ENABLE_LIVE_SEARCH:
            return jsonify(results=results)
        return render_template("search_professors.html", query=query, results=results)

    @app.route("/search/students")
    @login_required
    def search_students_route():
        query = request.args.get("q", "")
        subject_id = request.args.get("subject_id", type=int)
        results = search.search_students(query, subject_id)
        if wants_json() and Features.ENABLE_LIVE_SEARCH:
            return jsonify(results=results)
        return render_template("search_students.html", query=query, subject_id=subject_id, results=results)

    @app.route("/search/assignments")
    @login_required
    def search_assignments_route():
        query = request.args.get("q", "")
        subject_id = request.args.get("subject_id", type=int)
        results = search.search_assignments(query, subject_id)
        if wants_json() and Features.ENABLE_LIVE_SEARCH:
            return jsonify(results=results)
        return render_template("search_assignments.html", query=query, subject_id=subject_id, results=results)


# -----------------------------------------------------------------------
# Notifications
# -----------------------------------------------------------------------

def _register_notification_routes(app: Flask) -> None:

    @app.route("/notifications", methods=["GET", "POST"])
    @login_required
    @feature_required("ENABLE_NOTIFICATIONS")
    def notification_list():
        if request.method == "POST":
            notification_id = request.form.get("notification_id", type=int)
            if notification_id:
                ok, error = notifications.mark_as_read(notification_id, UserSession.user_id())
                if not ok:
                    flash_error(error or "Could not mark notification as read.")
                else:
                    flash_success("Notification marked as read.")
                    return redirect(url_for("notification_list"))
            else:
                flash_error("No notification ID provided.")
                return redirect(url_for("notification_list"))    
            return redirect(url_for("notification_list")) 
        read_only_filter = request.args.get("filter", "all")or "all"
        print("Notification filter:", read_only_filter)
        return render_template(
                    "notifications/index.html", notifications=notifications.list_notification(unread_only=read_only_filter, id=UserSession.user_id()))
            
# -----------------------------------------------------------------------
# Events / global calendar
# -----------------------------------------------------------------------

def _register_event_routes(app: Flask) -> None:

    @app.route("/events")
    @login_required
    @feature_required("ENABLE_EVENTS")
    def event_list():
        return render_template("events.html", events=events.list_events(UserSession.user_id()))

    @app.route("/event/add", methods=["GET", "POST"])
    @login_required
    @feature_required("ENABLE_EVENTS")
    def event_add():
        if request.method == "POST":
            ok, error, new_id = events.create_event(UserSession.user_id(), request.form)
            if not ok:
                flash_error(error or "Could not create event.")
                return redirect(url_for("event_add"))
            flash_success("Event created.")
            return redirect(url_for("event_detail", event_id=new_id))
        return render_template("event_add.html")

    @app.route("/event/<int:event_id>")
    @login_required
    @feature_required("ENABLE_EVENTS")
    def event_detail(event_id: int):
        data = events.get_event(event_id)
        if data is None:
            abort(404)
        return render_template("event.html", event=data)


# -----------------------------------------------------------------------
# Messages
# -----------------------------------------------------------------------

def _register_message_routes(app: Flask) -> None:

    @app.route("/messages")
    @login_required
    @feature_required("ENABLE_MESSAGES")
    def message_list():
        return render_template(
            "messages.html", conversations=messages.list_conversations(UserSession.user_id())
        )

    @app.route("/messages/<int:other_user_id>", methods=["GET", "POST"])
    @login_required
    @feature_required("ENABLE_MESSAGES")
    def message_thread(other_user_id: int):
        if request.method == "POST":
            ok, error = messages.send_message(UserSession.user_id(), other_user_id, request.form)
            if not ok:
                flash_error(error or "Could not send message.")
            return redirect(url_for("message_thread", other_user_id=other_user_id))
        return render_template(
            "message_thread.html",
            other_user_id=other_user_id,
            thread=messages.get_conversation(UserSession.user_id(), other_user_id),
        )


# -----------------------------------------------------------------------
# Professor tools — dashboard for a professor's own subjects/materials.
# Distinct from /professor/<id>, which is a public-facing profile.
# -----------------------------------------------------------------------

def _register_professor_tool_routes(app: Flask) -> None:

    @app.route("/professor-tools/dashboard")
    @professor_required
    def professor_dashboard():
        user_id = UserSession.user_id()
        subjs = subjects.list_subjects(filters={"professor_profile_id": user_id})
        return render_template(
            "professor_dashboard.html",
            subjects=subjs,
        )

    @app.route("/professor-tools/materials")
    @professor_required
    def professor_materials():
        user_id = UserSession.user_id()
        prof_materials = []
        with sql_h.get_db("main.db") as conn:
            c = conn.cursor()
            c.execute("""
                SELECT m.*, s.name as subject_name, s.code as subject_code
                FROM materials m
                JOIN subjects s ON m.subject_id = s.id
                WHERE m.uploaded_by = ?
                ORDER BY m.created_at DESC
            """, (user_id,))
            prof_materials = [dict(r) for r in c.fetchall()]
        return render_template("professor_materials.html", materials=prof_materials)

    @app.route("/professor-tools/subjects")
    @professor_required
    def professor_subjects():
        user_id = UserSession.user_id()
        subjs = subjects.list_subjects(filters={"professor_profile_id": user_id})
        return render_template(
            "professor_subjects.html",
            subjects=subjs,
        )


# -----------------------------------------------------------------------
# Administration
# -----------------------------------------------------------------------

def _register_admin_routes(app: Flask) -> None:

    @app.route("/admin")
    @admin_required
    def admin_dashboard():
        return render_template("admin_dashboard.html", stats=admin.get_dashboard_stats())

    @app.route("/admin/users")
    @admin_required
    def admin_users():
        query_filters = {"authority": request.args.get("authority"), "state": request.args.get("state")}
        return render_template("admin_users.html", users=admin.list_users(query_filters))

    @app.route("/admin/user/<int:user_id>")
    @admin_required
    def admin_user_detail(user_id: int):
        data = admin.get_user(user_id)
        if data is None:
            abort(404)
        return render_template("admin_user.html", user=data)

    @app.route("/admin/subjects")
    @admin_required
    def admin_subjects():
        return render_template("admin_subjects.html", pending=admin.list_pending_subjects())

    @app.route("/admin/subject/<int:subject_id>/approve", methods=["POST"])
    @admin_required
    def admin_subject_approve(subject_id: int):
        ok, error = admin.approve_subject(subject_id, UserSession.user_id())
        if not ok:
            flash_error(error or "Could not approve subject.")
        else:
            flash_success("Subject approved.")
        return redirect(url_for("admin_subjects"))

    @app.route("/admin/materials")
    @admin_required
    def admin_materials():
        return render_template("admin_materials.html", pending=admin.list_pending_materials())

    @app.route("/admin/material/<int:material_id>/approve", methods=["POST"])
    @admin_required
    def admin_material_approve(material_id: int):
        ok, error = admin.approve_material(material_id, UserSession.user_id())
        if not ok:
            flash_error(error or "Could not approve material.")
        else:
            flash_success("Material approved.")
        return redirect(url_for("admin_materials"))

    @app.route("/admin/notes")
    @admin_required
    def admin_notes():
        return render_template("admin_notes.html", pending=admin.list_pending_notes())

    @app.route("/admin/note/<int:note_id>/approve", methods=["POST"])
    @admin_required
    def admin_note_approve(note_id: int):
        ok, error = admin.approve_note(note_id, UserSession.user_id())
        if not ok:
            flash_error(error or "Could not approve note.")
        else:
            flash_success("Note approved and now public.")
        return redirect(url_for("admin_notes"))

    @app.route("/admin/reports")
    @admin_required
    def admin_reports():
        return render_template("admin_reports.html", reports=admin.list_reports())

    @app.route("/admin/events")
    @admin_required
    @feature_required("ENABLE_EVENTS")
    def admin_events():
        return render_template("admin_events.html", events=events.list_events(UserSession.user_id()))

    @app.route("/admin/logs")
    @senior_admin_required
    def admin_logs():
        return render_template("admin_logs.html", logs=admin.list_logs())


# -----------------------------------------------------------------------
# Moderation — warn/ban/unban. Enforces two rules that are easy to get
# wrong, so they live here explicitly rather than being assumed inside
# moderation_module:
#   1. Professors are immune: no one can warn/ban a Authority.PROFESSOR
#      account, regardless of the acting admin's level.
#   2. An admin may only act on a user with a STRICTLY LOWER authority
#      level than their own (so ADMIN_L2 cannot moderate ADMIN_L3, but
#      SENIOR_ADMIN_L5 can moderate any ADMIN_L2-L4).
# -----------------------------------------------------------------------

def _register_moderation_routes(app: Flask) -> None:

    def _assert_moderatable(target_user_id: int) -> dict:
        target = admin.get_user(target_user_id)
        if target is None:
            abort(404)
        target_authority = Authority(target["authority"])
        if target_authority == Authority.PROFESSOR:
            abort(403)
        acting_authority = UserSession.authority()
        if acting_authority is None or target_authority >= acting_authority:
            abort(403)
        return target

    @app.route("/admin/user/<int:user_id>/warn", methods=["POST"])
    @admin_required
    def moderation_warn(user_id: int):
        _assert_moderatable(user_id)
        reason = request.form.get("reason", "")
        ok, error = moderation.warn_user(user_id, UserSession.user_id(), reason)
        if not ok:
            flash_error(error or "Could not issue warning.")
        else:
            flash_success("Warning issued.")
        return redirect(url_for("admin_user_detail", user_id=user_id))

    @app.route("/admin/user/<int:user_id>/ban", methods=["POST"])
    @admin_required
    def moderation_ban(user_id: int):
        _assert_moderatable(user_id)
        reason = request.form.get("reason", "")
        ok, error = moderation.ban_user(user_id, UserSession.user_id(), reason)
        if not ok:
            flash_error(error or "Could not ban user.")
        else:
            flash_success("User banned.")
        return redirect(url_for("admin_user_detail", user_id=user_id))

    @app.route("/admin/user/<int:user_id>/unban", methods=["POST"])
    @admin_required
    def moderation_unban(user_id: int):
        _assert_moderatable(user_id)
        ok, error = moderation.unban_user(user_id, UserSession.user_id())
        if not ok:
            flash_error(error or "Could not unban user.")
        else:
            flash_success("User unbanned.")
        return redirect(url_for("admin_user_detail", user_id=user_id))


###############################################################################
# Entry point
###############################################################################

app = create_app()

if __name__ == "__main__":
   
    app.config.from_object(Config)
    app.run(debug=Config.DEBUG)
   


###############################################################################
# REVIEW NOTES — every assumption / known rough edge in this file, with
# exact line references (from `grep -n` against this file as delivered).
# Use these as your review checklist rather than re-reading everything.
###############################################################################
#
# These are deliberate placeholders, not bugs — but each one is a point
# where this file's assumption may not match your real data.py, so check
# them first:
#
# 1. auth.authenticate() / _FAKE_USERS shape (modules/auth_module.py) —
#    assumes user dict keys: user_id, email, authority, state, profile_id,
#    warning_count, approved. If your real accounts table uses different
#    column names, update UserSession.start()'s call site in the /login
#    route (search "def login()") and nothing else needs to change.
#
# 2. note_edit() / note_delete() ownership check — search "def note_edit"
#    and "def note_delete". These call notes.edit_note()/delete_note()
#    passing UserSession.user_id(), but note_module's stub doesn't verify
#    the caller is the author before "succeeding" — the real module must
#    do that check (or app.py needs the note's author_id back from a GET
#    first, then wrap with owner_or_admin_required like the pattern
#    already defined above for other resources).
#
# 3. professor_materials() — search "def professor_materials". material_
#    module has no "materials uploaded by this professor" query yet
#    (list_materials requires a subject_id). Currently renders an empty
#    list rather than guessing a query shape.
#
# 4. Features.MULTI_UNIVERSITY = False — cross-university enrollment
#    (mentioned as a future idea, explicitly not required now) has no
#    routes at all. Nothing references this flag yet; it's a marker for
#    when you're ready to design that feature, not a gate on anything.
#
# 5. wants_json() — used by favorite_toggle() and the /search* routes for
#    the one place you said JS/AJAX might be used (live search) plus the
#    favorite button. This is a guess at how your frontend will signal
#    "give me JSON" (Accept header or ?format=json); adjust to match
#    whatever your JS actually sends.
#
# 6. subject_add() / material_upload() approval branching — both check
#    "Features.REQUIRE_UPLOAD_APPROVAL and not UserSession.is_admin()" to
#    decide the flash wording, but the actual pending/approved DB write
#    is assumed to happen inside subjects.create_subject() / materials.
#    upload_material() themselves. If those modules don't yet set
#    approval state internally, the flash message would say "submitted
#    for approval" without it actually being true — verify the module
#    side sets ApprovalState.PENDING correctly.
#
# 7. owner_or_admin_required() decorator (search "def owner_or_admin_
#    required") is defined but not yet applied anywhere, since none of
#    the current module stubs return an owner_user_id lookup function
#    it could call. It's ready to use once note_module (or any future
#    per-user resource) exposes a "get owner of X" lookup.
#
###############################################################################