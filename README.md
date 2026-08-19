# Student Management Platform

<p align="center">
  <strong>A multi-user academic management platform built with Flask, Python, SQLite, HTML, CSS, and JavaScript.</strong>
</p>

<p align="center">
  <a href="https://github.com/Amr-Ahmad-dev">GitHub</a>
  &nbsp;•&nbsp;
  <a href="https://www.linkedin.com/">LinkedIn</a>
  &nbsp;•&nbsp;
  <a href="mailto:amrahmadsalah@gmail.com">Email</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.x-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Flask-Web%20Framework-black?logo=flask&logoColor=white" alt="Flask">
  <img src="https://img.shields.io/badge/SQLite-Database-003B57?logo=sqlite&logoColor=white" alt="SQLite">
  <img src="https://img.shields.io/badge/HTML5-Frontend-E34F26?logo=html5&logoColor=white" alt="HTML5">
  <img src="https://img.shields.io/badge/CSS3-Styling-1572B6?logo=css3&logoColor=white" alt="CSS3">
  <img src="https://img.shields.io/badge/JavaScript-Frontend-F7DF1E?logo=javascript&logoColor=black" alt="JavaScript">
  <img src="https://img.shields.io/badge/Status-Beta-orange" alt="Beta">
</p>

---

## Overview

**Student Management Platform** is a multi-user academic web application originally developed as my **CS50 final project** and expanded into a larger system for managing academic resources, communication, student information, academic progress, notifications, and administrative moderation.

The application is designed around the interaction between multiple systems rather than a collection of isolated pages:

```text
Authentication
      │
      ▼
Authorization
      │
      ├───────────────┐
      ▼               ▼
Academic System   User System
      │               │
      ├───────┬───────┤
      ▼       ▼       ▼
 Materials  Search  Messaging
      │       │       │
      └───────┼───────┘
              ▼
        Notifications
              │
              ▼
       Administration
```

The project is currently in **beta**. The main application is functional, but some functionality still requires debugging, refinement, and additional testing.

---

## Contact

**Amr Ahmad**
Computer Science Student

**GitHub:** [Amr-Ahmad-dev](https://github.com/Amr-Ahmad-dev)
**LinkedIn:** [Connect with me](https://www.linkedin.com/)
**Email:** [amrahmadsalah@gmail.com](mailto:amrahmadsalah@gmail.com)

---

# Core Features

## 🎓 Student Management

Students can:

* Create and edit their profiles
* Browse subjects
* Search subjects
* Filter subjects
* Add subjects
* Favorite subjects
* View recently visited subjects
* Add additional subjects
* Add educational materials
* View available materials
* Send and receive messages
* View notifications
* View upcoming events
* Use the calendar
* Calculate their GBA
* Track their GBA over time

---

## 🔎 Search & Discovery

The application provides multiple search mechanisms.

Users can search for:

* Subjects
* Users
* Materials
* General information

Subject searches can also be filtered according to the available subject properties.

A general search is available from the home page to provide a broader way of discovering information throughout the application.

---

## 🔔 Notifications

The platform contains an event-driven notification system.

Notifications can be generated automatically when an application event requires a specific user to be informed.

Examples include:

* Adding a subject
* Replying to a subject-related interaction
* Other user-specific application events

The system therefore connects application events with the users affected by those events.

---

## 💬 Messaging

Users can communicate through the platform's messaging functionality.

Messaging is integrated with the application's user and notification systems so that relevant communication can reach the appropriate users.

---

# 📚 Academic Management

## Subjects & Materials

The academic content system allows users to:

* Browse subjects
* Search subjects
* Filter subjects
* Add subjects
* Favorite subjects
* View recently visited subjects
* Access materials
* Submit additional materials

Content submitted by users can enter the administrative moderation workflow before being made publicly available.

---

## 🧮 GBA Calculator & Academic Tracking

The platform includes a built-in GBA calculator.

Students can:

1. Enter academic information
2. Calculate their GBA
3. Track their academic results
4. Monitor how their GBA changes over time
5. Observe how additional subjects affect their overall result

The goal is to turn GBA calculation from a one-time calculation into an integrated academic tracking feature.

---

## 📅 Calendar & Events

The application includes:

* A calendar
* Upcoming events
* Event-related information

This provides students with a centralized place to keep track of academic events.

---

# 🛡️ Authorization System

One of the central parts of the application is its hierarchical authorization system.

The platform contains approximately **seven authority levels**, starting from the base student level and increasing through higher administrative levels until reaching the highest authority.

The system does not treat every administrator as having identical permissions.

Instead, actions depend on the user's authority level.

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

An administrator can exercise authority over users below their level, but cannot exercise the same authority over an administrator with equal or greater authority.

This creates explicit permission boundaries between different levels of the system.

---

# 🔐 Content Moderation

A key design decision in the application is separating **content creation** from **content publication**.

Students can contribute content, but content intended to become publicly available can require administrative approval before publication.

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
   ├──────────────┐
   ▼              ▼
Approve         Reject
   │
   ▼
Published
```

This prevents the permission to create content from automatically becoming permission to publish it.

Administrators can also manage existing content according to their authority.

Administrative capabilities include:

* Edit materials
* Delete materials
* Edit notes
* Delete notes
* Edit subjects
* Delete subjects
* Warn users
* Ban users
* Remove users
* Review submitted content

---

# 🔑 Authentication & Account Security

The application includes user authentication, session management, and password recovery.

### Password Reset

When a user forgets their password, the system can generate a password-reset link containing a protected token.

The user follows the generated link and can update their password without needing to know their previous password.

The reset process authorizes the password change through the generated reset link rather than exposing the user's existing password.

---

# 🧠 Application Architecture

The application is built using **Flask** and follows an **MVC-oriented architecture**.

The overall structure separates different responsibilities within the application:

```text
┌─────────────────────────────┐
│          Frontend           │
│       HTML / CSS / JS       │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│       Flask Application     │
│     Routes + Logic + Flow   │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│        Database Layer       │
│             SQL             │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│           SQLite            │
└─────────────────────────────┘
```

The application also uses **object-oriented programming and class-based structures** to organize system components.

Classes are used to represent different parts of the application and help control the availability of functionality that is implemented, incomplete, or still under development.

The intention is to make the application easier to extend as additional functionality is introduced.

---

# 🗄️ Database

The application uses **SQLite** as its relational database.

SQL is used for working with persistent application data.

The database stores information associated with areas such as:

* Users
* Subjects
* Materials
* Messages
* Notifications
* Events
* Academic records
* Favorites
* Recently visited subjects
* Administrative information

The database allows these systems to share persistent information while maintaining relationships between the different entities.

---

# 🧩 Sessions

The application uses **Flask sessions** to maintain state across requests.

Sessions are part of the authentication flow and allow the application to identify and maintain the state of the currently authenticated user while navigating through different parts of the platform.

---

# ⚙️ Technology Stack

| Technology                       | Purpose                                              |
| -------------------------------- | ---------------------------------------------------- |
| **Python**                       | Core programming language                            |
| **Flask**                        | Web application framework                            |
| **SQLite**                       | Relational database                                  |
| **SQL**                          | Database querying and data management                |
| **Flask Sessions**               | Session and authentication state                     |
| **HTML5**                        | Page structure                                       |
| **CSS3**                         | Styling and layout                                   |
| **JavaScript**                   | Client-side interaction                              |
| **Jinja / Flask Templates**      | Dynamic server-rendered pages                        |
| **Object-Oriented Programming**  | Classes and application components                   |
| **MVC-oriented Architecture**    | Separation of application responsibilities           |
| **Role-Based Authorization**     | Permission management                                |
| **CRUD**                         | Data creation, retrieval, modification, and deletion |
| **Database Relationships**       | Connecting application entities                      |
| **Password-Reset Tokens**        | Account recovery                                     |
| **Session-Based Authentication** | Maintaining authenticated user state                 |

---

# 🧰 Skills Demonstrated

### Backend Development

* Python
* Flask
* Routing
* Request handling
* Sessions
* Authentication
* Authorization
* CRUD operations
* Application logic

### Database Development

* SQLite
* SQL
* Relational data modeling
* Database relationships
* Persistent storage
* Data retrieval and modification

### Software Architecture

* MVC-oriented architecture
* Object-oriented programming
* Class-based design
* Separation of responsibilities
* Feature organization
* Permission boundaries
* Hierarchical authority

### Web Development

* HTML
* CSS
* JavaScript
* Jinja templates
* Server-side rendering
* Client-side interaction

### Application Design

* User workflows
* Content moderation
* Notifications
* Messaging
* Search and filtering
* Academic tracking
* Account recovery
* Administrative workflows
* System initialization

---

# 🏗️ Important Design Decisions

The project became substantially more interesting as the individual features started interacting.

### Creation vs. Publication

A student being allowed to create content does not mean that the student should automatically be allowed to publish it.

The system therefore separates:

```text
Create
  ≠
Publish
```

This allows student contributions while retaining administrative control over public content.

---

### Relative Administrative Authority

The system does not simply check whether:

```text
user.is_admin == True
```

when determining administrative relationships.

The authority level of the users matters.

An administrator's ability to act on another administrator depends on their relative position in the hierarchy.

---

### User-Specific Notifications

Notifications are generated for the users affected by application events.

This allows the system to distinguish between:

```text
An event happened
```

and:

```text
This particular user needs to know that the event happened.
```

---

### Feature Availability

The application uses class-based structures and feature identification to distinguish functionality that is available from functionality that is still being developed.

This makes it possible to continue expanding the application without treating unfinished functionality as if it were already complete.

---

# 🔄 Administrator Bootstrap Problem

One of the remaining architectural problems concerns the initialization of the administrator hierarchy.

The normal model assumes:

```text
Existing Administrator
          │
          ▼
Approves New Administrator
```

But the system also needs an initial administrator.

Otherwise:

```text
Admin B requires Admin A
Admin A requires an existing administrator
Existing administrator does not exist
```

This creates a circular dependency during system initialization.

### Planned Solution

The planned solution is a controlled administrator credential/code that allows an authorized initial administrator to authenticate and establish the initial administrative state.

```text
Authorized Credential
        │
        ▼
Administrator Login
        │
        ▼
Initial Administrator
        │
        ▼
Normal Approval Hierarchy
```

After initialization, new administrators can return to the normal approval process.

This feature is **planned but not yet implemented**.

---

# 🧪 Current Status

## Beta

The application is functional, but it is **not yet production-ready**.

### Implemented

| Area                     | Status |
| ------------------------ | :----: |
| User accounts            |    ✅   |
| Profiles                 |    ✅   |
| Subjects                 |    ✅   |
| Materials                |    ✅   |
| Search                   |    ✅   |
| Filtering                |    ✅   |
| Messaging                |    ✅   |
| Notifications            |    ✅   |
| Calendar                 |    ✅   |
| Events                   |    ✅   |
| GBA calculator           |    ✅   |
| GBA tracking             |    ✅   |
| Administrative hierarchy |    ✅   |
| Content moderation       |    ✅   |
| Password reset           |    ✅   |
| User management          |    ✅   |

### Under Development

| Area                    |        Status       |
| ----------------------- | :-----------------: |
| Favorites               | ⚠️ Needs refinement |
| Overall stability       |       ⚠️ Beta       |
| Edge-case handling      |      🚧 Ongoing     |
| Additional testing      |      🚧 Ongoing     |
| Administrator bootstrap |      🚧 Planned     |

The project is intentionally labeled **beta** rather than being presented as a finished production system.

---

# 📈 Future Improvements

Planned improvements include:

* Complete the administrator bootstrap mechanism
* Resolve remaining favorites issues
* Improve application stability
* Expand testing
* Improve validation and error handling
* Refine notification behavior
* Improve search and filtering
* Expand academic analytics
* Complete remaining beta functionality
* Prepare the application for deployment

---

# 🎯 What I Learned

This project started as a CS50 final project, but expanding it beyond the original requirements changed the nature of the problem.

The challenge became less about implementing individual pages and more about making multiple systems work together consistently.

Some of the most important lessons came from interactions between features:

> **Administrator approval creates a system-initialization problem.**

> **Content submission is different from content publication.**

> **Multiple authority levels require relative permission checks.**

> **Notifications require application events to be connected to the correct users.**

> **Adding more features increases the importance of architecture and ownership boundaries.**

Working through these problems gave me practical experience with the design and development of a larger multi-user web application rather than only isolated programming exercises.

---

# 🚀 Project Origin

The application was originally created as my **CS50 final project**.

I continued expanding it beyond the original requirements to explore how a student-focused web application could evolve into a larger system involving:

**Authentication → Authorization → Academic Management → Communication → Moderation → Search → Notifications → Academic Tracking**

The project remains under development and is currently available as a **beta application**.

---

# 📬 Contact

<p align="center">

<strong>Amr Ahmad</strong><br>
Computer Science Student

<br><br>

<a href="https://github.com/Amr-Ahmad-dev">
  <img src="https://img.shields.io/badge/GitHub-Amr--Ahmad--dev-181717?style=for-the-badge&logo=github" alt="GitHub">
</a>

<a href="https://www.linkedin.com/">
  <img src="https://img.shields.io/badge/LinkedIn-Connect-0A66C2?style=for-the-badge&logo=linkedin" alt="LinkedIn">
</a>

<a href="mailto:amrahmadsalah@gmail.com">
  <img src="https://img.shields.io/badge/Email-amrahmadsalah%40gmail.com-EA4335?style=for-the-badge&logo=gmail&logoColor=white" alt="Email">
</a>

<br><br>

<strong>Python • Backend Development • Web Applications • Databases • Automation • Data Analysis</strong>

</p>

---

<p align="center">
  <sub>Built and continuously developed by Amr Ahmad as part of my journey in Computer Science and software development.</sub>
</p>
