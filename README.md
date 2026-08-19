# Student Management Platform

<p align="center">
  <strong>A full-stack academic management platform built with Flask</strong>
</p>

<p align="center">
  <a href="https://github.com/Amr-Ahmad-dev">GitHub</a>
  •
  <a href="https://www.linkedin.com/">LinkedIn</a>
  •
  <a href="mailto:YOUR_EMAIL">Email</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-Backend-blue" alt="Python">
  <img src="https://img.shields.io/badge/Flask-Web%20Framework-black" alt="Flask">
  <img src="https://img.shields.io/badge/SQLAlchemy-Database-red" alt="SQLAlchemy">
  <img src="https://img.shields.io/badge/JavaScript-Frontend-yellow" alt="JavaScript">
  <img src="https://img.shields.io/badge/Status-Beta-orange" alt="Beta">
</p>

---

## About

**Student Management Platform** is a multi-user academic web application originally developed as my **CS50 final project** and subsequently expanded into a significantly larger system.

The project brings together academic resources, communication, student profiles, notifications, academic progress tracking, search, events, and administrative moderation inside a single application.

Rather than implementing the project as a collection of isolated CRUD pages, I designed it around interacting systems:

**authentication → authorization → users → academic content → moderation → notifications → search → academic tracking**

The application is currently in **beta**. The core functionality is operational, while several areas are still being refined and tested.

---

## Contact

**Amr Ahmad**
Computer Science Student
Python & Backend Development • Automation & Data Processing • AI/ML & Data Analysis

**GitHub:** [Amr-Ahmad-dev](https://github.com/Amr-Ahmad-dev)
**LinkedIn:** [Connect with me](https://www.linkedin.com/)
**Email:** `YOUR_EMAIL`

---

# What the Application Does

The platform is designed around the everyday academic workflow of a student while also providing the administrative infrastructure required to manage shared content.

### For Students

* 👤 Create and edit personal profiles
* 📚 Browse and search subjects
* 🔎 Filter subjects and other content
* ⭐ Favorite subjects
* 🕘 View recently visited subjects
* 📎 Add additional subjects and materials
* 💬 Send and receive messages
* 🔔 Receive user-specific notifications
* 📅 View upcoming events
* 🗓️ Use the calendar
* 🧮 Calculate GBA
* 📈 Track GBA changes over time
* 🔍 Use general search from the home page

### For Administrators

* 🛡️ Manage users according to authority level
* ✏️ Edit existing content
* 🗑️ Delete materials, notes, and subjects
* ⚠️ Warn users
* 🚫 Ban or remove users
* ✅ Review submitted content
* 📋 Approve or reject content before publication
* 🔐 Operate within a hierarchical administrative permission system

---

# Architecture

The application follows an **MVC-oriented architecture** built around Flask.

At a high level:

```text
┌─────────────────────────────┐
│          Interface          │
│       HTML / CSS / JS       │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│       Flask Application      │
│     Routes + Application     │
│            Logic             │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│        SQLAlchemy            │
│       Database Layer         │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│      Relational Database     │
└─────────────────────────────┘
```

The application also uses classes and class-based structures to organize system components and distinguish functionality according to its implementation state.

The goal is to keep responsibilities separated as the application grows instead of allowing the entire system to become concentrated inside route handlers.

---

# Authorization & Permission Model

One of the central engineering problems in the application is **controlling what different users are allowed to do**.

The system contains approximately **seven authority levels**, beginning with the base student level and increasing toward the highest administrative authority.

Permissions are determined by the user's authority level.

This creates a hierarchy rather than a simple:

```text
Student
   vs.
Admin
```

model.

Instead, administrative authority is relative:

```text
Highest Authority
       │
       ▼
    Admin A
       │
       ▼
    Admin B
       │
       ▼
    Admin C
       │
       ▼
    Student
```

An administrator can exercise authority over users below their level, but not over an administrator with equal or greater authority.

This creates explicit ownership boundaries between different levels of the system.

---

# Content Moderation

A major design decision was separating **content creation** from **content publication**.

Students can contribute content, but publicly available material can require administrator approval before it becomes visible as published content.

```text
Student
   │
   ▼
Submit Content
   │
   ▼
Pending Review
   │
   ▼
Administrator
   │
   ├───────────────┐
   ▼               ▼
Approve          Reject
   │
   ▼
Published
```

This prevents the permission to contribute from automatically becoming permission to publish.

Administrators can also manage existing subjects, notes, and materials according to their authority.

---

# Notifications

The application contains a notification system that can generate **user-specific notifications automatically from application events**.

For example:

* A user adds a subject
* A user replies to a subject-related interaction
* An event occurs that requires another specific user to be informed

The notification system is therefore connected to application behavior rather than functioning only as a manually created message list.

---

# Messaging

Users can communicate through the application's messaging system.

Messaging is connected to the user and notification systems so that relevant communication can reach the intended account.

---

# Search & Discovery

The platform provides multiple ways to discover information.

### General Search

A general search is available directly from the home page.

### Filtered Search

Users can search and filter:

* Subjects
* Users
* Materials
* Other available application content

The objective is to reduce the amount of navigation required to locate information inside the system.

---

# Academic Tracking

## GBA Calculator

The application contains a built-in GBA calculator that allows students to calculate and track their academic performance.

Students can:

1. Enter academic information
2. Calculate their GBA
3. Record academic changes
4. Track how their GBA changes over time
5. Observe the effect of additional subjects on their overall result

This turns the calculator from a one-time calculation into part of the student's academic record and tracking workflow.

---

# Subjects & Materials

The academic content system allows users to:

* Browse subjects
* Search subjects
* Filter subjects
* Favorite subjects
* View recently visited subjects
* Add additional subjects
* Add educational materials
* Access available materials

Submitted content can subsequently pass through the administrative moderation workflow.

---

# Calendar & Events

The platform includes a calendar and upcoming-event functionality.

Students can use the system to view relevant events and keep academic information in one centralized location.

---

# Authentication & Account Security

The application includes:

* User authentication
* Session management
* Password authentication
* Password-reset functionality

### Password Reset

When a user forgets their password, the application can generate a password-reset link containing a protected token.

The user follows the generated link and can update their password without needing access to their previous password.

The reset process is based on authorization through the generated reset link rather than exposing the user's existing password.

---

# Administrator Initialization

The current authorization model creates an interesting system-initialization problem.

If a new administrator must be approved by an existing administrator, the system needs a way to create the **first trusted administrator**.

Otherwise:

```text
Admin B needs Admin A
        ↓
Admin A needs to already exist
        ↓
Who creates Admin A?
```

This is a bootstrap problem caused by the interaction between authentication and hierarchical authorization.

The planned solution is a controlled administrator credential/code that allows an authorized initial administrator to authenticate and establish the initial administrative authority.

After that initial state exists, the normal administrator approval hierarchy can take over.

This feature is **not yet implemented**.

---

# Technology Stack

| Technology                       | Role in the Project                                                                  |
| -------------------------------- | ------------------------------------------------------------------------------------ |
| **Python**                       | Core application language                                                            |
| **Flask**                        | Web application framework                                                            |
| **SQLAlchemy**                   | Database interaction / ORM                                                           |
| **SQL**                          | Relational data management                                                           |
| **Flask Sessions**               | User session and authentication state                                                |
| **HTML**                         | Application structure                                                                |
| **CSS**                          | Styling and layout                                                                   |
| **JavaScript**                   | Client-side behavior and interaction                                                 |
| **Jinja / Flask Templates**      | Dynamic HTML rendering                                                               |
| **MVC-oriented architecture**    | Separation of application responsibilities                                           |
| **Object-Oriented Programming**  | Classes and structured application components                                        |
| **Role-Based Authorization**     | Permission and authority management                                                  |
| **CRUD Operations**              | Creation, retrieval, modification, and deletion of application data                  |
| **Database Relationships**       | Connecting users, subjects, materials, notifications, messages, and academic records |
| **Password-Reset Tokens**        | Account recovery workflow                                                            |
| **Session-Based Authentication** | Maintaining authenticated user state                                                 |

> **Note:** The exact third-party packages used for email delivery and password-reset token generation should be added here once the dependency names are confirmed from the project's `requirements.txt`.

---

# Engineering Concepts Demonstrated

This project gave me practical experience with several areas of software development:

### Backend Development

* Flask routing
* Request handling
* Application logic
* Sessions
* Authentication
* Authorization
* CRUD operations

### Database Development

* SQL
* SQLAlchemy
* Relational data
* Database relationships
* Persistent application state
* Data access through an ORM

### Software Architecture

* MVC-oriented organization
* Object-oriented programming
* Separation of responsibilities
* Feature organization
* Permission boundaries
* Hierarchical authority

### Application Design

* User workflows
* Content moderation
* Notification generation
* Search and filtering
* Academic tracking
* Account recovery
* Administrative workflows
* System initialization

### Frontend Development

* HTML
* CSS
* JavaScript
* Dynamic server-rendered pages
* User interaction

---

# Design Decisions

Several parts of the application became more interesting once the individual features had to work together.

### Creation vs. Publication

A user being able to create content does not necessarily mean they should be able to publish it.

The application therefore separates the two permissions.

### Relative Administrative Authority

An administrator is not simply "an admin."

The system considers the relative authority of users when determining whether one administrator can act on another.

### User-Specific Notifications

Notifications are associated with the users who need to receive them rather than being treated as one global event stream.

### System Bootstrap

The administrator hierarchy creates a dependency during initial setup.

Recognizing that dependency led to the planned administrator-credential mechanism rather than ignoring the problem.

---

# Current Status

## 🟠 Beta

The application is **functional but not production-ready**.

### Working

* User accounts
* Profiles
* Subjects
* Materials
* Messaging
* Notifications
* Search
* Filtering
* Calendar
* Events
* GBA calculation
* GBA tracking
* Administrative hierarchy
* Content moderation
* Password reset
* User management

### Still Being Refined

* Favorites functionality
* Overall application stability
* Edge-case handling
* Additional testing
* Administrator bootstrap mechanism

I am intentionally keeping the project marked as **beta** rather than presenting it as a finished production application.

---

# What I Learned

The biggest lesson from this project was that building a larger application is not simply a matter of implementing more features.

The difficult part is making the features **interact consistently**.

For example:

> Adding administrator approval creates a system-initialization problem.

> Allowing users to submit content creates a distinction between creation and publication.

> Introducing multiple authority levels creates relative permission boundaries.

> Adding notifications means application events must be connected to the correct users.

These interactions forced me to think more about **architecture, ownership, state, permissions, and system behavior** rather than treating each feature as an isolated task.

---

# Project Status & Future Work

The project is still under active development.

Planned improvements include:

* Complete administrator bootstrap
* Fix remaining favorites issues
* Improve stability
* Expand testing
* Improve validation and error handling
* Refine notification behavior
* Improve search and filtering
* Expand academic analytics
* Finish remaining beta functionality
* Prepare the application for deployment

---

# Project Origin

This application began as my **CS50 final project**.

I continued developing it beyond the original requirements because I wanted to use the project to explore what happens when a relatively small academic application grows into a multi-user system with:

**authentication + authorization + databases + communication + moderation + search + academic tracking**

The current beta is the result of that expansion.

---

# Connect

<p align="center">
  <strong>Amr Ahmad</strong><br>
  Computer Science Student<br><br>

  <a href="https://github.com/Amr-Ahmad-dev">
    <img src="https://img.shields.io/badge/GitHub-Amr--Ahmad--dev-181717?style=for-the-badge&logo=github" alt="GitHub">
  </a>
  <a href="https://www.linkedin.com/">
    <img src="https://img.shields.io/badge/LinkedIn-Connect-0A66C2?style=for-the-badge&logo=linkedin" alt="LinkedIn">
  </a>
  <a href="mailto:YOUR_EMAIL">
    <img src="https://img.shields.io/badge/Email-Contact%20Me-EA4335?style=for-the-badge&logo=gmail" alt="Email">
  </a>
</p>

<p align="center">
  <strong>Python & Backend Development • Automation & Data Processing • AI/ML & Data Analysis</strong>
</p>
