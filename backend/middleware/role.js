// backend/middleware/role.js

const checkRole = (roles) => {
  return (req, res, next) => {
    // 🚀 Stakeholder Logic: Checks if the user's role (admin, driver, passenger) 
    // from the token matches the allowed roles for this route.
    if (!req.user || !roles.includes(req.user.role)) {
      return res.status(403).json({ 
        message: `Forbidden: This area is restricted to ${roles.join(' or ')} only.` 
      });
    }
    next();
  };
};

module.exports = checkRole;
