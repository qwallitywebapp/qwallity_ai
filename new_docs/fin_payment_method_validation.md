# Payment Method Fields and Database  
- **Credit Card Fields:**  
  - Card Number: Numbers only.  
  - Expiry Date: Date format.  
  - Card CVV: Exactly 3 numbers.  
- **Cash Option:**  
  - If Cash is selected, Card Number, Expiry, and CVV are saved as NULL.  
- **Database Tracking:** Data is added to `Users` and `User_Payments` tables.  
