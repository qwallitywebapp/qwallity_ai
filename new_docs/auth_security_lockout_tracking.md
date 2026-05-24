# Security, Lockout, and Tracking  
- **Invalid Login:** Shows message “Username or password is incorrect”.  
- **Account Lockout:** System blocks the account after 6 failed login attempts.  
- **Login Tracking Table (user_login_history):**  
  - id: INT, PK, Not Null.  
  - login_date: datetime.  
  - logout_date: datetime (Null until logout or timeout).  
  - user_id: INT, Foreign Key.  
- **Session Termination:** Logout date is populated upon manual logout or configurable session timeout.  
